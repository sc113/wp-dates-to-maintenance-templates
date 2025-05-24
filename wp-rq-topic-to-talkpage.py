# -*- coding: utf-8 -*-
import pywikibot
import re
import mwparserfromhell
import json
import time
from typing import Dict, List, Set, Tuple, Optional
from pywikibot import exceptions as pwb_exceptions # Добавлено для QuitKeyboardInterrupt

# --- CONFIGURATION ---
TARGET_CATEGORY = "Категория:Википедия:Статьи с некорректным использованием шаблона rq"
PROJECT_TEMPLATE_REDIRECT_CACHE_FILE = "project_template_redirects_cache.json"
DEBUG_ARTICLE = ""  # Для отладки конкретной статьи, например "Название статьи"
AUTOSAVE = False # Автоматическое сохранение

# Компактная карта тем и их алиасов к шаблонам проектов или 'skip'
# Ключи - кортежи алиасов темы (все в нижнем регистре)
COMPACT_TOPIC_TO_PROJECT_TEMPLATE_MAP = {
    ('architecture', 'архитектура'): 'Статья проекта Архитектура',
    ('art', 'искусство'): 'Статья проекта Искусство',
    ('astronomy', 'астрономия'): 'Статья проекта Астрономия',
    ('automanufacturer', 'автопроизводитель', 'autotech', 'автотехника', 'auto', 'авто', 'автомобиль'): 'Статья проекта Автомобиль',
    ('biology', 'биология'): 'Статья проекта Биология',
    ('chemistry', 'химия'): 'Статья проекта Химия',
    ('cinema', 'кино'): 'Статья проекта Кино',
    ('comics', 'комиксы'): 'Статья проекта Комиксы',
    ('pharmacology', 'drug', 'фармакология'): 'Статья проекта Фармация',
    ('economics', 'экономика'): 'Статья проекта Экономика',
    ('education', 'образование'): 'Статья проекта Образование',
    ('entertainment', 'развлечения'): 'skip',
    ('games', 'игры', 'videogames', 'компьютерные игры'): 'Статья проекта Компьютерные игры',
    ('geography', 'география'): 'skip',
    ('geology', 'геология'): 'Статья проекта Геология',
    ('history', 'история'): 'Статья проекта История',
    ('it', 'comp', 'computers', 'ит'): 'Статья проекта Информационные технологии',
    ('law', 'legal', 'право'): 'Статья проекта Право',
    ('linguistics', 'лингвистика'): 'Статья проекта Лингвистика',
    ('literature', 'литература'): 'Статья проекта Литература',
    ('logic', 'логика'): 'Статья проекта Логика',
    ('math', 'математика'): 'Статья проекта Математика',
    ('medicine', 'медицина'): 'Статья проекта Медицина',
    ('music', 'музыка'): 'Статья проекта Музыка',
    ('navy', 'флот'): 'Статья проекта Адмиралтейство',
    ('philosophy', 'философия'): 'Статья проекта Философия',
    ('physics', 'физика'): 'Статья проекта Физика',
    ('politics', 'политика'): 'Статья проекта Политика',
    ('psychiatry', 'психиатрия', 'psychology', 'психология'): 'Статья проекта Психология и психиатрия',
    ('religion', 'религия'): 'skip',
    ('sociology', 'социология'): 'Статья проекта Социология',
    ('sport', 'спорт'): 'Статья проекта Спорт',
    ('statistics', 'статистика'): 'Статья проекта Статистика',
    ('technology', 'техника'): 'skip',
    ('telecommunication', 'телекоммуникации'): 'skip',
    ('theatre', 'theater', 'театр'): 'Статья проекта Театр',
    ('transport', 'транспорт'): 'skip',
}

# Словарь эквивалентов: если на СО есть КЛЮЧ, это равносильно наличию ЗНАЧЕНИЯ (которое мы бы поставили)
PROJECT_EQUIVALENTS_ON_TALK_PAGE = {
    'Статья проекта Классическая музыка': 'Статья проекта Музыка',
    'Статья проекта Энтомология': 'Статья проекта Биология',
    'Статья проекта Ботаника': 'Статья проекта Биология',
}

# Шаблоны, которые мы ищем как "Статья проекта" на СО
PROJECT_TEMPLATE_PREFIX = "Статья проекта"
# --- END CONFIGURATION ---

