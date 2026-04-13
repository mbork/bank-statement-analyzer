# * Configuration and path resolution
import os
import platform
from pathlib import Path

# * Data directory

def get_data_dir() -> Path:
    env_dir = os.environ.get('BANK_ANALYZER_DATA_DIR')
    if env_dir is None:
        system = platform.system()
        if system == 'Windows':
            path = Path(os.environ['APPDATA']) / 'bank-statement-analyzer'
        elif system in ('Linux', 'Darwin'):
            # Linux or MacOS
            path = Path.home() / '.local/share/bank-statement-analyzer'
        else:
            raise RuntimeError(f'Unsupported platform: {system}')
    else:
        path = Path(env_dir)

    path.mkdir(parents=True, exist_ok=True)
    return path


def get_db_path() -> Path:
    return get_data_dir() / 'bank_analyzer.db'
