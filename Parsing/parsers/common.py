import re
import time
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from config import BASE_URL, HEADERS, REQUEST_DELAY, SITEMAP_URL, SOURCE_CODE, SOURCE_NAME
from db import cursor

session = requests.Session()
session.headers.update(HEADERS)

ABILITY_FORMS = {
    'сила': 'Сила', 'силы': 'Сила', 'силе': 'Сила', 'силу': 'Сила',
    'ловкость': 'Ловкость', 'ловкости': 'Ловкость', 'ловкостью': 'Ловкость', 'ловкостию': 'Ловкость',
    'телосложение': 'Телосложение', 'телосложения': 'Телосложение', 'телосложению': 'Телосложение',
    'интеллект': 'Интеллект', 'интеллекта': 'Интеллект', 'интеллекту': 'Интеллект',
    'мудрость': 'Мудрость', 'мудрости': 'Мудрость', 'мудростью': 'Мудрость',
    'харизма': 'Харизма', 'харизмы': 'Харизма', 'харизме': 'Харизма', 'харизму': 'Харизма',
}

ABILITY_NAMES = ['Сила', 'Ловкость', 'Телосложение', 'Интеллект', 'Мудрость', 'Харизма']

SKILL_NAMES = [
    'Атлетика', 'Акробатика', 'Ловкость рук', 'Скрытность', 'Анализ',
    'История', 'Магия', 'Природа', 'Религия', 'Восприятие',
    'Выживание', 'Медицина', 'Проницательность', 'Уход за животными',
    'Выступление', 'Запугивание', 'Обман', 'Убеждение',
]

SCHOOL_ALIASES = {
    'воплощение': 'Воплощение', 'вызов': 'Вызов', 'иллюзия': 'Иллюзия', 'некромантия': 'Некромантия',
    'ограждение': 'Ограждение', 'превращение': 'Превращение', 'прорицание': 'Прорицание', 'очарование': 'Очарование',
}

CLASS_NAMES = ['Бард', 'Варвар', 'Воин', 'Волшебник', 'Друид', 'Жрец', 'Колдун', 'Монах', 'Паладин', 'Плут', 'Следопыт', 'Чародей']

COINS = {
    'мм': 'cp', 'мед': 'cp', 'медь': 'cp',
    'см': 'sp', 'сер': 'sp', 'сереб': 'sp',
    'эм': 'ep',
    'зм': 'gp', 'зол': 'gp', 'золот': 'gp',
    'пм': 'pp', 'плат': 'pp',
}


def clean_spaces(text: str) -> str:
    return re.sub(r'\s+', ' ', text or '').strip()


def clean_multiline(text: str) -> str:
    text = re.sub(r'[ \t]+', ' ', text or '')
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def normalize_for_match(text: str) -> str:
    text = clean_spaces(text).lower().replace('ё', 'е').replace('’', "'")
    text = re.sub(r'\b(2014|2024)\b', '', text)
    return clean_spaces(text)


def source_matches(text: str) -> bool:
    """Строгая проверка источника. Для PH14 принимаем PH14 и Player's Handbook 2014/Player's Handbook."""
    raw = text or ''
    low_raw = raw.lower().replace('ё', 'е')
    code = SOURCE_CODE.lower()
    if re.search(rf'(?<![a-zа-я0-9]){re.escape(code)}(?![a-zа-я0-9])', low_raw, flags=re.I):
        return True

    norm = normalize_for_match(raw)
    source_norm = normalize_for_match(SOURCE_NAME)
    if source_norm and source_norm in norm:
        return True

    if code == 'ph14':
        if "player's handbook" in norm or 'players handbook' in norm or 'книга игрока' in norm:
            # Не берём явно 2024, если оно встретилось рядом.
            return '2024' not in low_raw and 'ph24' not in low_raw
    return False


def get_soup(url: str) -> BeautifulSoup:
    time.sleep(REQUEST_DELAY)
    response = session.get(url, timeout=35)
    response.raise_for_status()
    return BeautifulSoup(response.text, 'html.parser')


def get_xml_soup(url: str = SITEMAP_URL) -> BeautifulSoup:
    time.sleep(REQUEST_DELAY)
    response = session.get(url, timeout=45)
    response.raise_for_status()
    return BeautifulSoup(response.content, 'xml')


def absolute(href: str, base: str = BASE_URL) -> str:
    return urljoin(base + '/', href)


def normalize_url(url: str) -> str:
    parsed = urlparse(url)
    return f'{parsed.scheme}://{parsed.netloc}{parsed.path}'


