# -*- coding: utf-8 -*-
import pywikibot
import re
import mwparserfromhell
from datetime import datetime
from typing import Dict, List, Set, Tuple, Optional, Union
import platform
import time
import sys
from difflib import SequenceMatcher
import json

# Конфигурация
CONFIG = {
    'mode': 'rq',  # Режим обработки: 'meta', 'single', 'rq', 'metarq'.
    'search_mode': 2,  # 1 - линейный поиск от последней ревизии, 2 - линейный поиск от первой ревизии, 3 - бинарный поиск от первой ревизии
    'max_revisions': 0,  # Пропускать статьи, если количество ревизий превышает это значение (0 - без ограничений)

    'debug_article': "",  # Название статьи для отладки. Если указано, скрипт обработает только эту статью с логикой, соответствующbим CONFIG['mode'].
    'debug_output': False,  # Включить/выключить отладочный вывод
    'autosave': True,  # Автоматическое сохранение изменений в статьи

    'meta_category': "Категория:Отслеживающие категории:Статьи с шаблонами-сообщениями без указанных дат",
    'single_category': "Категория:Википедия:Статьи, нейтральность которых поставлена под сомнение без указанной даты",
    'rq_category': "Категория:Википедия:Статьи к замене параметров шаблона rq",
}

# Шаблоны, которые нужно обрабатывать с учетом разделов
SECTION_TEMPLATES = [
    'В разделе нет вторичных источников',
    'Глобализировать раздел',
    'Дополнить раздел',
    'Достоверность раздела под сомнением',
    'Неупорядоченный список',
    'Нейтральность раздела под сомнением',
    'Нет источников в разделе',
    'Обновить раздел',
    'Опечатки в разделе',
    'Орисс в разделе',
    'Ориссный раздел неточностей',
    'Перенести раздел',
    'Переработать раздел',
    'Переформировать разделы',
    'Пустой раздел',
    'Разделить раздел',
    'Раздел, требующий дополнительных источников',
    'Сократить раздел',
    'Список фактов',
    'Стиль раздела',
    'Чистить раздел',
]

# Соответствие параметров шаблона Rq и названий шаблонов
RQ_PARAM_TEMPLATES = {
    "birth": "нет даты рождения",
    "birthplace": "нет места рождения",
    "burialplace": "нет места захоронения",
    "cat": "нет категорий",
    "check": "проверить факты",
    "checktranslate": "плохой перевод",
    "cleanup": "переработать",
    "coord": "нет координат",
    "death": "нет даты смерти",
    "deathplace": "нет места смерти",
    "descript": "дополнить раздел",
    "empty": "дописать",
    "global": "глобализировать",
    "grammar": "опечатки",
    "img": "нет иллюстрации",
    "infobox": "нет карточки",
    "isbn": "оформить литературу",
    "linkless": "изолированная статья",
    "neutral": "проверить нейтральность",
    "nolead": "нет преамбулы",
    "notability": "значимость",
    "overlinked": "много внутренних ссылок",
    "part": "нет разделов",
    "patronymic": "отчество",
    "pronun": "нужна транскрипция",
    "recat": "уточнить категории",
    "refless": "нет сносок",
    "renew": "обновить",
    "shortlead": "короткая преамбула",
    "sources": "нет источников",
    "sources-cleanup": "лишняя литература",
    "stress": "нужно ударение",
    "style": "стиль статьи",
    "taxobox": "нет таксобокса",
    "tex": "оформить формулы",
    "translate": "закончить перевод",
    "underlinked": "мало внутренних ссылок",
    "wikify": "плохое оформление",
    "yo": "ёфицировать",
    #Перенаправления
    "dewikify": "много внутренних ссылок",
    "footnotes": "нет сносок",
    "image": "нет иллюстрации",
    "images": "нет иллюстрации",
    "introduction": "нет преамбулы",
    "makeup": "плохое оформление",
    "pre": "короткая преамбула",
    "ref": "нет сносок",
    "source": "нет источников",
    "stub": "дописать",
    "taxbox": "нет таксобокса",
    "обновить": "обновить",
}

# Список параметров шаблона Rq, при наличии которых пропускаем обработку статьи
RQ_SKIP_PARAMS = ["all", "infobox2", "imdb", "fromlang"]

# Глобальный кэш для редиректов самостоятельных шаблонов, используемый при обработке Rq
RQ_STANDALONE_REDIRECT_CACHE: Dict[str, Dict[str, str]] = {}
RQ_STANDALONE_REDIRECT_CACHE_FILE = "rq_standalone_redirects_cache.json"

# Словарь для нормализации значений параметра topic в шаблоне Rq
RQ_TOPIC_NORMALIZATION_MAP: Dict[str, str] = {
    # Канонический : вариант (все в нижнем регистре)
    'architecture': 'architecture', 'архитектура': 'architecture',
    'art': 'art', 'искусство': 'art',
    'astronomy': 'astronomy', 'астрономия': 'astronomy',
    'automanufacturer': 'automanufacturer', 'автопроизводитель': 'automanufacturer',
    'autotech': 'autotech', 'автотехника': 'autotech',
    'auto': 'auto', 'авто': 'auto', 'автомобиль': 'auto',
    'biology': 'biology', 'биология': 'biology',
    'chemistry': 'chemistry', 'химия': 'chemistry',
    'cinema': 'cinema', 'кино': 'cinema',
    'comics': 'comics', 'комиксы': 'comics',
    'pharmacology': 'pharmacology', 'drug': 'pharmacology', 'фармакология': 'pharmacology',
    'economics': 'economics', 'экономика': 'economics',
    'education': 'education', 'образование': 'education',
    'entertainment': 'entertainment', 'развлечения': 'entertainment',
    'games': 'games', 'игры': 'games',
    'geography': 'geography', 'география': 'geography',
    'geology': 'geology', 'геология': 'geology',
    'history': 'history', 'история': 'history',
    'it': 'it', 'comp': 'it', 'computers': 'it', 'ит': 'it',
    'law': 'law', 'legal': 'law', 'право': 'law',
    'linguistics': 'linguistics', 'лингвистика': 'linguistics',
    'literature': 'literature', 'литература': 'literature',
    'logic': 'logic', 'логика': 'logic',
    'math': 'math', 'математика': 'math',
    'medicine': 'medicine', 'медицина': 'medicine',
    'music': 'music', 'музыка': 'music',
    'navy': 'navy', 'флот': 'navy',
    'philosophy': 'philosophy', 'философия': 'philosophy',
    'physics': 'physics', 'физика': 'physics',
    'politics': 'politics', 'политика': 'politics',
    'psychiatry': 'psychiatry', 'психиатрия': 'psychiatry',
    'psychology': 'psychology', 'психология': 'psychology',
    'religion': 'religion', 'религия': 'religion',
    'sociology': 'sociology', 'социология': 'sociology',
    'sport': 'sport', 'спорт': 'sport',
    'statistics': 'statistics', 'статистика': 'statistics',
    'technology': 'technology', 'техника': 'technology',
    'telecommunication': 'telecommunication', 'телекоммуникации': 'telecommunication',
    'theatre': 'theatre', 'theater': 'theatre', 'театр': 'theatre',
    'transport': 'transport', 'транспорт': 'transport',
    'videogames': 'videogames', 'компьютерные игры': 'videogames',
}

def print_debug(message: str) -> None:
    if CONFIG['debug_output']:
        print(message)

def print_article_header(page: pywikibot.Page, creation_date: datetime, revision_count: int,
                        current_article: int, category_articles: int,
                        current_category: int, total_categories: int,
                        processed_articles: int, total_articles: int) -> None:
    print(f"⬜️⬜️⬜️ {page.title()}")
    print(f"    ✏️ Создана: {creation_date.strftime('%Y-%m-%d')}    📝 Всего ревизий: {revision_count}    📊 Прогресс: {current_article}/{category_articles}, категория {current_category}/{total_categories}, всего {processed_articles}/{total_articles}")

def get_revision_info(page: pywikibot.Page) -> Tuple[datetime, int, List[Dict]]:
    print(f"⏳ Начинаем обработку ревизий...")
    revisions = []
    for rev in page.revisions(content=True, reverse=True):
        if not isinstance(rev, dict):
            rev_dict = {
                'revid': rev.revid,
                'timestamp': rev.timestamp,
                'text': rev.text
            }
            revisions.append(rev_dict)
        else:
            revisions.append(rev)
            
    creation_date = revisions[0]['timestamp'] if revisions else datetime.now()
    revision_count = len(revisions)
    return creation_date, revision_count, revisions

def get_normalized_section_name(section_name: str) -> str:
    """
    Нормализует название раздела, удаляя общие вариации, лишние пробелы и вики-разметку
    """
    # Удаляем вики-разметку
    normalized = section_name.replace("'''", "").replace("''", "")
    normalized = normalized.replace("[[", "").replace("]]", "")
    
    # Удаляем общие вариации служебных слов
    common_variations = ['и', 'или', 'а также', 'также']
    normalized = normalized.lower()
    for var in common_variations:
        normalized = normalized.replace(f' {var} ', ' ')
    
    return ' '.join(normalized.split())

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

    if n1[1:] != n2[1:]:
        return False

    return True

def find_sections(wikitext: str) -> List[Tuple[str, int, int]]:
    """
    Находит все разделы и их позиции в тексте.
    Возвращает список кортежей (название_раздела, начальная_позиция, конечная_позиция).
    Вводный раздел (до первого заголовка) определяется как "Вводный раздел".
    """
    sections = []
    current_pos = 0
    
    # Сначала найдем первый заголовок, чтобы определить вводный раздел
    first_section_pos = -1
    for level in range(2, 7):
        equals = "=" * level
        section_start = wikitext.find(f"\n{equals}")
        if section_start != -1 and (first_section_pos == -1 or section_start < first_section_pos):
            first_section_pos = section_start
    
    # Если есть текст до первого заголовка, добавляем его как вводный раздел
    if first_section_pos > 0:
        sections.append(("Вводный раздел", 0, first_section_pos))
    elif first_section_pos == -1:  # Если заголовков нет вообще
        sections.append(("Вводный раздел", 0, len(wikitext)))
        return sections
    
    # Теперь найдем все остальные разделы
    while True:
        next_section = -1
        min_level = 99
        pos = -1
        
        for level in range(2, 7):
            equals = "=" * level
            # section_pattern = f"\n[ ]*{equals}[ ]*" # Удалено, т.к. переменная не используется
            section_start = wikitext.find("\n", current_pos)
            
            while section_start != -1:
                line_start = section_start + 1
                line_end = wikitext.find("\n", line_start)
                if line_end == -1:
                    line_end = len(wikitext)
                
                line = wikitext[line_start:line_end].strip()
                
                # Проверяем, начинается и заканчивается ли строка одинаковым количеством знаков равенства
                if line.startswith(equals) and line.endswith(equals):
                    if pos == -1 or section_start < pos:
                        pos = section_start
                        next_section = section_start
                        min_level = level
                        break
                
                section_start = wikitext.find("\n", section_start + 1)
        
        if next_section == -1:
            break
            
        section_end = wikitext.find("\n", next_section + 1)
        if section_end == -1:
            section_end = len(wikitext)
        
        # Извлекаем и очищаем название раздела
        section_text = wikitext[next_section:section_end]
        section_name = section_text.strip("= \n")
        
        next_section_start = -1
        for level in range(2, 7):
            pattern = f"\n[ ]*{'=' * level} "
            pos = wikitext.find("\n", section_end)
            while pos != -1:
                line_start = pos + 1
                line_end = wikitext.find("\n", line_start)
                if line_end == -1:
                    line_end = len(wikitext)
                
                line = wikitext[line_start:line_end].strip()
                if line.startswith('=' * level) and line.endswith('=' * level):
                    if next_section_start == -1 or pos < next_section_start:
                        next_section_start = pos
                        break
                
                pos = wikitext.find("\n", pos + 1)
        
        if next_section_start == -1:
            next_section_start = len(wikitext)
            
        sections.append((section_name, section_end, next_section_start))
        current_pos = section_end
    
    return sections

def get_section_for_template(wikicode: mwparserfromhell.wikicode.Wikicode, 
                           template: mwparserfromhell.nodes.Template,
                           sections: List[Tuple[str, int, int]]) -> List[str]:
    """
    Определяет, к каким разделам принадлежит шаблон.
    Возвращает список названий разделов.
    """
    found_sections = []
    try:
        template_str = str(template)
        full_text = str(wikicode)
        start = 0
        found_positions = []
        
        # Находим все позиции шаблона в тексте
        while True:
            pos = full_text.find(template_str, start)
            if pos == -1:
                break
            found_positions.append(pos)
            start = pos + len(template_str)  # Изменено: ищем следующее вхождение после конца текущего
        
        # Для каждой найденной позиции определяем раздел
        for pos in found_positions:
            for section_name, start_pos, end_pos in sections:
                if start_pos <= pos < end_pos and section_name not in found_sections:
                    found_sections.append(section_name)
        
        if found_positions and not found_sections:
            print_debug(f"      ℹ️ Шаблон статьи найден на позиции {found_positions[0]}")
        elif not found_positions:
            print_debug(f"      ⚠️ Шаблон не найден в тексте")
    except Exception as e:
        print(f"Ошибка при определении раздела для шаблона: {e}")
    
    return found_sections

def get_section_template_text(sections: List[Tuple[str, int, int]], 
                            wikicode: mwparserfromhell.wikicode.Wikicode,
                            full_text: str,
                            normalized_target: str) -> Optional[str]:
    """Получает текст шаблона из целевого раздела с учетом вариаций названия раздела"""
    for section_name, start, end in sections:
        if get_normalized_section_name(section_name) == normalized_target:
            section_text = full_text[start:end]
            return section_text
    return None

def normalize_section_name(name: str) -> str:
    """Нормализует название раздела для сравнения"""
    # Удаляем спецсимволы
    for char in '«»""\'\'[]()„"':
        name = name.replace(char, '')
    name = name.lower()
    name = ' '.join(name.split())
    return name

def sections_are_similar(name1: str, name2: str) -> bool:
    """
    Проверяет схожесть названий разделов используя алгоритм сравнения последовательностей.
    Учитывает наибольшую общую последовательность символов.
    """
    # Специальная обработка для вводного раздела
    if name1 == "Вводный раздел" or name2 == "Вводный раздел":
        return name1 == name2
        
    # Фильтруем явно мусорные значения
    if any(x in (name1, name2) for x in ('".', '"', ".", "предыстория")):
        return False
        
    name1 = normalize_section_name(name1)
    name2 = normalize_section_name(name2)
    
    # Если названия пустые после нормализации - не сравниваем
    if not name1 or not name2:
        return False
    
    if name1 == name2:
        return True
    
    # Используем SequenceMatcher для сравнения строк
    similarity = SequenceMatcher(None, name1, name2).ratio()
    
    return len(name1) >= 5 and len(name2) >= 4 and similarity >= 0.70

def get_section_history(page: pywikibot.Page, current_section_name: str) -> List[str]:
    """
    Отслеживает историю изменений названия раздела от новых к старым ревизиям.
    Возвращает список исторических названий раздела, начиная с текущего.
    """
    section_names = [current_section_name]
    
    try:
        for rev in page.revisions(content=True, reverse=True):
            if 'text' not in rev or rev['text'] is None:
                continue
                
            text = rev['text']
            sections = find_sections(text)
            
            # Ищем похожий раздел среди всех разделов в этой ревизии
            for section_name, _, _ in sections:
                # Пропускаем уже известные названия
                if section_name in section_names:
                    continue
                
                # Проверяем схожесть названий с последним известным названием
                if sections_are_similar(section_names[-1], section_name):
                    print_debug(f"    🔄 Найдено предыдущее название раздела: «{section_name}»")
                    section_names.append(section_name)  # Добавляем в конец списка
                    break
            
    except Exception as e:
        print(f"Ошибка при получении истории раздела: {e}")
        
    return section_names

def find_first_template_addition_in_section(page: pywikibot.Page, 
                                          section_names: List[str],
                                          template_redirects: Dict[str, Dict[str, str]]) -> Optional[Tuple[str, str, str]]:
    """
    Находит первое появление любого варианта шаблона в любом из исторических названий раздела,
    считая все исторические названия одним и тем же разделом.
    Возвращает кортеж (дата, id_ревизии, название_шаблона) или None.
    """
    cutoff_date = datetime(2025, 1, 1)
    normalized_targets = [get_normalized_section_name(name) for name in section_names]
    
    try:
        # Вместо отслеживания каждого раздела отдельно, отслеживаем общее присутствие
        previous_templates = set()
        
        for rev in page.revisions(content=True, reverse=True):
            timestamp = rev['timestamp']
            if timestamp > cutoff_date:
                continue
                
            if 'text' not in rev or rev['text'] is None:
                continue
                
            current_text = rev['text']
            wikicode = mwparserfromhell.parse(current_text)
            sections = find_sections(current_text)
            
            # Получаем все шаблоны из всех исторических названий раздела в этой ревизии
            current_templates = set()
            for normalized_target in normalized_targets:
                section_text = get_section_template_text(sections, wikicode, current_text, normalized_target)
                if section_text:
                    for template in mwparserfromhell.parse(section_text).filter_templates():
                        template_name = str(template.name).strip().lower()
                        for templates in template_redirects.values():
                            for redirect_name, main_name in templates.items():
                                if template_name == redirect_name.lower():
                                    current_templates.add((template_name, main_name))
            
            # Если находим шаблоны в этой ревизии, но не в предыдущей,
            # это может быть первым добавлением
            if current_templates and not previous_templates:
                template_name, main_name = next(iter(current_templates))
                
                existing_date = None
                for template in wikicode.filter_templates():
                    if str(template.name).strip().lower() == template_name:
                        for param in template.params:
                            param_name = str(param.name).strip().lower()
                            if param_name in ['date', 'дата']:
                                existing_date = str(param.value).strip()
                                break
                        if existing_date:
                            break
                            
                if existing_date and any(x in existing_date.lower() for x in ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря']):
                    return (existing_date, str(rev['revid']), main_name)
                else:
                    return (timestamp.strftime("%Y-%m-%d"), str(rev['revid']), main_name)
            
            previous_templates = current_templates
                        
    except Exception as e:
        print(f"Ошибка при получении истории ревизий: {e}")
        
    return None

def get_input_with_timeout(prompt: str, timeout: int = 5) -> str:
    """
    Получает ввод от пользователя с таймаутом.
    Работает как на Windows, так и на Unix-системах.
    
    Args:
        prompt: Текст приглашения
        timeout: Время ожидания в секундах
    
    Returns:
        str: Введенная строка или пустая строка, если превышен таймаут
    """
    print(prompt, end='', flush=True)
    
    if platform.system() == 'Windows':
        import msvcrt
        start_time = time.time()
        input_str = ''
        
        while True:
            if msvcrt.kbhit():
                char = msvcrt.getwche()
                if char == '\r':
                    print()  # Переход на новую строку
                    break
                input_str += char
            
            if time.time() - start_time > timeout:
                print()  # Переход на новую строку
                return ''
            
            time.sleep(0.1)  # Небольшая задержка чтобы не нагружать процессор
            
        return input_str
    else:
        import select
        import termios
        import tty
        
        # Сохраняем старые настройки терминала
        old_settings = termios.tcgetattr(sys.stdin.fileno())
        try:
            # Устанавливаем новые настройки терминала
            tty.setcbreak(sys.stdin.fileno())
            
            # Ожидаем ввод
            start_time = time.time()
            input_str = ''
            while True:
                # Проверяем, есть ли данные для чтения
                if select.select([sys.stdin], [], [], max(0, timeout - (time.time() - start_time)))[0]:
                    char = sys.stdin.read(1)
                    if char == '\n':
                        print()  # Переход на новую строку
                        break
                    input_str += char
                    print(char, end='', flush=True)
                else:
                    print()  # Переход на новую строку
                    return ''
                
                # Проверяем таймаут
                if time.time() - start_time > timeout:
                    print()  # Переход на новую строку
                    return ''
                    
            return input_str
        finally:
            # Восстанавливаем старые настройки терминала
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)

