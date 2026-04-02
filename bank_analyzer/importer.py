# * CSV import and deduplication

import csv
import pathlib

# * Bank configurations

BANKS: dict[str, dict] = {}

# * Canonicalization

def canonicalize_description(description: str) -> str:
    ...

# * Parsing and import

def parse_csv(filepath: pathlib.Path, bank: str) -> list[dict]:
    ...

def import_file(filepath: pathlib.Path, bank: str) -> dict[str, int]:
    ...
