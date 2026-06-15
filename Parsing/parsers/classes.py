import re
from urllib.parse import urlparse

from config import BASE_URL
from db import cursor
from parsers.common import (
    absolute,
    clean_spaces,
    extract_known_skills,
    find_equipment_mentions,
    get_id_by_name,
    get_or_create_source,
    get_soup,
    page_text,
    print_result,
    russian_name_from_heading,
    source_matches,
    split_heading_sections,
)


def get_class_links():
    """Берёт классы с /class/ по источнику в тексте ссылки, без ручного списка классов."""
    soup = get_soup(f"{BASE_URL}/class/")
    links = []
    seen = set()

    for a in soup.find_all("a"):
        href = a.get("href")
        text = a.get_text(" ", strip=True)

        if not href or not re.search(r"/class/\d+[-\w]*/?", href):
            continue

        # На странице классов источник написан в ссылке: "Воин Fighter Player's Handbook".
        if not source_matches(text):
            continue

        name = russian_name_from_heading(text)
        url = absolute(BASE_URL, href)
        parsed = urlparse(url)
        url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"

        if url not in seen:
            seen.add(url)
            links.append({"url": url, "name": name})

    return links


def extract_hit_die(text: str) -> str:
    """Берёт кость хитов из текста страницы класса."""
    lower = text.lower().replace("к", "d")

    patterns = [
        r"кость\s+хитов\s*[:—-]?\s*(?:1)?d(6|8|10|12)",
        r"хиты\s+на\s+1\s+уровне.*?d(6|8|10|12)",
        r"(?:1)?d(6|8|10|12)\s+за\s+уровень",
        r"(?:1)?d(6|8|10|12)",
    ]

    for pattern in patterns:
        match = re.search(pattern, lower, flags=re.S)
        if match:
            return "d" + match.group(1)

    # Технический запасной вариант, если сайт поменял формат текста.
    return "d8"


def extract_primary_ability_id(text: str):
    """Пытается взять основную характеристику из текста страницы, а не из словаря классов."""
    ability_names = ["Сила", "Ловкость", "Телосложение", "Интеллект", "Мудрость", "Харизма"]

    patterns = [
        r"основн(?:ая|ые)\s+характеристик(?:а|и)\s*[:—-]?\s*([^\.\n]+)",
        r"главн(?:ая|ые)\s+характеристик(?:а|и)\s*[:—-]?\s*([^\.\n]+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, flags=re.I)
        if match:
            fragment = match.group(1)
            for ability in ability_names:
                if re.search(rf"\b{re.escape(ability)}\b", fragment, flags=re.I):
                    return get_id_by_name("ability_scores", ability)

    # Если отдельной строки нет, берём первую характеристику из блока про заклинания/создание класса.
    for ability in ["Интеллект", "Мудрость", "Харизма", "Сила", "Ловкость"]:
        if re.search(rf"\b{re.escape(ability)}\b", text, flags=re.I):
            return get_id_by_name("ability_scores", ability)

    return None


def extract_starting_equipment_text(soup) -> str:
    sections = split_heading_sections(soup)
    for section in sections:
        title = section["title"].lower()
        if "снаряжение" in title or "стартовое" in title or "начальное" in title:
            return section["text"]

    text = page_text(soup)
    match = re.search(
        r"(?:Снаряжение|Начальное снаряжение|Стартовое снаряжение)\s*[:\n](.+?)(?:\n\s*###|\n\s*##|Классовые умения|Мультиклассирование|$)",
        text,
        flags=re.I | re.S,
    )
    return match.group(1) if match else ""


def extract_skill_choice_text(soup) -> str:
    text = page_text(soup)
    match = re.search(
        r"(?:Навыки|Владение навыками)\s*[:\n](.+?)(?:\n|\.)",
        text,
        flags=re.I | re.S,
    )
    return match.group(1) if match else text


def parse_class(url: str, list_name: str):
    soup = get_soup(url)
    text = page_text(soup)
    heading = soup.find("h1")
    page_name = russian_name_from_heading(heading.get_text(" ", strip=True)) if heading else list_name
    name = list_name or page_name

    skill_text = extract_skill_choice_text(soup)
    skills = extract_known_skills(skill_text)

    equipment_text = extract_starting_equipment_text(soup)
    equipment_mentions = find_equipment_mentions(equipment_text)

    return {
        "name": name,
        "description": text,
        "hit_die": extract_hit_die(text),
        "primary_ability_id": extract_primary_ability_id(text),
        "skills": skills,
        "starting_equipment": equipment_mentions,
        "starting_equipment_text": clean_spaces(equipment_text),
    }


def save_class(data: dict, source_id: int) -> int:
    with cursor() as cur:
        cur.execute("SELECT id FROM classes WHERE lower(name) = lower(%s)", (data["name"],))
        row = cur.fetchone()
        if row:
            class_id = row[0]
            cur.execute(
                """
                UPDATE classes
                SET description = %s,
                    hit_die = %s,
                    primary_ability_id = %s,
                    source_id = %s
                WHERE id = %s
                """,
                (data["description"], data["hit_die"], data["primary_ability_id"], source_id, class_id),
            )
            return class_id

        cur.execute(
            """
            INSERT INTO classes (name, description, hit_die, primary_ability_id, source_id)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
            """,
            (data["name"], data["description"], data["hit_die"], data["primary_ability_id"], source_id),
        )
        return cur.fetchone()[0]


def save_class_skills(class_id: int, skill_names: list[str]):
    with cursor() as cur:
        cur.execute("DELETE FROM class_skill_choices WHERE class_id = %s", (class_id,))
        for skill_name in skill_names:
            cur.execute("SELECT id FROM skills WHERE lower(name) = lower(%s)", (skill_name,))
            row = cur.fetchone()
            if row:
                cur.execute(
                    """
                    INSERT INTO class_skill_choices (class_id, skill_id)
                    VALUES (%s, %s)
                    ON CONFLICT (class_id, skill_id) DO NOTHING
                    """,
                    (class_id, row[0]),
                )


def save_class_equipment(class_id: int, mentions: list[tuple[int, str, int]]):
    with cursor() as cur:
        cur.execute("DELETE FROM class_starting_equipment WHERE class_id = %s", (class_id,))
        seen = set()
        for equipment_id, _name, quantity in mentions:
            key = (class_id, equipment_id)
            if key in seen:
                continue
            seen.add(key)
            cur.execute(
                """
                INSERT INTO class_starting_equipment (class_id, equipment_id, quantity)
                VALUES (%s, %s, %s)
                """,
                (class_id, equipment_id, quantity),
            )


def parse_all_classes():
    source_id = get_or_create_source()
    links = get_class_links()
    print(f"Найдено классов выбранного источника: {len(links)}")

    success = 0
    failed = 0
    for item in links:
        try:
            data = parse_class(item["url"], item["name"])
            class_id = save_class(data, source_id)
            save_class_skills(class_id, data["skills"])
            save_class_equipment(class_id, data["starting_equipment"])
            print(f"+ {data['name']} | {data['hit_die']} | навыков: {len(data['skills'])} | старт. предметов: {len(data['starting_equipment'])}")
            success += 1
        except Exception as exc:
            print(f"Ошибка класса: {item['url']}")
            print(exc)
            failed += 1

    print_result("КЛАССЫ", success, failed)
