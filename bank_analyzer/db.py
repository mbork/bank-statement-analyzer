# * Database access

import sqlite3

from bank_analyzer import config

# * Connection

def get_connection() -> sqlite3.Connection:
    ...

# * Schema

def create_schema(conn: sqlite3.Connection) -> None:
    ...
