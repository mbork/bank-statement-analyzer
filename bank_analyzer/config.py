# * Configuration and path resolution
import os
import platform
from pathlib import Path

# * Data directory

def get_db_path() -> Path:
    db_path = os.environ.get('BANK_ANALYZER_DB_PATH')
    if db_path is None:
        system = platform.system()
        if system == 'Windows':
            path = Path(os.environ['APPDATA']) / 'bank-statement-analyzer/bank_analyzer.db'
        elif system in ('Linux', 'Darwin'):
            # Linux or MacOS
            path = Path.home() / '.local/share/bank-statement-analyzer/bank_analyzer.db'
        else:
            raise RuntimeError(f'Unsupported platform: {system}')
    else:
        path = Path(db_path).resolve()

    path.parent.mkdir(parents=True, exist_ok=True)
    return path
