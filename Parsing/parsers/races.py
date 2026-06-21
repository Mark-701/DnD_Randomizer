import re

from db import cursor
from parsers.common import (
    clean_name, clean_page_description, choice_bonus_options, extract_ability_bonuses, extract_speed,
    fixed_bonus, get_or_create_simple, get_or_create_source, get_sitemap_urls, get_soup,
    page_name, page_text, print_result, source_matches, split_heading_sections
)

# ВАЖНО: этот файл специально ограничен только расами и подрасами PH14.
# Никакие расы/подрасы из других книг сюда не добавляются.
PH14_RACES = {
    'Дварф': {
        'speed': 25,
        'bonuses': [('Телосложение', 2)],
        'languages': ['Общий', 'Дварфский'],
        'subraces': {
            'Холмовой дварф': [('Мудрость', 1)],
            'Горный дварф': [('Сила', 2)],
        },
    },
    'Эльф': {
        'speed': 30,
        'bonuses': [('Ловкость', 2)],
        'languages': ['Общий', 'Эльфийский'],
        'subraces': {
            'Высший эльф': [('Интеллект', 1)],
            'Лесной эльф': [('Мудрость', 1)],
            'Дроу': [('Харизма', 1)],
        },
    },
    'Полурослик': {
        'speed': 25,
        'bonuses': [('Ловкость', 2)],
        'languages': ['Общий', 'Полуросликов'],
        'subraces': {
            'Легконогий полурослик': [('Харизма', 1)],
            'Коренастый полурослик': [('Телосложение', 1)],
        },
    },
    'Человек': {
        'speed': 30,
        'bonuses': [('Сила', 1), ('Ловкость', 1), ('Телосложение', 1), ('Интеллект', 1), ('Мудрость', 1), ('Харизма', 1)],
        'languages': ['Общий'],
        'subraces': {},
    },
    'Драконорождённый': {
        'speed': 30,
        'bonuses': [('Сила', 2), ('Харизма', 1)],
        'languages': ['Общий', 'Драконий'],
        'subraces': {},
    },
    'Гном': {
        'speed': 25,
        'bonuses': [('Интеллект', 2)],
        'languages': ['Общий', 'Гномий'],
        'subraces': {
            'Лесной гном': [('Ловкость', 1)],
            'Скальный гном': [('Телосложение', 1)],
        },
    },
    'Полуэльф': {
        'speed': 30,
        'bonuses': [('Харизма', 2)],
        'choice': (2, 1),
        'languages': ['Общий', 'Эльфийский'],
        'subraces': {},
    },
    'Полуорк': {
        'speed': 30,
        'bonuses': [('Сила', 2), ('Телосложение', 1)],
        'languages': ['Общий', 'Орочий'],
        'subraces': {},
    },
    'Тифлинг': {
        'speed': 30,
        'bonuses': [('Интеллект', 1), ('Харизма', 2)],
        'languages': ['Общий', 'Инфернальный'],
        'subraces': {},
    },
}

# Слова, по которым можно понять страницу из sitemap, не открывая каждую расу подряд.
# Это не источник истины, а только быстрый предварительный фильтр URL.
PH14_RACE_URL_KEYWORDS = {
    'Дварф': ['dwarf', 'dwarves', 'дварф', 'дворф'],
    'Эльф': ['elf', 'elves', 'эльф'],
    'Полурослик': ['halfling', 'полурослик'],
    'Человек': ['human', 'человек', 'люди'],
    'Драконорождённый': ['dragonborn', 'драконорожден', 'драконорожд'],
    'Гном': ['gnome', 'гном'],
    'Полуэльф': ['half-elf', 'half_elf', 'halfelf', 'полуэльф'],
    'Полуорк': ['half-orc', 'half_orc', 'halforc', 'полуорк'],
    'Тифлинг': ['tiefling', 'тифлинг'],
}

RACE_ALIASES = {
    'Дварфы': 'Дварф', 'Дворф': 'Дварф', 'Дворфы': 'Дварф',
    'Эльфы': 'Эльф', 'Полурослики': 'Полурослик', 'Люди': 'Человек',
    'Драконорождённые': 'Драконорождённый', 'Драконорожденный': 'Драконорождённый', 'Драконорожденные': 'Драконорождённый',
    'Гномы': 'Гном', 'Полуэльфы': 'Полуэльф', 'Полуорки': 'Полуорк', 'Тифлинги': 'Тифлинг',
}

SUBRACE_ALIASES = {
    'Тёмный эльф': 'Дроу', 'Темный эльф': 'Дроу', 'Тёмные эльфы': 'Дроу', 'Темные эльфы': 'Дроу', 'Дроу': 'Дроу',
}


def normalize_for_compare(text: str) -> str:
    return re.sub(r'\s+', ' ', (text or '').lower().replace('ё', 'е')).strip()


def normalize_race_name(name: str) -> str:
    name = clean_name(name)
    return RACE_ALIASES.get(name, name)


