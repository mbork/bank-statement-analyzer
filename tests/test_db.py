# * Database tests

import datetime
import sqlite3

import pytest

from bank_analyzer import db


def test_insert_imported_file(conn):
    assert db.insert_imported_file(conn, 'filename.csv', 'bank') == 1
    rows = conn.execute('select * from imported_files').fetchall()
    assert len(rows) == 1
    row = rows[0]
    assert row['imported_file_id'] == 1
    assert row['filename'] == 'filename.csv'
    assert row['bank'] == 'bank'
    datetime.datetime.fromisoformat(row['imported_at']) # raises if invalid


# ** insert_transactions

ROWS_A = [
    {'date': datetime.date(2026, 4, 1), 'amount': -500, 'description': 'Żabka'},
    {'date': datetime.date(2026, 4, 2), 'amount': -1200, 'description': 'Biedronka'},
]

ROWS_B = [
    # duplicate of ROWS_A[1]
    {'date': datetime.date(2026, 4, 2), 'amount': -1200, 'description': 'Biedronka'},
    {'date': datetime.date(2026, 4, 3), 'amount': -300, 'description': 'Dino'},
]


def test_insert_transactions_inserts_rows(conn):
    file_id = db.insert_imported_file(conn, 'file.csv', 'bank')
    count = db.insert_transactions(conn, ROWS_A, file_id)
    assert count == 2
    rows = conn.execute('select * from transactions').fetchall()
    assert len(rows) == 2


def test_insert_transactions_deduplicates_identical_set(conn):
    file_id = db.insert_imported_file(conn, 'file.csv', 'bank')
    db.insert_transactions(conn, ROWS_A, file_id)
    count = db.insert_transactions(conn, ROWS_A, file_id)
    assert count == 0
    rows = conn.execute('select * from transactions').fetchall()
    assert len(rows) == 2


def test_insert_transactions_deduplicates_overlapping_sets(conn):
    file_id = db.insert_imported_file(conn, 'file.csv', 'bank')
    db.insert_transactions(conn, ROWS_A, file_id)
    count = db.insert_transactions(conn, ROWS_B, file_id)
    assert count == 1
    rows = conn.execute('select * from transactions').fetchall()
    assert len(rows) == 3

# * Categories

def test_get_all_categories_empty(conn):
    assert db.get_all_categories(conn) == []

def test_get_all_categories_returns_names_sorted_alphabetically(conn):
    db.insert_category(conn, 'groceries')
    db.insert_category(conn, 'books')
    db.insert_category(conn, 'utilities')
    assert [c['name'] for c in db.get_all_categories(conn)] == ['books', 'groceries', 'utilities']

def test_insert_category(conn):
    result = db.insert_category(conn, 'groceries')
    assert result['name'] == 'groceries'
    assert isinstance(result['category_id'], int)

def test_insert_category_duplicate_raises(conn):
    db.insert_category(conn, 'books')
    with pytest.raises(sqlite3.IntegrityError):
        db.insert_category(conn, 'books')

def test_update_category_changes_name(conn):
    result_insert = db.insert_category(conn, 'food')
    category_id = result_insert['category_id']
    db.update_category(conn, category_id, 'groceries')
    assert db.get_all_categories(conn) == [{'category_id': category_id, 'name': 'groceries'}]

def test_update_category_nonexistent_raises(conn):
    with pytest.raises(ValueError, match='no category with id 1337'):
        db.update_category(conn, 1337, 'leet')

def test_update_category_duplicate_raises(conn):
    result_food = db.insert_category(conn, 'food')
    db.insert_category(conn, 'utilities')
    with pytest.raises(sqlite3.IntegrityError):
        db.update_category(conn, result_food['category_id'], 'utilities')

def test_delete_category_removes_row(conn):
    result = db.insert_category(conn, 'food')
    assert len(db.get_all_categories(conn)) == 1
    db.delete_category(conn, result['category_id'])
    assert len(db.get_all_categories(conn)) == 0

def test_delete_category_nonexistent_raises(conn):
    with pytest.raises(ValueError, match='no category with id 1337'):
        db.delete_category(conn, 1337)

def test_delete_category_raises_when_referenced_by_transaction(conn):
    category = db.insert_category(conn, 'food')
    category_id = category['category_id']
    file_id = db.insert_imported_file(conn, 'file.csv', 'bank')
    row = {
        'date': datetime.date(2026, 4, 1),
        'amount': -500,
        'description': 'Żabka',
    }
    db.insert_transactions(conn, [row], file_id)
    transaction_id = conn.execute('select transaction_id from transactions').fetchone()[0]
    db.set_transaction_category(conn, transaction_id, category_id)
    with pytest.raises(sqlite3.IntegrityError):
        db.delete_category(conn, category_id)

# * get_all_transactions / set_transaction_category