def load_rq_redirect_cache_from_json(filename: str) -> Dict[str, Dict[str, str]]:
    """Загружает кэш редиректов RQ из JSON-файла."""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            cache = json.load(f)
            print_debug(f"    💾  Кэш редиректов RQ успешно загружен из {filename}.")
            return cache
    except FileNotFoundError:
        print_debug(f"    ℹ️ Файл кэша редиректов RQ {filename} не найден. Будет создан новый.")
        return {}
    except json.JSONDecodeError:
        print_debug(f"    ⚠️ Ошибка декодирования JSON из файла {filename}. Будет создан новый кэш.")
        return {}

def save_rq_redirect_cache_to_json(filename: str, cache_data: Dict[str, Dict[str, str]]) -> None:
    """Сохраняет кэш редиректов RQ в JSON-файл."""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=4)
            print_debug(f"    💾  Кэш редиректов RQ успешно сохранен в {filename}.")
    except IOError:
        print_debug(f"    ⚠️ Ошибка при сохранении кэша редиректов RQ в файл {filename}.")

def get_template_redirects(site: pywikibot.Site, template_name: str, use_rq_specific_cache: bool = False) -> Dict[str, str]:
    """
    Получает все редиректы для заданного шаблона.
    
    Args:
        site (pywikibot.Site): Объект сайта Wikipedia
        template_name (str): Название шаблона
        use_rq_specific_cache (bool): Использовать ли специальный кэш для Rq обработки
    
    Returns:
        Dict[str, str]: Словарь {название_редиректа: основное_название}
    """
    # Если используем кэш и шаблон уже в нем есть
    if use_rq_specific_cache and template_name in RQ_STANDALONE_REDIRECT_CACHE:
        print_debug(f"    ♻️  Редиректы для шаблона '{template_name}' взяты из RQ кэша.")
        return RQ_STANDALONE_REDIRECT_CACHE[template_name]
        
    redirects = {}
    template_page = pywikibot.Page(site, f"Шаблон:{template_name}")
    
    try:
        # Проверяем, является ли страница редиректом
        if template_page.isRedirectPage():
            target = template_page.getRedirectTarget()
            main_name = target.title(with_ns=False)
            redirects[template_name] = main_name
            template_page = target
        else:
            # Если это не редирект, то это основной шаблон
            redirects[template_name] = template_name
        
        # Получаем все редиректы на этот шаблон
        for redirect in template_page.redirects():
            # Убираем префикс "Шаблон:" из названия
            redirect_name = redirect.title(with_ns=False)
            redirects[redirect_name] = template_name if not template_page.isRedirectPage() else main_name
            
    except pywikibot.exceptions.Error as e:
        print(f"Ошибка при получении редиректов для шаблона {template_name}: {e}")
    
    # Если используем кэш, сохраняем результат
    if use_rq_specific_cache:
        RQ_STANDALONE_REDIRECT_CACHE[template_name] = redirects
        print_debug(f"    💾  Редиректы для шаблона '{template_name}' сохранены в RQ кэш.")
        save_rq_redirect_cache_to_json(RQ_STANDALONE_REDIRECT_CACHE_FILE, RQ_STANDALONE_REDIRECT_CACHE)
        
    return redirects

def build_template_pattern(template_name: str) -> str:
    """
    Создаёт регулярное выражение для поиска шаблона с учётом пробелов и нижних подчёркиваний в имени.
    Регистр не важен для всех букв.
    Также учитывает возможность замены е на ё и наоборот.
    """
    name_chars = list(template_name)
    pattern = ''
    for c in name_chars:
        if c == ' ':
            pattern += r'[\s_]+'  # Пробел или нижнее подчёркивание
        elif c == '_':
            pattern += r'[\s_]+'  # Пробел или нижнее подчёркивание
        elif c.lower() == 'е':
            pattern += '[еёЕЁ]'
        elif c.lower() == 'ё':
            pattern += '[еёЕЁ]'
        else:
            pattern += f'[{c.upper()}{c.lower()}]'
    # Используем более строгое определение границ шаблона
    return r'\{\{\s*' + pattern + r'\s*(?:\|[^{}]*?)?\}\}'

def build_template_patterns(template_redirects: Dict[str, str]) -> Dict[str, Tuple[str, str]]:
    """
    Создаёт регулярные выражения для поиска шаблона и его редиректов.
    """
    patterns = {}
    for redirect_name, main_name in template_redirects.items():
        pattern = build_template_pattern(redirect_name)
        patterns[redirect_name] = (pattern, main_name)
    return patterns

def update_template_with_date_and_name(text: str, found_template: str, main_template: str, iso_date: str, template_position: Optional[int] = None) -> str:
    """
    Обновляет шаблон в тексте, добавляя дату и заменяя редирект на основное название.
    Корректно обрабатывает вложенные шаблоны и сохраняет форматирование.
    """
    def find_template_end(s: str, start: int) -> int:
        """
        Находит позицию закрывающих скобок шаблона с учетом вложенности.
        """
        stack = []
        i = start
        
        while i < len(s):
            if s[i:i+2] == '{{':
                stack.append(i)
                i += 2
                continue
            elif s[i:i+2] == '}}' and stack:
                stack.pop()
                if not stack:  # Если это закрывающие скобки нашего шаблона
                    return i
                i += 2
                continue
            i += 1
        return -1

    def process_template(match):
        nonlocal processed_count, processed_positions
        template_start = match.start()
        
        # Если указана конкретная позиция, обрабатываем только шаблон в этой позиции
        if template_position is not None and template_start != template_position:
            return match.group(0)
            
        # Проверяем, не обработали ли мы уже шаблон в этой позиции
        if template_start in processed_positions:
            return match.group(0)
            
        template_end = find_template_end(text, template_start)
        if template_end == -1:
            return match.group(0)
            
        processed_count += 1
        processed_positions.add(template_start)
        
        # Получаем весь текст шаблона
        template = text[template_start:template_end+2]
        
        # Проверяем наличие параметра даты
        if '|дата=' in template.lower() or '|date=' in template.lower():
            # Если дата уже есть, только заменяем имя шаблона
            template_lines = template.split('|')
            template_name = template_lines[0][2:].strip()  # Убираем {{ и пробелы
            is_first_upper = template_name[0].isupper()
            formatted_main_template = main_template if is_first_upper else main_template.lower()
            template_lines[0] = '{{' + formatted_main_template
            return '|'.join(template_lines)
        
        # Добавляем дату перед закрывающими скобками
        template_name = template[2:template.find('|') if '|' in template else -2].strip()
        is_first_upper = template_name[0].isupper()
        formatted_main_template = main_template if is_first_upper else main_template.lower()
        
        if '|' in template:
            # Если есть другие параметры, добавляем дату перед последними двумя скобками
            return template[:-2] + f"|дата={iso_date}{'}'*2}"
        else:
            # Если нет других параметров
            return f"{'{{'*2}{formatted_main_template}|дата={iso_date}{'}'*2}"

    pattern = build_template_pattern(found_template)
    processed_count = 0
    processed_positions = set()
    
    result = re.sub(pattern, process_template, text, flags=re.IGNORECASE)
    return result

def get_active_subcategories(site: pywikibot.Site, parent_category_name: str) -> List[Tuple[str, int]]:
    """
    Получает список существующих подкатегорий с количеством статей, отсортированный по возрастанию.
    
    Returns:
        List[Tuple[str, int]]: Список кортежей (название_категории, количество_статей)
    """
    active_categories = []
    parent_category = pywikibot.Category(site, parent_category_name)
    
    try:
        for subcategory in parent_category.subcategories():
            article_count = len(list(subcategory.articles()))
            if article_count > 0:
                active_categories.append((subcategory.title(), article_count))
                
        # Сортируем по количеству статей
        active_categories.sort(key=lambda x: x[1])
        
    except pywikibot.exceptions.Error as e:
        print(f"Ошибка при получении подкатегорий для {parent_category_name}: {e}")
    
    return active_categories

def get_templates_from_category(site: pywikibot.Site, category_page: pywikibot.Page) -> Dict[str, Dict[str, str]]:
    """
    Извлекает названия шаблонов из категории и их редиректы.
    """
    templates = {}
    
    pattern = r'\{\{Категория к ежемесячной очистке\|([^}]+)\}\}'
    matches = re.finditer(pattern, category_page.text, re.IGNORECASE)
    
    for match in matches:
        params = match.group(1).split('|')
        for param in params:
            if '=' not in param:
                template_name = param.strip()
                if template_name:
                    # Получаем редиректы для шаблона
                    redirects = get_template_redirects(site, template_name)
                    
                    # Проверяем, является ли сам шаблон редиректом
                    template_page = pywikibot.Page(site, f"Шаблон:{template_name}")
                    if template_page.isRedirectPage():
                        target = template_page.getRedirectTarget()
                        main_name = target.title(with_ns=False)
                        # Если шаблон - редирект, используем основной шаблон как ключ
                        if main_name not in templates:
                            templates[main_name] = {}
                        templates[main_name].update(redirects)
                    else:
                        # Если шаблон не редирект, добавляем его и его редиректы
                        if template_name not in templates:
                            templates[template_name] = {}
                        templates[template_name].update(redirects)
                        templates[template_name][template_name] = template_name
    
    return templates

def get_templates_by_categories(site: pywikibot.Site, category_names: List[str]) -> Dict[str, Dict[str, Dict[str, str]]]:
    templates_by_category = {}
    total_categories = len(category_names)
    print("\n🔄 Получение шаблонов из категорий...")
    
    for i, category_name in enumerate(category_names, 1):
        print(f"📂 Категория {i}/{total_categories}: {category_name}")
        try:
            category = pywikibot.Page(site, category_name)
            if not category.exists():
                print("❌ Категория не существует")
                continue
            templates = get_templates_from_category(site, category)
            if templates:
                templates_by_category[category_name] = templates
                for template, redirects in templates.items():
                    template_cap = template[0].upper() + template[1:]
                    redirect_list = [r[0].upper() + r[1:] for r in redirects if r != template]
                    print(f"🔵 «{template_cap}»")
                    if redirect_list:
                        print(f"       ↪️ {', '.join(redirect_list)}")
            else:
                print("⚠️ Не найдены шаблоны в категории")
        except pywikibot.exceptions.Error as e:
            print(f"❌ Ошибка: {e}")
        print("-" * 40)
    return templates_by_category

def cache_template_info(template_redirects: Dict[str, Dict[str, str]]) -> Dict[str, Dict[str, str]]:
    """
    Кэширует информацию о шаблонах и их редиректах для быстрого доступа.
    
    Returns:
        Dict[str, Dict[str, str]]: {
            'normalized_variants': {нормализованное_имя: основное_имя},
            'original_names': {нормализованное_имя: оригинальное_имя},
            'all_variants': {вариант_имени: (основное_имя, оригинальное_имя)}
        }
    """
    template_info = {
        'normalized_variants': {},  # нормализованное -> основное_имя
        'original_names': {},       # нормализованное -> оригинальное_имя
        'all_variants': {}          # любой вариант -> (основное_имя, оригинальное_имя)
    }
    
    for templates in template_redirects.values():
        for redirect_name, main_name in templates.items():
            # Сохраняем оригинальное написание
            original_name = redirect_name
            
            # Нормализованная версия (нижний регистр, пробелы)
            normalized = normalize_template_name(redirect_name)
            template_info['normalized_variants'][normalized] = main_name
            template_info['original_names'][normalized] = original_name
            
            # Добавляем все возможные варианты написания
            variants = {
                redirect_name,                    # оригинальное написание
                redirect_name.lower(),            # нижний регистр
                redirect_name.replace(' ', '_'),  # с подчёркиваниями
                redirect_name.lower().replace(' ', '_'),  # нижний регистр с подчёркиваниями
                redirect_name.replace('_', ' '),  # с пробелами
                redirect_name.lower().replace('_', ' ')   # нижний регистр с пробелами
            }
            
            for variant in variants:
                template_info['all_variants'][variant] = (main_name, original_name)
    
    return template_info

def clean_section_name(name: str) -> str:
    """Очищает название раздела от специальных символов и лишних пробелов"""
    for char in '«»""\'\'[]()':
        name = name.replace(char, '')
    name = name.lower()
    name = ' '.join(name.split())
    return name

def get_section_content(text: str, section_name: str, sections: List[Tuple[str, int, int]]) -> Optional[str]:
    """Получает содержимое раздела по его названию"""
    clean_target = clean_section_name(section_name)
    for name, start, end in sections:
        if clean_section_name(name) == clean_target:
            return text[start:end]
    return None

def normalize_template_name(name: str) -> str:
    """
    Нормализует название шаблона для сравнения:
    - приводит к нижнему регистру
    - заменяет подчёркивания на пробелы
    - удаляет лишние пробелы
    """
    name = name.lower()
    name = name.replace('_', ' ')
    name = ' '.join(name.split())
    return name

def has_section_parameter(template: mwparserfromhell.nodes.Template) -> bool:
    """
    Проверяет, содержат ли параметры шаблона слово "раздел".
    
    Args:
        template: Объект шаблона
    
    Returns:
        bool: True, если в параметрах шаблона есть слово "раздел"
    """
    for param in template.params:
        param_name = str(param.name).strip().lower()
        param_value = str(param.value).strip().lower()
        
        # Проверяем, если параметр имеет название "раздел" или его значение содержит это слово
        if "раздел" in param_name or "раздел" in param_value:
            return True
    
    return False

def check_templates_in_revision(rev: Dict, templates_to_find: List[Tuple[str, Optional[str], Dict[str, str]]]) -> Dict[str, Tuple[datetime, str, Optional[str], str]]:
    """
    Проверяет наличие шаблонов в конкретной ревизии.
    
    Args:
        rev: Словарь с информацией о ревизии (text, timestamp, revid)
        templates_to_find: Список кортежей (template_name, section_name, variants)
        
    Returns:
        Dict[str, Tuple[datetime, str, Optional[str], str]]: Словарь {ключ_шаблона: (timestamp, revid, section_name, variant_found)}
    """
    if 'text' not in rev or rev['text'] is None:
        return {}
        
    results = {}
    text = rev['text']
    wikicode = mwparserfromhell.parse(text)
    sections = find_sections(text)
    
    # Проверяем каждый шаблон
    for template in wikicode.filter_templates():
        template_name = str(template.name).strip()
        
        # Проверяем, есть ли этот шаблон среди искомых
        for t_name, section_name, variants in templates_to_find:
            # t_name здесь - это нормализованное имя основного шаблона
            # section_name - либо имя раздела, либо None
            template_key = f"{t_name}_{section_name}" if section_name is not None else f"{t_name}_None"
            
            # Проверяем совпадение нормализованных имен с вариантами
            found_variant_match = None # Store the actual variant that matched
            for variant_in_dict in variants: # variant_in_dict is an alias or main name from the redirects dict
                if compare_template_names(template_name, variant_in_dict):
                    found_variant_match = template_name # Store the name as it appears in the text
                    break

            if found_variant_match:
                if section_name:
                    # Для шаблонов разделов проверяем, в правильном ли разделе находится шаблон
                    template_sections = get_section_for_template(wikicode, template, sections)
                    for found_section in template_sections:
                        if sections_are_similar(found_section, section_name):
                            results[template_key] = (rev['timestamp'], str(rev['revid']), found_section, found_variant_match)
                            break
                else:
                    # Проверяем, имеет ли шаблон параметр "раздел"
                    has_section_param_flag = has_section_parameter(template) # Renamed to avoid conflict
                    
                    if has_section_param_flag:
                        # Если шаблон содержит параметр "раздел", ищем раздел, в котором он находится
                        template_sections = get_section_for_template(wikicode, template, sections)
                        if template_sections:
                            # Используем первый найденный раздел
                            found_section = template_sections[0]
                            # Создаем новый ключ с найденным разделом
                            # section_key = f"{t_name}_{normalize_template_name(found_section)}"
                            # Используем оригинальный t_name и found_section для ключа, 
                            # т.к. section_name в templates_to_find уже нормализован или None.
                            # Если has_section_param_flag, то section_name для этого t_name изначально был None.
                            # Мы создаем НОВУЮ запись для этого шаблона, найденного В КОНКРЕТНОМ разделе.
                            section_key = f"{t_name}_{found_section}" 
                            results[section_key] = (rev['timestamp'], str(rev['revid']), found_section, found_variant_match)
                    else:
                        # Для обычных шаблонов (section_name is None в templates_to_find)
                        # template_key уже будет t_name_None
                        results[template_key] = (rev['timestamp'], str(rev['revid']), None, found_variant_match)
    
    return results

