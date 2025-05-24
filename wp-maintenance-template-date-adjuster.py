import pywikibot
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# --- НАСТРОЙКИ СЦЕНАРИЕВ ОБРАБОТКИ ---
PROCESSING_CONFIGS = [
    {
        "category_name": "Категория:Википедия:Статьи без ссылок на источники с октября 2024 года",
        "main_template_to_update": "Нет источников", # Имя шаблона, который обновляем
        "main_template_for_summary": "[[ш:Нет источников]]", # Как шаблон отображается в сводке
        "bot_name": "MBHbot",
        "replacement_date": datetime(2024, 10, 19),
        "rq_cutoff_date": datetime(2024, 10, 19), # Дата до которой ищем rq
        "rq_params_list": ["sources", "source"], # Параметры в rq
    },
    {
        "category_name": "Категория:Википедия:Статьи без ссылок на источники с июня 2018 года",
        "main_template_to_update": "Нет источников",
        "main_template_for_summary": "[[ш:Нет источников]]",
        "bot_name": "AbiyoyoBot",
        "replacement_date": datetime(2018, 6, 20),
        "rq_cutoff_date": datetime(2018, 6, 20),
        "rq_params_list": ["sources", "source"], # Предполагаем те же параметры, уточните если нужно
    },
]
# --- КОНЕЦ НАСТРОЕК ---

def get_template_redirects(site: pywikibot.Site, template_name: str) -> Dict[str, str]:
    """
    Получает все редиректы для заданного шаблона.
    
    Args:
        site (pywikibot.Site): Объект сайта Wikipedia
        template_name (str): Название шаблона
    
    Returns:
        Dict[str, str]: Словарь {название_редиректа: основное_название}
    """
    redirects = {}
    template_page = pywikibot.Page(site, f"Шаблон:{template_name}")
    
    try:
        # Получаем все редиректы на этот шаблон
        for redirect in template_page.redirects():
            # Убираем префикс "Шаблон:" из названия
            redirect_name = redirect.title(with_ns=False)
            redirects[redirect_name] = template_name
    except pywikibot.exceptions.Error as e:
        print(f"Ошибка при получении редиректов для шаблона {template_name}: {e}")
    
    return redirects

def build_template_pattern(template_name: str) -> str:
    """
    Создаёт регулярное выражение для поиска шаблона с учётом пробелов в имени.
    """
    name_chars = list(template_name)
    first_letter = f'[{name_chars[0].upper()}{name_chars[0].lower()}]'
    rest_of_name = ''
    for c in name_chars[1:]:
        if c == ' ':
            rest_of_name += r'\s+'
        else:
            rest_of_name += f'\\s*{re.escape(c)}'
    return r'\{\{\s*' + first_letter + rest_of_name + r'\s*(?:\|[^}]*?)?\s*\}\}'

def find_rq_sources_date(page: pywikibot.Page, rq_cutoff_date: datetime, rq_params_list: List[str]) -> Optional[Tuple[str, str, str]]:
    """
    Ищет дату добавления указанных параметров в шаблоне rq до указанной даты.
    
    Args:
        page (pywikibot.Page): Объект страницы
        rq_cutoff_date (datetime): Дата отсечки (поиск до этой даты, не включая ее)
        rq_params_list (List[str]): Список параметров для поиска в шаблоне rq (например, ["sources", "source"])

    Returns:
        Optional[Tuple[str, str, str]]: (ISO дата, ID ревизии, найденный параметр) или None, если не найдено
    """
    
    def get_rq_params(text: str, params_to_find: List[str]) -> Optional[str]:
        if not params_to_find:
            return None
        # Экранируем параметры для использования в регулярном выражении
        escaped_params = [re.escape(p) for p in params_to_find]
        # Создаем группу ИЛИ для параметров: (param1|param2|...)
        params_pattern_group = '|'.join(escaped_params)
        
        pattern = r'{{\s*[Rr]q\s*\|[^}]*?(' + params_pattern_group + r')[^}]*}}'
        match = re.search(pattern, text, re.IGNORECASE)
        if not match:
            return None
            
        # match.group(1) вернет найденный параметр (например, "sources" или "source")
        return match.group(1).lower() # Возвращаем найденный параметр в нижнем регистре
    
    try:
        for rev in page.revisions(content=True, reverse=True):
            if 'text' not in rev or rev['text'] is None:
                continue
                
            timestamp = rev['timestamp']
            # Дата должна быть строго до rq_cutoff_date
            if timestamp.date() >= rq_cutoff_date.date():
                continue
                
            param_found = get_rq_params(rev['text'], rq_params_list)
            if param_found:
                return (
                    timestamp.strftime("%Y-%m-%d"),
                    str(rev['revid']),
                    param_found
                )
                
    except Exception as e:
        print(f"Ошибка при получении истории ревизий для поиска параметров {rq_params_list}: {e}")
    
    return None