def get_sitemap_urls(pattern: str | None = None) -> list[str]:
    soup = get_xml_soup()
    urls = []
    for loc in soup.find_all('loc'):
        url = loc.get_text(strip=True)
        if not url:
            continue
        if pattern and not re.search(pattern, url):
            continue
        urls.append(normalize_url(url))
    return sorted(set(urls))


def page_root(soup: BeautifulSoup):
    return soup.find('article') or soup.find('main') or soup.body or soup


def page_text(soup: BeautifulSoup) -> str:
    return clean_multiline(page_root(soup).get_text('\n', strip=True))


def clean_name(text: str) -> str:
    text = clean_spaces(text)
    text = re.sub(r'\[[^\]]+\]', '', text)
    text = re.sub(r'\([^)]*(?:PH14|Player|Handbook|Источник)[^)]*\)', '', text, flags=re.I)
    text = re.sub(r'\bPH\d+\b', '', text, flags=re.I)
    text = re.sub(r"Player'?s Handbook(?:\s*2014)?", '', text, flags=re.I)
    text = re.sub(r'Книга игрока(?:\s*2014)?', '', text, flags=re.I)
    text = re.sub(r'\s+—\s+.*$', '', text)
    text = re.sub(r'\s+-\s+.*$', '', text)
    return clean_spaces(text)


def russian_name_from_text(text: str) -> str:
    text = clean_name(text)
    m = re.match(r'^([А-Яа-яЁё0-9\s\-:,«»]+)', text)
    return clean_name(m.group(1)) if m else clean_name(text)


def page_name(soup: BeautifulSoup, fallback: str = '') -> str:
    h1 = page_root(soup).find('h1') or soup.find('h1')
    if h1:
        return russian_name_from_text(h1.get_text(' ', strip=True))
    return russian_name_from_text(fallback)


def split_heading_sections(soup: BeautifulSoup):
    root = page_root(soup)
    headings = root.find_all(['h2', 'h3', 'h4'])
    sections = []
    for heading in headings:
        level = int(heading.name[1])
        title = clean_spaces(heading.get_text(' ', strip=True))
        parts = []
        for sibling in heading.next_siblings:
            name = getattr(sibling, 'name', None)
            if name in ['h2', 'h3', 'h4'] and int(name[1]) <= level:
                break
            if hasattr(sibling, 'get_text'):
                txt = sibling.get_text('\n', strip=True)
            else:
                txt = str(sibling).strip()
            if txt:
                parts.append(txt)
        sections.append({'level': level, 'title': title, 'text': clean_multiline('\n'.join(parts))})
    return sections


def field_value(text: str, labels: list[str] | str) -> str:
    if isinstance(labels, str):
        labels = [labels]
    label_re = '|'.join(re.escape(x) for x in labels)
    pattern = rf'(?:^|\n)\s*(?:{label_re})\s*[:.]\s*(.+?)(?=\n\s*[А-ЯЁA-Z][^\n]{{1,60}}\s*[:.]|\n\s*#{1,6}\s|$)'
    m = re.search(pattern, text, flags=re.I | re.S)
    return clean_spaces(m.group(1)) if m else ''


def get_or_create_source() -> int:
    with cursor() as cur:
        cur.execute(
            """
            INSERT INTO sources (name, code)
            VALUES (%s, %s)
            ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name
            RETURNING id
            """,
            (SOURCE_NAME, SOURCE_CODE),
        )
        return cur.fetchone()[0]


def get_or_create_simple(table: str, name: str, **extra) -> int:
    with cursor() as cur:
        cur.execute(f'SELECT id FROM {table} WHERE lower(name)=lower(%s)', (name,))
        row = cur.fetchone()
        if row:
            return row[0]
        cols = ['name'] + list(extra.keys())
        vals = [name] + list(extra.values())
        cur.execute(
            f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({', '.join(['%s'] * len(vals))}) RETURNING id",
            vals,
        )
        return cur.fetchone()[0]


def get_id(table: str, name: str):
    with cursor() as cur:
        cur.execute(f'SELECT id FROM {table} WHERE lower(name)=lower(%s)', (name,))
        row = cur.fetchone()
        return row[0] if row else None


def load_ability_map() -> dict[str, int]:
    with cursor() as cur:
        cur.execute('SELECT id, name FROM ability_scores')
        return {name.lower(): ability_id for ability_id, name in cur.fetchall()}


def normalize_ability_name(word: str):
    return ABILITY_FORMS.get((word or '').lower().replace('ё', 'е').strip())


