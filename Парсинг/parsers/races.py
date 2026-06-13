import requests
import time
import re
from bs4 import BeautifulSoup

from db import conn, cursor

BASE_URL = "https://dnd.su"
SOURCE_CODE = "PH14"
SOURCE_NAME = "Player's Handbook 2014"

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0"
})


def clean_name(text):
    text = text.strip()

    if " — " in text:
        text = text.split(" — ")[0]

    if " - " in text:
        text = text.split(" - ")[0]

    return text.strip()


def extract_russian_name_from_link_text(text):
    text = text.strip()
    text = text.replace(SOURCE_CODE, "").strip()

    match = re.match(r"^([А-Яа-яЁё\s\-]+)", text)

    if match:
        return clean_name(match.group(1))

    return clean_name(text)


def extract_speed(text):
    text = text.lower()

    match = re.search(r"скорость.*?(\d+)\s*фут", text)

    if match:
        return int(match.group(1))

    return 30


def get_or_create_source():
    cursor.execute("""
        INSERT INTO sources (name, code)
        VALUES (%s, %s)
        ON CONFLICT (code) DO NOTHING
    """, (SOURCE_NAME, SOURCE_CODE))

    conn.commit()

    cursor.execute("""
        SELECT id
        FROM sources
        WHERE code = %s
    """, (SOURCE_CODE,))

    return cursor.fetchone()[0]


def load_ability_map():
    cursor.execute("""
        SELECT id, name
        FROM ability_scores
    """)

    return {
        name.lower(): ability_id
        for ability_id, name in cursor.fetchall()
    }


def normalize_ability_name(name):
    name = name.lower().strip()

    forms = {
        "сила": "сила",
        "силы": "сила",
        "силе": "сила",

        "ловкость": "ловкость",
        "ловкости": "ловкость",

        "телосложение": "телосложение",
        "телосложения": "телосложение",
        "телосложению": "телосложение",

        "интеллект": "интеллект",
        "интеллекта": "интеллект",
        "интеллекту": "интеллект",

        "мудрость": "мудрость",
        "мудрости": "мудрость",

        "харизма": "харизма",
        "харизмы": "харизма",
        "харизме": "харизма"
    }

    return forms.get(name)


def extract_fixed_ability_bonuses(text):
    ability_map = load_ability_map()

    bonuses = []
    text = text.lower()

    patterns = [
        r"(?:значение\s+вашей|ваше\s+значение)?\s*(силы|ловкости|телосложения|интеллекта|мудрости|харизмы)\s+увеличивается\s+на\s+(\d+)",
        r"(?:ваша|ваш|ваше)\s+(сила|ловкость|телосложение|интеллект|мудрость|харизма)\s+увеличивается\s+на\s+(\d+)",
        r"(сила|ловкость|телосложение|интеллект|мудрость|харизма)\s+увеличивается\s+на\s+(\d+)",
        r"\+(\d+)\s+к\s+(силе|ловкости|телосложению|интеллекту|мудрости|харизме)"
    ]

    for pattern in patterns:
        matches = re.findall(pattern, text)

        for match in matches:
            if match[0].isdigit():
                bonus = int(match[0])
                ability_name = match[1]
            else:
                ability_name = match[0]
                bonus = int(match[1])

            normalized_name = normalize_ability_name(ability_name)

            if normalized_name and normalized_name in ability_map:
                bonuses.append({
                    "ability_score_id": ability_map[normalized_name],
                    "bonus": bonus,
                    "is_choice": False,
                    "choice_count": None,
                    "description": None
                })

    unique = []
    seen = set()

    for bonus in bonuses:
        key = (
            bonus["ability_score_id"],
            bonus["bonus"],
            bonus["is_choice"]
        )

        if key not in seen:
            seen.add(key)
            unique.append(bonus)

    return unique


def word_number_to_int(word):
    word = word.lower().strip()

    numbers = {
        "одна": 1,
        "одну": 1,
        "одной": 1,
        "один": 1,
        "одно": 1,

        "две": 2,
        "два": 2,
        "двух": 2,

        "три": 3,
        "трёх": 3,
        "трех": 3
    }

    if word.isdigit():
        return int(word)

    return numbers.get(word)


def extract_choice_ability_bonuses(text):
    bonuses = []
    text_lower = text.lower()

    patterns = [
        r"(?:значения?\s+)?((?:одной|одну|одна|один|одно|двух|две|два|трёх|трех|три|\d+))\s+(?:других\s+)?характеристик(?:и|у)?\s+на\s+ваш\s+выбор\s+увеличива(?:ются|ется)\s+на\s+(\d+)",

        r"((?:одной|одну|одна|один|одно|двух|две|два|трёх|трех|три|\d+))\s+(?:другие\s+)?характеристик(?:и|у)?\s+по\s+вашему\s+выбору\s+увеличива(?:ются|ется)\s+на\s+(\d+)",

        r"выберите\s+((?:одну|одной|одна|один|одно|две|двух|два|три|трёх|трех|\d+))\s+характеристик(?:у|и)?,?\s+котор(?:ая|ые|ую)\s+увеличива(?:ются|ется)\s+на\s+(\d+)"
    ]

    for pattern in patterns:
        matches = re.findall(pattern, text_lower)

        for match in matches:
            choice_count = word_number_to_int(match[0])
            bonus = int(match[1])

            if not choice_count:
                continue

            bonuses.append({
                "ability_score_id": None,
                "bonus": bonus,
                "is_choice": True,
                "choice_count": choice_count,
                "description": f"{choice_count} характеристики на выбор увеличиваются на {bonus}"
            })

    unique = []
    seen = set()

    for bonus in bonuses:
        key = (bonus["bonus"], bonus["choice_count"])

        if key not in seen:
            seen.add(key)
            unique.append(bonus)

    return unique


