# * Extract translatable strings
# Updates .ts files in translations/ by scanning Python source files for
# self.tr() calls.  Run this after adding new translatable strings, then
# translate the new entries in the .ts files, then run build-assets.py.
#
# Usage: uv run python scripts/extract-strings.py

import subprocess
import sys
from pathlib import Path

# * Main

_ROOT = Path(__file__).resolve().parent.parent
_SOURCES = sorted(_ROOT.glob('bank_analyzer/**/*.py'))
_TS_FILES = sorted((_ROOT / 'translations').glob('*.ts'))

if __name__ == '__main__':
    source_args = [str(p) for p in _SOURCES]
    for ts_file in _TS_FILES:
        print(f'Updating {ts_file.relative_to(_ROOT)}')
        cmd = ['pyside6-lupdate'] + source_args + ['-ts', str(ts_file)]
        result = subprocess.run(cmd)
        if result.returncode != 0:
            sys.exit(result.returncode)
