# * Rules service

from bank_analyzer import db

# * CRUD

def get_all_rules() -> list[dict]:
    with db.transaction() as conn:
        return db.get_all_rules(conn)

def insert_rule(pattern: str, category_id: int) -> dict:
    with db.transaction() as conn:
        return db.insert_rule(conn, pattern, category_id)

def delete_rule(rule_id: int) -> None:
    with db.transaction() as conn:
        db.delete_rule(conn, rule_id)
