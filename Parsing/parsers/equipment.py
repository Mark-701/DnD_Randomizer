import re
from urllib.parse import urlparse

from config import EQUIPMENT_BASE_URL
from db import cursor
from parsers.common import (
    absolute,
    clean_name,
    clean_spaces,
    get_or_create_simple,
    get_or_create_source,
    get_soup,
    page_text,
    print_result,
    russian_name_from_heading,
)


def guess_category(raw_category: str, text: str) -> str:
    value = f"{raw_category} {text}".lower()
    if "оруж" in value or "арбалет" in value or "меч" in value or "лук" in value:
        return "Оружие"
    if "доспех" in value or "брон" in value or "щит" in value:
        return "Доспехи"
    if "инструмент" in value or "набор" in value and "снаряжения" not in value:
        return "Инструменты"
    if "боеприпас" in value or "стрел" in value or "болт" in value:
        return "Амуниция"
    if "транспорт" in value or "повоз" in value or "кораб" in value:
        return "Транспорт"
    if "еда" in value or "напит" in value or "рацион" in value:
        return "Еда и напитки"
    if "услуг" in value:
        return "Услуги"
    if "живот" in value or "лошад" in value:
        return "Вьючные животные"
    return clean_name(raw_category) or "Предметы"


def get_equipment_links():
    soup = get_soup(f"{EQUIPMENT_BASE_URL}/equipment/")
    links = []
    seen = set()

    for a in soup.find_all("a", href=True):
        href = a.get("href")

        if not href:
            continue

        # На next.dnd.su предметы имеют вид:
        # /equipment/4-dagger
        # /equipment/84-arrows
        if not re.search(r"^/equipment/\d+[-\w]*$", href):
            continue

        url = absolute(EQUIPMENT_BASE_URL, href)

        parsed = urlparse(url)
        url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"

        if url not in seen:
            seen.add(url)
            links.append(url)

    return links

def find_equipment_heading(soup):
    """
    Ищет настоящий заголовок предмета, а не служебный заголовок сайта.
    На странице предмета нормальный заголовок выглядит так:
    Кинжал [Dagger]
    """
    headings = soup.find_all(["h1", "h2", "h3"])

    for heading in headings:
        text = clean_spaces(heading.get_text(" ", strip=True))

        if not text:
            continue

        lower = text.lower()

        # Пропускаем служебные заголовки
        if lower in ["dnd.su", "снаряжение", "комментарии", "галерея"]:
            continue

        # Хороший признак карточки предмета:
        # русское название + английское название в квадратных скобках
        if "[" in text and "]" in text:
            return heading

    # Запасной вариант: первый нормальный h2/h1 после служебных
    for heading in headings:
        text = clean_spaces(heading.get_text(" ", strip=True))
        lower = text.lower()

        if lower not in ["dnd.su", "снаряжение", "комментарии", "галерея"]:
            return heading

    return None


def parse_equipment(url: str):
    soup = get_soup(url)
    text = page_text(soup)

    heading = find_equipment_heading(soup)

    if not heading:
        raise ValueError(f"Не найден заголовок предмета: {url}")

    name = russian_name_from_heading(heading.get_text(" ", strip=True))

    if not name or name.lower() == "dnd.su" or name.lower() == "снаряжение":
        raise ValueError(f"Неверное название предмета '{name}' на странице {url}")

    lines = [clean_spaces(line) for line in text.split("\n") if clean_spaces(line)]

    raw_category = "Предметы"

    # На странице предмета после заголовка идут строки:
    # Простое Рукопашное оружие
    # Стоимость: 2 ЗМ
    # Вес: 1 фнт.
    for index, line in enumerate(lines):
        if name.lower() in line.lower():
            for next_line in lines[index + 1:index + 6]:
                lower = next_line.lower()

                if "стоимость" in lower or "вес" in lower or "урон" in lower:
                    continue

                if any(word in lower for word in [
                    "оружие",
                    "доспех",
                    "инструмент",
                    "предмет",
                    "набор",
                    "боеприпас",
                    "щит",
                    "фокусировка"
                ]):
                    raw_category = next_line
                    break

            break

    category_name = guess_category(raw_category, text)
    return {
        "name": name,
        "category_name": category_name,
        "description": text,
    }


def save_equipment(data: dict, source_id: int) -> int:
    category_id = get_or_create_simple("equipment_categories", data["category_name"])

    with cursor() as cur:
        cur.execute(
            "SELECT id FROM equipment WHERE lower(name) = lower(%s)",
            (data["name"],)
        )

        row = cur.fetchone()

        if row:
            equipment_id = row[0]

            cur.execute(
                """
                UPDATE equipment
                SET category_id = %s,
                    description = %s,
                    source_id = %s
                WHERE id = %s
                """,
                (
                    category_id,
                    data["description"],
                    source_id,
                    equipment_id,
                )
            )

            return equipment_id

        cur.execute(
            """
            INSERT INTO equipment
                (name, category_id, description, source_id)
            VALUES
                (%s, %s, %s, %s)
            RETURNING id
            """,
            (
                data["name"],
                category_id,
                data["description"],
                source_id,
            )
        )

        return cur.fetchone()[0]


def parse_all_equipment():
    source_id = get_or_create_source()
    links = get_equipment_links()
    print(f"Найдено предметов снаряжения: {len(links)}")

    success = 0
    failed = 0
    for url in links:
        try:
            data = parse_equipment(url)
            if not data["name"] or data["name"] == "Снаряжение":
                continue
            save_equipment(data, source_id)
            print(f"+ {data['name']} [{data['category_name']}]")
            success += 1
        except Exception as exc:
            print(f"Ошибка предмета: {url}")
            print(exc)
            failed += 1

    print_result("СНАРЯЖЕНИЕ", success, failed)
