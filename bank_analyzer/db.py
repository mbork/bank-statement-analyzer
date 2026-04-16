# * Database access
import datetime
import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass

from bank_analyzer import config

# * Connection

@contextmanager
def manage_connection() -> Generator[sqlite3.Connection, None, None]:
    path = config.get_db_path()
    conn = sqlite3.connect(path)
    conn.execute('PRAGMA foreign_keys = ON')
    conn.create_function('lower', 1, lambda s: s.lower() if isinstance(s, str) else s)
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
            bank text not null,
            imported_at text not null
        )
    ''')
    conn.execute('''
        create table if not exists categories (
            category_id integer primary key,
            name text unique not null
        )
    ''')
    conn.execute('''
        create table if not exists transactions (
            transaction_id integer primary key,
            date text not null,
            description text not null,
            amount integer not null, -- [grosz]
            category_id integer references categories(category_id),
            imported_file_id integer not null references imported_files(imported_file_id),
            unique (date, amount, description)
        )
    ''')
    conn.execute('''
        create table if not exists rules (
            rule_id integer primary key,
            pattern text unique not null,
            category_id integer not null references categories(category_id)
        )
    ''')
    conn.execute('''
        create table if not exists settings (
            key text primary key,
            value text not null
        )
    ''')
    conn.commit()

# * Importing transactions

def insert_imported_file(conn: sqlite3.Connection, filename: str, bank: str) -> int:
    cursor = conn.execute(
        'insert into imported_files (filename, bank, imported_at) values (?, ?, ?)',
        (filename, bank, datetime.datetime.now().astimezone().isoformat())
    )
    imported_file_id = cursor.lastrowid
    assert imported_file_id is not None # insert raises on failure, so this is always set
    return imported_file_id

def insert_transactions(conn: sqlite3.Connection, rows: list[dict], imported_file_id: int) -> int:
    cursor = conn.executemany(
        '''
            insert into transactions (date, description, amount, imported_file_id)
            values (?, ?, ?, ?) on conflict do nothing
        ''',
        (
            (row['date'].isoformat(), row['description'], row['amount'], imported_file_id)
            for row in rows
        )
    )
    return cursor.rowcount

# * Transactions

@dataclass
class TransactionFilters:
    category_id: int | None = None
    date_from: datetime.date | None = None
    date_to: datetime.date | None = None
    amount_min: int | None = None
    amount_max: int | None = None
    description: str | None = None

def get_all_transactions(
        conn: sqlite3.Connection,
        filters: TransactionFilters | None = None,
) -> list[dict]:
    conditions: list[str] = []
    params: list[str | int] = []
    where = ''
    if filters is not None:
        if filters.category_id is not None:
            conditions.append('t.category_id = ?')
            params.append(filters.category_id)
        if filters.date_from is not None:
            conditions.append('t.date >= ?')
            params.append(filters.date_from.isoformat())
        if filters.date_to is not None:
            conditions.append('t.date <= ?')
            params.append(filters.date_to.isoformat())
        if filters.amount_min is not None:
            conditions.append('abs(t.amount) >= ?')
            params.append(filters.amount_min)
        if filters.amount_max is not None:
            conditions.append('abs(t.amount) <= ?')
            params.append(filters.amount_max)
        if filters.description is not None:
            conditions.append('lower(t.description) like ?')
            params.append('%' + filters.description.lower() + '%')
        where = ('where ' + ' and '.join(conditions)) if conditions else ''
    cursor = conn.execute(f'''
        select t.transaction_id, t.date, t.description, t.amount,
               t.category_id, c.name as category
        from transactions t
        left join categories c using (category_id)
        {where}
        order by t.date desc, t.transaction_id desc
    ''', params)
    return [dict(row) for row in cursor]

def set_transaction_category(
    conn: sqlite3.Connection, transaction_id: int, category_id: int | None
) -> None:
    conn.execute(
        'update transactions set category_id = ? where transaction_id = ?',
        (category_id, transaction_id),
    )

# * Categories

def get_all_categories(conn: sqlite3.Connection) -> list[dict]:
    cursor = conn.execute('select category_id, name from categories order by name')
    return [dict(row) for row in cursor]

def insert_category(conn: sqlite3.Connection, name: str) -> dict:
    cursor = conn.execute(
        'insert into categories (name) values (?) returning category_id, name',
        (name,),
    )
    return dict(cursor.fetchone())

def update_category(conn: sqlite3.Connection, category_id: int, new_name: str) -> None:
    cursor = conn.execute(
        'update categories set name = ? where category_id = ?',
        (new_name, category_id,),
    )
    if cursor.rowcount == 0:
        raise ValueError(f'no category with id {category_id}')

def delete_category(conn: sqlite3.Connection, category_id: int) -> None:
    cursor = conn.execute('delete from categories where category_id = ?', (category_id,))
    if cursor.rowcount == 0:
        raise ValueError(f'no category with id {category_id}')

# * Rules

def get_all_rules(conn: sqlite3.Connection) -> list[dict]:
    cursor = conn.execute('''
        select rule_id, pattern, r.category_id, c.name as category
        from rules r
        left join categories c using (category_id)
        order by rule_id
    ''')
    return [dict(row) for row in cursor]

def insert_rule(conn: sqlite3.Connection, pattern: str, category_id: int) -> dict:
    cursor = conn.execute('''
        insert into rules (pattern, category_id) values (?, ?)
        returning rule_id, pattern, category_id
    ''', (pattern, category_id))
    return dict(cursor.fetchone())

def update_rule(
        conn: sqlite3.Connection, rule_id: int, new_pattern: str, new_category_id: int
) -> None:
    cursor = conn.execute(
        'update rules set pattern = ?, category_id = ? where rule_id = ?',
        (new_pattern, new_category_id, rule_id,),
    )
    if cursor.rowcount == 0:
        raise ValueError(f'no rule with id {rule_id}')

def delete_rule(conn: sqlite3.Connection, rule_id: int) -> None:
    cursor = conn.execute('delete from rules where rule_id = ?', (rule_id,))
    if cursor.rowcount == 0:
        raise ValueError(f'no rule with id {rule_id}')

# * Settings

def get_setting(conn: sqlite3.Connection, key: str) -> str | None:
    cursor = conn.execute('select value from settings where key = ?', (key,))
    return next((row['value'] for row in cursor), None)

def set_setting(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute('''
        insert into settings (key, value) values (?, ?)
        on conflict(key) do update set value = excluded.value
    ''', (key, value))
