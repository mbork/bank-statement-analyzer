# * Export tests

import csv
import io

from bank_analyzer import export

# * Helpers

def parse_csv(text: str) -> list[list[str]]:
    return list(csv.reader(io.StringIO(text), delimiter=';'))

# * transactions_to_csv tests

def test_transactions_to_csv_basic() -> None:
    rows = [
        {'date': '2024-01-15', 'description': 'Sklep', 'amount': -1234, 'category': 'Food'},
    ]
    dest = io.StringIO()
    export.transactions_to_csv(rows, dest)
    parsed = parse_csv(dest.getvalue())
    assert parsed == [['2024-01-15', 'Sklep', '-12,34', 'Food']]

def test_transactions_to_csv_uncategorized() -> None:
    rows = [
        {'date': '2024-01-15', 'description': 'Sklep', 'amount': -100, 'category': None},
    ]
    dest = io.StringIO()
    export.transactions_to_csv(rows, dest)
    parsed = parse_csv(dest.getvalue())
    assert parsed[0][3] == '-'

def test_transactions_to_csv_multiple_rows() -> None:
    rows = [
        {'date': '2024-01-01', 'description': 'A', 'amount': -100, 'category': 'X'},
        {'date': '2024-01-02', 'description': 'B', 'amount': -200, 'category': 'Y'},
    ]
    dest = io.StringIO()
    export.transactions_to_csv(rows, dest)
    parsed = parse_csv(dest.getvalue())
    assert len(parsed) == 2
    assert parsed[1][0] == '2024-01-02'

def test_transactions_to_csv_empty() -> None:
    dest = io.StringIO()
    export.transactions_to_csv([], dest)
    assert dest.getvalue() == ''

def test_transactions_to_csv_no_header() -> None:
    rows = [
        {'date': '2024-01-01', 'description': 'A', 'amount': -100, 'category': 'X'},
    ]
    dest = io.StringIO()
    export.transactions_to_csv(rows, dest)
    parsed = parse_csv(dest.getvalue())
    assert len(parsed) == 1  # data row only, no header

def test_transactions_to_csv_description_with_semicolon() -> None:
    rows = [
        {'date': '2024-01-01', 'description': 'A; B', 'amount': -100, 'category': 'X'},
    ]
    dest = io.StringIO()
    export.transactions_to_csv(rows, dest)
    parsed = parse_csv(dest.getvalue())
    assert parsed[0][1] == 'A; B'

# * report_to_csv tests

def test_report_to_csv_basic() -> None:
    rows = [
        {'period': '2024-01', 'category': 'Food', 'total_grosz': 5000},
    ]
    dest = io.StringIO()
    export.report_to_csv(rows, dest)
    parsed = parse_csv(dest.getvalue())
    assert parsed == [['2024-01', 'Food', '50,00']]

def test_report_to_csv_uncategorized() -> None:
    rows = [
        {'period': '2024-01', 'category': None, 'total_grosz': 100},
    ]
    dest = io.StringIO()
    export.report_to_csv(rows, dest)
    parsed = parse_csv(dest.getvalue())
    assert parsed[0][1] == '-'

def test_report_to_csv_empty() -> None:
    dest = io.StringIO()
    export.report_to_csv([], dest)
    assert dest.getvalue() == ''

def test_report_to_csv_no_header() -> None:
    rows = [
        {'period': '2024-01', 'category': 'Food', 'total_grosz': 5000},
    ]
    dest = io.StringIO()
    export.report_to_csv(rows, dest)
    parsed = parse_csv(dest.getvalue())
    assert len(parsed) == 1
