import re
from urllib.parse import urlparse

from config import BASE_URL, SOURCE_CODE
from db import cursor
from parsers.common import (
    absolute,
    clean_name,
    extract_ability_bonuses,
    extract_speed,
    get_or_create_source,
    get_soup,
    page_text,
    print_result,
    russian_name_from_heading,
    source_matches,
    split_heading_sections,
)

RACE_STOP_TITLES = [
    "комментарии", "галерея", "персонализация", "имена", "возраст",
    "мировоззрение", "размер", "языки", "в мире", "в пути",
]


def get_race_links():
    """Берёт ссылки на расы прямо со страницы /race/ и фильтрует по источнику из .env."""
    soup = get_soup(f"{BASE_URL}/race/")
    links = []
    seen = set()

    for a in soup.find_all("a"):
        href = a.get("href")
        text = a.get_text(" ", strip=True)

        if not href or not re.search(r"/race/\d+[-\w]*/?", href):
            continue

        # В расах dnd.su источник находится в тексте ссылки: "Гном Gnome PH14".
        if not source_matches(text):
            continue

        name = russian_name_from_heading(text)
        if "своё происхождение" in name.lower():
            continue

        url = absolute(BASE_URL, href)
        parsed = urlparse(url)
        url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"

        if url not in seen:
            seen.add(url)
            links.append({"url": url, "name": name})

    return links


def extract_base_race_section(soup) -> str:
    """
    Берёт только блок особенностей основной расы.
    Это важно, чтобы не смешать бонусы расы и бонусы подрас.
    """
    sections = split_heading_sections(soup)

    for section in sections:
        title = section["title"].lower()
        if "особенности" in title or "расовые особенности" in title:
            return f"{section['title']}\n{section['text']}"

    return page_text(soup)


def extract_subrace_sections(soup):
    """Находит подрасы по секциям страницы, а не по ручному списку."""
    sections = split_heading_sections(soup)
    result = []
    started = False

    for section in sections:
        title = clean_name(section["title"])
        lower_title = title.lower()
        text = section["text"]
        lower_text = text.lower()

        if "подрас" in lower_title or "разновидност" in lower_title:
            started = True
            continue

        if not started:
            continue

        if any(stop in lower_title for stop in RACE_STOP_TITLES):
            break

        # Подрасу считаем полезной, если в её тексте есть признаки механики/бонусов.
        if (
            "увеличение характеристик" in lower_text
            or "увеличение значения характеристик" in lower_text
            or "значение вашей" in lower_text
            or "+" in lower_text
        ):
            result.append({"name": title, "text": text})

    return result


def parse_race(url: str, list_name: str):
    soup = get_soup(url)
    text = page_text(soup)

    heading = soup.find("h1")
    page_name = russian_name_from_heading(heading.get_text(" ", strip=True)) if heading else list_name
    name = list_name or page_name

    base_section = extract_base_race_section(soup)
    speed = extract_speed(base_section or text)

    # Бонусы берутся из текста страницы, а не из ручной таблицы в коде.
    bonuses = extract_ability_bonuses(base_section)

    subraces = []
    for sub in extract_subrace_sections(soup):
        sub_bonuses = extract_ability_bonuses(sub["text"])
        if sub_bonuses:
            subraces.append({
                "name": sub["name"],
                "description": sub["text"],
                "bonuses": sub_bonuses,
            })

    return {
        "name": name,
        "description": text,
        "speed": speed,
        "bonuses": bonuses,
        "subraces": subraces,
    }


def save_race(data: dict, source_id: int) -> int:
    with cursor() as cur:
        cur.execute(
            """
            INSERT INTO races (name, description, speed, source_id)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (name) DO UPDATE
            SET description = EXCLUDED.description,
                speed = EXCLUDED.speed,
                source_id = EXCLUDED.source_id
            RETURNING id
            """,
            (data["name"], data["description"], data["speed"], source_id),
        )
        return cur.fetchone()[0]


def save_subrace(race_id: int, data: dict, source_id: int) -> int:
    with cursor() as cur:
        cur.execute(
            """
            SELECT id FROM subraces
            WHERE race_id = %s AND lower(name) = lower(%s)
            """,
            (race_id, data["name"]),
        )
        row = cur.fetchone()
        if row:
            subrace_id = row[0]
            cur.execute(
                """
                UPDATE subraces
                SET description = %s, source_id = %s
                WHERE id = %s
                """,
                (data["description"], source_id, subrace_id),
            )
            return subrace_id

        cur.execute(
            """
            INSERT INTO subraces (name, description, race_id, source_id)
            VALUES (%s, %s, %s, %s)
            RETURNING id
            """,
            (data["name"], data["description"], race_id, source_id),
        )
        return cur.fetchone()[0]


def save_race_bonuses(race_id: int, bonuses: list[dict]):
    with cursor() as cur:
        cur.execute("DELETE FROM race_ability_bonuses WHERE race_id = %s", (race_id,))
        for bonus in bonuses:
            cur.execute(
                """
                INSERT INTO race_ability_bonuses
                    (race_id, ability_score_id, bonus, is_choice, choice_count, description)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    race_id,
                    bonus.get("ability_score_id"),
                    bonus["bonus"],
                    bonus.get("is_choice", False),
                    bonus.get("choice_count"),
                    bonus.get("description"),
                ),
            )


def save_subrace_bonuses(subrace_id: int, bonuses: list[dict]):
    with cursor() as cur:
        cur.execute("DELETE FROM race_ability_bonuses WHERE subrace_id = %s", (subrace_id,))
        for bonus in bonuses:
            cur.execute(
                """
                INSERT INTO race_ability_bonuses
                    (subrace_id, ability_score_id, bonus, is_choice, choice_count, description)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    subrace_id,
                    bonus.get("ability_score_id"),
                    bonus["bonus"],
                    bonus.get("is_choice", False),
                    bonus.get("choice_count"),
                    bonus.get("description"),
                ),
            )


def parse_all_races():
    source_id = get_or_create_source()
    links = get_race_links()
    print(f"Найдено рас {SOURCE_CODE}: {len(links)}")

    success = 0
    failed = 0
    for item in links:
        try:
            data = parse_race(item["url"], item["name"])
            race_id = save_race(data, source_id)
            save_race_bonuses(race_id, data["bonuses"])

            for subrace in data["subraces"]:
                subrace_id = save_subrace(race_id, subrace, source_id)
                save_subrace_bonuses(subrace_id, subrace["bonuses"])

            print(f"+ {data['name']} | бонусов: {len(data['bonuses'])} | подрас: {len(data['subraces'])}")
            success += 1
        except Exception as exc:
            print(f"Ошибка расы: {item['url']}")
            print(exc)
            failed += 1

    print_result("РАСЫ", success, failed)
