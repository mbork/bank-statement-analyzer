# * Money formatting tests

import pytest

from bank_analyzer.money import format_amount_csv, format_amount_ui

# * format_amount_csv tests

@pytest.mark.parametrize(('amount', 'expected'), [
    (0,       '0,00'),
    (100,     '1,00'),
    (101,     '1,01'),
    (105,     '1,05'),   # leading zero in grosz
    (1234,    '12,34'),
    (100000,  '1000,00'),  # no thousands separator in CSV
    (-100,    '-1,00'),
    (-101,    '-1,01'),
    (-1234,   '-12,34'),
])
def test_format_amount_csv(amount: int, expected: str) -> None:
    assert format_amount_csv(amount) == expected

# * format_amount_ui tests

@pytest.mark.parametrize(('amount', 'expected'), [
    (0,         '0,00'),
    (100,       '1,00'),
    (101,       '1,01'),
    (105,       '1,05'),         # leading zero in grosz
    (1234,      '12,34'),
    (100000,    '1\u00a0000,00'),  # thousands separator
    (1000000,   '10\u00a0000,00'),
    (10000000,  '100\u00a0000,00'),
    (-100,      '-1,00'),
    (-100000,   '-1\u00a0000,00'),
])
def test_format_amount_ui(amount: int, expected: str) -> None:
    assert format_amount_ui(amount) == expected
