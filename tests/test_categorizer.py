# * Categorizer tests
import datetime

import pytest

from bank_analyzer import categorizer, db

# * Fixtures

@pytest.fixture
def setup(conn):
    file_id = db.insert_imported_file(conn, 'file.csv', 'bank')
    groceries_id = db.insert_category(conn, 'groceries')['category_id']
    transport_id = db.insert_category(conn, 'transport')['category_id']
    db.insert_transactions(conn, [
        {'date': datetime.date(2026, 4, 1), 'amount': -500,  'description': 'Biedronka'},
        {'date': datetime.date(2026, 4, 2), 'amount': -1200, 'description': 'PKP Intercity'},
        {'date': datetime.date(2026, 4, 3), 'amount': -300,  'description': 'Żabka'},
    ], file_id)
    return {'conn': conn, 'groceries_id': groceries_id, 'transport_id': transport_id}


# * Tests

def test_categorize_transactions_assigns_category(setup):
    conn = setup['conn']
    groceries_id = setup['groceries_id']
    db.insert_rule(conn, 'Biedronka', groceries_id)
    categorizer.categorize_transactions(conn)
    rows = db.get_all_transactions(conn)
    by_desc = {r['description']: r for r in rows}
    assert by_desc['Biedronka']['category_id'] == groceries_id
    assert by_desc['Żabka']['category_id'] is None
    assert by_desc['PKP Intercity']['category_id'] is None

def test_categorize_transactions_skips_already_categorized(setup):
    conn = setup['conn']
    groceries_id = setup['groceries_id']
    transport_id = setup['transport_id']
    transaction_id = conn.execute(
        "select transaction_id from transactions where description = 'Biedronka'"
    ).fetchone()[0]
    db.set_transaction_category(conn, transaction_id, transport_id)
    db.insert_rule(conn, 'Biedronka', groceries_id)
    categorizer.categorize_transactions(conn)
    rows = db.get_all_transactions(conn)
    biedronka = next(r for r in rows if r['description'] == 'Biedronka')
    assert biedronka['category_id'] == transport_id

def test_categorize_transactions_earlier_rule_wins(conn):
    groceries_id = db.insert_category(conn, 'groceries')['category_id']
    transport_id = db.insert_category(conn, 'transport')['category_id']
    file_id = db.insert_imported_file(conn, 'file.csv', 'bank')
    db.insert_transactions(conn, [
        # matched by both rules — earlier rule (groceries) should win
        {'date': datetime.date(2026, 4, 1), 'amount': -500,  'description': 'Sklep Biedronka'},
        # matched only by the later rule (transport)
        {'date': datetime.date(2026, 4, 2), 'amount': -1200, 'description': 'Sklep PKP'},
    ], file_id)
    db.insert_rule(conn, 'Biedronka', groceries_id)  # rule 1 — wins on overlap
    db.insert_rule(conn, 'Sklep', transport_id)       # rule 2 — applies where rule 1 doesn't
    categorizer.categorize_transactions(conn)
    rows = {r['description']: r for r in db.get_all_transactions(conn)}
    assert rows['Sklep Biedronka']['category_id'] == groceries_id
    assert rows['Sklep PKP']['category_id'] == transport_id

def test_categorize_transactions_returns_count(setup):
    conn = setup['conn']
    groceries_id = setup['groceries_id']
    transport_id = setup['transport_id']
    db.insert_rule(conn, 'Biedronka', groceries_id)
    db.insert_rule(conn, 'PKP', transport_id)
    count = categorizer.categorize_transactions(conn)
    assert count == 2