# --- UTILITY FUNCTIONS ---
def print_debug(message: str) -> None:
    print(message) # Для этого скрипта отладка всегда включена

def get_site() -> pywikibot.Site:
    site = pywikibot.Site('ru', 'wikipedia')
    site.login()
    return site

def compare_template_names(name1: str, name2: str) -> bool:
    """
    Compares template names similar to MediaWiki link rules:
    - First letter is case-insensitive.
    - The rest of the name is case-sensitive.
    - Spaces and underscores are treated as equivalent and normalized to a single space.
    """
    n1 = ' '.join(name1.replace('_', ' ').split())
    n2 = ' '.join(name2.replace('_', ' ').split())

    if not n1 or not n2:
        return n1 == n2

    if n1[0].lower() != n2[0].lower():
        return False

    if len(n1) > 1 and len(n2) > 1: # Only compare suffixes if both names have them
        if n1[1:] != n2[1:]:
            return False
    elif len(n1) != len(n2): # If one has a suffix and the other doesn't
        return False
        
    return True

def load_json_cache(filename: str) -> Dict:
    """Загружает кэш из JSON-файла."""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            cache = json.load(f)
            print_debug(f"    💾 Кэш успешно загружен из {filename}.")
            return cache
    except FileNotFoundError:
        print_debug(f"    ℹ️ Файл кэша {filename} не найден. Будет создан новый.")
        return {}
    except json.JSONDecodeError:
        print_debug(f"    ⚠️ Ошибка декодирования JSON из файла {filename}. Будет создан новый кэш.")
        return {}

def save_json_cache(filename: str, cache_data: Dict) -> None:
    """Сохраняет кэш в JSON-файл."""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=4)
            print_debug(f"    💾 Кэш успешно сохранен в {filename}.")
    except IOError:
        print_debug(f"    ⚠️ Ошибка при сохранении кэша в файл {filename}.")

def get_template_redirects(site: pywikibot.Site, template_name: str) -> Dict[str, str]:
    """
    Получает все редиректы для заданного шаблона.
    Возвращает словарь {название_редиректа_нормализованное: основное_название_оригинальное}.
    """
    redirects: Dict[str, str] = {}
    # Убираем префикс "Шаблон:", если он есть, для основного поиска
    if template_name.lower().startswith("шаблон:"):
        template_name_core = template_name[len("шаблон:"):]
    else:
        template_name_core = template_name
        
    template_page = pywikibot.Page(site, f"Шаблон:{template_name_core}")
    main_name_original_case = template_name_core # По умолчанию, если это не редирект

    try:
        if template_page.isRedirectPage():
            target = template_page.getRedirectTarget()
            main_name_original_case = target.title(with_ns=False)
            # Добавляем сам редирект (исходное имя) в словарь
            redirects[normalize_template_name_for_comparison(template_name_core)] = main_name_original_case
            template_page = target # Теперь работаем с целевой страницей
        else:
            # Если это не редирект, то это основной шаблон. main_name_original_case уже установлено.
            pass # main_name_original_case уже правильное

        # Добавляем сам основной шаблон (или цель редиректа) в словарь
        redirects[normalize_template_name_for_comparison(main_name_original_case)] = main_name_original_case
        
        # Получаем все редиректы на этот шаблон (или на цель редиректа)
        for redirect in template_page.redirects(namespaces=site.namespaces.TEMPLATE):
            redirect_title_no_ns = redirect.title(with_ns=False)
            redirects[normalize_template_name_for_comparison(redirect_title_no_ns)] = main_name_original_case
            
    except pywikibot.exceptions.Error as e:
        print_debug(f"    ⚠️ Ошибка при получении редиректов для шаблона {template_name_core}: {e}")
    
    return redirects

def normalize_template_name_for_comparison(name: str) -> str:
    """Нормализует имя шаблона для сравнения: нижний регистр, пробелы вместо подчеркиваний."""
    return ' '.join(name.lower().replace('_', ' ').split())