def find_template_and_section_history(page: pywikibot.Page, revisions: List[Dict], sections_to_track: Set[str], 
                                    templates_to_find: List[Tuple[str, Optional[str], Dict[str, str]]], 
                                    template_info: Dict[str, Dict[str, str]]) -> Tuple[Dict[str, List[str]], Dict[str, Tuple[datetime, str, str]]]:
    """
    Находит историю переименований разделов и даты первого появления шаблонов.
    
    Args:
        page: Страница статьи
        revisions: Список ревизий
        sections_to_track: Множество разделов для отслеживания
        templates_to_find: Список шаблонов для поиска в формате (имя_шаблона, имя_раздела, словарь_редиректов)
        template_info: Информация о шаблонах
        
    Returns:
        Кортеж (section_history, template_results)
    """
    # Используем универсальную функцию для поиска
    search_mode = CONFIG['search_mode']
    return find_first_appearance(
        page=page,
        revisions=revisions,
        search_mode=search_mode,
        template_search=True,
        templates_to_find=templates_to_find,
        sections_to_track=sections_to_track,
        template_info=template_info
    )

def get_template_addition_dates(page: pywikibot.Page, template_redirects: Dict[str, Dict[str, str]], search_mode: int, revisions: List[Dict] = None) -> Tuple[List[Tuple[str, str, str, str, str, Optional[str], str]], Dict[str, List[str]], Dict[str, Dict[str, str]]]: # Added 7th element to tuple
    try:
        if revisions is None:
            creation_date, revision_count, revisions = get_revision_info(page)
        
        print("\n🔍 Анализ текущей версии статьи...")
        current_text = page.text
        wikicode = mwparserfromhell.parse(current_text)
        current_sections = find_sections(current_text)
        template_info = cache_template_info(template_redirects)
        
        # Создаем словарь шаблонов с параметром "раздел"
        templates_with_section_param = {}
        for template in wikicode.filter_templates():
            if has_section_parameter(template):
                template_name = str(template.name).strip()
                templates_with_section_param[normalize_template_name(template_name)] = True
        
        print_debug("    📝 Доступные группы шаблонов:")
        for main_name, redirects in template_redirects.items():
            print_debug(f"        • {main_name}: {', '.join(redirects.keys())}")
        
        # Сначала подсчитаем количество каждого шаблона
        template_counts = {}  # {main_name_lower: [(template_name, main_name, sections)]}
        
        # Поиск шаблонов в тексте и подсчет их количества
        print("🔍 Поиск шаблонов в тексте и подсчет их количества:") 

        for template in wikicode.filter_templates():
            template_name = str(template.name).strip()
            
            # Ищем совпадение без учета регистра в ключах all_variants
            found_match = None
            # Используем новую функцию сравнения
            for variant_key, variant_value in template_info['all_variants'].items():
                 if compare_template_names(template_name, variant_key):
                    found_match = variant_value # (main_name, original_name)
                    # Заменяем прямой print на print_debug
                    print_debug(f"        >>> НАЙДЕН через compare_template_names! ('{template_name}' -> '{variant_key}' -> {found_match}) <<<") 
                    break # Нашли первое совпадение, выходим

            if found_match:
                # Используем найденное значение
                main_name, original_name = found_match 
                # main_name_lower больше не нужен для поиска ключа, но оставим для совместимости, если он где-то используется
                main_name_lower = normalize_template_name(main_name) 
                sections = get_section_for_template(wikicode, template, current_sections)

                # Собираем информацию о шаблоне
                if main_name_lower not in template_counts:
                    template_counts[main_name_lower] = []
                template_counts[main_name_lower].append((original_name, main_name, sections))
            else:
                 # Можно добавить логирование через print_debug при необходимости
                 pass # Просто пропускаем шаблон, если он не найден
        
        if not template_counts:
            print("    ℹ️ Не найдены шаблоны для обработки")
            return [], {}, {}
            
        print("🔍 Подготовка к поиску в истории ревизий:")
        section_templates = []
        regular_templates = []
        found_templates = set()
        found_templates_in_sections = {}
        sections_to_track = set()
        need_section_history = False
        
        # Анализируем каждый шаблон
        for main_name_lower, occurrences in template_counts.items():
            template_name, main_name, sections = occurrences[0]
            template_cap = main_name[0].upper() + main_name[1:]
            
            # Проверяем, является ли шаблон шаблоном раздела
            is_section = main_name in SECTION_TEMPLATES or normalize_template_name(template_name) in templates_with_section_param
            
            # Если шаблон (включая редиректы) встречается больше одного раза или он шаблон раздела
            if len(occurrences) > 1 or is_section:
                need_section_history = True  # Отмечаем, что нужен поиск истории разделов
                print(f"    🔵 «{template_cap}» (найден {len(occurrences)} раз)")
                if is_section and not (main_name in SECTION_TEMPLATES):
                    print(f"        📋 Обрабатывается как шаблон разделов (найден параметр 'раздел')")
                    # Добавляем в список SECTION_TEMPLATES для дальнейшей обработки
                    SECTION_TEMPLATES.append(main_name)
                else:
                    print(f"        📋 Обрабатывается как шаблон разделов")
                # Собираем все разделы, где встречается шаблон или его редиректы
                sections_found = []
                for template_name, _, template_sections in occurrences:
                    for section_name in template_sections:
                        section_key = f"{normalize_template_name(template_name)}_{normalize_template_name(section_name)}"
                        if section_key not in found_templates_in_sections:
                            found_templates_in_sections[section_key] = True
                            sections_to_track.add(section_name)
                            section_templates.append((template_name, main_name, section_name))
                            sections_found.append(section_name)
                print(f"        Найден в разделах: {', '.join(f'«{s}»' for s in sections_found)}")
            else:
                # Если шаблон встречается один раз и не в списке SECTION_TEMPLATES
                if main_name_lower not in found_templates:
                    print(f"    🔵 «{template_cap}» (найден 1 раз)")
                    print(f"        📃 Обрабатывается как шаблон статьи")
                    regular_templates.append((template_name, main_name))
                    found_templates.add(main_name_lower)

        # Подготавливаем список всех шаблонов для поиска
        templates_to_find = []
        
        # Добавляем шаблоны разделов
        for template_name, main_name, section_name in section_templates:
            template_variants = set()
            # Используем все возможные варианты написания из template_info
            for variant, (variant_main, _) in template_info['all_variants'].items():
                if variant_main.lower() == main_name.lower():
                    template_variants.add(variant)
            templates_to_find.append((normalize_template_name(template_name), section_name, template_variants))
        
        # Добавляем обычные шаблоны
        for template_name, main_name in regular_templates:
            template_variants = set()
            # Используем все возможные варианты написания из template_info
            for variant, (variant_main, _) in template_info['all_variants'].items():
                if variant_main.lower() == main_name.lower():
                    template_variants.add(variant)
            templates_to_find.append((normalize_template_name(template_name), None, template_variants))
        
        print("\n🔍 Начинаем поиск в истории ревизий...")
        # Получаем историю разделов и даты добавления шаблонов за один проход
        section_history = {}
        if need_section_history:
            section_history, template_dates_dict = find_template_and_section_history(
                page, revisions, sections_to_track, templates_to_find, template_info['normalized_variants']
            )
        else:
            _, template_dates_dict = find_template_and_section_history(
                page, revisions, set(), templates_to_find, template_info['normalized_variants']
            )
        
        # Формируем результат
        template_dates = []
        
        # Группируем результаты по основным шаблонам для вывода
        results_by_main = {}
        
        print_debug(f"    DEBUG: template_dates_dict keys: {list(template_dates_dict.keys())}") # ADDED

        # Обрабатываем результаты поиска
        for template_name, section_name, _ in templates_to_find: # template_name is normalized main name
            key = f"{template_name}_{section_name}" if section_name else f"{template_name}_None" # CORRECTED KEY NAME from key_from_templates_to_find
            print_debug(f"    DEBUG: Checking key: '{key}'") # ADDED

            if key in template_dates_dict:
                timestamp, revid, section_name_at_addition, variant_found = template_dates_dict[key] # Unpack variant_found
                iso_date = timestamp.strftime("%Y-%m-%d")
                # main_name = template_info['normalized_variants'][template_name] # This was for old template_info structure
                # Find the main_name corresponding to the normalized template_name from the original template_redirects
                # This is a bit convoluted; template_redirects is Dict[main_name, Dict[redirect, main_name]]
                # We need to find which main_name in template_redirects.keys() normalizes to template_name
                actual_main_name = ""
                original_redirect_name_for_trigger = variant_found # This is the name as it appeared in text
                
                # Determine the ultimate main_name for the found variant
                # The variant_found is the name as it appeared in the text.
                # We need to map this variant_found back to its ultimate main_name via template_info['all_variants']
                if variant_found in template_info['all_variants']:
                    actual_main_name, _ = template_info['all_variants'][variant_found]
                elif normalize_template_name(variant_found) in template_info['normalized_variants']:
                    # Fallback if variant_found itself is not in all_variants (e.g. different case not covered)
                    actual_main_name = template_info['normalized_variants'][normalize_template_name(variant_found)]
                else: # Should not happen if template_info is comprehensive
                    actual_main_name = template_name # Fallback to normalized name
                    
                print_debug(f"    DEBUG: Found key '{key}'. Timestamp: {timestamp}, ReVID: {revid}, Variant: '{variant_found}', MainName: '{actual_main_name}', SectionAtAddition: {section_name_at_addition}") # ADDED
                
                # template_dates.append((iso_date, iso_date, revid, template_name, main_name, section_name_at_addition))
                template_dates.append((iso_date, iso_date, revid, original_redirect_name_for_trigger, actual_main_name, section_name_at_addition, variant_found))
                
                # Группируем результаты
                if actual_main_name not in results_by_main:
                    results_by_main[actual_main_name] = {'sections': [], 'regular': None, 'variants_found': set()}
                
                results_by_main[actual_main_name]['variants_found'].add(variant_found)
                if section_name_at_addition:
                    results_by_main[actual_main_name]['sections'].append((section_name_at_addition, iso_date, revid, variant_found))
                else:
                    results_by_main[actual_main_name]['regular'] = (iso_date, revid, variant_found)

        # Выводим сгруппированные результаты
        if template_dates:
            print("✅ Результаты поиска:")
            for main_name, results in results_by_main.items():
                main_cap = main_name[0].upper() + main_name[1:]
                variants_display = f" (варианты: {', '.join(sorted(list(results['variants_found'])))})" if len(results['variants_found']) > 1 else ""
                print(f"    🔵 «{main_cap}»{variants_display}")
                
                if results['regular'] is not None:
                    iso_date, revid, variant_found_reg = results['regular']
                    trigger_info = f" (как «{variant_found_reg}»)" if variant_found_reg.lower() != main_name.lower() else ""
                    print(f"        Добавлен{trigger_info}: {iso_date} (ревизия {revid})")
                
                if results['sections']:
                    if len(results['sections']) > 1:
                        print(f"        Найден в {len(results['sections'])} разделах:")
                    else:
                        print(f"        Найден в разделе:")
                        
                    for section_name, iso_date, revid, variant_found_sect in sorted(results['sections'], key=lambda x: x[1]):
                        history = section_history.get(section_name, [])
                        trigger_info_sect = f" (как «{variant_found_sect}»)" if variant_found_sect.lower() != main_name.lower() else ""
                        if history:
                            print(f"            • «{section_name}» ({' → '.join(history)}){trigger_info_sect}: {iso_date} (ревизия {revid})")
                        else:
                            print(f"            • «{section_name}»{trigger_info_sect}: {iso_date} (ревизия {revid})")

            template_dates.sort(key=lambda x: x[0])
            print(f"📊 Всего найдено: {len(template_dates)} шаблон(ов)")
            return template_dates, section_history, template_info
        else:
            print_debug(f"    DEBUG: template_dates list is empty. template_dates_dict was: {template_dates_dict}") # ADDED
            print("    ℹ️ Не найдены шаблоны для обновления")
            return [], {}, {}
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return [], {}, {}

