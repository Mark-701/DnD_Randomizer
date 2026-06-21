import re

from config import SOURCE_CODE
from db import cursor
from parsers.common import (
    CLASS_NAMES, clean_name, clean_page_description, ensure_class, extract_known_skills,
    get_or_create_source, get_sitemap_urls, get_soup, load_ability_map, page_name, page_text,
    print_result, source_matches, split_heading_sections
)

PH14_CLASSES = {
    'Варвар': ('d12', 'Сила', ['Атлетика', 'Восприятие', 'Выживание', 'Запугивание', 'Природа', 'Уход за животными']),
    'Бард': ('d8', 'Харизма', CLASS_NAMES and ['Акробатика', 'Атлетика', 'Выступление', 'Запугивание', 'История', 'Ловкость рук', 'Магия', 'Медицина', 'Обман', 'Природа', 'Проницательность', 'Религия', 'Скрытность', 'Убеждение', 'Уход за животными', 'Анализ', 'Восприятие', 'Выживание']),
    'Жрец': ('d8', 'Мудрость', ['История', 'Медицина', 'Проницательность', 'Религия', 'Убеждение']),
    'Друид': ('d8', 'Мудрость', ['Восприятие', 'Выживание', 'Магия', 'Медицина', 'Природа', 'Проницательность', 'Религия', 'Уход за животными']),
    'Воин': ('d10', 'Сила', ['Акробатика', 'Атлетика', 'Восприятие', 'Выживание', 'Запугивание', 'История', 'Проницательность', 'Уход за животными']),
    'Монах': ('d8', 'Ловкость', ['Акробатика', 'Атлетика', 'История', 'Проницательность', 'Религия', 'Скрытность']),
    'Паладин': ('d10', 'Сила', ['Атлетика', 'Запугивание', 'Медицина', 'Проницательность', 'Религия', 'Убеждение']),
    'Следопыт': ('d10', 'Ловкость', ['Анализ', 'Атлетика', 'Восприятие', 'Выживание', 'Природа', 'Проницательность', 'Скрытность', 'Уход за животными']),
    'Плут': ('d8', 'Ловкость', ['Акробатика', 'Атлетика', 'Восприятие', 'Выступление', 'Запугивание', 'Ловкость рук', 'Обман', 'Проницательность', 'Скрытность', 'Убеждение', 'Анализ']),
    'Чародей': ('d6', 'Харизма', ['Запугивание', 'Магия', 'Обман', 'Проницательность', 'Религия', 'Убеждение']),
    'Колдун': ('d8', 'Харизма', ['Анализ', 'Запугивание', 'История', 'Магия', 'Обман', 'Природа', 'Религия']),
    'Волшебник': ('d6', 'Интеллект', ['Анализ', 'История', 'Магия', 'Медицина', 'Проницательность', 'Религия']),
}

CLASS_ALIASES = {
    'Бард': 'Бард', 'Варвар': 'Варвар', 'Воин': 'Воин', 'Волшебник': 'Волшебник',
    'Друид': 'Друид', 'Жрец': 'Жрец', 'Колдун': 'Колдун', 'Монах': 'Монах',
    'Паладин': 'Паладин', 'Плут': 'Плут', 'Разбойник': 'Плут', 'Следопыт': 'Следопыт',
    'Рейнджер': 'Следопыт', 'Чародей': 'Чародей', 'Сорcerer': 'Чародей',
}

SUBCLASS_STOP = ['создание', 'быстрое создание', 'умения класса', 'классовые умения', 'снаряжение', 'заклинания']


def normalize_class_name(name: str):
    name = clean_name(name)
    return CLASS_ALIASES.get(name, name)


def get_class_links():
    return get_sitemap_urls(r'/classes/\d+')


def extract_hit_die(text: str, fallback: str):
    m = re.search(r'(?:Кость хитов|Хиты|Hit Dice|Hit Die)\s*[:.]?\s*[^\n.]*?(d\d+|к\d+)', text, flags=re.I)
    if not m:
        return fallback
    return m.group(1).lower().replace('к', 'd')