def get_all_project_template_redirects(site: pywikibot.Site) -> Dict[str, Dict[str, str]]:
    """
    Собирает редиректы для всех шаблонов проектов из COMPACT_TOPIC_TO_PROJECT_TEMPLATE_MAP 
    и для ключей и значений из PROJECT_EQUIVALENTS_ON_TALK_PAGE.
    Обновляет кэш, если в конфигурации появились новые шаблоны.
    Возвращает словарь: { 'оригинальное_имя_шаблона_проекта_или_эквивалента': { 'нормализованный_редирект': 'оригинальное_имя_этого_шаблона' } }
    """
    global PROJECT_TEMPLATE_REDIRECT_CACHE_FILE
    
    cached_redirects = load_json_cache(PROJECT_TEMPLATE_REDIRECT_CACHE_FILE)
    
    unique_templates_to_ensure_in_cache: Set[str] = set()
    # Добавляем шаблоны, которые мы можем захотеть поставить (значения из COMPACT_TOPIC_TO_PROJECT_TEMPLATE_MAP)
    for template_name in COMPACT_TOPIC_TO_PROJECT_TEMPLATE_MAP.values():
        if template_name != 'skip':
            unique_templates_to_ensure_in_cache.add(template_name)
    # Добавляем шаблоны, которые могут быть эквивалентами на СО (ключи из PROJECT_EQUIVALENTS_ON_TALK_PAGE)
    for template_name in PROJECT_EQUIVALENTS_ON_TALK_PAGE.keys():
        unique_templates_to_ensure_in_cache.add(template_name)
    # Добавляем также и значения из PROJECT_EQUIVALENTS_ON_TALK_PAGE, так как для них тоже могут понадобиться редиректы,
    # если они сами по себе являются целью (например, "Статья проекта Музыка" в вашем примере)
    for template_name in PROJECT_EQUIVALENTS_ON_TALK_PAGE.values():
        unique_templates_to_ensure_in_cache.add(template_name)

    templates_to_fetch_now: Set[str] = set()
    if not cached_redirects:
        print_debug("    🔎 Кэш редиректов не найден или пуст. Будет произведен полный сбор редиректов.")
        templates_to_fetch_now = unique_templates_to_ensure_in_cache.copy()
    else:
        print_debug("    ♻️  Редиректы шаблонов проектов загружены из кэша. Проверка на полноту...")
        for template_name_original in unique_templates_to_ensure_in_cache:
            if template_name_original not in cached_redirects:
                templates_to_fetch_now.add(template_name_original)
        
        if templates_to_fetch_now:
            print_debug(f"    ℹ️ Обнаружены новые/отсутствующие шаблоны в кэше для: {len(templates_to_fetch_now)} элемент(ов) ({ ', '.join(list(templates_to_fetch_now)[:3]) }{ ' и др.' if len(templates_to_fetch_now) > 3 else '' }). Будут загружены их редиректы.")
        else:
            print_debug("    ✅ Кэш полный. Используем существующий кэш.")
            return cached_redirects # Кэш существует и полон

    # Если мы здесь, то либо кэш был пуст, либо он был неполным.
    # `templates_to_fetch_now` содержит шаблоны, для которых нужно получить редиректы.
    # `final_redirects` будет содержать объединенные данные.
    final_redirects: Dict[str, Dict[str, str]] = cached_redirects.copy() if cached_redirects else {}
    cache_was_updated = False

    if not templates_to_fetch_now and not final_redirects: # Если кэш был пуст и нечего загружать (маловероятно)
        print_debug("    ⚠️ Нет шаблонов для загрузки редиректов.")
        return {}

    if templates_to_fetch_now:
        print_debug(f"    🔎 Загрузка редиректов для {len(templates_to_fetch_now)} шаблон(а/ов)...")
        for i, template_name_original in enumerate(list(templates_to_fetch_now)):
            print_debug(f"        ({i+1}/{len(templates_to_fetch_now)}) Получение редиректов для: Шаблон:{template_name_original}")
            redirects_for_one = get_template_redirects(site, template_name_original) 
            
            # Добавляем или обновляем данные в final_redirects
            if template_name_original not in final_redirects:
                final_redirects[template_name_original] = {}

            newly_added_redirects_for_this_template = False
            for norm_redirect, main_original_name_from_func in redirects_for_one.items():
                # main_original_name_from_func должен быть равен template_name_original, если get_template_redirects работает как ожидается
                # для наших целей, мы хотим, чтобы значение было именно template_name_original (для которого искали редиректы)
                if norm_redirect not in final_redirects[template_name_original] or \
                   final_redirects[template_name_original][norm_redirect] != template_name_original:
                    final_redirects[template_name_original][norm_redirect] = template_name_original 
                    newly_added_redirects_for_this_template = True
                if norm_redirect != normalize_template_name_for_comparison(template_name_original) and newly_added_redirects_for_this_template:
                    print_debug(f"            ↪️ Найден и добавлен/обновлен редирект: '{norm_redirect}' -> '{template_name_original}'")
            
            # Добавляем сам главный шаблон (нормализованный) в его же список редиректов, если его еще нет
            normalized_main_name = normalize_template_name_for_comparison(template_name_original)
            if normalized_main_name not in final_redirects[template_name_original] or \
               final_redirects[template_name_original][normalized_main_name] != template_name_original:
                final_redirects[template_name_original][normalized_main_name] = template_name_original
                newly_added_redirects_for_this_template = True
            
            if newly_added_redirects_for_this_template:
                cache_was_updated = True
    
    # Сохраняем кэш только если он был обновлен (или если его не было и мы его создали)
    if cache_was_updated or not cached_redirects: # Если кэша не было, templates_to_fetch_now не будет пустым (если есть конфиг)
        save_json_cache(PROJECT_TEMPLATE_REDIRECT_CACHE_FILE, final_redirects)
    
    return final_redirects

