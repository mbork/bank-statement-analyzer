# * CSV import and deduplication

import csv
import datetime
import pathlib
import re
import sqlite3

from bank_analyzer import db

# * Exceptions

class FileAlreadyImportedError(Exception):
    pass

# * Bank configurations

BANKS: dict[str, dict] = {
    'pko_bp': {
        'encoding': 'cp1250',
        'column_sep': ',',
        'date_col': 'Data waluty',
        'date_format': '%Y-%m-%d',
        'amount_col': 'Kwota',
        'decimal_sep': '.',
        'thousand_sep': '',
        'description_cols': [
            'Typ transakcji', 'Opis transakcji', 'Opis transakcji+1', 'Opis transakcji+3',
        ],
    },
    'mbank': {
        'encoding': 'utf8',
        'column_sep': ';',
        'date_col': '#Data operacji',
        'date_format': '%Y-%m-%d',
        'amount_col': '#Kwota',
        'amount_regex': r'(?P<amount>-?[\d\s]+,\d{2}) PLN',
        'decimal_sep': ',',
        'thousand_sep': ' ',
        'description_cols': ['#Opis operacji', '#Kategoria'],
    },
}

# * Canonicalization

def canonicalize_description(description: str) -> str:
    """Strip and collapse all whitespace runs to single spaces."""
    return ' '.join(description.split())

# * Header detection

def get_anchor_cols(config: dict) -> set[str]:
    """Derive the set of anchor column names from config"""
    return {
        config['date_col'],
        config['amount_col'],
        *(col for col in config['description_cols'] if '+' not in col)
    }


def find_header_row(reader: csv.reader, anchor_cols: set[str]) -> list[str]:  # type: ignore[type-arg]
    """Find a header row in reader, return the list of column names"""
    for row in reader:
        if anchor_cols.issubset({cell.strip() for cell in row}):
            counter = 0
            last_cell = '_col'
            header = []
            for cell in row:
                if cell == '':
                    counter += 1
                    header.append(f'{last_cell}+{counter}')
                else:
                    counter = 0
                    last_cell = cell.strip()
                    header.append(last_cell)
            return header
    raise ValueError(f'Header row not found, expected columns: {sorted(anchor_cols)}')

# * Parsing and import

def parse_amount(raw: str, bank: str) -> int:
    bank_config = BANKS[bank]
    if 'amount_regex' in bank_config:
        match = re.search(bank_config['amount_regex'], raw)
        if match:
            raw = match.group('amount')
        else:
            raise ValueError(f'{raw} is not a valid amount')

    if 'thousand_sep' in bank_config:
        raw = raw.replace(bank_config['thousand_sep'], '')
    raw = raw.replace(bank_config['decimal_sep'], '.')

    try:
        return round(100 * float(raw))
    except ValueError:
        raise ValueError(f'{raw} is not a valid amount') from None

def parse_csv(filepath: pathlib.Path, bank: str) -> list[dict]:
    bank_config = BANKS[bank]
    with open(filepath, encoding=bank_config['encoding'], newline='') as f:
        reader = csv.reader(f, delimiter=bank_config['column_sep'])
        col_names = find_header_row(reader, get_anchor_cols(bank_config))
        dict_reader = csv.DictReader(f, fieldnames=col_names, delimiter=bank_config['column_sep'])
        result = []
        for row in dict_reader:
            # skip empty rows
            if not any(row.values()):
                continue
            date = datetime.datetime.strptime(
                row[bank_config['date_col']],
                bank_config['date_format']
            ).date()
            amount = parse_amount(row[bank_config['amount_col']], bank)
            description = canonicalize_description(
                ' '.join(row[col] for col in bank_config['description_cols'])
            )
            result.append({'date': date, 'amount': amount, 'description': description})
        return result

def import_file(filepath: pathlib.Path, bank: str) -> dict[str, int]:
    """Parse filepath (coming from bank) and insert its transactions into the DB.

    Returns a dict with keys 'total', 'inserted', and 'skipped'.
    Raises FileAlreadyImportedError if filepath.name was already imported.
    """
    rows = parse_csv(filepath, bank)
    with db.manage_connection() as conn:
        try:
            imported_file_id = db.insert_imported_file(conn, filepath.name)
        except sqlite3.IntegrityError as e:
            raise FileAlreadyImportedError(f'{filepath.name} has already been imported') from e
        inserted_count = db.insert_transactions(conn, rows, imported_file_id)
    return {'total': len(rows), 'inserted': inserted_count, 'skipped': len(rows) - inserted_count}
