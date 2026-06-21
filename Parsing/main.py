import argparse

from db import conn
from parsers.backgrounds import parse_all_backgrounds
from parsers.classes import parse_all_classes
from parsers.equipment import parse_all_equipment
from parsers.feats import parse_all_feats
from parsers.races import parse_all_races
from parsers.spells import parse_all_spells


def main():
    parser = argparse.ArgumentParser(description='Полный парсер dnd.su под структуру БД DnD Randomizer')
    parser.add_argument(
        'target',
        nargs='?',
        default='all',
        choices=['all', 'races', 'classes', 'backgrounds', 'equipment', 'spells', 'feats'],
        help='Что парсить',
    )
    args = parser.parse_args()

    try:
        # Порядок важен: сначала классы, затем заклинания, потому что spell_classes ссылается на classes.
        if args.target in ['all', 'classes']:
            parse_all_classes()

        if args.target in ['all', 'races']:
            parse_all_races()

        if args.target in ['all', 'backgrounds']:
            parse_all_backgrounds()

        if args.target in ['all', 'equipment']:
            parse_all_equipment()

        if args.target in ['all', 'spells']:
            parse_all_spells()

        if args.target in ['all', 'feats']:
            parse_all_feats()
    finally:
        conn.close()


if __name__ == '__main__':
    main()
