import json
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urlparse

from db import cursor
from parsers.common import (
    BASE_URL, CLASS_NAMES, clean_page_description, clean_spaces, field_value,
    get_or_create_source, get_sitemap_urls, get_soup, page_root, page_text,
    print_result, russian_name_from_text, school_id_from_text, absolute
)

# Для проекта берём только старый Player's Handbook: PH / PH14 / PHB.
# PH24 сам по себе НЕ подходит.
ALLOWED_PH_SPELL_CODES = {'PH', 'PH14', 'PHB'}
NON_OFFICIAL_SPELL_CODES = {'HB', 'UA', 'HOMEBREW'}
NON_OFFICIAL_WORDS_RE = r'(?:homebrew|хоумбрю|домашн(?:ий|ее|яя)|неофициальн|unearthed\s+arcana|раскопанн(?:ые|ая)\s+арканы)'

SOURCE_CODES_RE = (
    r'(PH14|PH24|PHB|PH|XGE|TCE|SCAG|EEPC|POA|FTD|FTOD|VRGR|AI|EGW|SCC|BMT|HB|UA|DMG|GGR|ERLW|RMR|SATO|AAG|IDROTF|GOS|LLK|OGA|DOSI|HOMEBREW)'
)

BLOCKED_HOSTS = {'next.dnd.su'}
ALLOWED_HOSTS = {'dnd.su', 'www.dnd.su', '5e14.dnd.su'}

CACHE_DIR = Path(__file__).resolve().parents[1] / 'cache'
SPELL_LINKS_CACHE = CACHE_DIR / 'spell_links_PH14_full_scan_v2.json'
SPELL_WORKERS = int(os.getenv('DND_SPELL_WORKERS', '8'))
USE_SPELL_CACHE = os.getenv('DND_USE_SPELL_CACHE', '1').strip().lower() not in {'0', 'false', 'no', 'нет'}