def find_replacement_revision(page: pywikibot.Page, bot_name: str, target_date_dt: datetime) -> Optional[str]:
    """
    Ищет ID ревизии, где указанный бот сделал правку в указанную дату.
    Args:
        page (pywikibot.Page): Объект страницы
        bot_name (str): Имя пользователя бота
        target_date_dt (datetime): Целевая дата для поиска ревизии
    Returns:
        Optional[str]: ID ревизии или None, если не найдено
    """
    try:
        for rev in page.revisions(reverse=True): # Просматриваем от старых к новым, чтобы найти первую правку в этот день
            if rev['user'] == bot_name and rev['timestamp'].date() == target_date_dt.date():
                return str(rev['revid'])
    except Exception as e:
        print(f"Ошибка при поиске ревизии замены ботом {bot_name}: {e}")
    return None

def update_no_sources_template(text: str, template_redirects: Dict[str, str], iso_date: str) -> str:
    """
    Обновляет шаблон Нет источников и его редиректы, добавляя или обновляя дату.
    """
    def replacer(match):
        template = match.group(0)
        inner = template[2:-2].strip()
        parts = [p.strip() for p in inner.split('|')]
        
        template_name = parts[0].strip()
        main_template = "Нет источников"  # Изменено
        
        # Сохраняем регистр первой буквы
        is_first_upper = template_name[0].isupper()
        formatted_main_template = (
            main_template[0].upper() + main_template[1:]
            if is_first_upper
            else main_template[0].lower() + main_template[1:]
        )

        # Обрабатываем параметры
        new_params = []
        date_added = False
        if len(parts) > 1:
            for param in parts[1:]:
                param = param.strip()
                if param.startswith(('date=', 'дата=')):
                    new_params.append(f'дата={iso_date}')
                    date_added = True
                else:
                    new_params.append(param)
        
        if not date_added:
            new_params.insert(0, f'дата={iso_date}')
            
        return f"{{{{{formatted_main_template} |{('|'.join(new_params)).strip()}}}}}"

    new_text = text
    for template_name in template_redirects:
        pattern = build_template_pattern(template_name)
        new_text = re.sub(pattern, replacer, new_text, flags=re.IGNORECASE)
    
    return new_text

def count_no_sources_templates(text: str, template_redirects: Dict[str, str]) -> int:
    """
    Подсчитывает количество шаблонов Нет источников и его редиректов в тексте.
    """
    count = 0
    for template_name in template_redirects:
        pattern = build_template_pattern(template_name)
        count += len(re.findall(pattern, text, re.IGNORECASE))
    return count

