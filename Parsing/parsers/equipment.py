import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from config import BASE_URL
from db import cursor
from parsers.common import (
    clean_spaces, clean_multiline, clean_page_description, get_or_create_simple,
    get_or_create_source, get_soup, page_root, page_text, parse_cost,
    parse_weight, print_result, source_matches
)

# Главная страница раздела инвентаря. Снаряжение теперь берётся НЕ из /items/ и НЕ из всего sitemap,
# а только из статей-подстраниц этого раздела.
INVENTORY_INDEX_URL = 'https://dnd.su/articles/inventory/'
INVENTORY_ARTICLE_PREFIX = '/articles/inventory/'

# Для PH14 нас интересуют именно страницы инвентаря из Player's Handbook.
# Список не является источником данных, он только ограничивает разделы, откуда можно читать таблицы.
PH14_INVENTORY_SLUGS = {
    '147-armor-arms-equipment-tools',
    '95-armor-and-shields',
    '96-arms',
    '98-equipment',
    '100-tools',
    '257-lifestyle-expenses',
    '101-services',
    '97-trade-goods-and-values',
}

NON_PH_SECTION_MARKERS = [
    '[xge]', '[dmg]', '[tce]', '[scag]', '[mpmm]', '[ftod]', '[vrgr]', '[eepc]', '[ph24]', '[ua]',
    'xanathar', 'руководство мастера', 'dungeon master', 'tasha', '2024'
]

CATEGORY_KEYWORDS = [
    ('Доспехи', ['доспех', 'броня', 'щит', 'armor', 'shields']),
    ('Оружие', ['оружие', 'arms', 'weapon']),
    ('Инструменты', ['инструмент', 'tools', 'набор ремеслен', 'музыкальн']),
    ('Вьючные животные', ['вьючные животные', 'животные', 'лошад', 'пони', 'осел', 'осёл', 'верблюд', 'мул']),
    ('Транспорт', ['транспорт', 'vehicles', 'повозка', 'кораб', 'лодка', 'судно']),
    ('Еда и напитки', ['еда', 'напитки', 'food', 'drink', 'рацион', 'вино', 'эль']),
    ('Услуги', ['услуг', 'services', 'постоялый двор', 'наем', 'наём', 'заклинание']),
    ('Амуниция', ['боеприпас', 'амуниция', 'снаряжение', 'equipment', 'предмет']),
]

COIN_WORDS = r'(?:мм|см|эм|зм|пм|медн\w*|серебр\w*|золот\w*|платин\w*)'
COST_RE = re.compile(rf'(\d+(?:[\s\u00a0]\d{{3}})*(?:[,.]\d+)?|[¼½¾]|1/2|1/4|3/4)\s*{COIN_WORDS}', re.I)
WEIGHT_RE = re.compile(r'(?:\d+(?:[\s\u00a0]\d{3})*(?:[,.]\d+)?|[¼½¾]|1/2|1/4|3/4)\s*фнт\.?', re.I)