# --- MAIN PROCESSING LOGIC ---

def check_rq_conditions(template: mwparserfromhell.nodes.Template) -> Optional[Tuple[str, str]]:
    """
    Проверяет, соответствует ли шаблон Rq заданным условиям.
    Возвращает кортеж (значение_параметра_topic, строка_шаблона_нет_иллюстрации_с_параметрами),
    если условия выполнены, иначе None.
    Условия:
    1. Только один именованный параметр 'topic'.
    2. Только один неименованный параметр.
    3. Неименованный параметр (после strip) является в точности шаблоном {{нет иллюстрации}} (или его редиректом),
       возможно с его собственными параметрами.
    """
    named_params_map: Dict[str, mwparserfromhell.wikicode.Wikicode] = {} # name_str -> value_wikicode
    unnamed_param_values: List[mwparserfromhell.wikicode.Wikicode] = []

    for param in template.params:
        if param.showkey: # Именованный параметр
            named_params_map[str(param.name).strip().lower()] = param.value
        else: # Неименованный параметр
            unnamed_param_values.append(param.value)

    if not (len(named_params_map) == 1 and 'topic' in named_params_map and len(unnamed_param_values) == 1):
        return None # Не выполнены условия по количеству/имени параметров

    topic_value_str = str(named_params_map['topic']).strip() # topic всегда один, его значение текстовое
    wikicode_of_unnamed_param = unnamed_param_values[0]
    
    try:
        inner_templates = wikicode_of_unnamed_param.filter_templates()

        if len(inner_templates) == 1:
            inner_template_node = inner_templates[0] # mwparserfromhell.nodes.Template
            
            # Проверяем, что неименованный параметр состоит ТОЛЬКО из этого шаблона
            # (с учетом возможных пробелов вокруг самого параметра).
            if str(wikicode_of_unnamed_param).strip() == str(inner_template_node): # Сравниваем строковые представления
                inner_template_name = str(inner_template_node.name).strip()
                if compare_template_names(inner_template_name, "нет иллюстрации"):
                    # Условия выполнены!
                    return topic_value_str, str(inner_template_node) # Возвращаем topic и строку шаблона "нет иллюстрации"
    except Exception as e:
        print_debug(f"        ⚠️ Ошибка при анализе неименованного параметра в Rq: {e}")
        # Пропускаем до return None в конце функции
        
    return None # Условия по внутреннему шаблону не выполнены или была ошибка

