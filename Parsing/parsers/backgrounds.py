import re
from urllib.parse import urlparse
from bs4 import NavigableString

from config import BASE_URL
from db import cursor
from parsers.common import (
    absolute,
    clean_name,
    clean_spaces,
    extract_known_skills,
    find_equipment_mentions,
    get_or_create_simple,
    get_or_create_source,
    get_soup,
    looks_like_source_heading,
    page_text,
    print_result,
    russian_name_from_heading,
    source_matches,
    split_heading_sections,
)


def get_background_links():
    """
    Берёт предыстории из нужного раздела источника на /backgrounds/.
    Для PH14 на сайте ссылки не содержат 'PH14', поэтому ищем блок 'Player's Handbook'
    и берём ссылки до следующего заголовка источника.
    """
    soup = get_soup(f"{BASE_URL}/backgrounds/")
    main = soup.find("article") or soup.find("main") or soup.body or soup

    links = []
    seen = set()
    active_source = False
    collected_after_source = False

    for node in main.descendants:
        if isinstance(node, NavigableString):
            text = clean_spaces(str(node))
            if not text:
                continue

            if source_matches(text):
                active_source = True
                collected_after_source = False
                continue

            if active_source and collected_after_source and looks_like_source_heading(text):
                # Начался следующий источник, значит блок выбранного источника закончился.
                break

        if getattr(node, "name", None) != "a" or not active_source:
            continue

        href = node.get("href")
        text = node.get_text(" ", strip=True)

        if not href or not re.search(r"/backgrounds/\d+[-\w]*/?", href):
            continue

        name = russian_name_from_heading(text)
        url = absolute(BASE_URL, href)
        parsed = urlparse(url)
        url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"

        if url not in seen:
            seen.add(url)
            links.append({"url": url, "name": name})
            collected_after_source = True

    # Запасной вариант для источников, у которых код/название указаны прямо в тексте ссылки.
    if not links:
        for a in soup.find_all("a"):
            href = a.get("href")
            text = a.get_text(" ", strip=True)
            if href and re.search(r"/backgrounds/\d+[-\w]*/?", href) and source_matches(text):
                url = absolute(BASE_URL, href)
                parsed = urlparse(url)
                url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                if url not in seen:
                    seen.add(url)
                    links.append({"url": url, "name": russian_name_from_heading(text)})

    return links


def extract_line(text: str, label: str) -> str:
    match = re.search(rf"{re.escape(label)}\s*:\s*(.+)", text, flags=re.I)
    if not match:
        return ""
    return clean_spaces(match.group(1))


def extract_tools(text: str) -> list[str]:
    line = extract_line(text, "Владение инструментами")
    if not line:
        return []
    line = re.split(r"(?:\.|\n)", line)[0]
    return [clean_name(x) for x in re.split(r",| и ", line) if clean_name(x)]


def extract_equipment_text(text: str) -> str:
    match = re.search(r"Снаряжение\s*:\s*(.+?)(?:\n\s*###|\n\s*##|\n[A-ЯЁ][^\n]{1,80}:|$)", text, flags=re.I | re.S)
    return clean_spaces(match.group(1)) if match else ""

def clean_background_description(text: str) -> str:
    """
    Убирает из описания предыстории служебные блоки сайта:
    Boosty, комментарии, рекламу, навигацию и т.п.
    """

    if not text:
        return ""

    stop_words = [
        "Boosty",
        "Комментарии",
        "Оставить комментарий",
        "Войти",
        "Регистрация",
        "Навигация",
        "Поддержать проект",
        "Patreon",
        "Telegram",
        "Discord",
        "Поделиться",
        "Главная",
    ]

    cleaned = text

    for word in stop_words:
        index = cleaned.lower().find(word.lower())

        if index != -1:
            cleaned = cleaned[:index]
            break

    # Убираем слишком частые пустые строки и пробелы
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    cleaned = re.sub(r"[ \t]+", " ", cleaned)

    return cleaned.strip()


def extract_feature(soup):
    sections = split_heading_sections(soup)
    for section in sections:
        title = clean_spaces(section["title"])
        lower = title.lower()
        if "умение" in lower or lower.startswith("особенность"):
            feature_name = re.sub(r"^умение\s*:\s*", "", title, flags=re.I)
            feature_name = re.sub(r"^особенность\s*:\s*", "", feature_name, flags=re.I)
            return clean_name(feature_name), clean_spaces(section["text"])
    return None, None