# Минимальный резервный список PH14. Используется только если таблицы с dnd.su не удалось прочитать.
# Основной режим всё равно берёт данные из /articles/inventory/.
PH14_EQUIPMENT_FALLBACK = [
    {'name': 'Кинжал', 'category': 'Оружие', 'cost_value': 2, 'cost_coin': 'gp', 'weight': 1, 'description': 'PH14 оружие'},
    {'name': 'Посох', 'category': 'Оружие', 'cost_value': 2, 'cost_coin': 'sp', 'weight': 4, 'description': 'PH14 оружие'},
    {'name': 'Дубинка', 'category': 'Оружие', 'cost_value': 1, 'cost_coin': 'sp', 'weight': 2, 'description': 'PH14 оружие'},
    {'name': 'Ручной топор', 'category': 'Оружие', 'cost_value': 5, 'cost_coin': 'gp', 'weight': 2, 'description': 'PH14 оружие'},
    {'name': 'Копьё', 'category': 'Оружие', 'cost_value': 1, 'cost_coin': 'gp', 'weight': 3, 'description': 'PH14 оружие'},
    {'name': 'Арбалет, лёгкий', 'category': 'Оружие', 'cost_value': 25, 'cost_coin': 'gp', 'weight': 5, 'description': 'PH14 оружие'},
    {'name': 'Короткий лук', 'category': 'Оружие', 'cost_value': 25, 'cost_coin': 'gp', 'weight': 2, 'description': 'PH14 оружие'},
    {'name': 'Длинный меч', 'category': 'Оружие', 'cost_value': 15, 'cost_coin': 'gp', 'weight': 3, 'description': 'PH14 оружие'},
    {'name': 'Короткий меч', 'category': 'Оружие', 'cost_value': 10, 'cost_coin': 'gp', 'weight': 2, 'description': 'PH14 оружие'},
    {'name': 'Длинный лук', 'category': 'Оружие', 'cost_value': 50, 'cost_coin': 'gp', 'weight': 2, 'description': 'PH14 оружие'},
    {'name': 'Кожаный доспех', 'category': 'Доспехи', 'cost_value': 10, 'cost_coin': 'gp', 'weight': 10, 'description': 'PH14 доспех'},
    {'name': 'Кольчуга', 'category': 'Доспехи', 'cost_value': 75, 'cost_coin': 'gp', 'weight': 55, 'description': 'PH14 доспех'},
    {'name': 'Щит', 'category': 'Доспехи', 'cost_value': 10, 'cost_coin': 'gp', 'weight': 6, 'description': 'PH14 доспех'},
    {'name': 'Рюкзак', 'category': 'Амуниция', 'cost_value': 2, 'cost_coin': 'gp', 'weight': 5, 'description': 'PH14 снаряжение'},
    {'name': 'Спальный мешок', 'category': 'Амуниция', 'cost_value': 1, 'cost_coin': 'gp', 'weight': 7, 'description': 'PH14 снаряжение'},
    {'name': 'Верёвка пеньковая, 50 футов', 'category': 'Амуниция', 'cost_value': 1, 'cost_coin': 'gp', 'weight': 10, 'description': 'PH14 снаряжение'},
    {'name': 'Факел', 'category': 'Амуниция', 'cost_value': 1, 'cost_coin': 'cp', 'weight': 1, 'description': 'PH14 снаряжение'},
    {'name': 'Рацион, 1 день', 'category': 'Еда и напитки', 'cost_value': 5, 'cost_coin': 'sp', 'weight': 2, 'description': 'PH14 снаряжение'},
    {'name': 'Воровские инструменты', 'category': 'Инструменты', 'cost_value': 25, 'cost_coin': 'gp', 'weight': 1, 'description': 'PH14 инструмент'},
]


def _slug_from_url(url: str) -> str:
    return url.rstrip('/').split('/')[-1]


def _is_inventory_article(url: str) -> bool:
    return INVENTORY_ARTICLE_PREFIX in url and _slug_from_url(url) in PH14_INVENTORY_SLUGS


def get_inventory_article_links() -> list[str]:
    """
    Берёт ссылки только с https://dnd.su/articles/inventory/.
    Если главная страница раздела временно недоступна, всё равно возвращает
    известную PH14-статью с таблицами инвентаря.
    """
    links = {'https://dnd.su/articles/inventory/147-armor-arms-equipment-tools/'}

    try:
        soup = get_soup(INVENTORY_INDEX_URL)
    except Exception as exc:
        print(f'Не удалось открыть индекс инвентаря, использую известные PH14-ссылки: {exc}')
        return sorted(links)

    for a in soup.select('a[href]'):
        href = a.get('href') or ''
        url = urljoin(BASE_URL + '/', href)
        if _is_inventory_article(url):
            links.add(url.rstrip('/') + '/')

    return sorted(links)


def _section_is_not_ph14(title: str) -> bool:
    low = (title or '').lower().replace('ё', 'е')
    return any(marker in low for marker in NON_PH_SECTION_MARKERS)


def _nearest_heading_text(tag) -> str:
    """Ищет ближайший предыдущий заголовок h2-h4 для определения категории таблицы."""
    for prev in tag.find_all_previous(['h2', 'h3', 'h4']):
        text = clean_spaces(prev.get_text(' ', strip=True))
        if text:
            return text
    return ''


def _detect_category(title: str, cells: list[str] | None = None) -> str:
    source = f"{title} {' '.join(cells or [])}".lower().replace('ё', 'е')
    for category, keys in CATEGORY_KEYWORDS:
        if any(k in source for k in keys):
            return category
    return 'Амуниция'


def _parse_fraction_number(value: str):
    value = clean_spaces(value).replace('\u00a0', ' ')
    value = value.replace('¼', '0.25').replace('½', '0.5').replace('¾', '0.75')
    value = value.replace('1/4', '0.25').replace('1/2', '0.5').replace('3/4', '0.75')
    value = re.sub(r'(?<=\d)\s+(?=\d{3}\b)', '', value)
    m = re.search(r'\d+(?:[,.]\d+)?', value)
    return float(m.group(0).replace(',', '.')) if m else None