def process_article(page: pywikibot.Page, site: pywikibot.Site, project_redirects_map: Dict[str, Dict[str, str]]):
    """
    Обрабатывает одну статью.
    project_redirects_map: { 'оригинальное_имя_шаблона_проекта': { 'нормализованный_редирект': 'оригинальное_имя_шаблона_проекта' } }
    """
    print_debug(f"--- Обработка статьи: {page.title()} ---")
    text = page.text
    wikicode = mwparserfromhell.parse(text)
    made_changes_to_article = False
    summary_parts_article = []

    # Ищем шаблон Rq
    for template in wikicode.filter_templates():
        # Используем compare_template_names для сравнения с "Rq" и его редиректами (если они есть)
        # Для простоты пока ищем только "Rq" с разным регистром.
        if not compare_template_names(str(template.name).strip(), "Rq"):
            continue

        print_debug(f"    🔍 Найден шаблон, похожий на Rq: {template.name}")
        
        # check_rq_conditions теперь возвращает кортеж (topic_value, net_illyustratsii_template_str)
        rq_check_result = check_rq_conditions(template) 

        if rq_check_result:
            topic_value_from_rq_conditions, net_illyustratsii_template_str = rq_check_result # Разбираем кортеж
            original_topic_display = topic_value_from_rq_conditions # Сохраняем для отображения
            topic_value_lower = original_topic_display.lower()      # Нормализуем для поиска в карте
            
            project_template_name_from_map = None # Инициализация
            for topic_aliases_tuple, template_or_skip_value in COMPACT_TOPIC_TO_PROJECT_TEMPLATE_MAP.items():
                if topic_value_lower in topic_aliases_tuple:
                    project_template_name_from_map = template_or_skip_value
                    break # Нашли соответствие, выходим из цикла

            if project_template_name_from_map is None:
                print_debug(f"        ⚠️ Неизвестный topic='{original_topic_display}'. Этот экземпляр {{Rq}} будет проигнорирован.")
                continue # Пропускаем этот экземпляр Rq, переходим к следующему шаблону в статье
            
            # ---- НОВОЕ ИЗМЕНЕНИЕ: Проверка на 'skip' ЗДЕСЬ ----
            if project_template_name_from_map == 'skip':
                print_debug(f"        ⏭️ Topic='{original_topic_display}' ({project_template_name_from_map}) указан как 'skip'. Этот {{Rq}} пропускается.")
                continue # Полностью пропускаем этот {{Rq}}, переходим к следующему шаблону в статье
            # ---- КОНЕЦ НОВОГО ИЗМЕНЕНИЯ ----
            
            # Если мы здесь, topic известен и НЕ 'skip'
            print_debug(f"        ✅ Условия для шаблона Rq выполнены. Topic='{original_topic_display}' сопоставлен с '{project_template_name_from_map}'")
            
            replacement_template_str = net_illyustratsii_template_str # Используем фактический шаблон "нет иллюстрации"
            summary_for_article = "" 
            talk_page_status: str = 'NO_ACTION_TAKEN' # Инициализация
            found_template_on_so_name: Optional[str] = None # Для хранения имени шаблона, найденного на СО

            # Обрабатываем СО (уже знаем, что project_template_name_from_map != 'skip')
            print_debug(f"        📋 Требуется добавить/проверить на СО: {{ {{{project_template_name_from_map}}} }}")
            talk_page = page.toggleTalkPage()
            talk_page_status, found_template_on_so_name = process_talk_page(talk_page, site, project_template_name_from_map, project_redirects_map, page.title(), original_topic_display)

            # Формируем описание для изменения в основной статье
            # project_template_name_from_map здесь точно не 'skip' и не None
            if talk_page_status == 'ALREADY_EXISTED_EQUIVALENT':
                if found_template_on_so_name:
                    summary_for_article = f"Раскрытие [[ш:Rq]] с единственным [[ш:Нет иллюстрации]], topic={original_topic_display} (отслеживание через [[ш:{found_template_on_so_name}]] на СО)"
                else: # На случай если found_template_on_so_name почему-то None, хотя не должен быть при этом статусе
                    summary_for_article = f"Раскрытие [[ш:Rq]] с единственным [[ш:Нет иллюстрации]], topic={original_topic_display} (шаблон этого или более точного проекта уже есть на СО)" 
            else: # ADDED_SUCCESSFULLY или NO_ACTION_TAKEN (если СО не изменилась)
                summary_for_article = f"Раскрытие [[ш:Rq]] с единственным [[ш:Нет иллюстрации]], topic={original_topic_display} заменён на [[ш:{project_template_name_from_map}]] на СО"
            
            try:
                wikicode.replace(template, replacement_template_str)
                made_changes_to_article = True 
                summary_parts_article.append(summary_for_article) 
                print_debug(f"        🔄 Шаблон Rq (topic: {original_topic_display}) будет заменен на: {replacement_template_str}")
                
                # Мы обрабатываем только первый подходящий {{Rq}} в статье за один вызов process_article
                break 
            except Exception as e:
                print_debug(f"        ❌ Ошибка при замене шаблона Rq в основной статье: {e}")
                wikicode = mwparserfromhell.parse(page.text) 
                made_changes_to_article = False
                summary_parts_article = []
                break
        else:
            print_debug(f"        ❌ Условия для шаблона Rq не выполнены.")

    if made_changes_to_article:
        new_text = str(wikicode)
        if new_text != page.text:
            summary = ", ".join(summary_parts_article)
            print_debug(f"    💾 Предлагаемое изменение в статье '{page.title()}'. Описание: {summary}")
            if AUTOSAVE:
                try:
                    page.text = new_text
                    page.save(summary=summary, minor=True)
                    print_debug(f"        ✅ Статья '{page.title()}' сохранена.")
                except Exception as e:
                    print_debug(f"        ❌ Ошибка сохранения статьи '{page.title()}': {e}")
            else:
                pywikibot.showDiff(page.text, new_text)
                choice = pywikibot.input_choice(f"Сохранить изменения в статье '{page.title()}'?", 
                                              [ ('Да', 'y'), ('Нет', 'n'), ('Выход', 'q') ], 
                                              default='N')
                if choice == 'y':
                    try:
                        page.text = new_text
                        page.save(summary=summary, minor=True)
                        print_debug(f"        ✅ Статья '{page.title()}' сохранена.")
                        return 'ADDED_SUCCESSFULLY'
                    except Exception as e:
                        print_debug(f"        ❌ Ошибка сохранения статьи '{page.title()}': {e}")
                else:
                    print_debug(f"        🚫 Изменения в статье '{page.title()}' не сохранены.")
        else:
            print_debug(f"    ℹ️ Изменений в тексте статьи '{page.title()}' не обнаружено после обработки.")
    else:
        print_debug(f"    ℹ️ Для статьи '{page.title()}' не требуется изменений.")