def process_articles(site: pywikibot.Site, 
                     no_sources_redirects: Dict[str, str], 
                     category_name: str,
                     main_template_name_for_summary: str, # для формирования корректной сводки, например "[[ш:Нет источников]]"
                     bot_name: str, 
                     replacement_date: datetime, 
                     rq_cutoff_date: datetime, 
                     rq_params_list: List[str]):
    """
    Обрабатывает статьи из указанной категории и обновляет шаблоны согласно конфигурации.
    """
    category = pywikibot.Category(site, category_name)
    print(f"\n--- Начало обработки категории: {category_name} ---")
    
    for page in category.articles():
        print(f"\nОбработка статьи: {page.title()}")
        
        try:
            # Проверяем количество шаблонов (например, Нет источников)
            # TODO: Если main_template_name может меняться, то count_no_sources_templates и update_no_sources_template
            # также должны его принимать или быть более общими.
            if count_no_sources_templates(page.text, no_sources_redirects) > 1:
                print(f"Пропускаем: в статье более одного шаблона типа '{main_template_name_for_summary}'")
                continue
            
            # Ищем дату установки шаблона rq с указанными параметрами
            rq_info = find_rq_sources_date(page, rq_cutoff_date, rq_params_list)
            if not rq_info:
                print(f"Не найдена дата установки шаблона rq с параметрами {rq_params_list} до {rq_cutoff_date.strftime('%Y-%m-%d')}")
                continue
                
            iso_date, revid, param_found = rq_info
            
            # Ищем ревизию замены шаблона указанным ботом
            replacement_revid = find_replacement_revision(page, bot_name, replacement_date)
            
            if not replacement_revid:
                print(f"Пропускаем: не найдена ревизия замены ботом {bot_name} от {replacement_date.strftime('%Y-%m-%d')}")
                continue
            
            # Обновляем шаблон
            # TODO: Аналогично count_no_sources_templates, если main_template_name меняется
            new_text = update_no_sources_template(page.text, no_sources_redirects, iso_date)
            
            if new_text != page.text:
                page.text = new_text
                summary = (
                    f"Уточнение даты установки {main_template_name_for_summary}: "
                    f"[[Special:Diff/{revid}|{iso_date}]] "
                    f"(до [[Special:Diff/{replacement_revid}|{replacement_date.strftime('%d.%m.%Y')}]] [[ш:Rq]] с параметром {param_found})"
                )
                page.save(summary=summary, minor=True)
                print(f"Обновлено: добавлена дата {iso_date}")
            else:
                print("Шаблон уже содержит правильную дату или не требует обновления")
                
        except pywikibot.exceptions.Error as e:
            print(f"Ошибка при обработке статьи {page.title()}: {e}")
    print(f"--- Завершение обработки категории: {category_name} ---")

def main():
    """
    Основная функция программы.
    """
    site = pywikibot.Site('ru', 'wikipedia')
    site.login()

    # TODO: Если main_template_to_update может отличаться для разных конфигураций,
    # получение редиректов нужно будет перенести внутрь цикла по конфигурациям
    # или сделать более умную логику для сбора всех необходимых редиректов заранее.
    # Пока предполагаем, что основной обновляемый шаблон ("Нет источников") общий.
    
    # Собираем все уникальные главные шаблоны из конфигураций
    unique_main_templates = list(set(config["main_template_to_update"] for config in PROCESSING_CONFIGS))
    
    all_redirects = {}
    for template_name in unique_main_templates:
        print(f"Получение редиректов для шаблона: {template_name}")
        redirects = get_template_redirects(site, template_name)
        all_redirects.update(redirects)
        # Добавляем сам главный шаблон в редиректы, чтобы он тоже обрабатывался build_template_pattern
        if template_name not in all_redirects:
             all_redirects[template_name] = template_name

    if not all_redirects:
        print("Не удалось получить редиректы для указанных шаблонов. Проверьте имена шаблонов в конфигурации.")
        return

    for config in PROCESSING_CONFIGS:
        print(f"\n===== Запуск обработки для конфигурации: {config['category_name']} =====")
        process_articles(
            site=site, 
            no_sources_redirects=all_redirects, # Передаем все собранные редиректы
            category_name=config["category_name"],
            main_template_name_for_summary=config["main_template_for_summary"],
            bot_name=config["bot_name"],
            replacement_date=config["replacement_date"],
            rq_cutoff_date=config["rq_cutoff_date"],
            rq_params_list=config["rq_params_list"]
        )
    
    print("\n===== Все конфигурации обработаны =====")

if __name__ == "__main__":
    main()