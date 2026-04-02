# Bank Statement Analyzer — CLAUDE.md

# Architecture

Approach 1: SQLite + Tkinter, themed with ttkbootstrap.

The UI layer is intentionally isolated so the app can later migrate to PySide6
by replacing `ui/` only.  Modules outside `ui/` must never import from `ui/`.

## Layers

| Module           | Responsibility                                                        |
|------------------|-----------------------------------------------------------------------|
| `config.py`      | Resolves DB path: `BANK_ANALYZER_DATA_DIR` env var → OS user-data dir |
| `db.py`          | Schema creation, all `sqlite3` queries; returns plain `list[dict]`   |
| `importer.py`    | CSV parsing, description canonicalization, deduplication              |
| `categories.py`  | Category CRUD                                                         |
| `reports.py`     | Spending report queries (by category and time interval)               |
| `ui/`            | All Tkinter code — calls the modules above, displays results          |

## Planned DB tables

- `transactions` — date, description (canonicalized), amount, category_id, source_file;
  dedup via `UNIQUE(date, amount, description)` + `ON CONFLICT DO NOTHING` at insert time
- `categories` — name
- `imported_files` — filename, imported_at

## Data location

- **Dev:** `./data/bank_analyzer.db` — set `BANK_ANALYZER_DATA_DIR=./data` in `.env`
- **Linux (prod):** `~/.local/share/bank-statement-analyzer/bank_analyzer.db`
- **Windows (prod):** `%APPDATA%\bank-statement-analyzer\bank_analyzer.db`

# Dev setup

`uv` replaces `pip`, `venv`, and `pip-tools`.  Install it once system-wide,
then per project:

```sh
uv sync          # creates .venv and installs all dependencies from uv.lock
cp .env.example .env
```

Dependencies are declared in `pyproject.toml`; `uv.lock` pins exact versions.
To add a dependency: `uv add <package>`.  Never use `pip install` directly.

# Commands

| Task                | Command                               |
|---------------------|---------------------------------------|
| Run the app         | `uv run python main.py`               |
| Run all tests       | `uv run pytest tests/`                |
| Run one test file   | `uv run pytest tests/test_importer.py` |
| Run tests verbosely | `uv run pytest --verbose tests/`      |

# Coding conventions

Inherits all rules from `~/.claude/CLAUDE.md`.  Project-specific additions:

- All SQL in `db.py` only — no inline queries elsewhere
- `db.py` and `reports.py` return plain `list[dict]`, never raw `sqlite3` row
  objects — keeps callers free of DB implementation details
- CSV format variations (date format, column names) are configured per bank in
  a `BANKS` dict in `importer.py`, not auto-detected
- Description canonicalization (strip, collapse whitespace) must be applied
  in `importer.py` before any insert — never rely on raw CSV strings for dedup
- Use Python exceptions (`raise`/`try`/`except`) for error handling; let
  exceptions propagate unless they can be meaningfully handled at that level
- Tests use plain `pytest` functions (no classes) with descriptive names, e.g.
  `test_duplicate_transactions_are_deduplicated`; use fixtures for shared setup
- Use type hints throughout (function signatures and local variables where non-obvious)

# Learning guidance

This is a learning project — the user writes the code.

- When explaining Python concepts, bring up Node.js analogues when they help
  clarify (e.g. "this is like `require.main === module` in Node.js")
- Guide and explain rather than writing implementation code unprompted
- Only write code when explicitly asked to

# What NOT to do without asking

- Add dependencies beyond those already in `pyproject.toml`
- Create or modify files without explicit instruction
- Refactor, rename, or reorganize beyond what was asked
- Run the app or tests unprompted