@pytest.fixture
def transaction_id(conn):
    file_id = db.insert_imported_file(conn, 'file.csv', 'bank')
    db.insert_transactions(conn, [
        {'date': datetime.date(2026, 4, 1), 'amount': -500, 'description': 'Żabka'},
    ], file_id)
    return conn.execute('select transaction_id from transactions').fetchone()[0]

def test_get_all_transactions_includes_category_id(conn, transaction_id):
    rows = db.get_all_transactions(conn)
    assert len(rows) == 1
    assert rows[0]['transaction_id'] == transaction_id
    assert rows[0]['category_id'] is None

def test_set_transaction_category_assigns_category(conn, transaction_id):
    category_id = db.insert_category(conn, 'food')['category_id']
    db.set_transaction_category(conn, transaction_id, category_id)
    rows = db.get_all_transactions(conn)
    assert rows[0]['category_id'] == category_id
    assert rows[0]['category'] == 'food'

def test_set_transaction_category_clears_category(conn, transaction_id):
    category_id = db.insert_category(conn, 'food')['category_id']
    db.set_transaction_category(conn, transaction_id, category_id)
    db.set_transaction_category(conn, transaction_id, None)
    rows = db.get_all_transactions(conn)
    assert rows[0]['category_id'] is None
    assert rows[0]['category'] is None

# * Filters

def test_get_all_transactions_no_filter_returns_all(conn):
    file_id = db.insert_imported_file(conn, 'file.csv', 'bank')
    db.insert_transactions(conn, [
        {'date': datetime.date(2026, 4, 1), 'amount': -500, 'description': 'Żabka'},
        {'date': datetime.date(2026, 4, 2), 'amount': -1000, 'description': 'Biedronka'},
    ], file_id)
    assert len(db.get_all_transactions(conn)) == 2

def test_get_all_transactions_filters_by_category(conn):
    file_id = db.insert_imported_file(conn, 'file.csv', 'bank')
    db.insert_transactions(conn, [
        {'date': datetime.date(2026, 4, 1), 'amount': -500, 'description': 'Żabka'},
        {'date': datetime.date(2026, 4, 2), 'amount': -1000, 'description': 'Biedronka'},
    ], file_id)
    category_id = db.insert_category(conn, 'groceries')['category_id']
    t_id = conn.execute(
        "select transaction_id from transactions where description = 'Żabka'"
    ).fetchone()[0]
    db.set_transaction_category(conn, t_id, category_id)
    rows = db.get_all_transactions(conn, db.TransactionFilters(category_id=category_id))
    assert len(rows) == 1
    assert rows[0]['description'] == 'Żabka'

def test_get_all_transactions_filters_by_date_from(conn):
    file_id = db.insert_imported_file(conn, 'file.csv', 'bank')
    db.insert_transactions(conn, [
        {'date': datetime.date(2026, 3, 31), 'amount': -500, 'description': 'Żabka'},
        {'date': datetime.date(2026, 4, 1), 'amount': -1000, 'description': 'Biedronka'},
    ], file_id)
    rows = db.get_all_transactions(
        conn,
        db.TransactionFilters(date_from=datetime.date(2026, 4, 1)),
    )
    assert len(rows) == 1
    assert rows[0]['description'] == 'Biedronka'

def test_get_all_transactions_filters_by_date_to(conn):
    file_id = db.insert_imported_file(conn, 'file.csv', 'bank')
    db.insert_transactions(conn, [
        {'date': datetime.date(2026, 3, 31), 'amount': -500, 'description': 'Żabka'},
        {'date': datetime.date(2026, 4, 1), 'amount': -1000, 'description': 'Biedronka'},
    ], file_id)
    rows = db.get_all_transactions(
        conn,
        db.TransactionFilters(date_to=datetime.date(2026, 3, 31)),
    )
    assert len(rows) == 1
    assert rows[0]['description'] == 'Żabka'

def test_get_all_transactions_filters_by_date_range(conn):
    file_id = db.insert_imported_file(conn, 'file.csv', 'bank')
    db.insert_transactions(conn, [
        {'date': datetime.date(2026, 3, 1), 'amount': -500, 'description': 'Żabka'},
        {'date': datetime.date(2026, 4, 15), 'amount': -1000, 'description': 'Biedronka'},
        {'date': datetime.date(2026, 5, 31), 'amount': -300, 'description': 'Dino'},
    ], file_id)
    rows = db.get_all_transactions(
        conn, db.TransactionFilters(
            date_from=datetime.date(2026, 4, 1),
            date_to=datetime.date(2026, 4, 30),
        )
    )
    assert len(rows) == 1
    assert rows[0]['description'] == 'Biedronka'

