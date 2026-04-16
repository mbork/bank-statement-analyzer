# * Main application window

import locale
import sys
from pathlib import Path

from PySide6.QtCore import QLocale, Qt, QTranslator
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from bank_analyzer import db
from bank_analyzer.ui import (
    categories_view,
    help_view,
    import_view,
    reports_view,
    rules_view,
    settings_view,
    transactions_view,
)

# * Application

class App(QMainWindow):
    def __init__(self, is_demo: bool = False) -> None:
        super().__init__()
        self.setWindowTitle(self.tr("Bank Statement Analyzer"))

        self._tabs = QTabWidget()

        self._import_tab = import_view.ImportView()
        self._transactions_tab = transactions_view.TransactionsView()
        self._categories_tab = categories_view.CategoriesView()
        self._reports_tab = reports_view.ReportsView()
        self._rules_tab = rules_view.RulesView()
        self._settings_tab = settings_view.SettingsView()
        self._help_tab = help_view.HelpView()
        self._import_tab.import_succeeded.connect(self._transactions_tab.refresh)
        self._categories_tab.categories_changed.connect(self._transactions_tab.refresh)

        self._tabs.addTab(self._import_tab, self.tr('Import'))
        self._tabs.addTab(self._transactions_tab, self.tr('Transactions'))
        self._tabs.addTab(self._reports_tab, self.tr('Reports'))
        self._tabs.addTab(self._categories_tab, self.tr('Categories'))
        self._tabs.addTab(self._rules_tab, self.tr('Rules'))
        self._tabs.addTab(self._settings_tab, self.tr('Settings'))
        self._tabs.addTab(self._help_tab, self.tr('Help'))

        # ** Central widget (with optional demo banner)
        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        if is_demo:
            banner = QLabel(self.tr(
                'DEMO MODE — this is temporary data, everything will be lost when you quit.'
            ))
            banner.setAlignment(Qt.AlignmentFlag.AlignCenter)
            banner.setMinimumHeight(40)
            banner.setStyleSheet('background: #f0ad4e; color: #000; padding: 4px 8px;')
            layout.addWidget(banner)

        layout.addWidget(self._tabs)
        self.setCentralWidget(central)

# * Entry point

_TRANSLATIONS_DIR = Path(__file__).resolve().parents[2] / 'translations'

def run(is_demo: bool = False) -> None:
    with db.manage_connection() as conn:
        db.create_schema(conn)
        language_override = db.get_setting(conn, 'language')
    locale.setlocale(locale.LC_ALL, '')
    qt_app = QApplication(sys.argv)
    translator = QTranslator()
    language = language_override or QLocale.system().name()[:2]
    qm_path = _TRANSLATIONS_DIR / f'{language}.qm'
    if translator.load(str(qm_path)):
        qt_app.installTranslator(translator)
    window = App(is_demo=is_demo)
    window.show()
    sys.exit(qt_app.exec())
