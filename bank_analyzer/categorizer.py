# * Auto-categorization
import sqlite3

from bank_analyzer import db

# * Categorization

def categorize_transactions(conn: sqlite3.Connection) -> int:
    """Apply all rules to uncategorized transactions.

    Skips transactions that already have a category (preserves manual overrides).
    Returns the number of transactions categorized.
    """
    rules = db.get_all_rules(conn)
    count = 0
    for rule in rules:
        category_id = rule['category_id']
        pattern = '%' + rule['pattern'].lower() + '%'
        cursor = conn.execute('''
            update transactions set category_id = ?
            where category_id is null
            and lower(description) like ?
        ''', (category_id, pattern))
        count += cursor.rowcount
    return count