def process_template_update(page: pywikibot.Page, template_dates: List[Tuple[str, str, str, str, str, Optional[str], str]], section_names: List[Optional[str]], section_history: Dict[str, List[str]], template_info: Dict[str, Dict[str, str]]) -> Tuple[str, str]:
    current_text = page.text
    changes_made = False
    template_changes = []
    processed_positions = set()  # Множество для отслеживания уже обработанных позиций
    
    print("🔄 Изменения:")
    
    # Создаем словарь для сопоставления разделов с их датами
    section_to_date = {}
    section_to_revid = {}
    section_to_original = {}
    
    # Заполняем словарь данными из template_dates
    for template_date, section_name in zip(template_dates, section_names):
        iso_date, _, revid, found_template, main_template, original_section_name, variant_found = template_date
        if section_name:
            section_to_date[section_name] = iso_date
            section_to_revid[section_name] = revid
            section_to_original[section_name] = original_section_name
    
    # Функция для безопасного определения границ шаблона
    def find_template_boundaries(text: str, start_pos: int) -> Tuple[int, int, bool]:
        """
        Находит точные границы шаблона с учетом вложенности.
        
        Args:
            text (str): Текст, в котором ищем шаблон
            start_pos (int): Позиция открывающей скобки шаблона {{
            
        Returns:
            Tuple[int, int, bool]: (начальная позиция, конечная позиция, успех)
        """
        # Проверяем, действительно ли начинается с {{
        if text[start_pos:start_pos+2] != '{{':
            return start_pos, start_pos, False
            
        stack = []
        pos = start_pos
        
        # Проверяем, не находится ли шаблон в заголовке
        line_start = text.rfind('\n', 0, start_pos)
        if line_start == -1:
            line_start = 0
        else:
            line_start += 1  # Пропускаем символ новой строки
            
        line_end = text.find('\n', start_pos)
        if line_end == -1:
            line_end = len(text)
            
        line = text[line_start:line_end]
        # Если это заголовок (содержит = в начале и конце), пропускаем
        if re.match(r'^=+\s.*\s=+$', line.strip()):
            return start_pos, start_pos, False
        
        # Ищем закрывающую скобку с учетом вложенности
        stack.append(start_pos)
        i = start_pos + 2  # Пропускаем начальные {{
        
        while i < len(text) and stack:
            if i + 1 < len(text) and text[i:i+2] == '{{':
                stack.append(i)
                i += 2
            elif i + 1 < len(text) and text[i:i+2] == '}}':
                stack.pop()
                if not stack:  # Нашли закрывающую скобку нашего шаблона
                    return start_pos, i + 1, True
                i += 2
            else:
                i += 1
                
        # Если мы здесь, значит не нашли закрывающие скобки
        return start_pos, start_pos, False
    
    # Обрабатываем каждый шаблон по отдельности
    for template_date, section_name in zip(template_dates, section_names):
        iso_date, _, revid, found_template, main_template, original_section_name, variant_found = template_date
        print_debug(f"      📝 Обработка шаблона: {found_template}")
        print_debug(f"      📅 Дата добавления: {iso_date}")
        print_debug(f"      📍 Раздел: {section_name}")
        
        # --- START CHANGE ---
        # Находим все известные варианты (редиректы + основное имя) для main_template
        relevant_variants = set()
        main_name_lower = normalize_template_name(main_template)
        for variant, (m_name, _) in template_info['all_variants'].items():
            if normalize_template_name(m_name) == main_name_lower:
                relevant_variants.add(variant)
        print_debug(f"      🔍 Ищем соответствия для: {list(relevant_variants)}")
        # --- END CHANGE ---

        # Анализируем текст с помощью mwparserfromhell
        wikicode = mwparserfromhell.parse(current_text)
        
        # Для каждого шаблона в тексте
        for template in wikicode.filter_templates():
            template_name = str(template.name).strip()
            
            # --- START CHANGE ---
            # Проверяем, совпадает ли имя шаблона из текста с одним из релевантных вариантов
            match_found_in_text = False
            for known_variant in relevant_variants:
                if compare_template_names(template_name, known_variant):
                    match_found_in_text = True
                    break
            
            if match_found_in_text:
            # --- END CHANGE ---
                template_str = str(template)
                
                # Ищем все вхождения шаблона в тексте
                pos = 0
                while True:
                    pos = current_text.find(template_str, pos)
                    if pos == -1:
                        break
                        
                    # Если позиция уже обработана, пропускаем
                    if pos in processed_positions:
                        pos += 1
                        continue
                    
                    # Находим точные границы шаблона
                    start_pos, end_pos, success = find_template_boundaries(current_text, pos)
                    
                    if not success:
                        pos += 1
                        continue
                        
                    # Проверяем, не находится ли шаблон в заголовке еще раз
                    # через более точный анализ окружения
                    line_start = current_text.rfind('\n', 0, start_pos)
                    if line_start == -1:
                        line_start = 0
                    else:
                        line_start += 1
                        
                    # Получаем текущую строку
                    line_end = current_text.find('\n', start_pos)
                    if line_end == -1:
                        line_end = len(current_text)
                        
                    line = current_text[line_start:line_end]
                    
                    # Проверка, является ли строка заголовком
                    is_heading = re.match(r'^=+\s', line) and re.search(r'\s=+$', line)
                    
                    if is_heading:
                        print_debug(f"      ⚠️ Шаблон находится в заголовке, пропускаем: {line}")
                        pos = end_pos
                        continue
                    
                    # Получаем разделы, в которых находится шаблон
                    sections = find_sections(current_text)
                    template_sections = []
                    
                    for section_title, section_start, section_end in sections:
                        if section_start <= start_pos < section_end:
                            template_sections.append(section_title)
                    
                    print_debug(f"      📑 Разделы шаблона: {template_sections}")
                    
                    # Проверяем, нет ли уже даты в шаблоне
                    has_date = False
                    for param in template.params:
                        param_name = str(param.name).strip().lower()
                        if param_name in ['дата', 'date']:
                            has_date = True
                            print_debug(f"      ⚠️ Шаблон уже имеет дату: {param.value}")
                            break
                            
                    if not has_date:
                        print_debug(f"      ✅ Шаблон не имеет даты, будет обновлен")
                        # Получаем имя шаблона из шаблона с сохранением регистра
                        old_template_name = str(template.name).strip()
                        is_first_upper = old_template_name[0].isupper()
                        formatted_main_template = main_template if is_first_upper else main_template[0].lower() + main_template[1:]
                        
                        # Создаем новый шаблон
                        new_template = mwparserfromhell.nodes.Template(formatted_main_template)
                        
                        # Копируем все параметры
                        for param in template.params:
                            new_template.add(str(param.name), str(param.value))
                        
                        # Определяем, в каком разделе находится шаблон
                        current_section = None
                        if template_sections:
                            current_section = template_sections[0]
                        
                        # Определяем правильную дату для этого раздела
                        template_date = iso_date
                        template_revid = revid
                        if current_section and current_section in section_to_date:
                            template_date = section_to_date[current_section]
                            template_revid = section_to_revid[current_section]
                        
                        # Добавляем дату
                        new_template.add('дата', template_date)
                        
                        # Преобразуем в строку
                        new_template_str = str(new_template)
                        
                        # Получаем текущую строку шаблона в тексте
                        current_template_str = current_text[start_pos:end_pos+1]
                        
                        # Заменяем шаблон в тексте
                        # Важно: здесь используем точные границы для замены
                        current_text = current_text[:start_pos] + new_template_str + current_text[end_pos+1:]
                        
                        processed_positions.add(start_pos)
                        changes_made = True
                        
                        # Определяем оригинальное название раздела
                        original_section = None
                        if current_section and current_section in section_to_original:
                            original_section = section_to_original[current_section]
                        
                        template_changes.append((found_template, main_template, template_date, current_section, template_revid, current_template_str, new_template_str, original_section))
                        
                        # Выводим каждое найденное изменение
                        if current_section:
                            # Для вводного раздела используем более понятное название
                            display_section = "вводной части статьи" if current_section == "Вводный раздел" else f"разделе «{current_section}»"
                            print(f"    • {current_template_str} → {new_template_str} в {display_section}")
                        else:
                            print(f"    • {current_template_str} → {new_template_str}")
                    
                    # Перемещаем позицию поиска
                    pos = end_pos
    
    if changes_made:
        # Группируем изменения для описания правки
        template_changes_by_main = {}
        for found_template, main_template, iso_date, section_name, revid, old_template_str, _, original_section_name in template_changes:
            if main_template not in template_changes_by_main:
                template_changes_by_main[main_template] = {'sections': [], 'redirects': set(), 'first_date': iso_date, 'first_revid': revid}
            if found_template.lower() != main_template.lower():
                # Извлекаем оригинальное имя шаблона из текста
                match = re.search(r'\{\{\s*([^|\}]+)', old_template_str)
                if match:
                    # Используем оригинальное написание шаблона из текста
                    original_template_name = match.group(1).strip()
                    template_changes_by_main[main_template]['redirects'].add(original_template_name)
                else:
                    template_changes_by_main[main_template]['redirects'].add(found_template)
            if section_name:
                # Проверяем, не добавлена ли уже эта секция
                section_info = (section_name, iso_date, revid, original_section_name)
                if section_info not in template_changes_by_main[main_template]['sections']:
                    template_changes_by_main[main_template]['sections'].append(section_info)
            else:
                # Для шаблонов вне разделов сохраняем дату и revid
                template_changes_by_main[main_template]['first_date'] = iso_date
                template_changes_by_main[main_template]['first_revid'] = revid
        
        summary_parts = []
        for main_template, changes in template_changes_by_main.items():
            # Делаем первую букву заглавной, остальные сохраняем как в оригинале
            template_cap = main_template[0].upper() + main_template[1:]
            sections = changes['sections']
            redirects = changes['redirects']
            first_date = changes['first_date']
            first_revid = changes['first_revid']
            
            # Определяем, является ли шаблон шаблоном раздела
            # Считается шаблоном раздела если: 
            # 1. Есть в списке SECTION_TEMPLATES
            # 2. Или если шаблон найден в нескольких разделах (sections > 1)
            is_section_template = main_template in SECTION_TEMPLATES or len(sections) > 1
            
            if len(sections) > 3:  # Если шаблонов больше трёх
                # Создаем множество уникальных пар (revid, date)
                unique_revisions = {(revid, date) for _, date, revid, _ in sections}
                dates_msg = []
                # Берем только уникальные ревизии
                for revid, date in list(unique_revisions)[:3]:
                    dates_msg.append(f"[[Special:Diff/{revid}|{date}]]")
                
                if redirects:
                    # Группируем редиректы без учета регистра
                    redirects_lower = {}
                    for r in redirects:
                        r_lower = r.lower()
                        if r_lower not in redirects_lower:
                            # Сохраняем оригинальное написание, но делаем первую букву заглавной
                            redirects_lower[r_lower] = r[0].upper() + r[1:] if r else r
                    
                    # Создаем текст с уникальными редиректами, разделенными "и"
                    unique_redirects = list(redirects_lower.values())
                    if len(unique_redirects) == 1:
                        redirect_text = f'[[ш:{unique_redirects[0]}]]'
                    else:
                        redirect_text = ' и '.join([f'[[ш:{r}]]' for r in unique_redirects])
                    
                    # Формируем сообщение с редиректами
                    redirect_msg = f"Замена редиректа {redirect_text} на актуальный [[ш:{template_cap}]]"
                    summary_parts.append(f"{redirect_msg} с добавлением дат установки в {len(sections)} шаблонах в нескольких разделах: {', '.join(dates_msg)} и др.")
                else:
                    summary_parts.append(f"В [[ш:{template_cap}]] добавлены даты установки в {len(sections)} шаблонах в нескольких разделах: {', '.join(dates_msg)} и др.")
            else:  # Если шаблонов три или меньше
                if redirects:
                    # Группируем редиректы без учета регистра
                    redirects_lower = {}
                    for r in redirects:
                        r_lower = r.lower()
                        if r_lower not in redirects_lower:
                            # Сохраняем оригинальное написание, но делаем первую букву заглавной
                            redirects_lower[r_lower] = r[0].upper() + r[1:] if r else r
                    
                    # Создаем текст с уникальными редиректами, разделенными "и"
                    unique_redirects = list(redirects_lower.values())
                    if len(unique_redirects) == 1:
                        redirect_text = f'[[ш:{unique_redirects[0]}]]'
                    else:
                        redirect_text = ' и '.join([f'[[ш:{r}]]' for r in unique_redirects])
                    
                    # Формируем сообщение с редиректами
                    redirect_msg = f"Замена редиректа {redirect_text} на актуальный [[ш:{template_cap}]]"
                    
                    if sections:
                        section_parts = []
                        for section_info in sections:
                            section, date, revid, original_name = section_info
                            # Для вводного раздела используем более понятное название только если это шаблон раздела
                            if section == "Вводный раздел":
                                if is_section_template:
                                    section_text = "во вводной части статьи"
                                else:
                                    # Для обычных шаблонов статьи, которые случайно во введении, не указываем раздел
                                    continue
                            else:
                                section_text = f"в разделе «{section}»"
                                # Убираем упоминание "ранее", если оригинальное название совпадает с текущим или отсутствует
                                if original_name and original_name != section and not sections_are_similar(original_name, section) and original_name != "Вводный раздел":
                                    section_text += f" (ранее: {original_name})"
                            
                            section_parts.append(f"{section_text} ([[Special:Diff/{revid}|{date}]])")
                        
                        if section_parts:
                            summary_parts.append(redirect_msg + f" с добавлением даты установки {', '.join(section_parts)}")
                        else:
                            summary_parts.append(f"{redirect_msg} с добавлением даты установки: [[Special:Diff/{first_revid}|{first_date}]]")
                    else:
                        summary_parts.append(f"{redirect_msg} с добавлением даты установки: [[Special:Diff/{first_revid}|{first_date}]]")
                else:
                    if sections:
                        section_parts = []
                        # Создаем множество уникальных пар (revid, date)
                        unique_revisions = {(revid, date) for _, date, revid, _ in sections}
                        # Создаем словарь для группировки секций по ревизиям
                        sections_by_revision = {}
                        for section_info in sections:
                            section, date, revid, original_name = section_info
                            if (revid, date) not in sections_by_revision:
                                sections_by_revision[(revid, date)] = []
                            
                            # Для вводного раздела используем более понятное название только если это шаблон раздела
                            if section == "Вводный раздел":
                                if is_section_template:
                                    section_text = "во вводной части статьи"
                                else:
                                    # Для обычных шаблонов статьи, которые случайно во введении, не указываем раздел
                                    continue
                            else:
                                section_text = f"в разделе «{section}»"
                                # Убираем упоминание "ранее", если оригинальное название совпадает с текущим или отсутствует
                                if original_name and original_name != section and not sections_are_similar(original_name, section) and original_name != "Вводный раздел":
                                    section_text += f" (ранее: {original_name})"
                            
                            sections_by_revision[(revid, date)].append(section_text)
                        
                        # Формируем части описания
                        for (revid, date), section_list in sections_by_revision.items():
                            if section_list:  # Пропускаем пустые списки
                                section_parts.append(f"{', '.join(section_list)} ([[Special:Diff/{revid}|{date}]])")
                        
                        if is_section_template and section_parts:
                            summary_parts.append(f"В [[ш:{template_cap}]] добавлена дата установки {', '.join(section_parts)}")
                        else:
                            # Для обычных шаблонов используем простой формат
                            summary_parts.append(f"В [[ш:{template_cap}]] добавлена дата установки: [[Special:Diff/{first_revid}|{first_date}]]")
                    else:
                        summary_parts.append(f"В [[ш:{template_cap}]] добавлена дата установки: [[Special:Diff/{first_revid}|{first_date}]]")
        
        summary = ". ".join(summary_parts)
        print("📋 Описание правки:")
        print(f"    {summary}")
        print("✅ Изменения подготовлены")
        
        return current_text, summary
    
    print("    ℹ️ Нет изменений для сохранения")
    return current_text, ""  # Возвращаем текущий текст и пустое описание вместо None

def process_article_with_limit(page: pywikibot.Page, templates: Dict[str, Dict[str, str]], 
                              search_mode: int, max_revisions: int, revision_count: int,
                              should_process_rq: bool) -> Tuple[bool, float, List[Tuple[str, str, str, str, str, Optional[str], str]], List[Optional[str]], Optional[Tuple[str, str]], Dict[str, Dict[str, str]]]:
    start_time = time.time()
    try:
        # Используем переданное количество ревизий вместо запроса
        if max_revisions > 0 and revision_count > max_revisions:
            print(f"⚠️ Пропуск статьи: превышено ограничение в {max_revisions} ревизий (найдено {revision_count})")
            return False, time.time() - start_time, [], [], None, {}
            
        # Получаем информацию о ревизиях один раз
        creation_date, revision_count, revisions = get_revision_info(page)
        
        # Сначала проверяем, нужно ли обработать шаблон Rq
        if should_process_rq:
            print("⏳ Проверка на наличие шаблона Rq...")
            # Получаем редиректы шаблона Rq
            site = page.site
            rq_templates = get_rq_template_redirects(site)
            
            # Обрабатываем шаблон Rq
            success, new_text, summary = process_rq_template(page, rq_templates, search_mode, revisions)
            
            if success:
                print("✅ Шаблон Rq успешно обработан")
                return True, time.time() - start_time, [], [], (new_text, summary), {}
            else:
                print("ℹ️ Шаблон Rq не найден или не требует обработки, продолжаем стандартную обработку")
            
        # Получаем даты добавления шаблонов и историю разделов
        template_dates, section_history, template_info = get_template_addition_dates(page, templates, search_mode, revisions)
        
        if not template_dates:
            # Добавляем возврат template_info для консистентности, хотя он и пуст
            return True, time.time() - start_time, [], [], None, {}
        
        # Извлекаем имена разделов
        section_names = [date[5] for date in template_dates]
        
        # Обновляем шаблоны, используя уже полученную историю разделов
        new_text, summary = process_template_update(page, template_dates, section_names, section_history, template_info)
        
        # Проверяем, есть ли реальные изменения
        if summary:  # Если есть описание изменений, значит были изменения
            return True, time.time() - start_time, template_dates, section_names, (new_text, summary), template_info
        else:
            return True, time.time() - start_time, template_dates, section_names, None, {}
        
    except Exception as e:
        print(f"❌ Ошибка при обработке статьи: {e}")
        return False, time.time() - start_time, [], [], None, {}

def process_articles(site: pywikibot.Site, category_templates: Dict[str, Dict[str, str]], 
                    search_mode: int, category_counts: Dict[str, int],
                    process_rq_for_this_run: bool):
    total_categories = len(category_templates)
    current_category = 0
    total_articles = sum(category_counts.values())
    processed_articles = 0
    skipped_articles = []
    
    for category_name, templates in category_templates.items():
        current_category += 1
        category_articles = category_counts[category_name]
        current_article = 0
        
        print(f"\n📂 Обработка категории: {category_name} ({current_category}/{total_categories})")
        print("=" * 100)
        
        try:
            category = pywikibot.Category(site, category_name)
            for page in category.articles():
                current_article += 1
                processed_articles += 1

                # Получаем базовую информацию о статье без загрузки всех ревизий
                creation_date = page.oldest_revision.timestamp
                revision_count = page.revision_count()
                
                print_article_header(page, creation_date, revision_count,
                                   current_article, category_articles,
                                   current_category, total_categories,
                                   processed_articles, total_articles)

                try:
                    success, elapsed_time, template_dates, section_names, update_info, template_info = process_article_with_limit(
                        page, templates, search_mode, CONFIG['max_revisions'], revision_count, process_rq_for_this_run
                    )
                    
                    if not success and elapsed_time is not None:
                        skipped_articles.append((page.title(), elapsed_time))
                        print("=" * 100)  # Добавляем разделительную линию после пропуска
                        continue
                    
                    # Обработка изменений и сохранение
                    if update_info:
                        new_text, summary = update_info
                        
                        if CONFIG['autosave']:
                            print(f"    💾 Автосохранение с описанием: {summary}") # ADDED
                            try:
                                page.text = new_text
                                page.save(summary=summary, minor=True)
                            except Exception as e:
                                print(f"❌ Ошибка при сохранении статьи «{page.title()}»: {e}")
                        else:
                            print("📝 Применение изменений...")
                            print(f"🔄 Будет сохранено с описанием: {summary}")
                            while True:
                                print("\nВыберите действие:")
                                print("1 - сохранить изменения")
                                print("2 - продолжить без сохранения")
                                print("3 - остановить работу")
                                print("4 - показать текст измененной статьи в консоли")
                                
                                response = input("\nВведите номер действия (1/2/3/4): ").strip()
                                
                                if response == "1":
                                    if not summary:
                                        print("\nℹ️ Нет изменений для сохранения")
                                        break
                                    try:
                                        page.text = new_text
                                        page.save(summary=summary, minor=True)
                                        print(f"\n✅ Сохранены изменения в статье «{page.title()}»")
                                    except Exception as e:
                                        print(f"\n❌ Ошибка при сохранении статьи: {e}")
                                    break
                                elif response == "2":
                                    print("Продолжаем без сохранения")
                                    break
                                elif response == "3":
                                    print("✋ Обработка остановлена пользователем")
                                    return
                                elif response == "4":
                                    print("\n📄 Текст измененной статьи:")
                                    print("=" * 100)
                                    print(new_text)
                                    print("=" * 100)
                                    continue
                                else:
                                    print("\n⚠️ Пожалуйста, введите 1, 2, 3 или 4")
                    
                except pywikibot.exceptions.Error as e:
                    print(f"❌ Ошибка при обработке статьи {page.title()}:")
                    print(f"   {e}")
                
                print("=" * 100)  # Добавляем разделительную линию после обработки
                    
        except pywikibot.exceptions.Error as e:
            print(f"❌ Ошибка при обработке категории {category_name}:")
            print(f"   {e}")
    
    # Выводим статистику по пропущенным статьям
    if skipped_articles:
        print("\n📊 Статистика пропущенных статей:")
        print(f"Всего пропущено: {len(skipped_articles)}")

def get_section_templates_with_redirects(site: pywikibot.Site) -> Dict[str, Dict[str, str]]:
    """
    Получает все шаблоны для разделов и их редиректы.
    Возвращает словарь {основной_шаблон: {редирект: основной_шаблон}}.
    """
    templates_with_redirects = {}
    
    for template_name in SECTION_TEMPLATES:
        redirects = {}
        template_page = pywikibot.Page(site, f"Шаблон:{template_name}")
        
        try:
            # Добавляем сам шаблон
            redirects[template_name.lower()] = template_name
            
            # Получаем все редиректы
            for redirect in template_page.redirects():
                redirect_name = redirect.title(with_ns=False)
                redirects[redirect_name.lower()] = template_name
                
            templates_with_redirects[template_name] = redirects
            
            template_cap = template_name[0].upper() + template_name[1:]
            print(f"✅ Получены редиректы для шаблона «{template_cap}»:")
            for redirect_name in redirects:
                if redirect_name.lower() != template_name.lower():
                    redirect_cap = redirect_name[0].upper() + redirect_name[1:]
                    print(f"  ↪️ «{redirect_cap}»")
                    
        except pywikibot.exceptions.Error as e:
            template_cap = template_name[0].upper() + template_name[1:]
            print(f"❌ Ошибка при получении редиректов для шаблона «{template_cap}»: {e}")
    
    return templates_with_redirects

def get_rq_template_redirects(site: pywikibot.Site) -> Dict[str, str]:
    """
    Получает все редиректы шаблона Rq.
    Возвращает словарь {редирект: написание_с_учетом_регистра}
    """
    redirects = {}
    # Основные названия шаблона Rq и его редиректов
    rq_templates = ["Rq", "Request", "Улучшить статью", "Multiple issues"]
    
    for template_name in rq_templates:
        # Проверяем и добавляем шаблон с большой буквы
        try:
            template_page = pywikibot.Page(site, f"Шаблон:{template_name}")
            if template_page.exists():
                redirects[template_name.lower()] = template_name
                
                # Получаем все редиректы
                for redirect in template_page.redirects():
                    redirect_name = redirect.title(with_ns=False)
                    redirects[redirect_name.lower()] = redirect_name
        except pywikibot.exceptions.Error as e:
            print(f"❌ Ошибка при получении редиректов для шаблона «{template_name}»: {e}")
        
        # Проверяем и добавляем шаблон с маленькой буквы
        template_name_lower = template_name[0].lower() + template_name[1:]
        try:
            template_page = pywikibot.Page(site, f"Шаблон:{template_name_lower}")
            if template_page.exists():
                redirects[template_name_lower.lower()] = template_name_lower
                
                # Получаем все редиректы
                for redirect in template_page.redirects():
                    redirect_name = redirect.title(with_ns=False)
                    redirects[redirect_name.lower()] = redirect_name
        except pywikibot.exceptions.Error as e:
            print(f"❌ Ошибка при получении редиректов для шаблона «{template_name_lower}»: {e}")
    
    print_debug(f"✅ Получены редиректы для шаблона Rq:")
    for redirect in redirects.values():
        print_debug(f"  ↪️ «{redirect}»")
    
    return redirects