def _parse_cost_from_text(text: str):
    value, coin = parse_cost('Цена: ' + text)
    if value is not None:
        return value, coin
    m = COST_RE.search(text or '')
    if not m:
        return None, 'gp'
    return parse_cost('Цена: ' + m.group(0))


def _parse_weight_from_text(text: str):
    weight = parse_weight('Вес: ' + (text or ''))
    if weight is not None:
        return weight
    m = WEIGHT_RE.search(text or '')
    return _parse_fraction_number(m.group(0)) if m else None


def _valid_item_name(name: str) -> bool:
    name = clean_spaces(name)
    if not name or len(name) > 150:
        return False
    low = name.lower().replace('ё', 'е')
    bad = [
        'предмет', 'название', 'стоимость', 'цена', 'вес', 'урон', 'свойства',
        'легкий доспех', 'средний доспех', 'тяжелый доспех', 'тяжелые доспехи',
        'простое рукопашное оружие', 'простое дальнобойное оружие',
        'воинское рукопашное оружие', 'воинское дальнобойное оружие',
        'инструменты ремесленников', 'музыкальные инструменты', 'игровой набор',
        'магическая фокусировка', 'фокусировка друидов', 'священный символ',
        'боеприпасы',
    ]
    if low in bad:
        return False
    if _section_is_not_ph14(name):
        return False
    return True


def _make_item(name: str, category: str, cost_text: str = '', weight_text: str = '', description: str = ''):
    name = clean_spaces(name)
    if not _valid_item_name(name):
        return None
    cost_value, cost_coin = _parse_cost_from_text(cost_text)
    weight = _parse_weight_from_text(weight_text)
    return {
        'name': name,
        'category': category,
        'cost_value': cost_value,
        'cost_coin': cost_coin,
        'weight': weight,
        'description': clean_multiline(description or ''),
    }


def _table_headers(table) -> list[str]:
    first = table.find('tr')
    if not first:
        return []
    return [clean_spaces(c.get_text(' ', strip=True)) for c in first.find_all(['th', 'td'])]


def _split_double_table_cells(cells: list[str], headers: list[str]) -> list[list[str]]:
    """
    На dnd.su таблица инструментов иногда склеена как:
    Предмет | Стоимость | Вес | Предмет | Стоимость | Вес
    Тогда одну строку делим на две записи.
    """
    header_text = ' '.join(headers).lower().replace('ё', 'е')
    # Делим только таблицы формата: Предмет | Стоимость | Вес | Предмет | Стоимость | Вес.
    # Обычные таблицы доспехов тоже имеют 6 колонок, но их делить нельзя.
    if len(cells) >= 6 and header_text.count('предмет') >= 2 and header_text.count('стоимость') >= 2:
        return [cells[:3], cells[3:6]]
    return [cells]


def _items_from_html_tables(soup: BeautifulSoup) -> list[dict]:
    items = []
    root = page_root(soup)

    for table in root.find_all('table'):
        heading = _nearest_heading_text(table)
        if _section_is_not_ph14(heading):
            continue

        category = _detect_category(heading)
        headers = [h.lower().replace('ё', 'е') for h in _table_headers(table)]
        if not any(x in ' '.join(headers) for x in ['стоимость', 'цена', 'вес', 'урон', 'класс доспеха']):
            continue

        rows = table.find_all('tr')
        for tr in rows[1:]:
            cells = [clean_spaces(c.get_text(' ', strip=True)) for c in tr.find_all(['td', 'th'])]
            cells = [c for c in cells if c]
            if not cells:
                continue

            for part in _split_double_table_cells(cells, headers):
                if len(part) < 2:
                    continue
                name = part[0]
                row_category = _detect_category(heading, part)
                cost_text = part[1] if len(part) > 1 else ''
                # Оружие: Название | Стоимость | Урон | Вес | Свойства
                # Доспехи: Доспех | Стоимость | КД | Сила | Скрытность | Вес
                if row_category == 'Оружие' and len(part) >= 4:
                    weight_text = part[3]
                elif row_category == 'Доспехи' and len(part) >= 6:
                    weight_text = part[5]
                elif len(part) >= 3:
                    weight_text = part[2]
                else:
                    weight_text = ' '.join(part[1:])

                item = _make_item(name, row_category, cost_text, weight_text, ' | '.join(part))
                if item:
                    items.append(item)

    return items


