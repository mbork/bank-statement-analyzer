# * Shared fixtures

import sqlite3

import pytest

from bank_analyzer import db


@pytest.fixture
def conn():
    connection = sqlite3.connect(':memory:')
    connection.row_factory = sqlite3.Row
    db.create_schema(connection)
    connection.execute('PRAGMA foreign_keys = ON')
    connection.create_function('lower', 1, lambda s: s.lower() if isinstance(s, str) else s)
    yield connection
    connection.close()
