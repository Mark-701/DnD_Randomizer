import re

from db import cursor
from parsers.common import (
    clean_name, clean_page_description, extract_known_skills, field_value, get_or_create_simple,
    get_or_create_source, get_sitemap_urls, get_soup, page_name, page_text, print_result, source_matches
)

PH14_BACKGROUND_SKILLS = {
    'Прислужник': ['Проницательность', 'Религия'],
    'Шарлатан': ['Ловкость рук', 'Обман'],
    'Преступник': ['Обман', 'Скрытность'],
    'Артист': ['Акробатика', 'Выступление'],
    'Народный герой': ['Выживание', 'Уход за животными'],
    'Гильдейский ремесленник': ['Проницательность', 'Убеждение'],
    'Отшельник': ['Медицина', 'Религия'],
    'Благородный': ['История', 'Убеждение'],
    'Чужеземец': ['Атлетика', 'Выживание'],
    'Мудрец': ['История', 'Магия'],
    'Моряк': ['Атлетика', 'Восприятие'],
    'Солдат': ['Атлетика', 'Запугивание'],
    'Беспризорник': ['Ловкость рук', 'Скрытность'],
}

BACKGROUND_ALIASES = {
    'Аколит': 'Прислужник', 'Прислужник': 'Прислужник', 'Артист': 'Артист', 'Гладиатор': 'Артист',
    'Гильдейский ремесленник': 'Гильдейский ремесленник', 'Гильдейский торговец': 'Гильдейский ремесленник',
    'Беспризорник': 'Беспризорник', 'Уличный мальчишка': 'Беспризорник',
}


def normalize_background_name(name: str) -> str:
    name = clean_name(name)
    return BACKGROUND_ALIASES.get(name, name)


def get_background_links():
    return get_sitemap_urls(r'/backgrounds/\d+')


def extract_feature(text: str):
    feature_name = ''
    feature_description = ''
    m = re.search(r'(?:Умение|Особенность)\s*[:.]\s*([^\n.]+)', text, flags=re.I)
    if m:
        feature_name = clean_name(m.group(1))
        start = m.end()
        feature_description = text[start:start + 1200].strip()
    return feature_name or None, clean_page_description(feature_description) or None


def extract_tools(text: str):
    line = field_value(text, ['Владение инструментами', 'Инструменты'])
    if not line:
        return []
    line = re.split(r'[.\n]', line)[0]
    return [clean_name(x) for x in re.split(r',| или | и ', line) if clean_name(x)]


def parse_background(url: str):
    soup = get_soup(url)
    text = page_text(soup)
    if not source_matches(text):
        return None
    name = normalize_background_name(page_name(soup))
    if name not in PH14_BACKGROUND_SKILLS:
        return None
    feature_name, feature_description = extract_feature(text)
    skill_line = field_value(text, 'Владение навыками')
    return {
        'name': name,
        'description': clean_page_description(text),
        'feature_name': feature_name,
        'feature_description': feature_description,
        'skills': extract_known_skills(skill_line) or PH14_BACKGROUND_SKILLS[name],
        'tools': extract_tools(text),
    }


def save_background(data, source_id: int) -> int:
    with cursor() as cur:
        cur.execute(
            """
            INSERT INTO backgrounds (name, description, feature_name, feature_description, source_id)
            VALUES (%s,%s,%s,%s,%s)
            ON CONFLICT (name) DO UPDATE
            SET description=EXCLUDED.description,
                feature_name=EXCLUDED.feature_name,
                feature_description=EXCLUDED.feature_description,
                source_id=EXCLUDED.source_id
            RETURNING id
            """,
            (data['name'], data['description'], data['feature_name'], data['feature_description'], source_id),
        )
        bg_id = cur.fetchone()[0]
        cur.execute('DELETE FROM background_skills WHERE background_id=%s', (bg_id,))
        cur.execute('DELETE FROM background_tools WHERE background_id=%s', (bg_id,))
        return bg_id


def save_background_skills(background_id: int, skills: list[str]):
    with cursor() as cur:
        for skill in skills:
            cur.execute('SELECT id FROM skills WHERE lower(name)=lower(%s)', (skill,))
            row = cur.fetchone()
            if row:
                cur.execute('INSERT INTO background_skills (background_id, skill_id) VALUES (%s,%s) ON CONFLICT DO NOTHING', (background_id, row[0]))


def save_background_tools(background_id: int, tools: list[str]):
    with cursor() as cur:
        for tool in tools:
            tool_id = get_or_create_simple('tool_proficiencies', tool)
            cur.execute('INSERT INTO background_tools (background_id, tool_id) VALUES (%s,%s) ON CONFLICT DO NOTHING', (background_id, tool_id))


def parse_all_backgrounds():
    source_id = get_or_create_source()
    urls = get_background_links()
    print(f'Найдено ссылок предысторий в sitemap: {len(urls)}')
    success = failed = skipped = 0
    parsed = set()
    for url in urls:
        try:
            data = parse_background(url)
            if not data:
                skipped += 1
                continue
            bg_id = save_background(data, source_id)
            save_background_skills(bg_id, data['skills'])
            save_background_tools(bg_id, data['tools'])
            parsed.add(data['name'])
            print(f"+ {data['name']} | навыков: {len(data['skills'])} | инструментов: {len(data['tools'])}")
            success += 1
        except Exception as exc:
            print(f'Ошибка предыстории {url}: {exc}')
            failed += 1

    for name, skills in PH14_BACKGROUND_SKILLS.items():
        if name in parsed:
            continue
        try:
            data = {'name': name, 'description': f'Предыстория PH14: {name}', 'feature_name': None, 'feature_description': None, 'skills': skills, 'tools': []}
            bg_id = save_background(data, source_id)
            save_background_skills(bg_id, skills)
            print(f'+ {name} [fallback] | навыков: {len(skills)}')
            success += 1
        except Exception as exc:
            print(f'Ошибка fallback предыстории {name}: {exc}')
            failed += 1
    print_result('ПРЕДЫСТОРИИ PH14', success, failed, skipped)