def extract_rq_params(template: mwparserfromhell.nodes.Template) -> Tuple[List[str], Dict[str, str]]:
    """
    Извлекает параметры из шаблона Rq.
    Возвращает кортеж: (список названий проблем статьи для конвертации, словарь специальных параметров).
    """
    params_for_conversion = []
    all_named_rq_params = {} # Для всех именованных: 'topic', 'fromlang', 'раздел', и т.д.
    
    # Собираем параметры
    for param in template.params:
        param_name_lower = str(param.name).strip().lower()
        param_value = str(param.value).strip() # Сохраняем оригинальное значение
        
        # Проверяем специальные параметры
        if param_name_lower.isdigit(): # Неименованный параметр
            value_lower = param_value.lower() # Приводим к нижнему регистру для проверок
            
            # Проверяем, не является ли параметр пропускаемым
            if value_lower in RQ_SKIP_PARAMS:
                # Просто игнорируем этот параметр и переходим к следующему
                print_debug(f"    ℹ️ Пропускаемый параметр '{value_lower}' будет проигнорирован.")
                continue 
            
            # Проверяем, есть ли значение в словаре соответствия параметров шаблонам
            if value_lower in RQ_PARAM_TEMPLATES:
                params_for_conversion.append(value_lower) # Добавляем в нижнем регистре для поиска дат
                print_debug(f"    ✅ Извлечен неименованный параметр для конвертации: '{value_lower}' → шаблон '{RQ_PARAM_TEMPLATES[value_lower]}'")
            else:
                print_debug(f"    ⚠️ Неизвестный неименованный параметр Rq '{value_lower}' будет проигнорирован (пропущен).")
        else: # Любой именованный параметр
            all_named_rq_params[param_name_lower] = param_value
            print_debug(f"    ✅ Извлечен именованный параметр: '{param_name_lower}={param_value}'")
            
    return params_for_conversion, all_named_rq_params

def find_rq_param_addition_dates(page: pywikibot.Page, rq_templates: Dict[str, str], 
                                current_params: List[str], search_mode: int, 
                                revisions: List[Dict]) -> Dict[str, Tuple[datetime, str, str]]:
    """
    Находит даты первого добавления каждого параметра шаблона Rq.
    
    Args:
        page: Страница статьи
        rq_templates: Словарь редиректов шаблона Rq
        current_params: Список текущих параметров шаблона Rq в статье
        search_mode: Режим поиска (1 - от последней ревизии, 2 - от первой, 3 - бинарный)
        revisions: Список ревизий статьи
        
    Returns:
        Dict[str, Tuple[datetime, str, str]]: Словарь {параметр: (дата, id_ревизии, имя_параметра_в_той_ревизии)}
    """
    # Очищаем и проверяем параметры
    valid_params = []
    for param in current_params:
        param = param.strip().lower()
        if param in RQ_PARAM_TEMPLATES:
            valid_params.append(param)
        else:
            print(f"    ⚠️ Параметр '{param}' не найден в словаре соответствия шаблонов, пропускаем")
    
    if not valid_params:
        print("    ⚠️ Нет корректных параметров для поиска")
        return {}
    
    print(f"    ✅ Параметры для поиска: {', '.join(valid_params)}")
    
    # Используем универсальную функцию для поиска
    return find_first_appearance(
        page=page,
        revisions=revisions,
        search_mode=search_mode,
        template_search=False,
        rq_templates=rq_templates,
        rq_params=valid_params
    )

def process_rq_template(page: pywikibot.Page, rq_templates: Dict[str, str], search_mode: int, revisions: List[Dict] = None) -> Tuple[bool, str, str]:
    """
    Обрабатывает статью с шаблоном Rq, заменяя его на шаблон-контейнер с внутренними шаблонами проблем.
    
    Args:
        page: Страница статьи
        rq_templates: Словарь редиректов шаблона Rq
        search_mode: Режим поиска дат добавления (1 - от последней ревизии, 2 - от первой)
        revisions: Список ревизий, если уже получен ранее
        
    Returns:
        Tuple[bool, str, str]: (успех, новый текст, описание правки)
    """
    try:
        print_debug("🔍 Анализируем шаблоны Rq в статье...")
        
        if revisions is None:
            _, _, revisions = get_revision_info(page)
        
        current_text = page.text
        wikicode = mwparserfromhell.parse(current_text)
        site = page.site # Get site object for get_template_redirects
        
        # Словарь для хранения найденных шаблонов Rq и их параметров
        found_rq_templates = []
        
        # Нормализуем названия шаблонов Rq для поиска
        normalized_redirects = {name.lower(): name for name, original in rq_templates.items()}
        
        # Находим все шаблоны Rq в статье
        for template in wikicode.filter_templates():
            template_name = str(template.name).strip()
            template_name_lower = template_name.lower()
            
            # Проверяем, является ли шаблон редиректом Rq
            if template_name_lower in normalized_redirects:
                # --- START CHANGE ---
                # Проверяем, содержит ли ТЕКУЩИЙ шаблон пропускаемые параметры.
                # Если да, то всю статью пропускаем, как и было задумано.
                current_template_raw_params = [str(p.value).strip().lower() 
                                               for p in template.params if str(p.name).strip().isdigit()]
                contains_skip_param = any(p in RQ_SKIP_PARAMS for p in current_template_raw_params)
                
                if contains_skip_param:
                    print_debug(f"    ⚠️ Текущий шаблон Rq содержит пропускаемый параметр ({[p for p in current_template_raw_params if p in RQ_SKIP_PARAMS]}). Пропускаем обработку статьи.")
                    return False, current_text, ""
                # --- END CHANGE ---

                # Извлекаем параметры
                extracted_params, special_params = extract_rq_params(template)
                
                # Если нет ВАЛИДНЫХ извлеченных параметров для конвертации, пропускаем этот шаблон Rq
                if not extracted_params:
                    if special_params:
                        print_debug("    ⚠️ Шаблон Rq не содержит параметров для конвертации (только специальные)")
                    else:
                        print_debug("    ⚠️ Шаблон Rq не содержит параметров для конвертации")
                    continue # Переходим к следующему шаблону Rq в статье, если он есть
                
                # Сохраняем шаблон, его параметры для конвертации и специальные параметры
                original_name = template_name  # Оригинальное написание с учетом регистра
                found_rq_templates.append((template, extracted_params, special_params, original_name))
                print_debug(f"    ✅ Найден шаблон «{original_name}» с параметрами для конвертации: {', '.join(extracted_params)}")
        
        if not found_rq_templates:
            print_debug("    ℹ️ Шаблоны Rq не найдены в статье (или все пропущены)")
            return False, current_text, ""
        
        changes_made = False
        processed_rq_details_for_summary = [] # Store details for summary generation
        
        # Обрабатываем каждый найденный шаблон
        for template, params, special_params, original_name in found_rq_templates:
            # Находим даты добавления только для конвертируемых параметров
            # param_dates_from_rq: Dict[str, Tuple[datetime, str, str (hist_rq_param_name)]]
            param_dates_from_rq = find_rq_param_addition_dates(page, rq_templates, params, search_mode, revisions)
            
            # --- START NEW LOGIC: Find dates for equivalent standalone templates ---
            final_param_dates_with_triggers: Dict[str, Tuple[datetime, str, str, str]] = {}
            
            print_debug("    🔄 Поиск дат для эквивалентных самостоятельных шаблонов...")

            # 1. Собрать все уникальные самостоятельные шаблоны-эквиваленты
            unique_standalone_templates_to_search: Dict[str, str] = {} # {normalized_name: original_name}
            for rq_param_name_for_standalone in params: # params - это параметры Rq из текущей статьи
                target_standalone_template_name = RQ_PARAM_TEMPLATES.get(rq_param_name_for_standalone.lower())
                if target_standalone_template_name:
                    normalized_standalone = normalize_template_name(target_standalone_template_name)
                    if normalized_standalone not in unique_standalone_templates_to_search:
                        unique_standalone_templates_to_search[normalized_standalone] = target_standalone_template_name
            
            standalone_template_addition_dates: Dict[str, Tuple[datetime, str, Optional[str], str]] = {}
            if unique_standalone_templates_to_search:
                print_debug(f"        🔍 Будут искаться standalone-эквиваленты: {list(unique_standalone_templates_to_search.values())}")
                
                # 2. Подготовить templates_to_find для find_first_appearance
                templates_to_find_for_all_standalones = []
                for norm_name, orig_name in unique_standalone_templates_to_search.items():
                    redirects = get_template_redirects(site, orig_name, use_rq_specific_cache=True)
                    if not redirects: # Должен всегда содержать хотя бы себя
                        redirects = {orig_name: orig_name}
                    templates_to_find_for_all_standalones.append(
                        (norm_name, None, redirects) # section_name is None
                    )
                
                # 3. Один вызов find_first_appearance для всех уникальных standalone шаблонов
                if templates_to_find_for_all_standalones:
                    _, standalone_template_addition_dates = find_first_appearance(
                        page, revisions, search_mode,
                        template_search=True,
                        templates_to_find=templates_to_find_for_all_standalones,
                        sections_to_track=set(), 
                        template_info={} # Не используется в этом режиме вызова find_first_appearance
                    )
                    print_debug(f"        ℹ️  Результаты поиска standalone (ключи): {list(standalone_template_addition_dates.keys())}")

            # 4. Сравнение дат и выбор наиболее ранней
            for rq_param_name, (rq_date, rq_revid, hist_rq_param_trigger) in param_dates_from_rq.items():
                current_best_date = rq_date
                current_best_revid = rq_revid
                current_best_trigger_name = hist_rq_param_trigger # Изначально это триггер из Rq
                current_best_trigger_type = 'rq' # Тип триггера: 'rq' или 'standalone'
                
                target_standalone_template_name_orig = RQ_PARAM_TEMPLATES.get(rq_param_name.lower())
                
                if target_standalone_template_name_orig:
                    normalized_target_standalone = normalize_template_name(target_standalone_template_name_orig)
                    # Ключ для standalone_template_addition_dates будет 'normalizedname_None'
                    standalone_key = f"{normalized_target_standalone}_None"
                    
                    print_debug(f"        🔹 Для Rq|{rq_param_name} (цель: {{ {{{target_standalone_template_name_orig}}} }} ):")
                    print_debug(f"            Дата из Rq-параметра ({hist_rq_param_trigger}): {rq_date.strftime('%Y-%m-%d')}")

                    if standalone_key in standalone_template_addition_dates:
                        st_date, st_revid, _, st_variant_found = standalone_template_addition_dates[standalone_key]
                        print_debug(f"            Дата из standalone шаблона ({st_variant_found}): {st_date.strftime('%Y-%m-%d')}")
                        if st_date < current_best_date:
                            print_debug(f"                ❗️ Найдена более ранняя дата от standalone шаблона ({st_variant_found}).")
                            current_best_date = st_date
                            current_best_revid = st_revid
                            current_best_trigger_name = st_variant_found # Теперь триггер - это имя standalone шаблона
                            current_best_trigger_type = 'standalone'
                    else:
                        print_debug(f"            Standalone шаблон {{ {{{target_standalone_template_name_orig}}} }} или его редиректы не найдены в истории (ключ: {standalone_key}).")
                else:
                    print_debug(f"        ⚠️ Для Rq|{rq_param_name} не найден целевой самостоятельный шаблон в RQ_PARAM_TEMPLATES.")
                
                final_param_dates_with_triggers[rq_param_name] = (current_best_date, current_best_revid, current_best_trigger_name, current_best_trigger_type)
            # --- END NEW LOGIC ---
            
            if not final_param_dates_with_triggers: # Check if any dates were determined
                print_debug("    ⚠️ Не удалось найти даты добавления параметров (после проверки standalone)")
                continue
            
            # Выводим найденные даты для отладки
            print_debug("    📅 Итоговые найденные даты добавления параметров (с учетом standalone):")
            for param, (date, revid, hist_param_or_template, trigger_type_log) in final_param_dates_with_triggers.items(): 
                print_debug(f"       • {param} (триггер «{hist_param_or_template}», тип: {trigger_type_log}): {date.strftime('%Y-%m-%d')} (ревизия {revid})")
                
            # Формируем новый шаблон-контейнер
            is_first_upper = original_name[0].isupper()
            template_name = "Rq" if is_first_upper else "rq"
            
            container_content = f"{{{{{template_name}|}}}}"
            inside_content = []

            # Группируем параметры по целевому шаблону и находим самую раннюю дату для каждого
            earliest_target_dates = {}
            # Используем final_param_dates_with_triggers для этой логики
            # Теперь он содержит 4 элемента, включая тип триггера, но он не нужен для earliest_target_dates
            for param, (date, revid, hist_param_or_template_trigger, _) in final_param_dates_with_triggers.items(): 
                if param in RQ_PARAM_TEMPLATES:
                    target_template = RQ_PARAM_TEMPLATES[param]
                    if target_template not in earliest_target_dates or date < earliest_target_dates[target_template][0]:
                        earliest_target_dates[target_template] = (date, revid, param, hist_param_or_template_trigger) 
            
            # Сортируем уникальные целевые шаблоны по их самой ранней дате
            sorted_targets = sorted(
                earliest_target_dates.items(), 
                key=lambda item: item[1][0] # Сортировка по дате (первый элемент кортежа в значении)
            )
            
            fromlang_wipe_ready = False 

            # Создаем внутренние шаблоны на основе отсортированных целевых шаблонов
            for target_template, (date, revid, original_param, hist_param_for_summary) in sorted_targets: # UNPACK hist_param_for_summary
                iso_date = date.strftime("%Y-%m-%d")
                
                template_str_parts = ["{{" + target_template] # Changed to string concatenation
                
                # Проверяем, является ли целевой шаблон "плохой перевод" 
                # и есть ли параметр "fromlang" в текущем наборе специальных параметров Rq
                if target_template == "плохой перевод" and "fromlang" in special_params:
                    fromlang_value = special_params["fromlang"]
                    template_str_parts.append(f"|язык={fromlang_value}") 
                    fromlang_wipe_ready = True 
                
                # Всегда добавляем параметр дата и закрывающие скобки
                template_str_parts.append(f"|дата={iso_date}" + "}}") # Changed to string concatenation
                
                final_template_str = "".join(template_str_parts)
                inside_content.append(final_template_str)
                # Обновляем отладочный вывод, чтобы он показывал полный сформированный шаблон
                alias_note = f" (ранее «{hist_param_for_summary}»)" if hist_param_for_summary.lower() != original_param.lower() else ""
                print_debug(f"       • Добавляется шаблон: {final_template_str} (из параметра '{original_param}'{alias_note}, ревизия {revid})")
                    
            if not inside_content:
                print_debug("    ⚠️ Не удалось сформировать внутренние шаблоны")
                continue
            
            # Формируем текст нового шаблона
            container_parts = ["{{" + template_name] # Имя Rq (с правильным регистром)
            
            has_added_any_param = False
            
            # Сначала обрабатываем специальные (именованные) параметры
            if special_params:
                first_special = True
                for name, value in sorted(special_params.items()): 
                    if name == "fromlang" and fromlang_wipe_ready:
                        print_debug(f"    ℹ️ Параметр 'fromlang' (значение: '{value}') был использован в шаблоне 'плохой перевод' и не будет добавлен в основной шаблон Rq.")
                        continue 
                    
                    processed_value = value
                    if name == "topic":
                        processed_value = normalize_rq_topic_value(value)
                        if processed_value != value: 
                            print_debug(f"    🔄 Нормализация topic: '{value}' → '{processed_value}'")
                    
                    if first_special:
                        container_parts.append(f"|{name}={processed_value}")
                        first_special = False
                    else:
                        container_parts.append(f"\n|{name}={processed_value}")
                    has_added_any_param = True
            
            # Затем добавляем вложенные шаблоны (неименованные параметры)
            if inside_content: # inside_content is guaranteed not to be empty here due to earlier check
                
                # Construct the full string for the single unnamed parameter
                # containing all sub-templates.
                unnamed_parameter_actual_content_parts = []
                # Start first sub-template on a new line for readability within the parameter
                unnamed_parameter_actual_content_parts.append("\n" + inside_content[0])
                for sub_template_str in inside_content[1:]:
                    # Subsequent sub-templates also start on a new line, NO pipe between them
                    unnamed_parameter_actual_content_parts.append("\n" + sub_template_str)
                
                full_unnamed_content_string = "".join(unnamed_parameter_actual_content_parts)

                if not has_added_any_param: # No named params yet, this is the very first parameter in {{rq|...}}
                    container_parts.append("|" + full_unnamed_content_string)
                else: # This unnamed parameter follows named parameters
                    container_parts[-1] += "|" # Append pipe to the last named parameter string
                    container_parts.append(full_unnamed_content_string) # Append the content string itself
                
                has_added_any_param = True
            
            # Завершаем шаблон Rq
            if has_added_any_param:
                container_parts.append("\n}}")
            else: # Если вообще не было параметров (пустой {{rq}})
                container_parts.append("}}")

            container_text = "".join(container_parts)
            
            # --- START NEW LOGIC: Simplify if only one inner template remains (unless topic has value) ---
            final_replacement_text_for_this_rq = container_text
            was_simplified_this_rq = False

            # Условие для упрощения: остался только один тип вложенного шаблона
            # ИЛИ параметр 'topic' отсутствует, ИЛИ параметр 'topic' пустой.
            if len(sorted_targets) == 1:
                # Проверяем, есть ли непустое значение у параметра 'topic'
                has_non_empty_topic = special_params.get('topic', '').strip()

                if not has_non_empty_topic:
                    # Упрощение возможно
                    single_target_template_name, _ = sorted_targets[0] # Нам нужно только имя

                    if inside_content: # Должно быть верно, если sorted_targets не пуст
                        final_replacement_text_for_this_rq = inside_content[0] # Это строка вида {{шаблон|дата=...}}
                        was_simplified_this_rq = True
                        print_debug(f"    ℹ️ Шаблон Rq с '{original_name}' будет упрощен до одиночного '{single_target_template_name}'.")
            # --- END NEW LOGIC ---

            # Заменяем шаблон в тексте
            old_template_str = str(template)
            current_text = current_text.replace(old_template_str, final_replacement_text_for_this_rq)
            changes_made = True
            
            print("    🔄 Замена шаблона:") 
            print(f"    • {old_template_str} → {final_replacement_text_for_this_rq}")

            processed_rq_details_for_summary.append({
                'original_rq_name_in_text': original_name,
                'was_simplified': was_simplified_this_rq,
                'final_param_dates_with_triggers': final_param_dates_with_triggers,
                'params_from_rq_for_summary': params, 
                'sorted_targets_for_summary': sorted_targets,
                'special_params_for_summary': special_params # Needed if summary logic depends on it
            })
        
        if changes_made:
            # Формируем описание правки
            summary_parts = []
            
            # for template, params, special_params, original_name in found_rq_templates:
            for rq_detail in processed_rq_details_for_summary:
                original_name = rq_detail['original_rq_name_in_text']
                was_simplified = rq_detail['was_simplified']
                local_final_param_dates = rq_detail['final_param_dates_with_triggers']
                params_for_summary_build = rq_detail['params_from_rq_for_summary']
                sorted_targets_for_summary_build = rq_detail['sorted_targets_for_summary']

                # Пропускаем, если нечего суммировать (маловероятно здесь, но для безопасности)
                if not was_simplified and not any(p in local_final_param_dates for p in params_for_summary_build):
                    continue

                display_name_rq = "Rq" if original_name[0].isupper() else "rq"

                if was_simplified:
                    if sorted_targets_for_summary_build: # Should be one item
                        single_target_name, (s_date, s_revid, s_original_param, s_hist_trigger) = sorted_targets_for_summary_build[0]
                        
                        # We need to build the 'final_details_in_parentheses' for this single param
                        # The key for local_final_param_dates is s_original_param (e.g., "img")
                        if s_original_param in local_final_param_dates:
                            date_detail, revid_detail, trigger_name_detail, trigger_type_detail = local_final_param_dates[s_original_param]
                            iso_date_detail = date_detail.strftime("%Y-%m-%d")
                            date_with_diff_link_detail = f"[[Special:Diff/{revid_detail}|{iso_date_detail}]]"
                            details_for_summary_text_detail = ""

                            if trigger_type_detail == 'rq':
                                if trigger_name_detail.lower() != s_original_param.lower():
                                    details_for_summary_text_detail = f"ранее {trigger_name_detail}, "
                            elif trigger_type_detail == 'standalone':
                                if compare_template_names(trigger_name_detail, single_target_name):
                                    details_for_summary_text_detail = f"шаблон уже был в статье, "
                                else:
                                    details_for_summary_text_detail = f"редирект [[ш:{trigger_name_detail}]] уже был в статье, "
                            
                            final_details_in_parentheses_simplified = ""
                            if details_for_summary_text_detail:
                                final_details_in_parentheses_simplified = f"({details_for_summary_text_detail}{date_with_diff_link_detail})"
                            else:
                                final_details_in_parentheses_simplified = f"({date_with_diff_link_detail})"
                            
                            # Original param (e.g. "img") part for the summary
                            # summary_param_part = f"{s_original_param} → [[ш:{single_target_name}]]"

                            # summary_parts.append(f"Замена [[ш:{display_name_rq}]] на {summary_param_part} {final_details_in_parentheses_simplified}")
                            # summary_parts.append(f"Замена [[ш:{display_name_rq}]] на [[ш:{single_target_name}]] {final_details_in_parentheses_simplified}")
                            # summary_parts.append(f"Замена [[ш:{display_name_rq}]] с единственным параметром {s_original_param} на [[ш:{single_target_name}]] {final_details_in_parentheses_simplified}")
                            summary_parts.append(f"[[ш:{display_name_rq}]] убран, т.к. осталась одна проблема: {s_original_param} → [[ш:{single_target_name}]] {final_details_in_parentheses_simplified}")
                        else: # Fallback if original param not in local_final_param_dates (should not happen)
                            iso_date_s = s_date.strftime("%Y-%m-%d")
                            date_with_diff_link_s = f"[[Special:Diff/{s_revid}|{iso_date_s}]]"
                            # summary_parts.append(f"Упрощение [[ш:{display_name_rq}]] до [[ш:{single_target_name}]] с датой установки {date_with_diff_link_s}")
                            summary_parts.append(f"[[ш:{display_name_rq}]] убран, т.к. осталась одна проблема: {s_original_param} → [[ш:{single_target_name}]] (дата установки {date_with_diff_link_s})")

                    else: # Should not happen if was_simplified is true
                        # summary_parts.append(f"Упрощение [[ш:{display_name_rq}]] до одиночного шаблона.")
                        summary_parts.append(f"[[ш:{display_name_rq}]] убран, т.к. осталась одна проблема (одиночный шаблон).")

                else: # Not simplified, build summary as before
                    param_dates_info = []
                    
                    # Сортируем параметры (из params_for_summary_build) по дате (из local_final_param_dates)
                    sorted_params_for_display = sorted(
                        [(p, local_final_param_dates[p]) for p in params_for_summary_build if p in local_final_param_dates],
                        key=lambda x: x[1][0]
                    )
                    
                    for param, (date, revid, trigger_name, trigger_type) in sorted_params_for_display: 
                        if param in RQ_PARAM_TEMPLATES:
                            target_template = RQ_PARAM_TEMPLATES[param]
                            iso_date = date.strftime("%Y-%m-%d")
                            
                            date_with_diff_link = f"[[Special:Diff/{revid}|{iso_date}]]"
                            details_for_summary_text = "" 
                            
                            if trigger_type == 'rq':
                                if trigger_name.lower() != param.lower(): 
                                    details_for_summary_text = f"ранее {trigger_name}, "
                            elif trigger_type == 'standalone':
                                if compare_template_names(trigger_name, target_template):
                                    details_for_summary_text = f"шаблон уже был в статье, "
                                else:
                                    details_for_summary_text = f"редирект [[ш:{trigger_name}]] уже был в статье, "
                            
                            final_details_in_parentheses = ""
                            if details_for_summary_text:
                                final_details_in_parentheses = f"({details_for_summary_text}{date_with_diff_link})"
                            else:
                                final_details_in_parentheses = f"({date_with_diff_link})"
                            
                            param_dates_info.append(f"{param} → [[ш:{target_template}]] {final_details_in_parentheses}")
                    
                    if param_dates_info:
                        summary_parts.append(f"Замена параметров [[ш:{display_name_rq}]] на вложенные шаблоны с датами установки: {', '.join(param_dates_info)}")
                
                summary = ". ".join(summary_parts)
                return True, current_text, summary
        else:
            return False, current_text, ""
    
    except Exception as e:
        print(f"❌ Ошибка при обработке шаблона Rq: {e}")
        return False, current_text, ""

