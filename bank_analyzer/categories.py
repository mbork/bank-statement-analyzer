# * Category management

from bank_analyzer import db

# * Queries

def get_all_categories() -> list[dict]:
    with db.transaction() as conn:
        return db.get_all_categories(conn)

def add_category(name: str) -> dict:
    with db.transaction() as conn:
        return db.insert_category(conn, name)

def rename_category(category_id: int, new_name: str) -> None:
    with db.transaction() as conn:
        db.update_category(conn, category_id, new_name)

def delete_category(category_id: int) -> None:
    with db.transaction() as conn:
        db.delete_category(conn, category_id)
