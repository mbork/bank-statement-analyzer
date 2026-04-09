# * Database tests

import datetime
import pytest
import sqlite3

from bank_analyzer import db

@pytest.fixture
def conn():
    connection = sqlite3.connect(':memory:')
    connection.row_factory = sqlite3.Row
    db.create_schema(connection)
    yield connection
    connection.close()

def test_insert_imported_file(conn):
    assert db.insert_imported_file(conn, 'filename.csv') == 1
    rows = conn.execute('select * from imported_files').fetchall()
    assert len(rows) == 1
    row = rows[0]
    assert row['imported_file_id'] == 1
    assert row['filename'] == 'filename.csv'
    datetime.datetime.fromisoformat(row['imported_at']) # raises if invalid


# ** insert_transactions

ROWS_A = [
    {'date': datetime.date(2026, 4, 1), 'amount': -500, 'description': 'Żabka'},
    {'date': datetime.date(2026, 4, 2), 'amount': -1200, 'description': 'Biedronka'},
]

ROWS_B = [
    {'date': datetime.date(2026, 4, 2), 'amount': -1200, 'description': 'Biedronka'},  # duplicate of ROWS_A[1]
    {'date': datetime.date(2026, 4, 3), 'amount': -300, 'description': 'Dino'},
]


def test_insert_transactions_inserts_rows(conn):
    file_id = db.insert_imported_file(conn, 'file.csv')
    count = db.insert_transactions(conn, ROWS_A, file_id)
    assert count == 2
    rows = conn.execute('select * from transactions').fetchall()
    assert len(rows) == 2


def test_insert_transactions_deduplicates_identical_set(conn):
    file_id = db.insert_imported_file(conn, 'file.csv')
    db.insert_transactions(conn, ROWS_A, file_id)
    count = db.insert_transactions(conn, ROWS_A, file_id)
    assert count == 0
    rows = conn.execute('select * from transactions').fetchall()
    assert len(rows) == 2


def test_insert_transactions_deduplicates_overlapping_sets(conn):
    file_id = db.insert_imported_file(conn, 'file.csv')
    db.insert_transactions(conn, ROWS_A, file_id)
    count = db.insert_transactions(conn, ROWS_B, file_id)
    assert count == 1
    rows = conn.execute('select * from transactions').fetchall()
    assert len(rows) == 3
