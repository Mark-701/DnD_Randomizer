import re
import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from config import HEADERS, REQUEST_DELAY, SOURCE_CODE, SOURCE_NAME
from db import cursor

session = requests.Session()
session.headers.update(HEADERS)

ABILITY_FORMS = {
    "сила": "Сила", "силы": "Сила", "силе": "Сила", "силу": "Сила",
    "ловкость": "Ловкость", "ловкости": "Ловкость", "ловкостью": "Ловкость",
    "телосложение": "Телосложение", "телосложения": "Телосложение", "телосложению": "Телосложение",
    "интеллект": "Интеллект", "интеллекта": "Интеллект", "интеллекту": "Интеллект",
    "мудрость": "Мудрость", "мудрости": "Мудрость", "мудростью": "Мудрость",
    "харизма": "Харизма", "харизмы": "Харизма", "харизме": "Харизма", "харизму": "Харизма",
}

SKILL_NAMES = [
    "Атлетика", "Акробатика", "Ловкость рук", "Скрытность", "Анализ",
    "История", "Магия", "Природа", "Религия", "Восприятие",
    "Выживание", "Медицина", "Проницательность", "Уход за животными",
    "Выступление", "Запугивание", "Обман", "Убеждение",
]

COINS = {
    "мм": "cp", "мед": "cp",
    "см": "sp", "сер": "sp",
    "эм": "ep",
    "зм": "gp", "зол": "gp",
    "пм": "pp", "плат": "pp",
}




def normalize_source_name(value: str) -> str:
    """Убирает год из названия источника, чтобы PH14 = Player's Handbook."""
    value = clean_spaces(value).lower()
    value = re.sub(r"\b(2014|2024)\b", "", value)
    value = value.replace("’", "'")
    return clean_spaces(value)


def source_matches(text: str) -> bool:
    """Проверяет, относится ли строка/ссылка к выбранному источнику из .env."""
    text_norm = normalize_source_name(text)
    code_norm = SOURCE_CODE.lower()
    source_norm = normalize_source_name(SOURCE_NAME)

    aliases = {code_norm, source_norm}

    # Для PH14 на dnd.su в разных разделах источник бывает написан по-разному:
    # в расах — PH14, в классах/предысториях — Player's Handbook.
    if code_norm == "ph14":
        aliases.add("player's handbook")
        aliases.add("players handbook")

    return any(alias and alias in text_norm for alias in aliases)


def looks_like_source_heading(text: str) -> bool:
    """Грубая проверка строки-заголовка источника на странице списка."""
    text = clean_spaces(text)
    if not text or len(text) > 90:
        return False
    # Источники на dnd.su в списках обычно написаны латиницей: Player's Handbook, Tasha's...
    return bool(re.search(r"[A-Za-z]", text)) and not bool(re.search(r"/|http|@", text))


def get_soup(url: str) -> BeautifulSoup:
    time.sleep(REQUEST_DELAY)
    response = session.get(url, timeout=30)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def absolute(base: str, href: str) -> str:
    return urljoin(base + "/", href)


def clean_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def clean_name(text: str) -> str:
    text = clean_spaces(text)
    text = re.sub(r"\[[^\]]+\]", "", text)
    text = text.replace(SOURCE_CODE, "")
    text = re.sub(r"\bPH\d+\b", "", text)
    text = re.sub(r"\s+—\s+.*$", "", text)
    text = re.sub(r"\s+-\s+.*$", "", text)
    return clean_spaces(text)


def russian_name_from_heading(text: str) -> str:
    text = clean_spaces(text)
    text = re.sub(r"\[[^\]]+\]", "", text)
    text = text.replace(SOURCE_CODE, "")
    match = re.match(r"^([А-Яа-яЁё\s\-]+)", text)
    return clean_name(match.group(1) if match else text)


def page_text(soup: BeautifulSoup) -> str:
    main = soup.find("article") or soup.find("main") or soup.body or soup
    return main.get_text("\n", strip=True)


def split_heading_sections(soup: BeautifulSoup):
    """
    Делит страницу на секции по h2/h3/h4.
    Возвращает список: {level, title, text}.
    """
    main = soup.find("article") or soup.find("main") or soup.body or soup
    headings = main.find_all(["h2", "h3", "h4"])
    sections = []

    for heading in headings:
        level = int(heading.name[1])
        title = clean_spaces(heading.get_text(" ", strip=True))
        parts = []

        for sibling in heading.next_siblings:
            name = getattr(sibling, "name", None)
            if name in ["h2", "h3", "h4"] and int(name[1]) <= level:
                break
            if hasattr(sibling, "get_text"):
                txt = sibling.get_text("\n", strip=True)
            else:
                txt = str(sibling).strip()
            if txt:
                parts.append(txt)

        sections.append({"level": level, "title": title, "text": "\n".join(parts)})

    return sections


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