def word_number_to_int(word: str):
    numbers = {
        'одна': 1, 'одну': 1, 'одной': 1, 'один': 1, 'одно': 1,
        'две': 2, 'два': 2, 'двух': 2,
        'три': 3, 'трех': 3, 'трёх': 3,
    }
    word = (word or '').lower().replace('ё', 'е').strip()
    return int(word) if word.isdigit() else numbers.get(word)


def unique_bonuses(bonuses: list[dict]) -> list[dict]:
    seen = set()
    result = []
    for b in bonuses:
        key = (b.get('ability_score_id'), b.get('bonus'), b.get('is_choice'), b.get('choice_count'))
        if key not in seen:
            seen.add(key)
            result.append(b)
    return result


def fixed_bonus(ability: str, bonus: int, description: str | None = None) -> dict:
    amap = load_ability_map()
    aid = amap.get(ability.lower())
    if not aid:
        raise ValueError(f'В таблице ability_scores нет характеристики: {ability}')
    return {'ability_score_id': aid, 'bonus': bonus, 'is_choice': False, 'choice_count': None, 'description': description}


def choice_bonus(count: int, bonus: int, description: str | None = None) -> dict:
    """
    Служебный вариант для старых мест кода.
    В новой схеме варианты выбора лучше хранить НЕ одной строкой с ability_score_id=NULL,
    а отдельной строкой для каждой доступной характеристики.
    """
    return {'ability_score_id': None, 'bonus': bonus, 'is_choice': True, 'choice_count': count, 'description': description or f'{count} характеристики на выбор +{bonus}'}


def choice_bonus_options(
    count: int,
    bonus: int,
    description: str | None = None,
    exclude: list[str] | None = None,
) -> list[dict]:
    """
    Возвращает ВСЕ характеристики, из которых игрок может выбирать.

    Раньше выбор сохранялся одной строкой:
        ability_score_id = NULL, is_choice = TRUE, choice_count = 2

    Из-за этого в БД не было видно, какие именно характеристики доступны на выбор.
    Теперь каждая доступная характеристика записывается отдельной строкой, например для полуэльфа PH14:
        Сила +1, выбор 2
        Ловкость +1, выбор 2
        Телосложение +1, выбор 2
        Интеллект +1, выбор 2
        Мудрость +1, выбор 2

    Харизма исключается, потому что у полуэльфа PH14 она уже получает фиксированный +2,
    а текст говорит: «двух других характеристик».
    """
    amap = load_ability_map()
    exclude_set = {x.lower() for x in (exclude or [])}
    result = []

    for ability in ABILITY_NAMES:
        if ability.lower() in exclude_set:
            continue

        aid = amap.get(ability.lower())
        if not aid:
            raise ValueError(f'В таблице ability_scores нет характеристики: {ability}')

        result.append({
            'ability_score_id': aid,
            'bonus': bonus,
            'is_choice': True,
            'choice_count': count,
            'description': description or f'Выбор {count} из доступных характеристик, +{bonus}',
        })

    return result


def extract_ability_bonuses(text: str) -> list[dict]:
    amap = load_ability_map()
    text = clean_spaces(text)
    lower = text.lower().replace('ё', 'е')
    bonuses = []

    # Человек PH14: все характеристики +1.
    if re.search(r'все\s+значения\s+(?:ваших\s+)?характеристик\s+увеличиваются\s+на\s+1', lower):
        for ability in ABILITY_NAMES:
            bonuses.append(fixed_bonus(ability, 1, 'Все характеристики +1'))
        return unique_bonuses(bonuses)

    ability_words = r'силы|силе|сила|ловкости|ловкость|телосложения|телосложению|телосложение|интеллекта|интеллекту|интеллект|мудрости|мудрость|харизмы|харизме|харизму|харизма'
    patterns = [
        rf'(?:значение\s+ваше(?:й|го)|ваше\s+значение|ваш[ае]?)?\s*({ability_words})\s+(?:увеличивается|повышается)\s+на\s+(\d+)',
        rf'\+(\d+)\s+к\s+({ability_words})',
        rf'({ability_words})\s*\+\s*(\d+)',
    ]
    for pattern in patterns:
        for m in re.findall(pattern, lower, flags=re.I):
            if m[0].isdigit():
                bonus = int(m[0]); word = m[1]
            else:
                word = m[0]; bonus = int(m[1])
            ability = normalize_ability_name(word)
            if ability and ability.lower() in amap:
                bonuses.append({'ability_score_id': amap[ability.lower()], 'bonus': bonus, 'is_choice': False, 'choice_count': None, 'description': None})

    numbers = r'одной|одну|одна|один|одно|двух|две|два|трех|три|\d+'
    choice_patterns = [
        rf'({numbers})\s+(?:других\s+|любых\s+)?характеристик(?:и|у)?\s+(?:на\s+ваш\s+выбор|по\s+вашему\s+выбору)\s+(?:увеличиваются|увеличивается|повышаются|повышается)\s+на\s+(\d+)',
        rf'выберите\s+({numbers})\s+характеристик(?:у|и)?.*?(?:увеличиваются|увеличивается|повышаются|повышается)\s+на\s+(\d+)',
    ]
    for pattern in choice_patterns:
        for m in re.finditer(pattern, lower, flags=re.I):
            count_word, bonus_value = m.group(1), m.group(2)
            count = word_number_to_int(count_word)
            if count:
                # Если в самом тексте сказано «других характеристик», исключаем уже найденные фиксированные бонусы.
                # Например, у полуэльфа PH14 Харизма +2 фиксированно, а +1 выбирается для двух ДРУГИХ характеристик.
                exclude = []
                if 'других' in m.group(0):
                    id_to_name = {v: k.capitalize() for k, v in amap.items()}
                    exclude = [id_to_name.get(b.get('ability_score_id'), '') for b in bonuses if not b.get('is_choice')]

                bonuses.extend(choice_bonus_options(
                    count,
                    int(bonus_value),
                    f'Выбор {count} характеристик +{bonus_value}',
                    exclude=exclude,
                ))

    return unique_bonuses(bonuses)


