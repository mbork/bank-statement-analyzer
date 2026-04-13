# * Importer tests

import csv
import datetime
import pathlib
import pytest
import re

FIXTURES = pathlib.Path(__file__).parent / 'fixtures'

from bank_analyzer import db, importer

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


# ** parse_amount
def test_parse_amount_pko_bp():
    assert importer.parse_amount('-6743.52', 'pko_bp') == -674352

@pytest.mark.parametrize('raw', [
    '1,234.56',   # comma not a valid decimal sep for pko_bp
    '1.234,56',   # European format, comma survives into float()
    '',           # empty string
])
def test_parse_amount_pko_bp_invalid(raw):
    with pytest.raises(ValueError):
        importer.parse_amount(raw, 'pko_bp')

def test_parse_amount_mbank_with_thousand_sep():
    assert importer.parse_amount('-1 234,56 PLN', 'mbank') == -123456

@pytest.mark.parametrize('raw', [
    'no match here',  # completely wrong
    '-43.52 PLN',     # period instead of comma
    '-43,52 USD',     # wrong currency
    '12,34PLN',       # no space before PLN
    '12,34  PLN',     # two spaces before PLN
    'PLN -43,52',     # currency before amount
])
def test_parse_amount_mbank_invalid(raw):
    with pytest.raises(ValueError):
        importer.parse_amount(raw, 'mbank')


# ** parse_csv
def test_parse_csv_mbank():
    result = importer.parse_csv(FIXTURES / 'lista_operacji_mbank.csv', 'mbank')
    assert len(result) == 24
    assert result[0] == {
        'date': datetime.date(2026, 4, 8),
        'amount': -80000,
        'description': 'BLIK WYPŁATA ATM WŁASNY PLANET CASH BLIK WYPŁATA ATM WŁASNY Wypłata gotówki',
    }
    assert result[11] == {
        'date': datetime.date(2026, 4, 1),
        'amount': 30000,
        'description': 'KONTRAHENT UL.STRASZNA 3 60-123 POZNAŃ PRZELEW WEWNĘTRZNY PRZYCHODZĄCY 00000000000000000000001000 Wpływy - inne',
    }
    assert result[23] == {
        'date': datetime.date(2026, 3, 15),
        'amount': -19000,
        'description': 'COMPANY R BLIK ZAKUP E-COMMERCE Zajęcia dodatkowe',
    }

def test_parse_csv_pko_bp_1():
    result = importer.parse_csv(FIXTURES / 'lista_operacji_pko_bp_1.csv', 'pko_bp')
    assert len(result) == 11
    assert result[2] == {
        'date': datetime.date(2026, 2, 19),
        'amount': -160000,
        'description': 'Wypłata z bankomatu Tytuł: PKO BP 10204027S1PO1965N6625C1252 Lokalizacja: Adres: Szeroka 67 Miasto: POZNAN Kraj: POLSKA Kwota Cash Back: 0.00',
    }
    assert result[10] == {
        'date': datetime.date(2026, 2, 4),
        'amount': -1000,
        'description': 'Opłata za użytkowanie karty Tytuł: OPŁATA MIESIĘCZNA ZA KARTĘ 123456******0987, 29.12-28.01',
    }

def test_parse_csv_pko_bp_2():
    result = importer.parse_csv(FIXTURES / 'lista_operacji_pko_bp_2.csv', 'pko_bp')
    assert len(result) == 11
    assert result[10] == {
        'date': datetime.date(2026, 2, 19),
        'amount': -160000,
        'description': 'Wypłata z bankomatu Tytuł: PKO BP 10204027S1PO1965N6625C1252 Lokalizacja: Adres: Szeroka 67 Miasto: POZNAN Kraj: POLSKA Kwota Cash Back: 0.00',
    }


# ** import_file

@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    monkeypatch.setenv('BANK_ANALYZER_DATA_DIR', str(tmp_path))
    with db.manage_connection() as conn:
        db.create_schema(conn)
        yield

def test_import_file(temp_db):
    stats = importer.import_file(FIXTURES / 'lista_operacji_pko_bp_1.csv', 'pko_bp')
    assert stats['total'] == 11
    assert stats['inserted'] == 11
    assert stats['skipped'] == 0

def test_duplicate_file_raises_error(temp_db):
    importer.import_file(FIXTURES / 'lista_operacji_mbank.csv', 'mbank')
    with pytest.raises(importer.FileAlreadyImportedError):
        importer.import_file(FIXTURES / 'lista_operacji_mbank.csv', 'mbank')

def test_duplicate_transactions_are_deduplicated(temp_db):
    importer.import_file(FIXTURES / 'lista_operacji_pko_bp_1.csv', 'pko_bp')
    stats2 = importer.import_file(FIXTURES / 'lista_operacji_pko_bp_2.csv', 'pko_bp')
    assert stats2['total'] == 11
    assert stats2['inserted'] == 8
    assert stats2['skipped'] == 3
