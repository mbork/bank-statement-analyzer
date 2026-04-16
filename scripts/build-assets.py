# * Build assets
# Compiles translations (.ts -> .qm) and generates help HTML from Org sources
# (requires pandoc on PATH).  Run this after all translations are complete.
#
# Usage: uv run python scripts/build-assets.py

import subprocess
import sys
from pathlib import Path

# * Main

_ROOT = Path(__file__).resolve().parent.parent
_TRANSLATIONS_DIR = _ROOT / 'translations'
_DOCS_DIR = _ROOT / 'docs'
_HELP_OUT_DIR = _ROOT / 'bank_analyzer/ui/help'

if __name__ == '__main__':
    # ** Compile translations
    for ts_file in sorted(_TRANSLATIONS_DIR.glob('*.ts')):
        qm_file = ts_file.with_suffix('.qm')
        print(f'Compiling {ts_file.relative_to(_ROOT)} -> {qm_file.relative_to(_ROOT)}')
        result = subprocess.run(['pyside6-lrelease', str(ts_file), '-qm', str(qm_file)])
        if result.returncode != 0:
            sys.exit(result.returncode)

    # ** Generate help HTML
    _HELP_OUT_DIR.mkdir(parents=True, exist_ok=True)
    for org_file in sorted(_DOCS_DIR.glob('help.*.org')):
        html_file = _HELP_OUT_DIR / org_file.with_suffix('.html').name
        print(f'Converting {org_file.relative_to(_ROOT)} -> {html_file.relative_to(_ROOT)}')
        result = subprocess.run([
            'pandoc', str(org_file),
            '--from=org', '--to=html',
            '--output', str(html_file),
        ])
        if result.returncode != 0:
            sys.exit(result.returncode)