def find_first_appearance(page: pywikibot.Page, 
                      revisions: List[Dict], 
                      search_mode: int,
                      template_search: bool = True,  # True для поиска шаблонов, False для поиска параметров Rq
                      templates_to_find: List[Tuple[str, Optional[str], Dict[str, str]]] = None,  # Для обычных шаблонов
                      sections_to_track: Set[str] = None,  # Для обычных шаблонов
                      template_info: Dict[str, Dict[str, str]] = None,  # Для обычных шаблонов
                      rq_templates: Dict[str, str] = None,  # Для параметров Rq
                      rq_params: List[str] = None  # Для параметров Rq
                     ) -> Union[Tuple[Dict[str, List[str]], Dict[str, Tuple[datetime, str, Optional[str], str]]], Dict[str, Tuple[datetime, str, str]]]:
    """
    Универсальная функция для поиска первого появления шаблонов или параметров шаблона Rq в статье.
    
    Args:
        page: Страница статьи
        revisions: Список ревизий
        search_mode: Режим поиска (1, 2 или 3)
        template_search: True для поиска шаблонов, False для поиска параметров Rq
        templates_to_find: Список шаблонов для поиска (для обычных шаблонов)
        sections_to_track: Множество разделов для отслеживания (для обычных шаблонов)
        template_info: Информация о шаблонах (для обычных шаблонов)
        rq_templates: Словарь редиректов шаблона Rq (для параметров Rq)
        rq_params: Список параметров шаблона Rq для поиска (для параметров Rq)
        
    Returns:
        Для template_search=True: Tuple[Dict[str, List[str]], Dict[str, Tuple[datetime, str, Optional[str], str]]]
            (section_history, template_results) - template_results содержит {ключ_шаблона: (timestamp, revid, section_name, variant_found)}
        Для template_search=False: Dict[str, Tuple[datetime, str, str]]
            словарь {параметр: (дата, id_ревизии, имя_параметра_в_той_ревизии)}
    """
    # Если search_mode == 1, разворачиваем список ревизий для поиска от конца
    if search_mode == 1:
        revisions = list(reversed(revisions))
    
    if template_search:
        # Логика поиска шаблонов как в функции find_template_and_section_history
        # Инициализируем историю всех разделов
        section_history = {section_name: [section_name] for section_name in sections_to_track}
        current_names = {section_name: section_name for section_name in sections_to_track}
        total_sections = len(sections_to_track)
        total_revisions = len(revisions)
        
        # Формируем ключи для templates_to_find_set единообразно
        templates_to_find_set = set()
        for t_tuple in templates_to_find: # t_tuple is (template_name, section_name, variants)
            key_name_part = t_tuple[0] # normalized template name
            key_section_part = t_tuple[1] # section name or None
            current_key = f"{key_name_part}_{key_section_part}" if key_section_part is not None else f"{key_name_part}_None"
            templates_to_find_set.add(current_key)
        
        # Проходим по ревизиям один раз для сбора истории всех разделов
        if sections_to_track:  # Выполняем поиск истории разделов только если есть разделы для отслеживания
            for rev_idx, rev in enumerate(revisions, 1):
                if 'text' not in rev or rev['text'] is None:
                    continue
                    
                text = rev['text']
                sections = find_sections(text)
                
                # Для каждого отслеживаемого раздела ищем его историческое название в этой ревизии
                for section_name in sections_to_track:
                    current_name = current_names[section_name]
                
                    # Ищем похожий раздел среди всех разделов в этой ревизии
                    for found_name, _, _ in sections:
                        if found_name in section_history[section_name]:
                            continue
                    
                        if sections_are_similar(current_name, found_name):
                            section_history[section_name].append(found_name)
                            current_names[section_name] = found_name  # Обновляем текущее название для следующей итерации
                            break
            
                # Показываем прогресс каждые 5%
                if rev_idx % max(1, total_revisions // 20) == 0:
                    progress = (rev_idx / total_revisions) * 100
                    print(f"\r        🔍 Поиск истории разделов: {progress:.1f}%", end='', flush=True)
            
            print("\r", end='')  # Очищаем строку прогресса
            
            # Выводим результаты поиска истории разделов
            for section_name, history in section_history.items():
                if search_mode == 1:
                    # Для режима 1 (от конца) разворачиваем историю
                    history.reverse()
                if len(history) > 1:
                    print(f"        📊 История раздела «{section_name}»")
                    print(f"            ↪️ {' → '.join(history)} ✓")
                else:
                    print(f"        📊 История раздела «{section_name}» (история не найдена)")
        
        print_debug(f"    ⏳ Начинаем поиск дат добавления шаблонов...")
        template_results = {}  # Хранит (timestamp, revid, section_name_at_addition)
        
        # Выбираем алгоритм поиска в зависимости от режима
        if search_mode == 1:  # Линейный поиск от конца
            # templates_to_find_set уже инициализирован выше
            first_occurrences = {}
            revision_cache = {}
            
            # Словарь для отслеживания шаблонов в текущей и следующей (более новой) ревизии
            templates_in_revision = {key: set() for key in templates_to_find_set}
            templates_in_next_revision = {key: set() for key in templates_to_find_set}
            
            # Сперва проверяем первую ревизию в списке (последнюю хронологически)
            if revisions:
                # Проверяем, доступна ли последняя ревизия
                if 'text' not in revisions[0] or revisions[0]['text'] is None:
                    print("        ⚠️ Последняя ревизия статьи недоступна!")
                    return {}, {}
                
                first_results = check_templates_in_revision(revisions[0], templates_to_find)
                revision_cache[0] = first_results
                
                # Заполняем шаблоны из последней ревизии
                for result_key, result_value in first_results.items():
                    result_parts = result_key.split('_', 1)
                    result_template = result_parts[0] 
                    result_section = result_parts[1] if len(result_parts) > 1 else None
                    
                    for template_key in list(templates_to_find_set):
                        template_parts = template_key.split('_', 1)
                        main_template = template_parts[0]
                        section = template_parts[1] if len(template_parts) > 1 else None
                        
                        templates_dict = next((t[2] for t in templates_to_find if t[0] == main_template), {})
                        
                        # Используем новую функцию сравнения
                        is_same_template = compare_template_names(result_template, main_template)
                        if not is_same_template:
                            # Проверяем редиректы
                            for redirect in templates_dict:
                                if compare_template_names(result_template, redirect):
                                    is_same_template = True
                                    break
                        
                        is_same_section = True
                        if section and result_section:
                            is_same_section = sections_are_similar(section, result_section)
                        elif section or result_section:
                            is_same_section = False
                        
                        if is_same_template and is_same_section:
                            templates_in_next_revision[template_key].add(result_key)
            
            print(f"\r        🔍 Поиск первого появления шаблонов (от последней ревизии)...", end='', flush=True)
            
            # Начинаем с индекса 1, так как 0 - это уже обработанная последняя ревизия
            for rev_idx in range(1, len(revisions)):
                current_rev = revisions[rev_idx]

                # Пропускаем удаленные/скрытые ревизии
                if 'text' not in current_rev or current_rev['text'] is None:
                    # Сохраняем состояние предыдущей ревизии для следующей итерации
                    # Это важно, чтобы корректно обрабатывать ситуации, когда несколько ревизий подряд удалены
                    continue

                # Проверяем текущую ревизию
                current_results = check_templates_in_revision(current_rev, templates_to_find)
                revision_cache[rev_idx] = current_results

                # Обрабатываем найденные шаблоны в текущей ревизии
                templates_in_revision = {key: set() for key in templates_to_find_set}
                for result_key, result_value in current_results.items():
                    result_parts = result_key.split('_', 1)
                    result_template = result_parts[0] 
                    result_section = result_parts[1] if len(result_parts) > 1 else None
                    
                    # Проверяем все искомые шаблоны
                    for template_key in list(templates_to_find_set):
                        template_parts = template_key.split('_', 1)
                        main_template = template_parts[0]
                        section = template_parts[1] if len(template_parts) > 1 else None
                        
                        # Получаем информацию о шаблоне и его редиректах
                        templates_dict = next((t[2] for t in templates_to_find if t[0] == main_template), {})
                        
                        # Используем новую функцию сравнения
                        is_same_template = compare_template_names(result_template, main_template)
                        if not is_same_template:
                            # Проверяем редиректы
                            for redirect in templates_dict:
                                if compare_template_names(result_template, redirect):
                                    is_same_template = True
                                    break
                        
                        is_same_section = True
                        if section and result_section:
                            is_same_section = sections_are_similar(section, result_section)
                        elif section or result_section:  # Один есть, другого нет
                            is_same_section = False
                        
                        # Если это тот же шаблон и нужный раздел, добавляем в текущие шаблоны
                        if is_same_template and is_same_section:
                            templates_in_revision[template_key].add(result_key)
                
                # Находим шаблоны, которые есть в следующей (более новой) ревизии, но отсутствуют в текущей
                for template_key in list(templates_to_find_set):
                    if templates_in_next_revision[template_key] and not templates_in_revision[template_key]:
                        # Шаблон есть в следующей ревизии, но отсутствует в текущей
                        # Значит, он был добавлен между текущей и следующей ревизиями
                        # Мы нашли ревизию, где шаблон впервые появился - это СЛЕДУЮЩАЯ ревизия
                        
                        # Берем данные из предыдущей ревизии в списке (следующей хронологически)
                        prev_rev_idx = rev_idx - 1
                        
                        # Проверяем, доступна ли предыдущая ревизия и содержит ли она текст
                        if prev_rev_idx < 0 or prev_rev_idx not in revision_cache:
                            continue
                            
                        prev_rev = revisions[prev_rev_idx]
                        if 'text' not in prev_rev or prev_rev['text'] is None:
                            # Если предыдущая ревизия недоступна, пропускаем обнаружение шаблона
                            continue
                            
                        prev_results = revision_cache[prev_rev_idx]
                        
                        # Находим первый ключ из вариантов шаблона, который присутствует
                        for variant_key in templates_in_next_revision[template_key]:
                            if variant_key in prev_results:
                                timestamp, revid, found_section, variant_found = prev_results[variant_key] # Unpack variant_found
                                
                                first_occurrences[template_key] = (timestamp, revid, found_section, variant_found) # Store variant_found
                                templates_to_find_set.remove(template_key)
                                
                                # Выводим информацию о найденном шаблоне
                                template_name_for_log = next(t[0] for t in templates_to_find if (f"{t[0]}_{t[1]}" if t[1] is not None else f"{t[0]}_None") == template_key)
                                section_name_for_log = next(t[1] for t in templates_to_find if (f"{t[0]}_{t[1]}" if t[1] is not None else f"{t[0]}_None") == template_key)
                                
                                if section_name_for_log:
                                    print_debug(f"\n        ✨ [{template_name_for_log}] Найдено первое появление шаблона в разделе «{found_section}»: {timestamp.strftime('%Y-%m-%d')}")
                                else:
                                    print_debug(f"\n        ✨ [{template_name_for_log}] Найдено первое появление шаблона: {timestamp.strftime('%Y-%m-%d')}")
                                break
                
                # Подготавливаем данные для следующей итерации
                templates_in_next_revision = templates_in_revision
                
                # Проверяем, нужно ли продолжать поиск
                if not templates_to_find_set:  # Если все шаблоны найдены, прекращаем поиск
                    break
                    
                # Показываем прогресс
                if rev_idx % max(1, len(revisions) // 20) == 0:
                    templates_found = len(first_occurrences)
                    total_templates = len(templates_to_find)
                    progress = (rev_idx + 1) / len(revisions) * 100
                    print(f"\r        🔍 Поиск шаблонов: найдено {templates_found}/{total_templates} • {progress:.1f}% ({rev_idx + 1}/{len(revisions)})", end='', flush=True)
            
            # Проверка шаблонов, которые могли быть добавлены в первой ревизии статьи
            # и остались необнаруженными, потому что нет предыдущей ревизии для сравнения
            if templates_to_find_set and len(revisions) > 0:
                # Проверяем последнюю ревизию в списке (она же первая хронологически)
                last_rev_idx = len(revisions) - 1
                last_rev = revisions[last_rev_idx]
                
                # Если ревизия ещё не кэширована, проверяем её
                if last_rev_idx not in revision_cache:
                    last_results = check_templates_in_revision(last_rev, templates_to_find)
                    revision_cache[last_rev_idx] = last_results
                else:
                    last_results = revision_cache[last_rev_idx]
                
                # Проверяем все оставшиеся ненайденные шаблоны
                for template_key in list(templates_to_find_set):
                    for result_key, result_value in last_results.items():
                        result_parts = result_key.split('_', 1)
                        result_template = result_parts[0]
                        result_section = result_parts[1] if len(result_parts) > 1 else None
                        
                        template_parts = template_key.split('_', 1)
                        main_template = template_parts[0]
                        section = template_parts[1] if len(template_parts) > 1 else None
                        
                        templates_dict = next((t[2] for t in templates_to_find if t[0] == main_template), {})
                        
                        # Используем новую функцию сравнения
                        is_same_template = compare_template_names(result_template, main_template)
                        if not is_same_template:
                            # Проверяем редиректы
                            for redirect in templates_dict:
                                if compare_template_names(result_template, redirect):
                                    is_same_template = True
                                    break
                        
                        is_same_section = True
                        if section and result_section:
                            is_same_section = sections_are_similar(section, result_section)
                        elif section or result_section:
                            is_same_section = False
                        
                        if is_same_template and is_same_section:
                            # Шаблон найден в первой ревизии, значит он был добавлен при создании статьи
                            timestamp, revid, found_section, variant_found = result_value # Unpack variant_found
                            first_occurrences[template_key] = (timestamp, revid, found_section, variant_found) # Store variant_found
                            templates_to_find_set.remove(template_key)
                            
                            # Выводим информацию о найденном шаблоне
                            template_name_for_log = next(t[0] for t in templates_to_find if (f"{t[0]}_{t[1]}" if t[1] is not None else f"{t[0]}_None") == template_key)
                            section_name_for_log = next(t[1] for t in templates_to_find if (f"{t[0]}_{t[1]}" if t[1] is not None else f"{t[0]}_None") == template_key)
                            
                            if section_name_for_log:
                                print_debug(f"\n        ✨ [{template_name_for_log}] Найдено первое появление шаблона в разделе «{found_section}» (добавлен при создании статьи): {timestamp.strftime('%Y-%m-%d')}")
                            else:
                                print_debug(f"\n        ✨ [{template_name_for_log}] Найдено первое появление шаблона (добавлен при создании статьи): {timestamp.strftime('%Y-%m-%d')}")
                            break
            
            template_results = first_occurrences
            
        elif search_mode == 2:  # Линейный поиск от первой ревизии
            # templates_to_find_set уже инициализирован выше
            first_occurrences = {}
            revision_cache = {}
            
            for rev_idx, rev in enumerate(revisions):
                # Пропускаем удаленные/скрытые ревизии
                if 'text' not in rev or rev['text'] is None:
                    continue
                
                current_results = check_templates_in_revision(rev, templates_to_find)
                revision_cache[rev_idx] = current_results
                
                for template_key in list(templates_to_find_set):
                    if template_key in current_results and template_key not in first_occurrences:
                        # Нашли потенциальное первое появление
                        timestamp, revid, found_section, variant_found = current_results[template_key] # Unpack variant_found
                        first_occurrences[template_key] = (timestamp, revid, found_section, variant_found) # Store variant_found
                        templates_to_find_set.remove(template_key)
                        
                        # Выводим информацию о найденном шаблоне
                        template_name_for_log = next(t[0] for t in templates_to_find if (f"{t[0]}_{t[1]}" if t[1] is not None else f"{t[0]}_None") == template_key)
                        section_name_for_log = next(t[1] for t in templates_to_find if (f"{t[0]}_{t[1]}" if t[1] is not None else f"{t[0]}_None") == template_key)
                        if section_name_for_log:
                            print_debug(f"\n        ✨ [{template_name_for_log}] Найдено первое появление шаблона в разделе «{found_section}»: {timestamp.strftime('%Y-%m-%d')}")
                        else:
                            print_debug(f"\n        ✨ [{template_name_for_log}] Найдено первое появление шаблона: {timestamp.strftime('%Y-%m-%d')}")

                # Обновляем прогресс
                templates_found = len(first_occurrences)
                total_templates = len(templates_to_find)
                print(f"\r        🔍 Поиск шаблонов: {templates_found}/{total_templates} (проверено ревизий: {rev_idx + 1})", end='', flush=True)

                if not templates_to_find_set:  # Если нашли все шаблоны
                    break
                    
            template_results = first_occurrences
            
        else:  # Бинарный поиск (search_mode == 3)
            # Логика бинарного поиска (можно перенести из find_template_and_section_history)
            first_occurrences = {}
            revision_cache = {}
            checked_revisions = set()  # Множество для отслеживания проверенных ревизий
            total_revisions = len(revisions)
            start_time = time.time()
            iterations = 0
            
            # Создаём отдельные диапазоны поиска для каждого шаблона
            search_ranges = {}
            for t_tuple_range in templates_to_find:
                key_name_part_range = t_tuple_range[0]
                key_section_part_range = t_tuple_range[1]
                current_key_range = f"{key_name_part_range}_{key_section_part_range}" if key_section_part_range is not None else f"{key_name_part_range}_None"
                search_ranges[current_key_range] = {'left': 0, 'right': len(revisions) - 1, 'first_found': None}
            
            def check_revision(rev_idx: int) -> Dict[str, Tuple[datetime, str, str]]:
                if rev_idx < 0 or rev_idx >= total_revisions:
                    return {}  # Защита от выхода за границы
                    
                checked_revisions.add(rev_idx)  # Отмечаем ревизию как проверенную
                if rev_idx in revision_cache:
                    return revision_cache[rev_idx]
                
                # Проверяем наличие текста в ревизии
                rev = revisions[rev_idx]
                if 'text' not in rev or rev['text'] is None:
                    # Если ревизия недоступна, возвращаем пустой результат
                    revision_cache[rev_idx] = {}
                    return {}
                
                current_results = check_templates_in_revision(revisions[rev_idx], templates_to_find)
                revision_cache[rev_idx] = current_results
                return current_results
            
            # Продолжаем поиск, пока есть непроверенные диапазоны
            while search_ranges:
                iterations += 1
                if iterations % 10 == 0:
                    print(f"\r        🔍 Итерация {iterations}: активных диапазонов {len(search_ranges)}, проверено {len(checked_revisions)}/{total_revisions} ревизий", end='', flush=True)
                    
                # Обработка диапазонов, которые исчерпаны
                keys_to_remove = []
                for template_key, range_info in search_ranges.items():
                    if range_info['left'] > range_info['right']:
                        if range_info['first_found'] is not None:
                            # first_found уже должен быть кортежем из 4 элементов
                            timestamp, revid, found_section, variant_found = range_info['first_found'] # Unpack variant_found
                            first_occurrences[template_key] = (timestamp, revid, found_section, variant_found) # Store variant_found (already should be correct)
                            template_name_for_log = next((t[0] for t in templates_to_find if (f"{t[0]}_{t[1]}" if t[1] is not None else f"{t[0]}_None") == template_key), "")
                            section_name_for_log = next((t[1] for t in templates_to_find if (f"{t[0]}_{t[1]}" if t[1] is not None else f"{t[0]}_None") == template_key), None)
                            if section_name_for_log:
                                print_debug(f"\n        ✨ [{template_name_for_log}] Найдено первое появление шаблона с параметром 'раздел' в разделе «{found_section}»: {timestamp.strftime('%Y-%m-%d')}")
                            elif found_section: # Для шаблонов разделов, где section_name_for_log может быть None, если t_tuple[1] был None
                                print_debug(f"\n        ✨ [{template_name_for_log}] Найдено первое появление шаблона в разделе «{found_section}»: {timestamp.strftime('%Y-%m-%d')}")
                            else:
                                print_debug(f"\n        ✨ [{template_name_for_log}] Найдено первое появление шаблона: {timestamp.strftime('%Y-%m-%d')}")
                        keys_to_remove.append(template_key)
                
                # Удаляем обработанные диапазоны
                for key in keys_to_remove:
                    search_ranges.pop(key, None)
                    
                if not search_ranges:  # Все диапазоны исчерпаны
                    break
                                                    
                # Выбираем следующую точку для проверки (обрабатываем по одному диапазону за раз)
                next_mid = None
                next_template_key = None
                
                # Выбираем один диапазон для проверки (вместо группировки)
                for template_key, range_info in search_ranges.items():
                    if range_info['left'] <= range_info['right']:
                        next_mid = (range_info['left'] + range_info['right']) // 2
                        next_template_key = template_key
                        break
                                        
                if next_mid is None:  # Не нашли точку для проверки
                    break
                    
                # Проверяем выбранную точку
                current_results = check_revision(next_mid)
                
                # Обновляем диапазон для выбранного шаблона
                if next_template_key not in search_ranges:
                    continue  # Шаблон мог быть удален в другом потоке
                    
                range_info = search_ranges[next_template_key]
                
                if next_template_key in current_results:
                    # Нашли шаблон, проверяем предыдущую ревизию
                    if next_mid > 0:
                        prev_results = check_revision(next_mid - 1)
                        if next_template_key not in prev_results:
                            # Это первое появление
                            first_occurrences[next_template_key] = current_results[next_template_key]
                            search_ranges.pop(next_template_key, None)
                            timestamp, revid, found_section, variant_found = current_results[next_template_key]
                            template_name_for_log = next((t[0] for t in templates_to_find if (f"{t[0]}_{t[1]}" if t[1] is not None else f"{t[0]}_None") == next_template_key), "")
                            section_name_for_log = next((t[1] for t in templates_to_find if (f"{t[0]}_{t[1]}" if t[1] is not None else f"{t[0]}_None") == next_template_key), None)
                            if section_name_for_log:
                                print_debug(f"\n        ✨ [{template_name_for_log}] Найдено первое появление шаблона в разделе «{found_section}»: {timestamp.strftime('%Y-%m-%d')}")
                            else:
                                print_debug(f"\n        ✨ [{template_name_for_log}] Найдено первое появление шаблона: {timestamp.strftime('%Y-%m-%d')}")
                            continue
                    
                    # Сохраняем это вхождение как потенциально первое и продолжаем поиск в более ранних ревизиях
                    range_info['first_found'] = current_results[next_template_key]
                    range_info['right'] = next_mid - 1
                else:
                    # Шаблон не найден, ищем в более поздних ревизиях
                    range_info['left'] = next_mid + 1
                
                # Обновляем прогресс каждые несколько итераций
                if iterations % 5 == 0:
                    templates_found = len(first_occurrences)
                    total_templates = len(templates_to_find)
                    checked_count = len(checked_revisions)
                    checked_percent = (checked_count / total_revisions) * 100
                    print(f"\r        🔍 Поиск шаблонов: {templates_found}/{total_templates} (проверено ревизий: {checked_count}/{total_revisions}, {checked_percent:.1f}%)", end='', flush=True)
            
            # Финальное обновление прогресса
            templates_found = len(first_occurrences)
            total_templates = len(templates_to_find)
            checked_count = len(checked_revisions)
            checked_percent = (checked_count / total_revisions) * 100
            print(f"\r        🔍 Поиск шаблонов: {templates_found}/{total_templates} (проверено ревизий: {checked_count}/{total_revisions}, {checked_percent:.1f}%)", end='', flush=True)
            
            print(f"\n        📊 Всего проверено {len(checked_revisions)} из {total_revisions} ревизий ({(len(checked_revisions) / total_revisions * 100):.1f}%)")
            print(f"        ⏱️ Время поиска: {(time.time() - start_time):.1f} секунд, выполнено {iterations} итераций")
            
            template_results = first_occurrences
        print()
        print_debug("\n    ✅ Поиск дат добавления шаблонов завершен")
        return section_history, template_results
    
    else:
        # Логика поиска параметров Rq как в функции find_rq_param_addition_dates
        # Создаем обратный словарь редиректов для поиска по нормализованным названиям
        normalized_redirects = {template.lower(): template for template in rq_templates.values()}
        
        # Результаты поиска {ключ_параметра_из_последней_версии: (дата, id_ревизии, имя_параметра_в_той_ревизии)}
        param_dates: Dict[str, Tuple[datetime, str, str]] = {}
        
        print_debug(f"    ⏳ Начинаем поиск дат добавления параметров шаблона Rq...")
        print_debug(f"       Параметры для поиска: {', '.join(rq_params)}")
        print_debug(f"       Режим поиска: {search_mode} ({('от последней ревизии' if search_mode == 1 else 'от первой ревизии' if search_mode == 2 else 'бинарный поиск')})")
        print_debug(f"       Количество ревизий: {len(revisions)}")
        
        # --- START MODIFICATION ---
        # Для режима 1: отслеживаем состояние в следующей (хронологически) ревизии
        # Ключи - параметры из rq_params (т.е. из последней версии статьи)
        # Значение - имя исторического параметра, который вызвал срабатывание для этой концепции, или None
        hist_triggers_in_next_rev: Dict[str, Optional[str]] = {lp: None for lp in rq_params}
        next_rev_timestamp = None 
        next_rev_id = None
        
        # Вспомогательная функция для определения, какие концепции из rq_params присутствуют в ревизии
        # и какой конкретно исторический параметр их вызвал.
        def get_hist_triggers_for_concepts(text: Optional[str], target_rq_params_list: List[str]) -> Dict[str, Optional[str]]:
            # Инициализируем все ключи (параметры из последней версии) как None (триггер не найден)
            hist_triggers_map: Dict[str, Optional[str]] = {lp: None for lp in target_rq_params_list}
            if text is None:
                return hist_triggers_map
            
            try:
                wikicode_rev = mwparserfromhell.parse(text)
                for template_rev in wikicode_rev.filter_templates():
                    template_name_rev_lower = str(template_rev.name).strip().lower()
                    if template_name_rev_lower in normalized_redirects: # Это Rq шаблон
                        params_in_hist_template, _ = extract_rq_params(template_rev)
                        
                        for hist_param_name_original_case in params_in_hist_template: # например, "source" (оригинальный регистр)
                            hist_param_name_lower = hist_param_name_original_case.lower()
                            if hist_param_name_lower in RQ_PARAM_TEMPLATES:
                                target_tpl_for_hist_param = RQ_PARAM_TEMPLATES[hist_param_name_lower]
                                
                                for latest_param_name in target_rq_params_list: # например, "sources" из rq_params
                                    # Если для этой концепции (latest_param_name) еще не найден триггер в этой ревизии
                                    if hist_triggers_map[latest_param_name] is None:
                                        latest_param_name_lower = latest_param_name.lower()
                                        if latest_param_name_lower in RQ_PARAM_TEMPLATES:
                                            target_tpl_for_latest_param = RQ_PARAM_TEMPLATES[latest_param_name_lower]
                                            
                                            if target_tpl_for_hist_param == target_tpl_for_latest_param:
                                                # Нашли! hist_param_name_original_case является триггером для концепции latest_param_name
                                                hist_triggers_map[latest_param_name] = hist_param_name_original_case
                                                # Можно было бы здесь `break` для внутреннего цикла по latest_param_name,
                                                # но это не нужно, т.к. внешний if hist_triggers_map[latest_param_name] is None заботится об этом.
            except Exception: 
                pass 
            return hist_triggers_map

        # Для режима 1: инициализируем состояние hist_triggers_in_next_rev на основе самой последней ревизии
        if search_mode == 1 and revisions:
            latest_chronological_rev = revisions[0]
            next_rev_timestamp = latest_chronological_rev['timestamp']
            next_rev_id = latest_chronological_rev['revid']
            if 'text' in latest_chronological_rev:
                 hist_triggers_in_next_rev = get_hist_triggers_for_concepts(latest_chronological_rev['text'], rq_params)
            else:
                print("        ⚠️ Не удалось обработать последнюю ревизию для инициализации поиска Rq параметров.")
        # --- END MODIFICATION ---
        
        # Просматриваем все ревизии
        start_index = 1 if search_mode == 1 and revisions else 0
        for rev_idx in range(start_index, len(revisions)):
            rev = revisions[rev_idx]
            current_rev_timestamp = rev['timestamp']
            current_rev_id = rev['revid']
            
            hist_triggers_in_current_rev: Dict[str, Optional[str]]
            
            if 'text' not in rev:
                # Если текст ревизии отсутствует, считаем, что никаких триггеров в ней нет
                hist_triggers_in_current_rev = {lp: None for lp in rq_params}
                if search_mode == 1:
                    # Для режима 1, если текущая (более старая) ревизия не имеет текста,
                    # а следующая (более новая, next_rev) имела триггер, то добавление произошло в next_rev.
                    for param_key in rq_params:
                        trigger_in_next = hist_triggers_in_next_rev.get(param_key)
                        if param_key not in param_dates and trigger_in_next is not None:
                            param_dates[param_key] = (next_rev_timestamp, str(next_rev_id), trigger_in_next)
                            print_debug(f"        ✨ Найдено первое появление концепции «{param_key}» (как «{trigger_in_next}»): {next_rev_timestamp.strftime('%Y-%m-%d')} (перед ревизией без текста)")
                # Пропускаем основную логику для этой ревизии, т.к. нет текста
                # В режиме 1, состояние next_rev обновится на это "пустое" состояние в конце итерации.
                if search_mode == 1:
                    hist_triggers_in_next_rev = hist_triggers_in_current_rev.copy() # станет {lp: None}
                    next_rev_timestamp = current_rev_timestamp # дата этой "пустой" ревизии
                    next_rev_id = current_rev_id
                continue

            current_text = rev['text']
            hist_triggers_in_current_rev = get_hist_triggers_for_concepts(current_text, rq_params)
            
            try:
                if search_mode == 1:
                    for param_key in rq_params:
                        trigger_in_next = hist_triggers_in_next_rev.get(param_key)
                        trigger_in_current = hist_triggers_in_current_rev.get(param_key)
                        
                        if param_key not in param_dates and trigger_in_next is not None and trigger_in_current is None:
                            param_dates[param_key] = (next_rev_timestamp, str(next_rev_id), trigger_in_next)
                            print_debug(f"        ✨ Найдено первое появление концепции «{param_key}» (как «{trigger_in_next}»): {next_rev_timestamp.strftime('%Y-%m-%d')}")
                
                elif search_mode == 2:
                    for param_key in rq_params:
                        trigger_in_current = hist_triggers_in_current_rev.get(param_key)
                        if param_key not in param_dates and trigger_in_current is not None:
                            param_dates[param_key] = (current_rev_timestamp, str(current_rev_id), trigger_in_current)
                            print_debug(f"        ✨ Найдено первое появление концепции «{param_key}» (как «{trigger_in_current}»): {current_rev_timestamp.strftime('%Y-%m-%d')}")
                
                if search_mode == 1:
                    hist_triggers_in_next_rev = hist_triggers_in_current_rev.copy()
                    next_rev_timestamp = current_rev_timestamp
                    next_rev_id = current_rev_id
                
                if len(param_dates) == len(rq_params):
                    break
                
                processed_count_display = rev_idx if search_mode == 1 and revisions else rev_idx + 1
                if processed_count_display % max(1, len(revisions) // 10) == 0:
                    print(f"\r        🔍 Поиск параметров: найдено {len(param_dates)}/{len(rq_params)} • {processed_count_display}/{len(revisions)}", end='', flush=True)
            
            except Exception as e:
                print(f"❌ Ошибка при обработке ревизии {current_rev_id}: {e}")
        
        if search_mode == 1 and revisions:
            earliest_chronological_rev = revisions[-1]
            if 'text' in earliest_chronological_rev:
                # Для режима 1, hist_triggers_in_next_rev должен содержать состояние самой ранней ревизии, если цикл дошел до нее.
                # Но безопаснее пересчитать для самой ранней.
                hist_triggers_in_earliest_rev = get_hist_triggers_for_concepts(earliest_chronological_rev['text'], rq_params)
                for param_key in rq_params:
                    trigger_in_earliest = hist_triggers_in_earliest_rev.get(param_key)
                    if param_key not in param_dates and trigger_in_earliest is not None:
                        param_dates[param_key] = (earliest_chronological_rev['timestamp'], str(earliest_chronological_rev['revid']), trigger_in_earliest)
                        print_debug(f"        ✨ Найдено первое появление концепции «{param_key}» (как «{trigger_in_earliest}», в самой ранней ревизии): {earliest_chronological_rev['timestamp'].strftime('%Y-%m-%d')}")
            
        if search_mode == 2 and revisions and (len(param_dates) < len(rq_params)):
            first_chronological_rev = revisions[0]
            if 'text' in first_chronological_rev:
                # hist_triggers_in_current_rev будет содержать состояние первой ревизии, если цикл дошел до нее
                # и она была последней обработанной. Пересчитаем для ясности.
                hist_triggers_in_first_rev = get_hist_triggers_for_concepts(first_chronological_rev['text'], rq_params)
                for param_key in rq_params:
                    trigger_in_first = hist_triggers_in_first_rev.get(param_key)
                    if param_key not in param_dates and trigger_in_first is not None:
                        param_dates[param_key] = (first_chronological_rev['timestamp'], str(first_chronological_rev['revid']), trigger_in_first)
                        print_debug(f"        ✨ Найдено первое появление концепции «{param_key}» (как «{trigger_in_first}», в первой ревизии): {first_chronological_rev['timestamp'].strftime('%Y-%m-%d')}")
        print()
        print_debug(f"\n    ✅ Найдены даты для {len(param_dates)}/{len(rq_params)} концепций параметров шаблона Rq")
        return param_dates

def normalize_rq_topic_value(topic_value: str) -> str:
    """
    Нормализует значение параметра topic= для шаблона Rq.
    Приводит к нижнему регистру и ищет в RQ_TOPIC_NORMALIZATION_MAP.
    Если найдено, возвращает каноническое значение.
    Если не найдено, возвращает исходное значение topic_value (с сохраненным регистром).
    """
    topic_value_lower = topic_value.lower()
    if topic_value_lower in RQ_TOPIC_NORMALIZATION_MAP:
        return RQ_TOPIC_NORMALIZATION_MAP[topic_value_lower]
    return topic_value # Возвращаем исходное значение с его регистром, если нет в карте

def handle_debug_save_interaction(page: pywikibot.Page, new_text: str, summary: str):
    """
    Обрабатывает взаимодействие с пользователем для сохранения изменений в режиме отладки.
    """
    print(f"🔄 Предлагаемое описание правки: {summary}")
    while True:
        print("\nДействия для отладки:")
        print("1 - сохранить изменения в статью")
        print("2 - пропустить сохранение")
        print("3 - показать предлагаемый текст статьи в консоли")
        
        response = input("Введите номер действия (1/2/3): ").strip()
        
        if response == "1":
            if not summary: 
                print("\nℹ️ Нет изменений для сохранения (описание пустое).")
                break
            try:
                page.text = new_text
                page.save(summary=summary, minor=True)
                print(f"\n✅ Сохранены изменения в статье «{page.title()}»")
            except Exception as e:
                print(f"\n❌ Ошибка при сохранении статьи: {e}")
            break
        elif response == "2":
            print("\nПропущено сохранение.")
            break
        elif response == "3":
            print("\n📄 Предлагаемый текст статьи:")
            print("=" * 100)
            print(new_text)
            print("=" * 100)
        else:
            print("\n⚠️ Пожалуйста, введите 1, 2 или 3.")

def handle_debug_mode(site: pywikibot.Site):
    """
    Обрабатывает логику отладки для одной статьи в соответствии с текущим CONFIG['mode'].
    """
    print(f"\n🔍 Режим отладки для статьи: {CONFIG['debug_article']} (используется логика режима: {CONFIG['mode']})")
    page = pywikibot.Page(site, CONFIG['debug_article'])
    if not page.exists():
        print("❌ Указанная для отладки статья не существует")
        return

    debug_templates_for_meta_single = {} 
    if CONFIG['mode'] == 'single' or CONFIG['mode'] == 'meta' or (CONFIG['mode'] == 'metarq'):
        category_source_for_templates = CONFIG['single_category']
        if CONFIG['mode'] == 'meta':
             print(f"ℹ️ В режиме отладки 'meta' будут использованы шаблоны из '{category_source_for_templates}' для контекста.")
        elif CONFIG['mode'] == 'metarq':
             print(f"ℹ️ В режиме отладки 'metarq', для мета-части будут использованы шаблоны из '{category_source_for_templates}'.")

        category_page = pywikibot.Page(site, category_source_for_templates)
        if category_page.exists():
            debug_templates_for_meta_single = get_templates_from_category(site, category_page)
            if debug_templates_for_meta_single:
                 print(f"ℹ️ Для отладки загружены шаблоны из категории '{category_source_for_templates}':")
                 for template, redirects in debug_templates_for_meta_single.items():
                    template_cap = template[0].upper() + template[1:]
                    redirect_list = [r[0].upper() + r[1:] for r in redirects if r != template]
                    print(f"    🔵 «{template_cap}»" + (f" (редиректы: {', '.join(redirect_list)})" if redirect_list else ""))
            else:
                print(f"⚠️ Не найдены шаблоны в категории '{category_source_for_templates}' для отладки.")
        else:
            print(f"❌ Категория '{category_source_for_templates}' для получения шаблонов в режиме отладки не существует.")

    creation_date = page.oldest_revision.timestamp
    revision_count = page.revision_count()
    print_article_header(page, creation_date, revision_count, 1, 1, 1, 1, 1, 1)
    print("=" * 100)

    if CONFIG['mode'] == 'metarq':
        print("\n--- Отладка: Этап 1 (Meta-логика) ---")
        success1, _, _, _, update_info1, _ = process_article_with_limit(
            page, debug_templates_for_meta_single, CONFIG['search_mode'], CONFIG['max_revisions'], revision_count,
            should_process_rq=False
        )
        if update_info1:
            handle_debug_save_interaction(page, update_info1[0], update_info1[1])
        else:
            print("ℹ️ Отладка (Этап 1 - Meta-логика): Нет изменений.")
        
        # Перезагружаем текст статьи, если были сохранения
        if update_info1 and CONFIG['autosave']: # Или если был ручной сейв, но это сложнее отследить без изменения handle_debug_save_interaction
             page = pywikibot.Page(site, CONFIG['debug_article']) # Перезагрузка

        print("\n--- Отладка: Этап 2 (Rq-логика) ---")
        success2, _, _, _, update_info2, _ = process_article_with_limit(
            page, {}, CONFIG['search_mode'], CONFIG['max_revisions'], revision_count,
            should_process_rq=True
        )
        if update_info2:
            handle_debug_save_interaction(page, update_info2[0], update_info2[1])
        else:
            print("ℹ️ Отладка (Этап 2 - Rq-логика): Нет изменений.")
    else: 
        current_debug_templates_for_call = {}
        _should_process_rq_debug = False # Default for unknown

        if CONFIG['mode'] == 'rq':
            _should_process_rq_debug = True
        elif CONFIG['mode'] == 'meta' or CONFIG['mode'] == 'single':
            _should_process_rq_debug = False
            current_debug_templates_for_call = debug_templates_for_meta_single
        else: # Unknown mode
            print(f"⚠️ Неизвестный режим '{CONFIG['mode']}' в логике отладки. Обработка Rq будет отключена (process_rq = False).")
            _should_process_rq_debug = False
            # current_debug_templates_for_call остается {}, так как непонятно, какие шаблоны использовать

        print(f"--- Отладка: Логика режима '{CONFIG['mode']}' (process_rq: {_should_process_rq_debug}) ---")
        success, _, _, _, update_info, _ = process_article_with_limit(
            page, current_debug_templates_for_call, CONFIG['search_mode'], CONFIG['max_revisions'], revision_count,
            should_process_rq=_should_process_rq_debug
        )
        if update_info:
            handle_debug_save_interaction(page, update_info[0], update_info[1])
        else:
            print(f"ℹ️ Отладка (Логика режима '{CONFIG['mode']}'): Нет изменений.")

def main():
    global RQ_STANDALONE_REDIRECT_CACHE
    site = pywikibot.Site('ru', 'wikipedia')
    print("🔑 Выполняется вход в систему...")
    site.login()
    print("✅ Вход выполнен успешно")
    
    RQ_STANDALONE_REDIRECT_CACHE = load_rq_redirect_cache_from_json(RQ_STANDALONE_REDIRECT_CACHE_FILE)
    
    if not RQ_STANDALONE_REDIRECT_CACHE:
        print("ℹ️ Кэш редиректов RQ пуст или не найден. Заполняем из RQ_PARAM_TEMPLATES...")
        unique_target_templates = set(RQ_PARAM_TEMPLATES.values())
        
        if unique_target_templates:
            total_templates_to_cache = len(unique_target_templates)
            cached_count = 0
            print_debug(f"    🔍 Всего уникальных шаблонов для кэширования: {total_templates_to_cache}")

            for template_name_val in unique_target_templates:
                if template_name_val:
                    get_template_redirects(site, template_name_val, use_rq_specific_cache=True)
                    cached_count += 1
                    if cached_count % 5 == 0 or cached_count == total_templates_to_cache:
                        print_debug(f"        🔄 Прогресс кэширования: {cached_count}/{total_templates_to_cache} шаблонов...")
            print("✅ Кэш редиректов RQ заполнен и сохранен.")
        else:
            print("    ⚠️ В RQ_PARAM_TEMPLATES нет значений для кэширования.")

    if CONFIG['debug_article']:
        handle_debug_mode(site)
        return

    category_templates = {}
    category_counts = {}

    if CONFIG['mode'] == 'single':
        CONFIG['process_rq'] = False
        print(f"\n🔍 Сканирование категории {CONFIG['single_category']} (только стандартная обработка)...")
        category = pywikibot.Page(site, CONFIG['single_category'])
        if not category.exists():
            print("❌ Указанная категория не существует")
            return

        templates = get_templates_from_category(site, category)
        if not templates:
            print("⚠️ Не найдены шаблоны в категории")
            return

        article_count = len(list(pywikibot.Category(site, CONFIG['single_category']).articles()))
        category_templates = {CONFIG['single_category']: templates}
        category_counts = {CONFIG['single_category']: article_count}
        
        for template, redirects in templates.items():
            template_cap = template[0].upper() + template[1:]
            redirect_list = [r[0].upper() + r[1:] for r in redirects if r != template]
            print(f"🔵 «{template_cap}»")
            if redirect_list:
                print(f"       ↪️ {', '.join(redirect_list)}")
                
        print(f"\n📊 Категория содержит {article_count} статей")
        process_articles(site, category_templates, CONFIG['search_mode'], category_counts,
                         process_rq_for_this_run=False)

    elif CONFIG['mode'] == 'meta':
        CONFIG['process_rq'] = False
        print(f"\n🔍 Сканирование метакатегории {CONFIG['meta_category']} (только стандартная обработка)...")
        active_categories_with_counts = get_active_subcategories(site, CONFIG['meta_category'])
        if not active_categories_with_counts:
            print("❌ Нет активных подкатегорий")
            return

        print(f"\n📊 Найдено {len(active_categories_with_counts)} категорий:")
        for category_name, count in active_categories_with_counts:
            category_counts[category_name] = count
            print(f"    • {category_name} ({count} статей)")
        
        active_categories = [cat for cat, _ in active_categories_with_counts]
        category_templates = get_templates_by_categories(site, active_categories)

        if not category_templates:
            print("\n⚠️ Не найдены шаблоны в категориях")
            return
        process_articles(site, category_templates, CONFIG['search_mode'], category_counts,
                         process_rq_for_this_run=False)

    elif CONFIG['mode'] == 'rq':
        CONFIG['process_rq'] = True
        print(f"\n🔍 Сканирование категории с шаблонами Rq: {CONFIG['rq_category']} (только обработка Rq)...")
        rq_category_page = pywikibot.Page(site, CONFIG['rq_category'])
        if not rq_category_page.exists():
            print("❌ Указанная категория не существует")
            return

        templates = {} # Шаблоны из категории не нужны для режима Rq
        article_count = len(list(pywikibot.Category(site, CONFIG['rq_category']).articles()))
        category_templates = {CONFIG['rq_category']: templates}
        category_counts = {CONFIG['rq_category']: article_count}

        print(f"\n📊 Категория содержит {article_count} статей")
        process_articles(site, category_templates, CONFIG['search_mode'], category_counts,
                         process_rq_for_this_run=True)

    elif CONFIG['mode'] == 'metarq':
        print("\n🚀 Запуск режима 'metarq'")
        print("-" * 30)
        print("Этап 1: Обработка подкатегорий из 'meta_category' (стандартная обработка)")
        print("-" * 30)
        CONFIG['process_rq'] = False
        meta_category_templates = {}
        meta_category_counts = {}

        print(f"\n🔍 Сканирование метакатегории {CONFIG['meta_category']}...")
        active_categories_with_counts_meta = get_active_subcategories(site, CONFIG['meta_category'])
        if not active_categories_with_counts_meta:
            print("❌ Нет активных подкатегорий в метакатегории.")
        else:
            print(f"\n📊 Найдено {len(active_categories_with_counts_meta)} категорий:")
            for category_name, count in active_categories_with_counts_meta:
                meta_category_counts[category_name] = count
                print(f"    • {category_name} ({count} статей)")

            active_categories_meta = [cat for cat, _ in active_categories_with_counts_meta]
            meta_category_templates = get_templates_by_categories(site, active_categories_meta)

            if not meta_category_templates:
                print("\n⚠️ Не найдены шаблоны в подкатегориях метакатегории.")
            else:
                print("\n📊 Итоговая статистика (Этап 1 - Meta):")
                total_articles_meta = sum(meta_category_counts.values())
                total_templates_meta = sum(len(cat_templates) for cat_templates in meta_category_templates.values())
                total_redirects_meta = 0
                for cat_templates in meta_category_templates.values():
                    for template, redirects in cat_templates.items():
                        total_redirects_meta += len([r for r in redirects if r != template])

                print(f"  • Категорий: {len(meta_category_templates)}")
                print(f"  • Шаблонов: {total_templates_meta}")
                print(f"  • Редиректов: {total_redirects_meta}")
                print(f"  • Статей для обработки: {total_articles_meta}")

                print("\n🚀 Начинаем обработку статей (Этап 1 - Meta)...")
                process_articles(site, meta_category_templates, CONFIG['search_mode'], meta_category_counts,
                                 process_rq_for_this_run=False)
                print("\n✅ Этап 1 (Meta) завершен.")

        print("-" * 30)
        print(f"Этап 2: Обработка категории '{CONFIG['rq_category']}' (только Rq)")
        print("-" * 30)
        CONFIG['process_rq'] = True
        rq_category_templates_metarq = {} # Renamed to avoid conflict
        rq_category_counts_metarq = {}    # Renamed to avoid conflict

        print(f"\n🔍 Сканирование категории с шаблонами Rq: {CONFIG['rq_category']}...")
        rq_category_page_metarq = pywikibot.Page(site, CONFIG['rq_category'])
        if not rq_category_page_metarq.exists():
            print("❌ Указанная категория Rq не существует. Пропуск этапа 2.")
        else:
            templates_rq_metarq = {} # Renamed to avoid conflict
            article_count_rq_metarq = len(list(pywikibot.Category(site, CONFIG['rq_category']).articles())) # Renamed
            rq_category_templates_metarq = {CONFIG['rq_category']: templates_rq_metarq}
            rq_category_counts_metarq = {CONFIG['rq_category']: article_count_rq_metarq}

            print(f"\n📊 Категория Rq содержит {article_count_rq_metarq} статей")
            print("\n🚀 Начинаем обработку статей (Этап 2 - Rq)...")
            process_articles(site, rq_category_templates_metarq, CONFIG['search_mode'], rq_category_counts_metarq,
                             process_rq_for_this_run=True)
            print("\n✅ Этап 2 (Rq) завершен.")
        print("\n✅ Режим 'metarq' полностью завершен.")

    else:
        print(f"❌ Неверный режим работы: {CONFIG['mode']}")
        print("Допустимые значения: 'single', 'meta', 'rq' или 'metarq'")

if __name__ == "__main__":
    main()