# * Database access
import datetime
import sqlite3
from collections.abc import Generator
from contextlib import contextmanager

from bank_analyzer import config

# * Connection

@contextmanager
def manage_connection() -> Generator[sqlite3.Connection, None, None]:
    path = config.get_db_path()
    conn = sqlite3.connect(path)
    conn.execute('PRAGMA foreign_keys = ON')
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

# * Schema

def create_schema(conn: sqlite3.Connection) -> None:
    conn.execute('''
        create table if not exists imported_files (
            imported_file_id integer primary key,
            filename text unique not null,
            imported_at text not null
        )
    ''')
    conn.execute('''
        create table if not exists categories (
            category_id integer primary key,
            name text not null
        )
    ''')
    conn.execute('''
        create table if not exists transactions (
            transaction_id integer primary key,
            date text not null,
            description text not null,
            amount integer not null, -- [grosz]
            category_id references categories(category_id),
            imported_file_id integer not null references imported_files(imported_file_id),
            unique (date, amount, description)
        )
    ''')
    conn.commit()

# * Inserting

def insert_imported_file(conn: sqlite3.Connection, filename: str) -> int:
    cursor = conn.execute(
        'insert into imported_files (filename, imported_at) values (?, ?)',
        (filename, datetime.datetime.now().astimezone().isoformat())
    )
    imported_file_id = cursor.lastrowid
    assert imported_file_id is not None # insert raises on failure, so this is always set
    return imported_file_id

def insert_transactions(conn: sqlite3.Connection, rows: list[dict], imported_file_id: int) -> int:
    cursor = conn.executemany(
        'insert into transactions (date, description, amount, imported_file_id) values (?, ?, ?, ?) on conflict do nothing',
        ((row['date'].isoformat(), row['description'], row['amount'], imported_file_id) for row in rows)
    )
    return cursor.rowcount
