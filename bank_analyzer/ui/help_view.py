# * Help view

from pathlib import Path

from PySide6.QtCore import QLocale
from PySide6.QtWidgets import (
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from bank_analyzer import db

# * Helpers

_HELP_DIR = Path(__file__).resolve().parent / 'help'


def _load_help_html(language: str) -> str:
    html_path = _HELP_DIR / f'help.{language}.html'
    if not html_path.exists():
        html_path = _HELP_DIR / 'help.en.html'
    if not html_path.exists():
        return '<p>Help not available.</p>'
    return html_path.read_text(encoding='utf-8')


# * View

class HelpView(QWidget):
    def __init__(self) -> None:
        super().__init__()

        with db.manage_connection() as conn:
            language = db.get_setting(conn, 'language') or QLocale.system().name()[:2]

        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)
        browser.setHtml(_load_help_html(language))

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(browser)
        self.setLayout(layout)