def get_id_by_name(table: str, name: str):
    with cursor() as cur:
        cur.execute(f"SELECT id FROM {table} WHERE lower(name) = lower(%s)", (name,))
        row = cur.fetchone()
        return row[0] if row else None


def get_or_create_simple(table: str, name: str, **extra) -> int:
    existing = get_id_by_name(table, name)
    if existing:
        return existing

    columns = ["name"] + list(extra.keys())
    values = [name] + list(extra.values())
    placeholders = ", ".join(["%s"] * len(values))

    with cursor() as cur:
        cur.execute(
            f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders}) RETURNING id",
            values,
        )
        return cur.fetchone()[0]


def load_ability_map() -> dict[str, int]:
    with cursor() as cur:
        cur.execute("SELECT id, name FROM ability_scores")
        return {name.lower(): ability_id for ability_id, name in cur.fetchall()}


def normalize_ability_name(value: str):
    return ABILITY_FORMS.get((value or "").lower().strip())


def extract_fixed_ability_bonuses(text: str):
    ability_map = load_ability_map()
    bonuses = []
    lower = text.lower().replace("ё", "е")

    patterns = [
        r"(?:значение\s+вашей|значение\s+вашего|ваше\s+значение|ваша|ваш|ваше)?\s*(силы|ловкости|телосложения|интеллекта|мудрости|харизмы|сила|ловкость|телосложение|интеллект|мудрость|харизма)\s+увеличивается\s+на\s+(\d+)",
        r"\+(\d+)\s+к\s+(силе|ловкости|телосложению|интеллекту|мудрости|харизме)",
    ]

    for pattern in patterns:
        for match in re.findall(pattern, lower, flags=re.I):
            if match[0].isdigit():
                bonus = int(match[0])
                ability_word = match[1]
            else:
                ability_word = match[0]
                bonus = int(match[1])

            normalized = normalize_ability_name(ability_word.replace("е", "ё") if ability_word == "телосложение" else ability_word)
            normalized = normalized or normalize_ability_name(ability_word)
            if normalized and normalized.lower() in ability_map:
                bonuses.append({
                    "ability_score_id": ability_map[normalized.lower()],
                    "bonus": bonus,
                    "is_choice": False,
                    "choice_count": None,
                    "description": None,
                })

    return unique_bonuses(bonuses)


def word_number_to_int(word: str):
    if not word:
        return None
    word = word.lower().strip().replace("ё", "е")
    numbers = {
        "одна": 1, "одну": 1, "одной": 1, "один": 1, "одно": 1,
        "две": 2, "два": 2, "двух": 2,
        "три": 3, "трех": 3,
    }
    return int(word) if word.isdigit() else numbers.get(word)


def extract_choice_ability_bonuses(text: str):
    bonuses = []
    lower = text.lower().replace("ё", "е")
    number_words = r"одной|одну|одна|один|одно|двух|две|два|трех|три|\d+"

    patterns = [
        rf"({number_words})\s+(?:других\s+|любых\s+)?характеристик(?:и|у)?\s+(?:на\s+ваш\s+выбор|по\s+вашему\s+выбору)\s+увеличива(?:ются|ется)\s+на\s+(\d+)",
        rf"выберите\s+({number_words})\s+характеристик(?:у|и)?,?.*?увеличива(?:ются|ется)\s+на\s+(\d+)",
    ]

    for pattern in patterns:
        for count_word, bonus_value in re.findall(pattern, lower, flags=re.I):
            count = word_number_to_int(count_word)
            if count:
                bonuses.append({
                    "ability_score_id": None,
                    "bonus": int(bonus_value),
                    "is_choice": True,
                    "choice_count": count,
                    "description": f"{count} характеристики на выбор увеличиваются на {bonus_value}",
                })

    return unique_bonuses(bonuses)


def unique_bonuses(bonuses):
    result = []
    seen = set()
    for bonus in bonuses:
        key = (
            bonus.get("ability_score_id"),
            bonus.get("bonus"),
            bonus.get("is_choice"),
            bonus.get("choice_count"),
        )
        if key not in seen:
            seen.add(key)
            result.append(bonus)
    return result


