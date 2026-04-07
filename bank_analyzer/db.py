# * Database access
import sqlite3

from bank_analyzer import config

# * Connection

def get_connection() -> sqlite3.Connection:
    path = config.get_db_path()
    conn = sqlite3.connect(path)
    conn.execute('PRAGMA foreign_keys = ON')
    conn.row_factory = sqlite3.Row
    return conn

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
