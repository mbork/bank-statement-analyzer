# * Demo script
# Launches the app in demo mode with a fresh temporary DB pre-populated
# with seed data.  All data is discarded when the app exits.
#
# Usage: uv run python scripts/demo.py

import os
import tempfile

import scripts.seed as seed
from bank_analyzer.ui import app

# * Main

if __name__ == '__main__':
    db_fd, db_path = tempfile.mkstemp(suffix='.db', prefix='bank_analyzer_demo_')
    os.close(db_fd)
    os.environ['BANK_ANALYZER_DB_PATH'] = db_path
    try:
        seed.seed()
        app.run(is_demo=True)
    finally:
        os.unlink(db_path)
