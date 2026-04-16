# * Entry point

import argparse
import os

from dotenv import load_dotenv

# * Main

if __name__ == "__main__":
    load_dotenv()
    parser = argparse.ArgumentParser(description='Bank Statement Analyzer')
    parser.add_argument('--demo', action='store_true', help='Run in demo mode with sample data')
    args = parser.parse_args()

    if args.demo:
        import atexit
        import tempfile
        db_fd, db_path = tempfile.mkstemp(suffix='.db', prefix='bank_analyzer_demo_')
        os.close(db_fd)
        os.environ['BANK_ANALYZER_DB_PATH'] = db_path
        atexit.register(os.unlink, db_path)
        import scripts.seed as seed
        seed.seed()

    import bank_analyzer.ui.app as app
    app.run(is_demo=args.demo)
