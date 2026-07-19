# * Profiling instrumentation (diagnostic build)
"""Always-on timing and environment logging for the diagnostic build.

Writes to a fixed, local log file (the user's home directory) so logging stays
fast even when the database itself lives on a slow or network path, and so a
Windows user can easily find and send the file.  This module is a temporary
diagnostic aid and is not meant to ship in a real release.
"""

import logging
import platform
import sqlite3
from pathlib import Path

# * Log file

LOG_PATH = Path.home() / 'bank_analyzer_profile.log'

def _build_logger() -> logging.Logger:
    logger = logging.getLogger('bank_analyzer.profiling')
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = logging.FileHandler(LOG_PATH, encoding='utf-8')
        handler.setFormatter(logging.Formatter('%(asctime)s %(message)s'))
        logger.addHandler(handler)
        logger.propagate = False
    return logger

_logger = _build_logger()

# * Public API

def log(message: str) -> None:
    _logger.info('%s', message)

def log_environment(conn: sqlite3.Connection, db_path: Path) -> None:
    is_unc_path = str(db_path).startswith('\\\\')
    _logger.info('--- startup ---')
    _logger.info('platform: %s %s', platform.system(), platform.release())
    _logger.info('db_path: %s', db_path)
    _logger.info('db_path is UNC/network share: %s', is_unc_path)
    for pragma in ('journal_mode', 'synchronous', 'wal_autocheckpoint', 'busy_timeout'):
        row = conn.execute(f'PRAGMA {pragma}').fetchone()
        _logger.info('PRAGMA %s = %s', pragma, row[0])
    for suffix in ('-wal', '-shm'):
        sidecar = Path(str(db_path) + suffix)
        if sidecar.exists():
            _logger.info('sidecar %s = %d bytes', sidecar.name, sidecar.stat().st_size)
        else:
            _logger.info('sidecar %s missing', sidecar.name)