def test_get_all_transactions_filters_by_description(conn):
    file_id = db.insert_imported_file(conn, 'file.csv', 'bank')
    db.insert_transactions(conn, [
        {'date': datetime.date(2026, 4, 1), 'amount': -500, 'description': 'Żabka'},
        {'date': datetime.date(2026, 4, 2), 'amount': -1000, 'description': 'Biedronka'},
    ], file_id)
    rows = db.get_all_transactions(conn, db.TransactionFilters(description='biedronka'))
    assert len(rows) == 1
    assert rows[0]['description'] == 'Biedronka'

@pytest.mark.parametrize(('stored','search'), [
    ('zażółć gęślą jaźń', 'zażółć gęślą jaźń'),  # db lower, filter lower
    ('zażółć gęślą jaźń', 'ZAŻÓŁĆ GĘŚLĄ JAŹŃ'),  # db lower, filter upper
    ('ZAŻÓŁĆ GĘŚLĄ JAŹŃ', 'zażółć gęślą jaźń'),  # db upper, filter lower
    ('ZAŻÓŁĆ GĘŚLĄ JAŹŃ', 'ZAŻÓŁĆ GĘŚLĄ JAŹŃ'),  # db upper, filter upper
    ('ZaŻółć gęŚLĄ jaŹŃ', 'zażółć gęślą jaźń'),  # db mixed, filter lower
    ('ZaŻółć gęŚLĄ jaŹŃ', 'ZAŻÓŁĆ GĘŚLĄ JAŹŃ'),  # db mixed, filter upper
])
def test_get_all_transactions_filters_by_description_case_insensitive_polish(
        conn, stored, search):
    file_id = db.insert_imported_file(conn, 'file.csv', 'bank')
    db.insert_transactions(conn, [
        {'date': datetime.date(2026, 4, 1), 'amount': -500, 'description': stored},
        {'date': datetime.date(2026, 4, 2), 'amount': -300, 'description': 'Biedronka'},
    ], file_id)
    rows = db.get_all_transactions(conn, db.TransactionFilters(description=search))
    assert len(rows) == 1
    assert rows[0]['description'] == stored

def test_get_all_transactions_filters_by_amount_min(conn):
    file_id = db.insert_imported_file(conn, 'file.csv', 'bank')
    db.insert_transactions(conn, [
        {'date': datetime.date(2026, 4, 1), 'amount': -500, 'description': 'Żabka'},
        {'date': datetime.date(2026, 4, 2), 'amount': -2000, 'description': 'Biedronka'},
    ], file_id)
    rows = db.get_all_transactions(conn, db.TransactionFilters(amount_min=1000))
    assert len(rows) == 1
    assert rows[0]['description'] == 'Biedronka'

def test_get_all_transactions_filters_by_amount_max(conn):
    file_id = db.insert_imported_file(conn, 'file.csv', 'bank')
    db.insert_transactions(conn, [
        {'date': datetime.date(2026, 4, 1), 'amount': -500, 'description': 'Żabka'},
        {'date': datetime.date(2026, 4, 2), 'amount': -2000, 'description': 'Biedronka'},
    ], file_id)
    rows = db.get_all_transactions(conn, db.TransactionFilters(amount_max=1000))
    assert len(rows) == 1
    assert rows[0]['description'] == 'Żabka'

def test_get_all_transactions_filters_by_amount_range(conn):
    file_id = db.insert_imported_file(conn, 'file.csv', 'bank')
    db.insert_transactions(conn, [
        {'date': datetime.date(2026, 4, 1), 'amount': -300, 'description': 'Żabka'},
        {'date': datetime.date(2026, 4, 2), 'amount': -1500, 'description': 'Biedronka'},
        {'date': datetime.date(2026, 4, 3), 'amount': -5000, 'description': 'Dino'},
    ], file_id)
    rows = db.get_all_transactions(
        conn, db.TransactionFilters(amount_min=1000, amount_max=3000)
    )
    assert len(rows) == 1
    assert rows[0]['description'] == 'Biedronka'

def test_get_all_transactions_amount_filter_includes_income(conn):
    file_id = db.insert_imported_file(conn, 'file.csv', 'bank')
    db.insert_transactions(conn, [
        {'date': datetime.date(2026, 4, 1), 'amount': 200000, 'description': 'Salary'},
        {'date': datetime.date(2026, 4, 2), 'amount': -500, 'description': 'Żabka'},
    ], file_id)
    rows = db.get_all_transactions(conn, db.TransactionFilters(amount_min=100000))
    assert len(rows) == 1
    assert rows[0]['description'] == 'Salary'

