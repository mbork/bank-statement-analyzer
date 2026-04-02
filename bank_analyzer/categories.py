# * Category management

# * Queries

def get_all_categories() -> list[dict]:
    ...

def add_category(name: str) -> dict:
    ...

def rename_category(category_id: int, new_name: str) -> None:
    ...

def delete_category(category_id: int) -> None:
    ...