def extract_ability_bonuses(text: str):
    return unique_bonuses(
        extract_fixed_ability_bonuses(text) + extract_choice_ability_bonuses(text)
    )


def extract_speed(text: str) -> int:
    """
    Достаёт скорость именно из пункта 'Скорость.',
    а не из случайной фразы со словом 'скорость'.
    """

    if not text:
        return 30

    normalized = clean_spaces(text)

    patterns = [
        # Скорость. Ваша базовая скорость ходьбы составляет 25 футов.
        r"Скорость\s*[.:]\s*[^.]*?(\d+)\s*фут",

        # Ваша базовая скорость ходьбы составляет 25 футов.
        r"базовая\s+скорость\s+ходьбы\s+составляет\s+(\d+)\s*фут",

        # Ваша скорость ходьбы составляет 30 футов.
        r"скорость\s+ходьбы\s+составляет\s+(\d+)\s*фут",

        # Ваша скорость равна 30 футам.
        r"скорость\s+равна\s+(\d+)\s*фут",
    ]

    for pattern in patterns:
        match = re.search(pattern, normalized, flags=re.IGNORECASE)

        if match:
            speed = int(match.group(1))

            # Защита от мусора: обычная скорость персонажей в D&D 5e
            # чаще всего 25, 30 или 35 футов.
            if 15 <= speed <= 60:
                return speed

    return 30


def extract_list_after_label(text: str, label: str) -> list[str]:
    """Достаёт строку после 'Владение навыками:' до конца строки."""
    pattern = rf"{re.escape(label)}\s*:\s*(.+)"
    match = re.search(pattern, text, flags=re.I)
    if not match:
        return []
    line = clean_spaces(match.group(1))
    line = re.split(r"(?:\.|;|\n)", line)[0]
    return [clean_name(x) for x in re.split(r",| и ", line) if clean_name(x)]


def extract_known_skills(text: str) -> list[str]:
    found = []
    for skill in SKILL_NAMES:
        if re.search(rf"\b{re.escape(skill)}\b", text, flags=re.I):
            found.append(skill)
    return found


def parse_cost(text: str):
    match = re.search(
        r"Стоимость\s*:\s*([\d,.]+)\s*([А-Яа-я]+)",
        text,
        flags=re.I
    )

    if not match:
        return None, None

    value = float(match.group(1).replace(",", "."))
    coin_raw = match.group(2).lower()

    coin = next((code for key, code in COINS.items() if key in coin_raw), "gp")

    return value, coin


def parse_weight(text: str):
    match = re.search(r"Вес\s*:\s*([\d,.]+)\s*ф", text, flags=re.I)
    if not match:
        return None
    return float(match.group(1).replace(",", "."))


def parse_quantity_around(item_name: str, text: str) -> int:
    """
    Пытается найти количество рядом с названием предмета.
    Поддерживает варианты: '20 стрел', '20 болтов', '2 x кинжал', 'стрелы 20 штук'.
    Если количество не найдено, возвращает 1.
    """
    escaped = re.escape(item_name)
    lower_name = item_name.lower()
    # Грубый корень для русских множественных форм: Стрелы -> стрел, Болты -> болт.
    stem = re.escape(re.sub(r"[ыияаей]+$", "", lower_name))

    patterns = [
        rf"(\d+)\s*[×x]\s*{escaped}",
        rf"(\d+)\s+{escaped}",
        rf"(\d+)\s+{stem}\w*",
        rf"{escaped}[^\n,;]*(\d+)\s*(?:штук|шт|дней)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, flags=re.I)
        if match:
            return int(match.group(1))

    return 1


def load_equipment_names() -> list[tuple[int, str]]:
    with cursor() as cur:
        cur.execute("SELECT id, name FROM equipment ORDER BY length(name) DESC")
        return cur.fetchall()


def find_equipment_mentions(text: str) -> list[tuple[int, str, int]]:
    mentions = []
    lower = text.lower()
    for equipment_id, name in load_equipment_names():
        if name.lower() in lower:
            mentions.append((equipment_id, name, parse_quantity_around(name, text)))
    return mentions


def print_result(title: str, success: int, failed: int):
    print("\n==========", title, "==========")
    print("Успешно:", success)
    print("Ошибок:", failed)