def normalize_subrace_name(name: str) -> str:
    name = clean_name(name)
    low = normalize_for_compare(name)
    for raw, normalized in SUBRACE_ALIASES.items():
        if normalize_for_compare(raw) in low:
            return normalized
    return name


def fallback_bonuses(race_name: str):
    info = PH14_RACES[race_name]
    bonuses = [fixed_bonus(a, b) for a, b in info.get('bonuses', [])]
    if 'choice' in info:
        count, value = info['choice']
        fixed_abilities = [ability for ability, _ in info.get('bonuses', [])]
        bonuses.extend(choice_bonus_options(
            count,
            value,
            'Две другие характеристики на выбор +1',
            exclude=fixed_abilities,
        ))
    return bonuses


def fallback_subrace_bonuses(race_name: str, subrace_name: str):
    data = PH14_RACES[race_name]['subraces'].get(subrace_name, [])
    return [fixed_bonus(a, b) for a, b in data]


def url_looks_like_ph14_race(url: str) -> bool:
    low_url = normalize_for_compare(url)
    return any(keyword in low_url for keywords in PH14_RACE_URL_KEYWORDS.values() for keyword in keywords)


def get_race_links():
    """
    Берём из sitemap только URL, похожие на 9 рас PH14.
    Раньше парсер перебирал все /race/..., из-за чего проходил по расам из других книг.
    Теперь sitemap используется только для поиска страниц этих 9 рас, а окончательная проверка PH14
    всё равно делается внутри parse_race().
    """
    urls = get_sitemap_urls(r'/race/\d+')
    links = []
    seen = set()
    for url in urls:
        if url in seen:
            continue
        seen.add(url)
        if url_looks_like_ph14_race(url):
            links.append(url)
    return links


def find_base_section(soup):
    sections = split_heading_sections(soup)
    for s in sections:
        title = s['title'].lower()
        if 'особенности' in title or 'расовые особенности' in title:
            return f"{s['title']}\n{s['text']}"
    text = page_text(soup)
    parts = re.split(r'\n\s*(?:Подрасы|Разновидности|Подраса)\b', text, maxsplit=1, flags=re.I)
    return parts[0]


def find_subrace_sections(soup, race_name: str):
    allowed = set(PH14_RACES[race_name]['subraces'].keys())
    if not allowed:
        return []

    result = []
    for s in split_heading_sections(soup):
        title = normalize_subrace_name(s['title'])
        # Жёсткий whitelist: сохраняются только PH14-подрасы текущей расы.
        if title in allowed:
            result.append({
                'name': title,
                'description': s['text'],
                'bonuses': extract_ability_bonuses(s['text']) or fallback_subrace_bonuses(race_name, title),
            })

    found = {x['name'] for x in result}
    for subrace_name in allowed - found:
        result.append({
            'name': subrace_name,
            'description': f'Подраса PH14 для расы {race_name}',
            'bonuses': fallback_subrace_bonuses(race_name, subrace_name),
        })

    return sorted(result, key=lambda x: list(PH14_RACES[race_name]['subraces']).index(x['name']))


def parse_race(url: str):
    soup = get_soup(url)
    full_text = page_text(soup)

    # Главное правило проекта: всё только из PH14.
    if not source_matches(full_text):
        return None

    race_name = normalize_race_name(page_name(soup))
    if race_name not in PH14_RACES:
        return None

    base_section = find_base_section(soup)

    # ВАЖНО: бонусы характеристик для PH14 НЕ берём из произвольного текста страницы.
    # На dnd.su в одной странице/блоке могут находиться варианты из других источников,
    # а регулярные выражения иногда цепляют только первый подходящий блок, например дварфа.
    # Поэтому для PH14 бонусы берутся из белого списка PH14_RACES.
    bonuses = fallback_bonuses(race_name)
    speed = extract_speed(base_section, PH14_RACES[race_name]['speed'])

    # Подрасы тоже PH14-only; их бонусы берутся из PH14_RACES, а не из текста сайта.
    subraces = [
        {
            'name': subrace_name,
            'description': f'Подраса PH14 для расы {race_name}',
            'bonuses': fallback_subrace_bonuses(race_name, subrace_name),
        }
        for subrace_name in PH14_RACES[race_name].get('subraces', {})
    ]

    return {
        'name': race_name,
        'description': clean_page_description(full_text),
        'speed': speed,
        'bonuses': bonuses,
        'languages': PH14_RACES[race_name]['languages'],
        'subraces': subraces,
    }


