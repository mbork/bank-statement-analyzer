# * Reports tests

import datetime

import pytest

from bank_analyzer import db, reports

# * Fixtures

@pytest.fixture
def conn_with_data(conn):
    file_id = db.insert_imported_file(conn, 'file.csv', 'bank')
    food_id = db.insert_category(conn, 'Food')['category_id']
    transport_id = db.insert_category(conn, 'Transport')['category_id']
    rows = [
        {'date': datetime.date(2026, 1, 5),  'amount': -1000, 'description': 'Żabka'},
        {'date': datetime.date(2026, 1, 10), 'amount': -3000, 'description': 'Biedronka'},
        {'date': datetime.date(2026, 1, 15), 'amount': -2000, 'description': 'Bus'},
        {'date': datetime.date(2026, 2, 3),  'amount': -500,  'description': 'Dino'},
        {'date': datetime.date(2026, 2, 20), 'amount':  8000, 'description': 'Salary'},  # income
        {'date': datetime.date(2026, 4, 1),  'amount': -1500, 'description': 'Tram'},
        {'date': datetime.date(2026, 1, 25), 'amount': -800,  'description': 'Misc'},  # no category
    ]
    db.insert_transactions(conn, rows, file_id)
    transactions = conn.execute(
        'select transaction_id, description from transactions'
    ).fetchall()
    by_desc = {row['description']: row['transaction_id'] for row in transactions}
    db.set_transaction_category(conn, by_desc['Żabka'],    food_id)
    db.set_transaction_category(conn, by_desc['Biedronka'], food_id)
    db.set_transaction_category(conn, by_desc['Bus'],       transport_id)
    db.set_transaction_category(conn, by_desc['Dino'],      food_id)
    db.set_transaction_category(conn, by_desc['Tram'],      transport_id)
    # 'Salary' and 'Misc' left uncategorized
    return conn, food_id, transport_id


# * empty category_ids returns empty list

def test_spending_report_empty_category_ids_returns_empty(conn_with_data):
    conn, food_id, transport_id = conn_with_data
    result = reports.spending_report(conn, None, None, [], 'month')
    assert result == []


# * income excluded

def test_spending_report_excludes_income(conn_with_data):
    conn, food_id, transport_id = conn_with_data
    result = reports.spending_report(conn, None, None, [food_id, transport_id], 'month')
    assert all(row['total_grosz'] > 0 for row in result)
    assert not any(row['total_grosz'] == -8000 for row in result)


# * totals correct

def test_spending_report_totals_correct(conn_with_data):
    conn, food_id, transport_id = conn_with_data
    result = reports.spending_report(
        conn,
        datetime.date(2026, 1, 1),
        datetime.date(2026, 1, 31),
        [food_id, transport_id],
        'month',
    )
    rows_by_category = {row['category']: row for row in result}
    assert rows_by_category['Food']['total_grosz'] == 4000   # 1000 + 3000
    assert rows_by_category['Transport']['total_grosz'] == 2000


# * percentages correct

def test_spending_report_percentages_correct(conn_with_data):
    conn, food_id, transport_id = conn_with_data
    result = reports.spending_report(
        conn,
        datetime.date(2026, 1, 1),
        datetime.date(2026, 1, 31),
        [food_id, transport_id],
        'month',
    )
    rows_by_category = {row['category']: row for row in result}
    assert rows_by_category['Food']['percentage'] == pytest.approx(200 / 3)
    assert rows_by_category['Transport']['percentage'] == pytest.approx(100 / 3)


# * percentages sum to 100 per period

def test_spending_report_percentages_sum_to_100(conn_with_data):
    conn, food_id, transport_id = conn_with_data
    result = reports.spending_report(conn, None, None, [food_id, transport_id], 'month')
    periods: dict[str, float] = {}
    for row in result:
        periods[row['period']] = periods.get(row['period'], 0.0) + row['percentage']
    for period, total in periods.items():
        assert total == pytest.approx(100.0), f'period {period}: percentages sum to {total}'


# * date filtering

def test_spending_report_date_from_filters(conn_with_data):
    conn, food_id, transport_id = conn_with_data
    result = reports.spending_report(
        conn,
        datetime.date(2026, 2, 1),
        None,
        [food_id, transport_id],
        'month',
    )
    periods = {row['period'] for row in result}
    assert '2026-01' not in periods
    assert '2026-02' in periods
    assert '2026-04' in periods
    rows_by_period_category = {(row['period'], row['category']): row for row in result}
    assert rows_by_period_category[('2026-02', 'Food')]['total_grosz'] == 500
    assert rows_by_period_category[('2026-04', 'Transport')]['total_grosz'] == 1500

