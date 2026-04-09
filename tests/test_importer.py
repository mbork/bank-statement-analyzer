# * Importer tests

import csv
import pytest
import re

from bank_analyzer import importer

# ** canonicalize_description
def test_no_whitespace_unchanged():
    assert importer.canonicalize_description('aqq') == 'aqq'

def test_empty_string_unchanged():
    assert importer.canonicalize_description('') == ''

def test_blank_string_collapsed():
    assert importer.canonicalize_description('  \t\n') == ''

def test_normal_string_unchanged():
    assert importer.canonicalize_description('aqq bum') == 'aqq bum'

def test_leading_whitespace_stripped():
    assert importer.canonicalize_description(' \taqq') == 'aqq'

def test_trailing_whitespace_stripped():
    assert importer.canonicalize_description('aqq\n') == 'aqq'

def test_whitespace_collapsed():
    assert importer.canonicalize_description('  aqq\t bum\n\n   \tbęc\t\n') == 'aqq bum bęc'


# ** get_anchor_cols
def test_anchor_cols_includes_date_and_amount():
    config = {
        'date_col': 'Data',
        'amount_col': 'Kwota',
        'description_cols': [],
    }
    assert importer.get_anchor_cols(config) == {'Data', 'Kwota'}


def test_anchor_cols_includes_non_synthetic_description_cols():
    config = {
        'date_col': 'Data',
        'amount_col': 'Kwota',
        'description_cols': ['Opis', 'Opis+1', 'Opis+2'],
    }
    assert importer.get_anchor_cols(config) == {'Data', 'Kwota', 'Opis'}


# ** find_header_row
def test_simple_header_returned():
    reader = csv.reader([
        'Data,Kwota,Opis',
        '2026-04-09,100.00,Zasilenie konta',
    ])
    assert importer.find_header_row(reader, {'Data', 'Kwota', 'Opis'}) == ['Data', 'Kwota', 'Opis']
    assert next(reader) == ['2026-04-09', '100.00', 'Zasilenie konta']

def test_no_header_row():
    reader = csv.reader([
        'Data,Kwota',
        'Kwota,Opis',
        'Data,Opis',
        'something,something',
    ])
    with pytest.raises(ValueError, match=re.escape("Header row not found, expected columns: ['Data', 'Kwota', 'Opis']")):
        importer.find_header_row(reader, {'Data', 'Kwota', 'Opis'})

def test_preamble_ignored():
    reader = csv.reader([
        'preamble,row',
        'Data,Kwota',
        'something,something,very,long,row',
        'Data,Kwota,Opis,',
        '2026-04-09,-100.00,Dino,gotówka',
    ])
    assert importer.find_header_row(reader, {'Data', 'Kwota', 'Opis'}) == ['Data', 'Kwota', 'Opis', 'Opis+1']
    assert next(reader) == ['2026-04-09', '-100.00', 'Dino', 'gotówka']

def test_spaces_in_column_names_stripped():
    reader = csv.reader([
        '\tData,   Kwota\t,Opis ',
        '2026-04-09,-50.00,Spar',
    ])
    assert importer.find_header_row(reader, {'Data', 'Kwota', 'Opis'}) == ['Data', 'Kwota', 'Opis']
    assert next(reader) == ['2026-04-09', '-50.00', 'Spar']

def test_synthetic_column_names():
    reader = csv.reader([
        'Data,,Kwota,Opis,,',
        '2026-04-09,,-50.00,Spar,,',
    ])
    assert importer.find_header_row(reader, {'Data', 'Kwota', 'Opis'}) == ['Data', 'Data+1', 'Kwota', 'Opis', 'Opis+1', 'Opis+2']
    assert next(reader) == ['2026-04-09', '', '-50.00', 'Spar', '', '']

def test_extra_names_columns_included():
    reader = csv.reader([
        'Data,Opis,Kwota,Waluta',
        '2026-04-09,Żabka,-20.00,PLN',
    ])
    assert importer.find_header_row(reader, {'Data', 'Kwota', 'Opis'}) == ['Data', 'Opis', 'Kwota', 'Waluta']
    assert next(reader) == ['2026-04-09', 'Żabka', '-20.00', 'PLN']
