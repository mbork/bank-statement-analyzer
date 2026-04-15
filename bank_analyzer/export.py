# * CSV export
import csv
from typing import TextIO

from bank_analyzer.money import format_amount_csv

# * Transactions

def transactions_to_csv(rows: list[dict], dest: TextIO) -> None:
    """Write transaction rows to a semicolon-delimited CSV (no header row).

    The caller is responsible for writing the header and for opening `dest`
    with ``encoding='utf-8-sig'`` and ``newline=''``.
    Uncategorized transactions are represented as ``-``.
    """
    writer = csv.writer(dest, delimiter=';')
    for row in rows:
        amount_formatted = format_amount_csv(row['amount'])
        category = row['category']
        category_formatted = category if category is not None else '-'
        writer.writerow([
            row['date'],
            row['description'],
            amount_formatted,
            category_formatted,
        ])

# * Report

def report_to_csv(rows: list[dict], dest: TextIO) -> None:
    """Write spending report rows to a semicolon-delimited CSV (no header row).

    The caller is responsible for writing the header and for opening `dest`
    with ``encoding='utf-8-sig'`` and ``newline=''``.
    """
    writer = csv.writer(dest, delimiter=';')
    for row in rows:
        total_formatted = format_amount_csv(row['total_grosz'])
        category = row['category']
        category_formatted = category if category is not None else '-'
        writer.writerow([
            row['period'],
            category_formatted,
            total_formatted,
        ])
