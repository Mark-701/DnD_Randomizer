import re

from db import cursor
from parsers.common import clean_page_description, field_value, get_or_create_simple, get_or_create_source, get_sitemap_urls, get_soup, page_name, page_text, print_result, source_matches

RARITIES = ['Обычный', 'Необычный', 'Редкий', 'Очень редкий', 'Легендарный', 'Артефакт']
TYPES = ['Оружие', 'Доспех', 'Кольцо', 'Жезл', 'Посох', 'Зелье', 'Свиток', 'Чудесный предмет', 'Щит', 'Амулет']


def get_magic_item_links():
    return get_sitemap_urls(r'/(magic-items|magicitems|items)/\d+')


def detect_rarity(text: str) -> str:
    low = text.lower()
    for rarity in RARITIES:
        if rarity.lower() in low[:1500]:
            return rarity
    return 'Обычный'


def detect_type(text: str) -> str:
    low = text.lower()
    for typ in TYPES:
        if typ.lower() in low[:1500]:
            return typ
    return 'Чудесный предмет'


def parse_magic_item(url: str):
    soup = get_soup(url)
    text = page_text(soup)
    if not source_matches(text):
        return None
    # В PH14 магических предметов почти нет; этот парсер безопасно заполнит только найденные PH14-страницы.
    if not re.search(r'магическ|редкост|настройк|attunement', text, flags=re.I):
        return None
    return {
        'name': page_name(soup),
        'type': detect_type(text),
        'rarity': detect_rarity(text),
        'description': clean_page_description(text),
        'attunement_required': bool(re.search(r'требуется\s+настройка|настройк[аи]|attunement', text, flags=re.I)),
        'attunement_requirements': field_value(text, ['Настройка', 'Требуется настройка']) or None,
    }


def save_magic_item(data, source_id: int):
    type_id = get_or_create_simple('item_types', data['type'])
    rarity_id = get_or_create_simple('item_rarities', data['rarity'])
    with cursor() as cur:
        cur.execute('SELECT id FROM magic_items WHERE lower(name)=lower(%s)', (data['name'],))
        row = cur.fetchone()
        if row:
            cur.execute(
                'UPDATE magic_items SET type_id=%s, rarity_id=%s, description=%s, attunement_required=%s, attunement_requirements=%s, source_id=%s WHERE id=%s',
                (type_id, rarity_id, data['description'], data['attunement_required'], data['attunement_requirements'], source_id, row[0]),
            )
            return row[0]
        cur.execute(
            'INSERT INTO magic_items (name, type_id, rarity_id, description, attunement_required, attunement_requirements, source_id) VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id',
            (data['name'], type_id, rarity_id, data['description'], data['attunement_required'], data['attunement_requirements'], source_id),
        )
        return cur.fetchone()[0]


def parse_all_magic_items():
    source_id = get_or_create_source()
    urls = get_magic_item_links()
    print(f'Найдено ссылок магических предметов в sitemap: {len(urls)}')
    success = failed = skipped = 0
    for url in urls:
        try:
            data = parse_magic_item(url)
            if not data:
                skipped += 1
                continue
            save_magic_item(data, source_id)
            print(f"+ {data['name']} | {data['rarity']} | {data['type']}")
            success += 1
        except Exception as exc:
            print(f'Ошибка магического предмета {url}: {exc}')
            failed += 1
    print_result('МАГИЧЕСКИЕ ПРЕДМЕТЫ PH14', success, failed, skipped)