def extract_ability_bonuses(text):
    ability_text = extract_ability_section(text)

    if not ability_text:
        return []

    fixed_bonuses = extract_fixed_ability_bonuses(ability_text)
    choice_bonuses = extract_choice_ability_bonuses(ability_text)

    return fixed_bonuses + choice_bonuses

def extract_ability_section(text):
    """
    Вытаскивает только блок про увеличение характеристик.
    Это нужно, чтобы не ловить бонусы подрас и лишние примеры.
    """

    lines = text.split("\n")

    section_titles = [
        "увеличение характеристик",
        "увеличение значения характеристик",
        "увеличение значений характеристик"
    ]

    stop_titles = [
        "возраст",
        "мировоззрение",
        "размер",
        "скорость",
        "языки",
        "тёмное зрение",
        "темное зрение",
        "подрасы",
        "разновидности"
    ]

    result = []
    inside = False

    for line in lines:
        clean_line = line.strip()
        lower_line = clean_line.lower()

        if not clean_line:
            continue

        if any(title in lower_line for title in section_titles):
            inside = True
            result.append(clean_line)
            continue

        if inside and any(title == lower_line for title in stop_titles):
            break

        if inside:
            result.append(clean_line)

    return "\n".join(result)


def get_race_links():
    url = f"{BASE_URL}/race/?source={SOURCE_CODE}"

    response = session.get(url)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    race_links = []
    seen = set()

    for link in soup.find_all("a"):
        href = link.get("href")
        link_text = link.get_text(" ", strip=True)

        if not href:
            continue

        if href == "/race/":
            continue

        if not href.startswith("/race/") or href.count("/") != 3:
            continue

        if SOURCE_CODE not in link_text:
            continue

        race_name_from_list = extract_russian_name_from_link_text(link_text)

        if "своё происхождение" in race_name_from_list.lower():
            continue

        full_url = BASE_URL + href

        if full_url in seen:
            continue

        seen.add(full_url)

        race_links.append({
            "url": full_url,
            "list_name": race_name_from_list
        })

    return race_links


def parse_race(url):
    response = session.get(url)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    h1 = soup.find("h1")
    name = clean_name(h1.get_text()) if h1 else "Неизвестно"

    article = soup.find("article")

    if article:
        text = article.get_text("\n", strip=True)
    else:
        text = soup.get_text("\n", strip=True)

    speed = extract_speed(text)
    bonuses = extract_ability_bonuses(text)

    return {
        "name": name,
        "description": text,
        "speed": speed,
        "bonuses": bonuses
    }


def save_race(race_data, source_id):
    try:
        cursor.execute("""
            INSERT INTO races (
                name,
                description,
                speed,
                source_id
            )
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (name) DO NOTHING
            RETURNING id
        """, (
            race_data["name"],
            race_data["description"],
            race_data["speed"],
            source_id
        ))

        result = cursor.fetchone()

        if result:
            race_id = result[0]
        else:
            cursor.execute("""
                SELECT id
                FROM races
                WHERE name = %s
            """, (race_data["name"],))

            race_id = cursor.fetchone()[0]

        conn.commit()
        return race_id

    except Exception as e:
        conn.rollback()
        print("Ошибка сохранения расы:")
        print(e)
        return None


def save_race_bonuses(race_id, bonuses):
    try:
        cursor.execute("""
            DELETE FROM race_ability_bonuses
            WHERE race_id = %s
        """, (race_id,))

        for bonus_data in bonuses:
            cursor.execute("""
                INSERT INTO race_ability_bonuses (
                    race_id,
                    ability_score_id,
                    bonus,
                    is_choice,
                    choice_count,
                    description
                )
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                race_id,
                bonus_data.get("ability_score_id"),
                bonus_data["bonus"],
                bonus_data.get("is_choice", False),
                bonus_data.get("choice_count"),
                bonus_data.get("description")
            ))

        conn.commit()

    except Exception as e:
        conn.rollback()
        print("Ошибка сохранения бонусов:")
        print(e)


def parse_all_races():
    source_id = get_or_create_source()

    races = get_race_links()

    print(f"Источник: {SOURCE_CODE}")
    print(f"Найдено рас: {len(races)}")

    success = 0
    failed = 0

    for race in races:
        try:
            print(f"\nПарсим: {race['url']}")

            race_data = parse_race(race["url"])

            race_data["name"] = race["list_name"]

            race_id = save_race(race_data, source_id)

            if race_id:
                save_race_bonuses(race_id, race_data["bonuses"])

            fixed_count = len([
                bonus for bonus in race_data["bonuses"]
                if not bonus.get("is_choice")
            ])

            choice_count = len([
                bonus for bonus in race_data["bonuses"]
                if bonus.get("is_choice")
            ])

            print(f"Добавлено: {race_data['name']}")
            print(f"Фиксированных бонусов: {fixed_count}")
            print(f"Бонусов на выбор: {choice_count}")

            success += 1
            time.sleep(1)

        except Exception as e:
            print(f"Ошибка: {race['url']}")
            print(e)

            failed += 1

    print("\n========== ИТОГ ==========")
    print(f"Успешно: {success}")
    print(f"Ошибок: {failed}")