def process_talk_page(talk_page: pywikibot.Page, site: pywikibot.Site, 
                      target_project_template_from_map: str, 
                      all_project_redirects_map: Dict[str, Dict[str, str]],
                      main_article_title: str,
                      topic_value_from_rq: str) -> Tuple[str, Optional[str]]:
    """
    Обрабатывает страницу обсуждения: добавляет шаблон проекта, если необходимо.
    Возвращает статус обработки и имя найденного шаблона на СО (если есть):
    ('ALREADY_EXISTED_EQUIVALENT', 'ИмяНайденногоШаблона'), 
    ('ADDED_SUCCESSFULLY', None), 
    ('NO_ACTION_TAKEN', None).
    all_project_redirects_map: { 'оригинальное_имя_шаблона_проекта_или_эквивалента': { 'нормализованный_редирект': 'оригинальное_имя_этого_шаблона' } }
    target_project_template_from_map: оригинальное имя шаблона, которое мы бы поставили согласно COMPACT_TOPIC_TO_PROJECT_TEMPLATE_MAP.
    topic_value_from_rq: значение параметра topic из шаблона Rq в основной статье.
    """
    print_debug(f"    💬 Обработка СО: {talk_page.title()}")
    
    # 1. Проверяем, есть ли уже наш целевой шаблон (target_project_template_from_map) или его редиректы
    redirects_for_target = all_project_redirects_map.get(target_project_template_from_map, {})
    if not redirects_for_target:
        print_debug(f"        ⚠️ Не найдены редиректы для целевого шаблона '{target_project_template_from_map}'. Это неожиданно. Пропускаем добавление.")
        return 'NO_ACTION_TAKEN', None

    talk_page_exists = talk_page.exists()
    current_talk_text = talk_page.text if talk_page_exists else ""
    
    if talk_page_exists:
        talk_wikicode = mwparserfromhell.parse(current_talk_text)
        for tpl_on_talk_page in talk_wikicode.filter_templates():
            tpl_on_talk_page_name_original = str(tpl_on_talk_page.name).strip() # Сохраняем оригинальное имя
            tpl_on_talk_page_name_norm = normalize_template_name_for_comparison(tpl_on_talk_page_name_original)
            if tpl_on_talk_page_name_norm in redirects_for_target: # Сравниваем с редиректами нашего целевого шаблона
                print_debug(f"        ✅ Целевой шаблон '{target_project_template_from_map}' (через '{tpl_on_talk_page_name_original}') уже есть на СО.")
                return 'ALREADY_EXISTED_EQUIVALENT', tpl_on_talk_page_name_original

        # 2. Если целевого нет, проверяем на наличие эквивалентов
        for equivalent_on_so, maps_to_our_target in PROJECT_EQUIVALENTS_ON_TALK_PAGE.items():
            if maps_to_our_target == target_project_template_from_map:
                # Это эквивалент нашего целевого шаблона. Теперь ищем ЕГО (equivalent_on_so) редиректы на СО.
                redirects_for_equivalent = all_project_redirects_map.get(equivalent_on_so, {})
                if not redirects_for_equivalent:
                    print_debug(f"        ⚠️ Не найдены редиректы для эквивалентного шаблона '{equivalent_on_so}'. Пропускаем эту проверку эквивалента.")
                    continue
                
                # talk_wikicode уже есть, используем его
                for tpl_on_talk_page in talk_wikicode.filter_templates(): # Повторный проход, но теперь ищем equivalent_on_so
                    tpl_on_talk_page_name_original_for_equiv = str(tpl_on_talk_page.name).strip() # Сохраняем оригинальное имя
                    tpl_on_talk_page_name_norm_for_equiv = normalize_template_name_for_comparison(tpl_on_talk_page_name_original_for_equiv)
                    if tpl_on_talk_page_name_norm_for_equiv in redirects_for_equivalent:
                        print_debug(f"        ✅ Эквивалентный шаблон '{equivalent_on_so}' (через '{tpl_on_talk_page_name_original_for_equiv}') уже есть на СО, считается за '{target_project_template_from_map}'.")
                        return 'ALREADY_EXISTED_EQUIVALENT', tpl_on_talk_page_name_original_for_equiv
    
    # Если мы здесь, значит ни целевого, ни его эквивалентов на СО нет.
    # Добавляем наш целевой шаблон (target_project_template_from_map)
    if not talk_page_exists:
        print_debug("        ℹ️ Страница обсуждения не существует. Будет создана.")
        # current_talk_text уже ""

    new_template_text = f"{{{{{target_project_template_from_map}}}}}"
    
    # Ищем другие шаблоны "Статья проекта"
    talk_wikicode_for_insertion = mwparserfromhell.parse(current_talk_text) # Перепарсим для чистоты
    
    last_project_banner_pos = -1
    
    # Ищем позицию последнего шаблона проекта
    # Мы не можем напрямую использовать filter_templates().index() или подобные методы,
    # так как нам нужна позиция в *строковом представлении* для корректной вставки.
    # Вместо этого, найдем все шаблоны и их строковые представления.
    
    existing_project_banners = []
    for node in talk_wikicode_for_insertion.nodes:
        if isinstance(node, mwparserfromhell.nodes.Template):
            if str(node.name).strip().startswith(PROJECT_TEMPLATE_PREFIX):
                existing_project_banners.append(str(node))

    if existing_project_banners:
        last_banner_str = existing_project_banners[-1]
        # Находим последнее вхождение этой строки в тексте
        # Это не идеально, если одинаковые баннеры повторяются, но для СО обычно уникальны или идут подряд
        pos = current_talk_text.rfind(last_banner_str)
        if pos != -1:
            last_project_banner_pos = pos + len(last_banner_str)
            # Вставляем после найденного шаблона, с новой строки
            # Если current_talk_text[last_project_banner_pos] уже \n, то будет два \n. Это нормально.
            # Если нет, то добавится \n.
            new_talk_text = (current_talk_text[:last_project_banner_pos] +
                             "\n" + new_template_text +
                             current_talk_text[last_project_banner_pos:])
            print_debug(f"        ➕ Добавляем шаблон '{target_project_template_from_map}' после существующих баннеров.")
        else: # Не смогли найти строку последнего баннера - странно, но добавим в начало
            new_talk_text = new_template_text + "\n" + current_talk_text
            print_debug(f"        ➕ Добавляем шаблон '{target_project_template_from_map}' в начало СО (не удалось найти позицию после баннеров).")
    else:
        # Нет других шаблонов проекта, добавляем в начало
        new_talk_text = new_template_text + "\n" + current_talk_text
        print_debug(f"        ➕ Добавляем шаблон '{target_project_template_from_map}' в начало СО.")

    # Убираем лишние пробелы/переносы строк в начале/конце, если они появились
    new_talk_text = new_talk_text.strip()

    if new_talk_text != current_talk_text.strip():
        # summary_talk = f"Установка [[ш:{target_project_template_from_map}]] по итогам раскрытия {{Rq|topic={topic_value_from_rq}}} в [[{main_article_title}|основной статье]]"
        summary_talk = f"Установка [[ш:{target_project_template_from_map}]] по итогам раскрытия {{{{Rq|topic={topic_value_from_rq}}}}} в [[{main_article_title}|основной статье]]"
        print_debug(f"    💾 Предлагаемое изменение на СО '{talk_page.title()}'. Описание: {summary_talk}")
        if AUTOSAVE:
            try:
                talk_page.text = new_talk_text
                talk_page.save(summary=summary_talk, minor=True)
                print_debug(f"        ✅ СО '{talk_page.title()}' сохранена.")
                return 'ADDED_SUCCESSFULLY', None
            except Exception as e:
                print_debug(f"        ❌ Ошибка сохранения СО '{talk_page.title()}': {e}")
        else:
            pywikibot.showDiff(current_talk_text, new_talk_text)
            choice = pywikibot.input_choice(f"Сохранить изменения на СО '{talk_page.title()}'?", 
                                          [ ('Да', 'y'), ('Нет', 'n'), ('Выход', 'q') ], 
                                          default='N')
            if choice == 'y':
                try:
                    talk_page.text = new_talk_text
                    talk_page.save(summary=summary_talk, minor=True)
                    print_debug(f"        ✅ СО '{talk_page.title()}' сохранена.")
                    return 'ADDED_SUCCESSFULLY', None
                except Exception as e:
                    print_debug(f"        ❌ Ошибка сохранения СО '{talk_page.title()}': {e}")
            else:
                print_debug(f"        🚫 Изменения на СО '{talk_page.title()}' не сохранены.")
    else:
        print_debug(f"    ℹ️ Изменений в тексте СО '{talk_page.title()}' не требуется.")
    return 'NO_ACTION_TAKEN', None


