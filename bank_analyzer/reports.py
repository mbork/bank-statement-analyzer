# * Spending reports

import datetime
import sqlite3
from typing import Literal

# * Century formatting

_ROMAN_DIGITS = [
    (1000, 'M'),
    (900, 'CM'),
    (500, 'D'),
    (400, 'CD'),
    (100, 'C'),
    (90, 'XC'),
    (50, 'L'),
    (40, 'XL'),
    (10, 'X'),
    (9, 'IX'),
    (5, 'V'),
    (4, 'IV'),
    (1, 'I'),
]

def arabic_to_roman(n: int) -> str:
    """Convert a positive integer to a Roman numeral string."""
    result = []
    if n <= 0:
        raise ValueError(f'expected positive integer, got {n}')

    for value, symbol in _ROMAN_DIGITS:
        count, n = divmod(n, value)
        result.append(symbol * count)
    return ''.join(result)

# * Queries

def spending_report(
    conn: sqlite3.Connection,
    date_from: datetime.date | None,
    date_to: datetime.date | None,
    category_ids: list[int | None],
    granularity: Literal['month', 'quarter', 'year', 'century'],
) -> list[dict]:
    conditions: list[str] = []
    params: list[str | int] = []
    if category_ids:
        real_ids = [c for c in category_ids if c is not None]
        include_uncategorized = None in category_ids
        category_conditions = []
        if real_ids:
            category_placeholders = ', '.join(['?'] * len(real_ids))
            category_conditions.append(f't.category_id in ({category_placeholders})')
        if include_uncategorized:
            category_conditions.append('t.category_id is null')
        conditions.append('(' + ' or '.join(category_conditions) + ')')
        params.extend(real_ids)
    else:
        return []
    if date_from is not None:
        conditions.append('t.date >= ?')
        params.append(date_from.isoformat())
    if date_to is not None:
        conditions.append('t.date <= ?')
        params.append(date_to.isoformat())
    where = ('and ' + ' and '.join(conditions)) if conditions else ''

    period_expression = {
        'month': "strftime('%Y-%m', t.date)",
        'quarter': "strftime('%Y', t.date) || '-Q'"
            " || cast(ceil(cast(strftime('%m', t.date) as int) / 3.0) as int)",
        'year': "strftime('%Y', t.date)",
        'century': "cast(ceil(cast(strftime('%Y', t.date) as int) / 100.0) as int)",
    }[granularity]

    fraction = f'-sum(t.amount) / sum(-sum(t.amount)) over (partition by {period_expression})'
    cursor = conn.execute(
        f'''
            select
                {period_expression} as period,
                c.name as category,
                -sum(t.amount) as total_grosz,
                100.0 * {fraction} as percentage
            from transactions t
            left join categories c using (category_id)
            where t.amount < 0
            {where}
            group by period, t.category_id
            order by period, t.category_id
        ''', params)
    return [dict(row) for row in cursor]
