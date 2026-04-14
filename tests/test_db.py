# * Database tests

import datetime
import sqlite3

import pytest

from bank_analyzer import db


@pytest.fixture
def conn():
    connection = sqlite3.connect(':memory:')
    connection.row_factory = sqlite3.Row
    db.create_schema(connection)
    yield connection
    connection.close()

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
    conn.execute('PRAGMA foreign_keys = ON')
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