def _items_from_text_fallback(soup: BeautifulSoup) -> list[dict]:
    """
    Запасной вариант, если сайт отдаст таблицы не тегами <table>, а обычным текстом.
    Берём только строки, похожие на элемент таблицы: название + цена + вес.
    """
    text = page_text(soup)
    lines = [clean_spaces(x) for x in text.split('\n') if clean_spaces(x)]
    items = []
    current_heading = ''

    for line in lines:
        if _section_is_not_ph14(line):
            current_heading = line
            continue
        if re.match(r'^(доспехи|оружие|снаряжение|инструменты|услуги|транспорт|вьючные животные)', line, re.I):
            current_heading = line
            continue
        if not COST_RE.search(line):
            continue

        category = _detect_category(current_heading, [line])
        cost_match = COST_RE.search(line)
        weight_match = WEIGHT_RE.search(line)
        if not cost_match:
            continue
        name = clean_spaces(line[:cost_match.start()])
        cost_text = cost_match.group(0)
        weight_text = weight_match.group(0) if weight_match else ''
        item = _make_item(name, category, cost_text, weight_text, line)
        if item:
            items.append(item)

    return items


def parse_inventory_article(url: str) -> list[dict]:
    soup = get_soup(url)
    text = page_text(soup)

    # Строго PH14/Player's Handbook 2014. Страницы без PH14/PHB не парсим.
    if not source_matches(text):
        return []

    # Страница инструментов содержит PHB сверху и XGE ниже. Табличный парсер отсекает секции [XGE].
    items = _items_from_html_tables(soup)
    if not items:
        items = _items_from_text_fallback(soup)

    result = []
    seen = set()
    for item in items:
        key = item['name'].lower()
        if key in seen:
            continue
        seen.add(key)
        # Описание всей статьи не кладём каждому предмету целиком, чтобы БД не раздувалась.
        if not item.get('description'):
            item['description'] = ''
        result.append(item)
    return result


def save_equipment(data, source_id: int) -> int:
    category_id = get_or_create_simple('equipment_categories', data['category'])
    with cursor() as cur:
        cur.execute('SELECT id FROM equipment WHERE lower(name)=lower(%s)', (data['name'],))
        row = cur.fetchone()
        if row:
            item_id = row[0]
            cur.execute(
                """
                UPDATE equipment
                SET category_id=%s,
                    cost_value=%s,
                    cost_coin=%s,
                    weight=%s,
                    description=%s,
                    source_id=%s
                WHERE id=%s
                """,
                (category_id, data['cost_value'], data['cost_coin'], data['weight'], data['description'], source_id, item_id),
            )
            return item_id
        cur.execute(
            """
            INSERT INTO equipment (name, category_id, cost_value, cost_coin, weight, description, source_id)
            VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id
            """,
            (data['name'], category_id, data['cost_value'], data['cost_coin'], data['weight'], data['description'], source_id),
        )
        return cur.fetchone()[0]


def parse_all_equipment():
    source_id = get_or_create_source()
    urls = get_inventory_article_links()
    print(f'Найдено PH14-подстраниц инвентаря: {len(urls)}')

    success = failed = skipped = 0
    saved_names = set()

    for url in urls:
        try:
            items = parse_inventory_article(url)
            if not items:
                skipped += 1
                continue

            print(f'\nСтатья: {url}')
            for data in items:
                key = data['name'].lower()
                if key in saved_names:
                    continue
                save_equipment(data, source_id)
                saved_names.add(key)
                print(f"+ {data['name']} | {data['category']}")
                success += 1
        except Exception as exc:
            print(f'Ошибка статьи инвентаря {url}: {exc}')
            failed += 1

    if success == 0:
        print('Таблицы инвентаря с сайта не прочитались. Добавляю минимальный резервный PH14-набор.')
        for data in PH14_EQUIPMENT_FALLBACK:
            key = data['name'].lower()
            if key in saved_names:
                continue
            try:
                save_equipment(data, source_id)
                saved_names.add(key)
                print(f"+ {data['name']} [fallback] | {data['category']}")
                success += 1
            except Exception as exc:
                print(f"Ошибка fallback-снаряжения {data['name']}: {exc}")
                failed += 1

    print_result('СНАРЯЖЕНИЕ PH14 ИЗ /articles/inventory/', success, failed, skipped)
