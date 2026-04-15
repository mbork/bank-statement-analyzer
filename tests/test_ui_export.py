# * UI export alignment tests
# Guards that the header tuples in the UI views stay aligned with the column
# order produced by the export functions.  Each test writes the header
# followed by one data row and compares the result to a literal two-line CSV.
# General export behavior (escaping, None handling, etc.) is covered by
# `test_export.py`.

import csv
import io

from bank_analyzer import export
from bank_analyzer.ui.reports_view import _REPORT_CSV_HEADERS
from bank_analyzer.ui.transactions_view import _TRANSACTIONS_CSV_HEADERS

# * Tests

def test_transactions_header_aligns_with_export_columns() -> None:
    row = {'date': '2024-01-15', 'description': 'Sklep', 'amount': -1234, 'category': 'Food'}
    dest = io.StringIO()
    writer = csv.writer(dest, delimiter=';')
    writer.writerow(_TRANSACTIONS_CSV_HEADERS)
    export.transactions_to_csv([row], dest)
    expected = (
        'date;description;amount;category\r\n'
        '2024-01-15;Sklep;-12,34;Food\r\n'
    )
    assert dest.getvalue() == expected

def test_report_header_aligns_with_export_columns() -> None:
    row = {'period': '2024-01', 'category': 'Food', 'total_grosz': 5000}
    dest = io.StringIO()
    writer = csv.writer(dest, delimiter=';')
    writer.writerow(_REPORT_CSV_HEADERS)
    export.report_to_csv([row], dest)
    expected = (
        'period;category;total\r\n'
        '2024-01;Food;50,00\r\n'
    )
    assert dest.getvalue() == expected
