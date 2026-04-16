# * Seed script
# Populates the DB with categories, rules, and sample transactions
# from the fixture CSVs for manual testing/development.
#
# Usage: uv run python scripts/seed.py

import pathlib

from dotenv import load_dotenv

load_dotenv()

from bank_analyzer import categories, db, importer, rules  # noqa: E402

# * Data

_FIXTURES = pathlib.Path(__file__).parent.parent / 'tests' / 'fixtures'

_SEED_CATEGORIES = [
    'Groceries',
    'Restaurants',
    'Cash / ATM',
    'Bank fees',
    'Fuel',
    'Online shopping',
    'Utilities',
    'Insurance',
    'Income',
    'Charity',
]

# (pattern, category name) — first matching rule wins at import time
_SEED_RULES = [
    ('LIDL',         'Groceries'),
    ('KFC',          'Restaurants'),
    ('McDonalds',    'Restaurants'),
    ('PKO BP',       'Cash / ATM'),
    ('BLIK WYPŁATA', 'Cash / ATM'),
    ('OPŁATA',       'Bank fees'),
    ('ALLEGRO',      'Online shopping'),
    ('BP STACJA',    'Fuel'),
    ('COMPANY Y',    'Utilities'),
    ('COMPANY Z',    'Utilities'),
    ('COMPANY P',    'Utilities'),
    ('LINK4',        'Insurance'),
    ('Smok Wawelski','Income'),
    ('PayPal',       'Income'),
    ('KONTRAHENT',   'Income'),
    ('FUNDACJA',     'Charity'),
]

_SEED_FILES = [
    ('lista_operacji_mbank.csv',    'mbank'),
    ('lista_operacji_pko_bp_1.csv', 'pko_bp'),
    # lista_operacji_pko_bp_2.csv intentionally omitted — left for the user to import manually
]

# * Seed

def seed() -> None:
    # ** Schema
    with db.manage_connection() as conn:
        db.create_schema(conn)

    # ** Categories
    print('Creating categories...')
    cat_map: dict[str, int] = {}
    for name in _SEED_CATEGORIES:
        row = categories.add_category(name)
        cat_map[name] = row['category_id']
        print(f'  + {name}')

    # ** Rules
    print('Creating rules...')
    for pattern, cat_name in _SEED_RULES:
        rules.insert_rule(pattern, cat_map[cat_name])
        print(f'  + "{pattern}" → {cat_name}')

    # ** Import CSVs
    print('Importing transactions...')
    for filename, bank in _SEED_FILES:
        filepath = _FIXTURES / filename
        try:
            result = importer.import_file(filepath, bank)
            print(
                f'  {filename}: '
                f'{result["inserted"]} inserted, '
                f'{result["skipped"]} skipped, '
                f'{result["categorized"]} categorized'
            )
        except importer.FileAlreadyImportedError:
            print(f'  {filename}: already imported, skipped')

    print('Done.')

if __name__ == '__main__':
    seed()