def extract_speed(text: str, default: int = 30) -> int:
    normalized = clean_spaces(text)
    patterns = [
        r'Скорость\s*[.:]\s*[^.]*?(\d+)\s*фут',
        r'базовая\s+скорость\s+ходьбы\s+составл\w*\s+(\d+)\s*фут',
        r'скорость\s+ходьбы\s+(?:равна|составляет)\s+(\d+)\s*фут',
    ]
    for pattern in patterns:
        m = re.search(pattern, normalized, flags=re.I)
        if m:
            return int(m.group(1))
    return default


def extract_known_skills(text: str) -> list[str]:
    found = []
    lower = (text or '').lower()
    for skill in SKILL_NAMES:
        if skill.lower() in lower and skill not in found:
            found.append(skill)
    return found


def ensure_class(name: str, hit_die: str = 'd8', primary_ability: str | None = None, source_id: int | None = None) -> int:
    primary_id = None
    if primary_ability:
        primary_id = load_ability_map().get(primary_ability.lower())
    with cursor() as cur:
        cur.execute('SELECT id FROM classes WHERE lower(name)=lower(%s)', (name,))
        row = cur.fetchone()
        if row:
            class_id = row[0]
            cur.execute('UPDATE classes SET hit_die=%s, primary_ability_id=COALESCE(%s, primary_ability_id), source_id=COALESCE(%s, source_id) WHERE id=%s', (hit_die, primary_id, source_id, class_id))
            return class_id
        cur.execute('INSERT INTO classes (name, description, hit_die, primary_ability_id, source_id) VALUES (%s,%s,%s,%s,%s) RETURNING id', (name, '', hit_die, primary_id, source_id))
        return cur.fetchone()[0]


def school_id_from_text(text: str) -> int:
    low = (text or '').lower().replace('ё', 'е')
    for key, name in SCHOOL_ALIASES.items():
        if key in low:
            return get_or_create_simple('magic_schools', name)
    return get_or_create_simple('magic_schools', 'Воплощение')


def parse_cost(text: str):
    m = re.search(r'(?:Стоимость|Цена)\s*[:.]\s*([\d,.]+)\s*([А-Яа-яЁёa-zA-Z]+)', text, flags=re.I)
    if not m:
        return None, 'gp'
    value = float(m.group(1).replace(',', '.'))
    raw = m.group(2).lower()
    coin = next((code for key, code in COINS.items() if key in raw), 'gp')
    return value, coin


def parse_weight(text: str):
    m = re.search(r'Вес\s*[:.]\s*([\d,.]+)\s*ф', text, flags=re.I)
    return float(m.group(1).replace(',', '.')) if m else None


def clean_page_description(text: str) -> str:
    stops = ['Комментарии', 'Оставить комментарий', 'Войти', 'Регистрация', 'Поддержать проект', 'Boosty', 'Patreon', 'Telegram', 'Discord']
    result = text or ''
    for stop in stops:
        idx = result.lower().find(stop.lower())
        if idx != -1:
            result = result[:idx]
    return clean_multiline(result)


def print_result(title: str, success: int, failed: int, skipped: int = 0):
    print('\n==========', title, '==========')
    print('Успешно:', success)
    print('Пропущено:', skipped)
    print('Ошибок:', failed)
