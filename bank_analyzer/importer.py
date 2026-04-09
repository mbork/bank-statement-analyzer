# * CSV import and deduplication

import csv
import pathlib

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
        'description_cols': ['Typ transakcji', 'Opis transakcji', 'Opis transakcji+1', 'Opis transakcji+3'],
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

def parse_csv(filepath: pathlib.Path, bank: str) -> list[dict]:
    ...

def import_file(filepath: pathlib.Path, bank: str) -> dict[str, int]:
    ...