def save_race(data, source_id: int) -> int:
    with cursor() as cur:
        cur.execute(
            """
            INSERT INTO races (name, description, speed, source_id)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (name) DO UPDATE
            SET description=EXCLUDED.description, speed=EXCLUDED.speed, source_id=EXCLUDED.source_id
            RETURNING id
            """,
            (data['name'], data['description'], data['speed'], source_id),
        )
        race_id = cur.fetchone()[0]
        cur.execute('DELETE FROM race_ability_bonuses WHERE race_id=%s', (race_id,))
        cur.execute('DELETE FROM race_languages WHERE race_id=%s', (race_id,))
        cur.execute('DELETE FROM subraces WHERE race_id=%s', (race_id,))
        return race_id


def save_bonuses(owner_column: str, owner_id: int, bonuses: list[dict]):
    if owner_column not in ('race_id', 'subrace_id'):
        raise ValueError('owner_column должен быть race_id или subrace_id')
    with cursor() as cur:
        cur.execute(f'DELETE FROM race_ability_bonuses WHERE {owner_column}=%s', (owner_id,))
        for b in bonuses:
            cur.execute(
                f"""
                INSERT INTO race_ability_bonuses
                    ({owner_column}, ability_score_id, bonus, is_choice, choice_count, description)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (owner_id, b.get('ability_score_id'), b['bonus'], b.get('is_choice', False), b.get('choice_count'), b.get('description')),
            )


def save_languages(race_id: int, language_names: list[str]):
    with cursor() as cur:
        for lang in language_names:
            language_id = get_or_create_simple('languages', lang)
            cur.execute(
                """
                INSERT INTO race_languages (race_id, language_id)
                VALUES (%s, %s)
                ON CONFLICT (race_id, language_id) DO NOTHING
                """,
                (race_id, language_id),
            )


def save_subrace(race_id: int, subrace: dict, source_id: int) -> int:
    with cursor() as cur:
        cur.execute(
            """
            INSERT INTO subraces (name, description, race_id, source_id)
            VALUES (%s, %s, %s, %s)
            RETURNING id
            """,
            (subrace['name'], subrace['description'], race_id, source_id),
        )
        return cur.fetchone()[0]


def build_base_race_data(name: str, info: dict) -> dict:
    return {
        'name': name,
        'description': f'Раса PH14: {name}',
        'speed': info['speed'],
        'bonuses': fallback_bonuses(name),
        'languages': info['languages'],
        'subraces': [
            {
                'name': subrace_name,
                'description': f'Подраса PH14 для расы {name}',
                'bonuses': fallback_subrace_bonuses(name, subrace_name),
            }
            for subrace_name in info.get('subraces', {})
        ],
    }


def save_full_race(data: dict, source_id: int):
    race_id = save_race(data, source_id)
    save_bonuses('race_id', race_id, data['bonuses'])
    save_languages(race_id, data['languages'])
    for subrace in data['subraces']:
        subrace_id = save_subrace(race_id, subrace, source_id)
        save_bonuses('subrace_id', subrace_id, subrace['bonuses'])
    return race_id


def parse_all_races():
    """
    Строгий режим PH14.
    В БД заносятся только 9 PH14-рас и только разрешённые PH14-подрасы.
    Sitemap не является источником данных о расах; он используется только для возможного обновления
    описаний этих же 9 рас. Если сайт отдаст лишние расы, они будут пропущены.
    """
    source_id = get_or_create_source()

    success = 0
    failed = 0

    # 1. Гарантированная база PH14.
    for name, info in PH14_RACES.items():
        try:
            data = build_base_race_data(name, info)
            save_full_race(data, source_id)
            print(f"+ {name} [PH14] | бонусов: {len(data['bonuses'])} | подрас: {len(data['subraces'])}")
            success += 1
        except Exception as exc:
            print(f'Ошибка добавления PH14-расы {name}: {exc}')
            failed += 1

    # 2. Дополнительное обогащение только страницами, похожими на 9 PH14-рас.
    try:
        urls = get_race_links()
        print(f'Найдено PH14-кандидатов рас в sitemap: {len(urls)}')
    except Exception as exc:
        print(f'Не удалось получить sitemap, оставлены базовые данные PH14: {exc}')
        print_result('РАСЫ PH14', success, failed, 0)
        return

    enriched = 0
    skipped = 0
    updated_names = set()

    for url in urls:
        try:
            data = parse_race(url)
            if not data:
                skipped += 1
                continue

            # Последняя защита от любых не-PH14 рас.
            if data['name'] not in PH14_RACES:
                skipped += 1
                continue

            # Не обновляем одну и ту же расу несколько раз, чтобы страница из другого источника не перетёрла PH14.
            if data['name'] in updated_names:
                skipped += 1
                continue

            save_full_race(data, source_id)
            updated_names.add(data['name'])
            print(f"~ обновлено PH14-страницей: {data['name']} | бонусов: {len(data['bonuses'])} | подрас: {len(data['subraces'])}")
            enriched += 1
        except Exception as exc:
            print(f'Ошибка обновления PH14-расы со страницы: {url}\n{exc}')
            failed += 1

    print(f'Обновлено страницами сайта: {enriched}')
    print_result('РАСЫ PH14', success, failed, skipped)