def _normalize_spell_url(url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path.rstrip('/') + '/'
    host = parsed.netloc.lower()
    scheme = parsed.scheme or 'https'
    return f'{scheme}://{host}{path}'


def _spell_numeric_id(url: str) -> int | None:
    parsed = urlparse(url)
    m = re.match(r'^/spells/(\d+)(?:[-_/a-zA-Z0-9]*)/?$', parsed.path)
    return int(m.group(1)) if m else None


def _is_spell_url(url: str) -> bool:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    if host in BLOCKED_HOSTS or host not in ALLOWED_HOSTS:
        return False
    return _spell_numeric_id(url) is not None


def _source_codes_from_text(text: str) -> set[str]:
    if not text:
        return set()
    return {m.group(1).upper() for m in re.finditer(SOURCE_CODES_RE, text, flags=re.I)}


def _has_non_official_marker(text: str) -> bool:
    if not text:
        return False
    codes = _source_codes_from_text(text)
    if codes & NON_OFFICIAL_SPELL_CODES:
        return True
    return bool(re.search(NON_OFFICIAL_WORDS_RE, text, flags=re.I))


def get_spell_links_from_sitemap() -> list[str]:
    urls = []
    for url in get_sitemap_urls(r'/spells/\d+'):
        if _is_spell_url(url):
            urls.append(_normalize_spell_url(url))
    result = sorted(set(urls))
    print(f'Найдено официальных URL заклинаний в sitemap: {len(result)}')
    return result


def get_spell_links_from_filtered_list_page() -> list[str]:
    urls: list[str] = []
    try:
        soup = get_soup(f'{BASE_URL.rstrip("/")}/spells/')
    except Exception as exc:
        print(f'Не удалось прочитать /spells/: {exc}')
        return urls

    for a in soup.find_all('a', href=True):
        url = absolute(a.get('href'))
        if _is_spell_url(url):
            urls.append(_normalize_spell_url(url))

    result = sorted(set(urls))
    if result:
        print(f'Найдено URL заклинаний на /spells/: {len(result)}')
    return result


def _short_text_candidates(soup) -> list[str]:
    """
    dnd.su не всегда держит название и источник строго в h1.
    Поэтому проверяем короткие текстовые блоки: h1/h2/h3, title, og:title и другие элементы.
    ВАЖНО: не проверяем весь текст страницы, иначе меню/ссылки могут сломать фильтр.
    """
    root = page_root(soup)
    candidates: list[str] = []

    for tag in root.find_all(['h1', 'h2', 'h3', 'h4']) + soup.find_all(['h1', 'h2', 'h3', 'h4']):
        txt = clean_spaces(tag.get_text(' ', strip=True))
        if txt and txt not in candidates:
            candidates.append(txt)

    if soup.title and soup.title.string:
        txt = clean_spaces(soup.title.string)
        if txt and txt not in candidates:
            candidates.append(txt)

    for meta_key in [('property', 'og:title'), ('name', 'title'), ('name', 'twitter:title')]:
        tag = soup.find('meta', attrs={meta_key[0]: meta_key[1]})
        if tag and tag.get('content'):
            txt = clean_spaces(tag.get('content'))
            if txt and txt not in candidates:
                candidates.append(txt)

    # Короткие строки с названием вида "Приказ [Command] PH14" могут быть внутри div/span.
    for node in root.find_all(string=True):
        txt = clean_spaces(str(node))
        if not txt or len(txt) > 220:
            continue
        if '[' in txt and ']' in txt and re.search(SOURCE_CODES_RE, txt, flags=re.I):
            if txt not in candidates:
                candidates.append(txt)

    return candidates


def spell_source_heading(soup) -> str:
    """
    Возвращает короткий блок с названием заклинания и источниками.
    Примеры подходящих строк:
        Приказ [Command] PH14 PH24
        Защита от оружия [Blade ward] PH14 PH24
        Неуязвимость [Invulnerability] XGE
    """
    candidates = []
    for text in _short_text_candidates(soup):
        if '[' not in text or ']' not in text:
            continue
        if re.search(SOURCE_CODES_RE, text, flags=re.I):
            candidates.append(text)

    if not candidates:
        return ''

    # Берём самый короткий нормальный заголовок, а не длинный title браузера.
    candidates.sort(key=len)
    return candidates[0]


def extract_source_codes_from_heading(heading: str) -> set[str]:
    if not heading:
        return set()
    after_en_name = heading.split(']', 1)[1] if ']' in heading else heading
    return _source_codes_from_text(after_en_name)


def is_ph_spell_page(soup) -> bool:
    heading = spell_source_heading(soup)
    codes = extract_source_codes_from_heading(heading)

    if not codes:
        return False
    if not bool(codes & ALLOWED_PH_SPELL_CODES):
        return False
    if bool(codes & NON_OFFICIAL_SPELL_CODES):
        return False
    if _has_non_official_marker(heading):
        return False

    # Не проверяем весь верх страницы на слова homebrew/UA: они могут быть в меню сайта.
    return True


def spell_name_from_source_heading(soup) -> str:
    heading = spell_source_heading(soup)
    if heading:
        ru = re.sub(r'\[.*?\].*$', '', heading).strip()
        if ru:
            return russian_name_from_text(ru)

    h1 = page_root(soup).find('h1') or soup.find('h1')
    if h1:
        text = h1.get_text(' ', strip=True)
        text = re.sub(r'\s+[—-]\s+Заклинания.*$', '', text, flags=re.I)
        return russian_name_from_text(text)
    return ''


def parse_level(text: str) -> int:
    low = (text or '').lower().replace('ё', 'е')
    if 'заговор' in low:
        return 0
    m = re.search(r'(?:Уровень|Level)\s*[:.]\s*(\d)', text or '', flags=re.I)
    if m:
        return int(m.group(1))
    m = re.search(r'(\d)[- ]?(?:й|го)?\s+уров', low)
    if m:
        return int(m.group(1))
    return 0


def extract_components(text: str):
    line = field_value(text, ['Компоненты', 'Components'])
    if not line:
        return 'V', None

    comp = []
    if re.search(r'\b[ВV]\b|верб', line, flags=re.I):
        comp.append('V')
    if re.search(r'\b[СS]\b|сомат', line, flags=re.I):
        comp.append('S')
    if re.search(r'\b[МM]\b|матер', line, flags=re.I):
        comp.append('M')

    m = re.search(r'\((.*?)\)', line)
    material = m.group(1).strip() if m else None
    return ','.join(comp) if comp else line[:20], material


def _class_entry_is_from_ph(entry: str) -> bool:
    if _has_non_official_marker(entry):
        return False
    codes = _source_codes_from_text(entry)
    if not codes:
        return True
    return bool(codes & ALLOWED_PH_SPELL_CODES) and not bool(codes & NON_OFFICIAL_SPELL_CODES)


def extract_classes(text: str):
    line = field_value(text, ['Классы', 'Доступно классам', 'Classes'])
    if not line:
        return []

    found = []
    entries = re.split(r'[,;]', line)
    for entry in entries:
        entry_low = entry.lower().replace('ё', 'е')
        if not _class_entry_is_from_ph(entry):
            continue
        for cls in CLASS_NAMES:
            cls_low = cls.lower().replace('ё', 'е')
            if re.search(rf'(?<![а-яёa-z]){re.escape(cls_low)}(?![а-яёa-z])', entry_low) and cls not in found:
                found.append(cls)
    return found


def parse_spell_from_soup(url: str, soup) -> dict | None:
    if not is_ph_spell_page(soup):
        return None

    text = page_text(soup)
    name = spell_name_from_source_heading(soup)
    if not name:
        return None

    components, material = extract_components(text)
    return {
        'name': name,
        'level': parse_level(text),
        'school_id': school_id_from_text(text),
        'casting_time': field_value(text, ['Время накладывания', 'Время сотворения', 'Casting Time']) or '1 действие',
        'range': field_value(text, ['Дистанция', 'Range']) or 'На себя',
        'components': components[:20],
        'material_components': material,
        'duration': field_value(text, ['Длительность', 'Duration']) or 'Мгновенная',
        'description': clean_page_description(text),
        'higher_levels': field_value(text, ['На больших уровнях', 'Усиление', 'At Higher Levels']) or None,
        'is_ritual': bool(re.search(r'ритуал', text, flags=re.I)),
        'is_concentration': bool(re.search(r'концентрац', text, flags=re.I)),
        'classes': extract_classes(text),
        'url': url,
    }


def parse_spell(url: str):
    soup = get_soup(url)
    return parse_spell_from_soup(url, soup)


def _load_and_parse_spell_candidate(url: str):
    try:
        soup = get_soup(url)
        data = parse_spell_from_soup(url, soup)
        return url, data, None
    except Exception as exc:
        return url, None, exc


def load_ph_spell_data_full_scan(candidate_urls: list[str]) -> list[dict]:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    if USE_SPELL_CACHE and SPELL_LINKS_CACHE.exists():
        try:
            cached = json.loads(SPELL_LINKS_CACHE.read_text(encoding='utf-8'))
            cached_urls = cached.get('urls', [])
            if cached.get('source') == 'PH14' and cached.get('mode') == 'official_full_scan_v2' and cached_urls:
                print(f'Используется кэш полного сканирования PH/PH14: {len(cached_urls)} ссылок')
                candidate_urls = cached_urls
        except Exception:
            pass

    print(f'Этап 1: полное сканирование источников PH/PH14. Кандидатов: {len(candidate_urls)}')
    print(f'Параллельных потоков: {SPELL_WORKERS}')

    accepted_data: list[dict] = []
    accepted_urls: list[str] = []
    failed = skipped = 0

    with ThreadPoolExecutor(max_workers=max(1, SPELL_WORKERS)) as executor:
        futures = {executor.submit(_load_and_parse_spell_candidate, url): url for url in candidate_urls}
        for future in as_completed(futures):
            url, data, exc = future.result()
            if exc:
                failed += 1
                print(f'Ошибка проверки/парсинга {url}: {exc}')
                continue
            if not data:
                skipped += 1
                continue
            accepted_data.append(data)
            accepted_urls.append(url)
            print(f"PH/PH14: {data['name']} ({len(accepted_data)})")

    accepted_data.sort(key=lambda x: x['name'])
    accepted_urls = sorted(set(accepted_urls))
    SPELL_LINKS_CACHE.write_text(
        json.dumps({'source': 'PH14', 'mode': 'official_full_scan_v2', 'urls': accepted_urls}, ensure_ascii=False, indent=2),
        encoding='utf-8',
    )

    print(f'После полного фильтра PH/PH14 осталось заклинаний: {len(accepted_data)}')
    print(f'Пропущено не-PH/PH14: {skipped}; ошибок: {failed}')
    return accepted_data


def get_spell_candidates_for_full_scan() -> list[str]:
    list_page_urls = get_spell_links_from_filtered_list_page()
    sitemap_urls = get_spell_links_from_sitemap()
    urls = sorted(set(list_page_urls) | set(sitemap_urls))
    print(f'Всего уникальных кандидатов для полного сканирования: {len(urls)}')
    return urls


def save_spell(data, source_id: int) -> int:
    with cursor() as cur:
        cur.execute('SELECT id FROM spells WHERE lower(name)=lower(%s)', (data['name'],))
        row = cur.fetchone()
        if row:
            spell_id = row[0]
            cur.execute(
                """
                UPDATE spells SET level=%s, school_id=%s, casting_time=%s, range=%s, components=%s,
                    material_components=%s, duration=%s, description=%s, higher_levels=%s,
                    is_ritual=%s, is_concentration=%s, source_id=%s
                WHERE id=%s
                """,
                (data['level'], data['school_id'], data['casting_time'], data['range'], data['components'],
                 data['material_components'], data['duration'], data['description'], data['higher_levels'],
                 data['is_ritual'], data['is_concentration'], source_id, spell_id),
            )
        else:
            cur.execute(
                """
                INSERT INTO spells (name, level, school_id, casting_time, range, components, material_components,
                    duration, description, higher_levels, is_ritual, is_concentration, source_id)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id
                """,
                (data['name'], data['level'], data['school_id'], data['casting_time'], data['range'], data['components'],
                 data['material_components'], data['duration'], data['description'], data['higher_levels'],
                 data['is_ritual'], data['is_concentration'], source_id),
            )
            spell_id = cur.fetchone()[0]

        cur.execute('DELETE FROM spell_classes WHERE spell_id=%s', (spell_id,))
        return spell_id


def save_spell_classes(spell_id: int, class_names: list[str]):
    with cursor() as cur:
        for cls in class_names:
            cur.execute('SELECT id FROM classes WHERE lower(name)=lower(%s)', (cls,))
            row = cur.fetchone()
            if row:
                cur.execute(
                    'INSERT INTO spell_classes (spell_id, class_id) VALUES (%s,%s) ON CONFLICT DO NOTHING',
                    (spell_id, row[0])
                )


def parse_all_spells():
    source_id = get_or_create_source()

    candidates = get_spell_candidates_for_full_scan()
    spell_data = load_ph_spell_data_full_scan(candidates)

    print(f'Этап 2: запись в БД только PH/PH14-заклинаний: {len(spell_data)}')

    success = failed = skipped = 0
    for data in spell_data:
        try:
            if not data:
                skipped += 1
                continue
            spell_id = save_spell(data, source_id)
            save_spell_classes(spell_id, data['classes'])
            print(f"+ {data['name']} | уровень {data['level']} | классов PH: {len(data['classes'])}")
            success += 1
        except Exception as exc:
            print(f"Ошибка записи заклинания {data.get('name', data.get('url', ''))}: {exc}")
            failed += 1

    print_result('ЗАКЛИНАНИЯ PH / PH14, ПОЛНОЕ СКАНИРОВАНИЕ', success, failed, skipped)
