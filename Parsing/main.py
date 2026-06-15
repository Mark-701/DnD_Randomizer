import argparse

from db import conn
from parsers.backgrounds import parse_all_backgrounds
from parsers.classes import parse_all_classes
from parsers.equipment import parse_all_equipment
from parsers.races import parse_all_races


def main():
    parser = argparse.ArgumentParser(description="Парсер dnd.su для DnD Randomizer")
    parser.add_argument(
        "target",
        nargs="?",
        default="all",
        choices=["all", "equipment", "races", "classes", "backgrounds"],
        help="Что парсить",
    )
    args = parser.parse_args()

    try:
        if args.target in ["all", "equipment"]:
            parse_all_equipment()

        if args.target in ["all", "races"]:
            parse_all_races()

        if args.target in ["all", "classes"]:
            # Классы лучше парсить после equipment, чтобы стартовые предметы могли связаться с equipment.
            parse_all_classes()

        if args.target in ["all", "backgrounds"]:
            # Предыстории тоже лучше после equipment.
            parse_all_backgrounds()
    finally:
        conn.close()


if __name__ == "__main__":
    main()