def test_get_all_transactions_amount_range_includes_matching_income_and_expense(conn):
    file_id = db.insert_imported_file(conn, 'file.csv', 'bank')
    # amounts (abs): 500 too small, 1500 in range, 5000 too large — for both expense and income
    db.insert_transactions(conn, [
        {'date': datetime.date(2026, 4, 1), 'amount': -500,   'description': 'Żabka'},
        {'date': datetime.date(2026, 4, 2), 'amount': -1500,  'description': 'Biedronka'},
        {'date': datetime.date(2026, 4, 3), 'amount': -5000,  'description': 'Dino'},
        {'date': datetime.date(2026, 4, 4), 'amount': 800,    'description': 'Zwrot'},
        {'date': datetime.date(2026, 4, 5), 'amount': 2000,   'description': 'Premia'},
        {'date': datetime.date(2026, 4, 6), 'amount': 200000, 'description': 'Salary'},
    ], file_id)
    rows = db.get_all_transactions(
        conn, db.TransactionFilters(amount_min=1000, amount_max=3000)
    )
    assert len(rows) == 2
    assert {r['description'] for r in rows} == {'Biedronka', 'Premia'}

# * Rules

@pytest.fixture
def category_id(conn):
    return db.insert_category(conn, 'groceries')['category_id']

def test_insert_rule(conn, category_id):
    result = db.insert_rule(conn, 'Biedronka', category_id)
    assert result['rule_id'] is not None
    assert result['pattern'] == 'Biedronka'
    assert result['category_id'] == category_id

def test_get_all_rules_returns_rules_with_category_name(conn, category_id):
    db.insert_rule(conn, 'Biedronka', category_id)
    rules = db.get_all_rules(conn)
    assert len(rules) == 1
    assert rules[0]['pattern'] == 'Biedronka'
    assert rules[0]['category_id'] == category_id
    assert rules[0]['category'] == 'groceries'

def test_delete_rule_removes_row(conn, category_id):
    rule_id = db.insert_rule(conn, 'Biedronka', category_id)['rule_id']
    db.delete_rule(conn, rule_id)
    assert db.get_all_rules(conn) == []

def test_delete_rule_nonexistent_raises(conn):
    with pytest.raises(ValueError, match='no rule with id 1337'):
        db.delete_rule(conn, 1337)

def test_update_rule_changes_pattern_and_category(conn, category_id):
    other_id = db.insert_category(conn, 'transport')['category_id']
    rule_id = db.insert_rule(conn, 'Biedronka', category_id)['rule_id']
    db.update_rule(conn, rule_id, 'PKP', other_id)
    rules = db.get_all_rules(conn)
    assert rules[0]['pattern'] == 'PKP'
    assert rules[0]['category_id'] == other_id

def test_update_rule_nonexistent_raises(conn):
    with pytest.raises(ValueError, match='no rule with id 1337'):
        db.update_rule(conn, 1337, 'PKP', 1)

# * Settings

def test_get_setting_returns_none_for_missing_key(conn):
    assert db.get_setting(conn, 'lang') is None

def test_get_setting_returns_stored_value(conn):
    conn.execute("insert into settings (key, value) values ('lang', 'pl')")
    assert db.get_setting(conn, 'lang') == 'pl'

def test_set_setting_stores_value(conn):
    db.set_setting(conn, 'lang', 'pl')
    row = conn.execute('select value from settings where key = ?', ('lang',)).fetchone()
    assert row is not None
    assert row['value'] == 'pl'

def test_set_setting_overwrites_existing_value(conn):
    db.set_setting(conn, 'lang', 'pl')
    db.set_setting(conn, 'lang', 'en')
    row = conn.execute('select value from settings where key = ?', ('lang',)).fetchone()
    assert row is not None
    assert row['value'] == 'en'

def test_set_setting_stores_independent_keys(conn):
    db.set_setting(conn, 'lang', 'pl')
    db.set_setting(conn, 'theme', 'dark')
    rows = {
        r['key']: r['value']
        for r in conn.execute('select key, value from settings').fetchall()
    }
    assert rows == {'lang': 'pl', 'theme': 'dark'}

# * Transactions

def test_get_all_transactions_combined_filters(conn):
    file_id = db.insert_imported_file(conn, 'file.csv', 'bank')
    db.insert_transactions(conn, [
        {'date': datetime.date(2026, 4, 15), 'amount': -1500, 'description': 'Biedronka Centrum'},
        {'date': datetime.date(2026, 3, 1),  'amount': -1500, 'description': 'Biedronka Stara'},
        {'date': datetime.date(2026, 4, 15), 'amount': -100,  'description': 'Biedronka Mała'},
        {'date': datetime.date(2026, 4, 15), 'amount': -1500, 'description': 'Żabka'},
    ], file_id)
    rows = db.get_all_transactions(conn, db.TransactionFilters(
        date_from=datetime.date(2026, 4, 1),
        date_to=datetime.date(2026, 4, 30),
        amount_min=1000,
        description='biedronka',
    ))
    assert len(rows) == 1
    assert rows[0]['description'] == 'Biedronka Centrum'