def test_spending_report_date_to_filters(conn_with_data):
    conn, food_id, transport_id = conn_with_data
    result = reports.spending_report(
        conn,
        None,
        datetime.date(2026, 1, 31),
        [food_id, transport_id],
        'month',
    )
    periods = {row['period'] for row in result}
    assert '2026-01' in periods
    assert '2026-02' not in periods
    assert '2026-04' not in periods
    rows_by_category = {row['category']: row for row in result if row['period'] == '2026-01'}
    assert rows_by_category['Food']['total_grosz'] == 4000
    assert rows_by_category['Transport']['total_grosz'] == 2000

def test_spending_report_date_range_filters(conn_with_data):
    conn, food_id, transport_id = conn_with_data
    result = reports.spending_report(
        conn,
        datetime.date(2026, 2, 1),
        datetime.date(2026, 2, 28),
        [food_id, transport_id],
        'month',
    )
    periods = {row['period'] for row in result}
    assert periods == {'2026-02'}
    rows_by_category = {row['category']: row for row in result}
    assert rows_by_category['Food']['total_grosz'] == 500
    assert 'Transport' not in rows_by_category

def test_spending_report_date_boundaries_are_inclusive(conn_with_data):
    # date_from = Biedronka's date, date_to = Bus's date; both must be included
    conn, food_id, transport_id = conn_with_data
    result = reports.spending_report(
        conn,
        datetime.date(2026, 1, 10),
        datetime.date(2026, 1, 15),
        [food_id, transport_id],
        'month',
    )
    rows_by_category = {row['category']: row for row in result}
    assert rows_by_category['Food']['total_grosz'] == 3000      # Biedronka (Jan 10) included
    assert rows_by_category['Transport']['total_grosz'] == 2000  # Bus (Jan 15) included


# * uncategorized

def test_spending_report_uncategorized_only(conn_with_data):
    conn, food_id, transport_id = conn_with_data
    result = reports.spending_report(conn, None, None, [None], 'month')
    assert len(result) == 1  # only Misc (-800, Jan); Salary excluded as income
    assert result[0]['category'] is None
    assert result[0]['total_grosz'] == 800

def test_spending_report_includes_uncategorized_when_requested(conn_with_data):
    conn, food_id, transport_id = conn_with_data
    result = reports.spending_report(conn, None, None, [food_id, None], 'month')
    categories = {row['category'] for row in result}
    assert None in categories

def test_spending_report_excludes_uncategorized_by_default(conn_with_data):
    conn, food_id, transport_id = conn_with_data
    result = reports.spending_report(conn, None, None, [food_id, transport_id], 'month')
    assert all(row['category'] is not None for row in result)


# * granularity

def test_spending_report_granularity_quarter(conn_with_data):
    conn, food_id, transport_id = conn_with_data
    result = reports.spending_report(conn, None, None, [food_id, transport_id], 'quarter')
    periods = {row['period'] for row in result}
    assert '2026-Q1' in periods
    assert '2026-Q2' in periods
    rows = {(row['period'], row['category']): row for row in result}
    assert rows[('2026-Q1', 'Food')]['total_grosz'] == 4500       # Żabka + Biedronka + Dino
    assert rows[('2026-Q1', 'Transport')]['total_grosz'] == 2000  # Bus
    assert rows[('2026-Q2', 'Transport')]['total_grosz'] == 1500  # Tram
    assert ('2026-Q2', 'Food') not in rows

def test_spending_report_granularity_year(conn_with_data):
    conn, food_id, transport_id = conn_with_data
    result = reports.spending_report(conn, None, None, [food_id, transport_id], 'year')
    periods = {row['period'] for row in result}
    assert '2026' in periods
    rows = {(row['period'], row['category']): row for row in result}
    assert rows[('2026', 'Food')]['total_grosz'] == 4500      # Żabka + Biedronka + Dino
    assert rows[('2026', 'Transport')]['total_grosz'] == 3500  # Bus + Tram

def test_spending_report_granularity_century(conn_with_data):
    conn, food_id, transport_id = conn_with_data
    result = reports.spending_report(conn, None, None, [food_id, transport_id], 'century')
    periods = {row['period'] for row in result}
    assert 21 in periods
    rows = {(row['period'], row['category']): row for row in result}
    assert rows[(21, 'Food')]['total_grosz'] == 4500      # Żabka + Biedronka + Dino
    assert rows[(21, 'Transport')]['total_grosz'] == 3500  # Bus + Tram

def test_spending_report_granularity_month_groups_correctly(conn_with_data):
    conn, food_id, transport_id = conn_with_data
    result = reports.spending_report(conn, None, None, [food_id], 'month')
    periods = {row['period'] for row in result}
    assert '2026-01' in periods
    assert '2026-02' in periods
    assert '2026-04' not in periods  # no food transactions in April
    rows = {row['period']: row for row in result}
    assert rows['2026-01']['total_grosz'] == 4000  # Żabka + Biedronka
    assert rows['2026-02']['total_grosz'] == 500   # Dino
