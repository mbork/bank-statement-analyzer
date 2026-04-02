# * Spending reports

import datetime

# * Queries

def spending_by_category(
    start_date: datetime.date,
    end_date: datetime.date,
) -> list[dict]:
    ...

def spending_by_month(category_id: int) -> list[dict]:
    ...