# --- MAIN FUNCTION ---
def main():
    site = get_site()
    print_debug(f"✅ Вход на {site.sitename} выполнен успешно.")

    # Получаем/кэшируем редиректы для шаблонов проектов
    # all_project_redirects_map: { 'оригинальное_имя_шаблона_проекта': { 'нормализованный_редирект': 'оригинальное_имя_шаблона_проекта' } }
    all_project_redirects_map = get_all_project_template_redirects(site)
    if not all_project_redirects_map:
        print_debug("❌ Не удалось получить редиректы для шаблонов проектов. Завершение работы.")
        return

    if DEBUG_ARTICLE:
        page = pywikibot.Page(site, DEBUG_ARTICLE)
        if page.exists():
            process_article(page, site, all_project_redirects_map)
        else:
            print_debug(f"❌ Отладочная статья '{DEBUG_ARTICLE}' не найдена.")
        return

    category = pywikibot.Category(site, TARGET_CATEGORY)
    articles = list(category.articles()) # Получаем список статей один раз
    
    print_debug(f"\n📚 Найдено {len(articles)} статей в категории '{TARGET_CATEGORY}'.")
    if not articles:
        print_debug("Нет статей для обработки.")
        return

    for i, page in enumerate(articles):
        print_debug(f"\n--- Обработка статьи {i+1}/{len(articles)}: [[{page.title()}]] ---")
        try:
            process_article(page, site, all_project_redirects_map)
        except pwb_exceptions.QuitKeyboardInterrupt:
            print_debug("\n🛑 Обработка прервана пользователем (нажата 'q').")
            break # Выход из цикла for, что приведет к завершению main()
        except Exception as e:
            print_debug(f"💥 КРИТИЧЕСКАЯ ОШИБКА при обработке статьи [[{page.title()}]]: {e}")
            # Можно добавить пропуск или более детальное логирование ошибки
        # Добавим небольшую задержку, чтобы не нагружать сервер слишком сильно
        time.sleep(1) 

    print_debug("\n✅ Обработка завершена.")

if __name__ == "__main__":
    main()
