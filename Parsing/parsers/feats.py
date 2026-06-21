import re
from urllib.parse import urlparse

from db import cursor
from parsers.common import (
    BASE_URL, clean_page_description, clean_spaces, extract_ability_bonuses,
    field_value, get_or_create_source, get_sitemap_urls, get_soup, page_root,
    page_text, print_result, russian_name_from_text, absolute
)

# Черты берём только из старого Player's Handbook: PH / PH14 / PHB.
# PH24 сам по себе не подходит.
ALLOWED_PH_FEAT_CODES = {'PH', 'PH14', 'PHB'}
NON_OFFICIAL_FEAT_CODES = {'HB', 'UA', 'HOMEBREW'}
SOURCE_CODES_RE = (
    r'(PH14|PH24|PHB|PH|XGE|TCE|SCAG|EEPC|POA|FTD|FTOD|VRGR|AI|EGW|SCC|BMT|HB|UA|DMG|GGR|ERLW|RMR|SATO|AAG|IDROTF|GOS|LLK|OGA|DOSI|HOMEBREW)'
)
NON_OFFICIAL_WORDS_RE = r'(?:homebrew|хоумбрю|домашн(?:ий|ее|яя)|неофициальн|unearthed\s+arcana|раскопанн(?:ые|ая)\s+арканы)'
ALLOWED_HOSTS = {'dnd.su', 'www.dnd.su', '5e14.dnd.su'}
BLOCKED_HOSTS = {'next.dnd.su'}


def _normalize_feat_url(url: str) -> str:
    parsed = urlparse(url)
    return f'{parsed.scheme or "https"}://{parsed.netloc.lower()}{parsed.path.rstrip("/")}/'


def _is_feat_url(url: str) -> bool:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    if host in BLOCKED_HOSTS or host not in ALLOWED_HOSTS:
        return False
    return re.match(r'^/feats/\d+(?:[-_/a-zA-Z0-9]*)/?$', parsed.path) is not None


def _source_codes_from_text(text: str) -> set[str]:
    if not text:
        return set()
    return {m.group(1).upper() for m in re.finditer(SOURCE_CODES_RE, text, flags=re.I)}


def _has_non_official_marker(text: str) -> bool:
    if not text:
        return False
    codes = _source_codes_from_text(text)
    if codes & NON_OFFICIAL_FEAT_CODES:
        return True
    return bool(re.search(NON_OFFICIAL_WORDS_RE, text, flags=re.I))


def get_feat_links():
    urls = []
    for url in get_sitemap_urls(r'/feats/\d+'):
        if _is_feat_url(url):
            urls.append(_normalize_feat_url(url))

    # Дополнительный источник — сама страница списка черт.
    try:
        soup = get_soup(f'{BASE_URL.rstrip("/")}/feats/')
        for a in soup.find_all('a', href=True):
            url = absolute(a.get('href'))
            if _is_feat_url(url):
                urls.append(_normalize_feat_url(url))
    except Exception as exc:
        print(f'Не удалось прочитать /feats/: {exc}')

    return sorted(set(urls))


def _short_text_candidates(soup) -> list[str]:
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

    for node in root.find_all(string=True):
        txt = clean_spaces(str(node))
        if not txt or len(txt) > 220:
            continue
        if re.search(SOURCE_CODES_RE, txt, flags=re.I):
            # У черт английское название в [] бывает не всегда, поэтому разрешаем просто короткую строку с источником.
            if txt not in candidates:
                candidates.append(txt)

    return candidates


def feat_source_heading(soup) -> str:
    candidates = []
    for text in _short_text_candidates(soup):
        if re.search(SOURCE_CODES_RE, text, flags=re.I):
            candidates.append(text)
    if not candidates:
        return ''
    candidates.sort(key=len)
    return candidates[0]


def extract_source_codes_from_heading(heading: str) -> set[str]:
    if not heading:
        return set()
    if ']' in heading:
        heading = heading.split(']', 1)[1]
    return _source_codes_from_text(heading)


def is_ph_feat_page(soup) -> bool:
    heading = feat_source_heading(soup)
    codes = extract_source_codes_from_heading(heading)
    if not codes:
        return False
    if not bool(codes & ALLOWED_PH_FEAT_CODES):
        return False
    if bool(codes & NON_OFFICIAL_FEAT_CODES):
        return False
    if _has_non_official_marker(heading):
        return False
    # Не проверяем весь текст страницы: там могут быть ссылки меню на homebrew/PH24.
    return True


def feat_name_from_heading(soup) -> str:
    heading = feat_source_heading(soup)
    if heading:
        # Убираем английское название и коды источника.
        text = re.sub(r'\[.*?\].*$', '', heading).strip()
        text = re.sub(SOURCE_CODES_RE, '', text, flags=re.I).strip()
        text = re.sub(r'\s+[—-]\s+.*$', '', text).strip()
        if text:
            return russian_name_from_text(text)

    h1 = page_root(soup).find('h1') or soup.find('h1')
    if h1:
        return russian_name_from_text(h1.get_text(' ', strip=True))
    return ''


def parse_feat(url: str):
    soup = get_soup(url)
    if not is_ph_feat_page(soup):
        return None

    text = page_text(soup)
    name = feat_name_from_heading(soup)
    if not name:
        return None

    return {
        'name': name,
        'description': clean_page_description(text),
        'prerequisite': field_value(text, ['Требование', 'Требования', 'Prerequisite']) or None,
        'benefit': field_value(text, ['Преимущество', 'Эффект', 'Benefit']) or clean_page_description(text),
        # В текущей таблице feat_ability_bonuses нет полей is_choice/choice_count,
        # поэтому сюда сохраняем только фиксированные бонусы.
        'bonuses': [b for b in extract_ability_bonuses(text) if not b.get('is_choice') and b.get('ability_score_id')],
    }


def save_feat(data, source_id: int) -> int:
    with cursor() as cur:
        cur.execute(
            """
            INSERT INTO feats (name, description, prerequisite, benefit, source_id)
            VALUES (%s,%s,%s,%s,%s)
            ON CONFLICT (name) DO UPDATE
            SET description=EXCLUDED.description, prerequisite=EXCLUDED.prerequisite,
                benefit=EXCLUDED.benefit, source_id=EXCLUDED.source_id
            RETURNING id
            """,
            (data['name'], data['description'], data['prerequisite'], data['benefit'], source_id),
        )
        feat_id = cur.fetchone()[0]
        cur.execute('DELETE FROM feat_ability_bonuses WHERE feat_id=%s', (feat_id,))
        for b in data['bonuses']:
            cur.execute(
                'INSERT INTO feat_ability_bonuses (feat_id, ability_score_id, bonus) VALUES (%s,%s,%s)',
                (feat_id, b['ability_score_id'], b['bonus'])
            )
        return feat_id


def parse_all_feats():
    source_id = get_or_create_source()
    urls = get_feat_links()
    print(f'Найдено официальных URL-кандидатов черт: {len(urls)}')
    success = failed = skipped = 0
    for url in urls:
        try:
            data = parse_feat(url)
            if not data:
                skipped += 1
                continue
            save_feat(data, source_id)
            print(f"+ {data['name']} | бонусов: {len(data['bonuses'])}")
            success += 1
        except Exception as exc:
            print(f'Ошибка черты {url}: {exc}')
            failed += 1
    print_result('ЧЕРТЫ PH / PH14', success, failed, skipped)