def extract_subclasses(soup):
    result = []
    for s in split_heading_sections(soup):
        title = clean_name(s['title'])
        low = title.lower()
        if any(x in low for x in SUBCLASS_STOP):
            continue
        text = s['text']
        if len(title) < 4 or len(title) > 80:
            continue
        if re.search(r'(архетип|домен|клятва|коллегия|круг|путь|традиция|покровитель|происхождение|школа|мастер|вор|ассасин|берсерк|чемпион)', title + ' ' + text[:250], flags=re.I):
            if title not in result:
                result.append({'name': title, 'description': text})
    return result[:12]


def parse_class(url: str):
    soup = get_soup(url)
    text = page_text(soup)
    if not source_matches(text):
        return None
    name = normalize_class_name(page_name(soup))
    if name not in PH14_CLASSES:
        return None
    hit_die, primary, fallback_skills = PH14_CLASSES[name]
    parsed_skills = extract_known_skills(text)
    return {
        'name': name,
        'description': clean_page_description(text),
        'hit_die': extract_hit_die(text, hit_die),
        'primary_ability': primary,
        'skills': parsed_skills or fallback_skills,
        'subclasses': extract_subclasses(soup),
    }


def save_class(data, source_id: int) -> int:
    ability_id = load_ability_map().get(data['primary_ability'].lower())
    with cursor() as cur:
        cur.execute('SELECT id FROM classes WHERE lower(name)=lower(%s)', (data['name'],))
        row = cur.fetchone()
        if row:
            class_id = row[0]
            cur.execute(
                'UPDATE classes SET description=%s, hit_die=%s, primary_ability_id=%s, source_id=%s WHERE id=%s',
                (data['description'], data['hit_die'], ability_id, source_id, class_id),
            )
        else:
            cur.execute(
                'INSERT INTO classes (name, description, hit_die, primary_ability_id, source_id) VALUES (%s,%s,%s,%s,%s) RETURNING id',
                (data['name'], data['description'], data['hit_die'], ability_id, source_id),
            )
            class_id = cur.fetchone()[0]
        cur.execute('DELETE FROM class_skill_choices WHERE class_id=%s', (class_id,))
        cur.execute('DELETE FROM subclasses WHERE class_id=%s', (class_id,))
        return class_id


def save_class_skills(class_id: int, skills: list[str]):
    with cursor() as cur:
        for skill in skills:
            cur.execute('SELECT id FROM skills WHERE lower(name)=lower(%s)', (skill,))
            row = cur.fetchone()
            if row:
                cur.execute(
                    'INSERT INTO class_skill_choices (class_id, skill_id) VALUES (%s,%s) ON CONFLICT (class_id, skill_id) DO NOTHING',
                    (class_id, row[0]),
                )


def save_subclasses(class_id: int, subclasses: list[dict], source_id: int):
    with cursor() as cur:
        for sub in subclasses:
            cur.execute(
                'INSERT INTO subclasses (name, description, class_id, source_id) VALUES (%s,%s,%s,%s)',
                (sub['name'], sub['description'], class_id, source_id),
            )


def parse_all_classes():
    source_id = get_or_create_source()
    urls = get_class_links()
    print(f'Найдено ссылок классов в sitemap: {len(urls)}')
    success = failed = skipped = 0
    parsed = set()
    for url in urls:
        try:
            data = parse_class(url)
            if not data:
                skipped += 1
                continue
            class_id = save_class(data, source_id)
            save_class_skills(class_id, data['skills'])
            save_subclasses(class_id, data['subclasses'], source_id)
            parsed.add(data['name'])
            print(f"+ {data['name']} | навыков: {len(data['skills'])} | подклассов: {len(data['subclasses'])}")
            success += 1
        except Exception as exc:
            print(f'Ошибка класса {url}: {exc}')
            failed += 1

    # Fallback добавляет базовые 12 классов, если сайт/разметка не дала часть ссылок.
    for name, (hit_die, primary, skills) in PH14_CLASSES.items():
        if name in parsed:
            continue
        try:
            data = {'name': name, 'description': f'Класс PH14: {name}', 'hit_die': hit_die, 'primary_ability': primary, 'skills': skills, 'subclasses': []}
            class_id = save_class(data, source_id)
            save_class_skills(class_id, skills)
            print(f'+ {name} [fallback] | навыков: {len(skills)}')
            success += 1
        except Exception as exc:
            print(f'Ошибка fallback класса {name}: {exc}')
            failed += 1
    print_result('КЛАССЫ PH14', success, failed, skipped)