def parse_background(url: str, list_name: str):
    soup = get_soup(url)

    full_text = page_text(soup)
    text = clean_background_description(full_text)

    heading = soup.find("h1")
    page_name = russian_name_from_heading(heading.get_text(" ", strip=True)) if heading else list_name
    name = list_name or page_name

    feature_name, feature_description = extract_feature(soup)
    starting_equipment_text = extract_equipment_text(text)

    return {
        "name": name,
        "description": text,
        "feature_name": feature_name,
        "feature_description": clean_background_description(feature_description),
        "skills": extract_known_skills(extract_line(text, "Владение навыками") or text),
        "tools": extract_tools(text),
        "starting_equipment": find_equipment_mentions(starting_equipment_text),
        "starting_equipment_text": starting_equipment_text,
    }


def save_background(data: dict, source_id: int) -> int:
    with cursor() as cur:
        cur.execute(
            """
            INSERT INTO backgrounds (name, description, feature_name, feature_description, source_id)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (name) DO UPDATE
            SET description = EXCLUDED.description,
                feature_name = EXCLUDED.feature_name,
                feature_description = EXCLUDED.feature_description,
                source_id = EXCLUDED.source_id
            RETURNING id
            """,
            (
                data["name"],
                data["description"],
                data["feature_name"],
                data["feature_description"],
                source_id,
            ),
        )
        return cur.fetchone()[0]


def save_background_skills(background_id: int, skill_names: list[str]):
    with cursor() as cur:
        cur.execute("DELETE FROM background_skills WHERE background_id = %s", (background_id,))
        for skill_name in skill_names:
            cur.execute("SELECT id FROM skills WHERE lower(name) = lower(%s)", (skill_name,))
            row = cur.fetchone()
            if row:
                cur.execute(
                    """
                    INSERT INTO background_skills (background_id, skill_id)
                    VALUES (%s, %s)
                    ON CONFLICT (background_id, skill_id) DO NOTHING
                    """,
                    (background_id, row[0]),
                )


def save_background_tools(background_id: int, tool_names: list[str]):
    with cursor() as cur:
        cur.execute("DELETE FROM background_tools WHERE background_id = %s", (background_id,))
        for tool_name in tool_names:
            tool_id = get_or_create_simple("tool_proficiencies", tool_name)
            cur.execute(
                """
                INSERT INTO background_tools (background_id, tool_id)
                VALUES (%s, %s)
                ON CONFLICT (background_id, tool_id) DO NOTHING
                """,
                (background_id, tool_id),
            )


def save_background_equipment(background_id: int, mentions: list[tuple[int, str, int]], raw_text: str):
    with cursor() as cur:
        cur.execute("DELETE FROM background_starting_equipment WHERE background_id = %s", (background_id,))
        seen = set()
        for equipment_id, name, quantity in mentions:
            key = (background_id, equipment_id)
            if key in seen:
                continue
            seen.add(key)
            cur.execute(
                """
                INSERT INTO background_starting_equipment (background_id, equipment_id, quantity, description)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT DO NOTHING
                """,
                (background_id, equipment_id, quantity, raw_text),
            )


def parse_all_backgrounds():
    source_id = get_or_create_source()
    links = get_background_links()
    print(f"Найдено предысторий выбранного источника: {len(links)}")

    success = 0
    failed = 0
    for item in links:
        try:
            data = parse_background(item["url"], item["name"])
            background_id = save_background(data, source_id)
            save_background_skills(background_id, data["skills"])
            save_background_tools(background_id, data["tools"])
            save_background_equipment(background_id, data["starting_equipment"], data["starting_equipment_text"])
            print(f"+ {data['name']} | навыков: {len(data['skills'])} | инструментов: {len(data['tools'])} | предметов: {len(data['starting_equipment'])}")
            success += 1
        except Exception as exc:
            print(f"Ошибка предыстории: {item['url']}")
            print(exc)
            failed += 1

    print_result("ПРЕДЫСТОРИИ", success, failed)
