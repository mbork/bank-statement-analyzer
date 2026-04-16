# * Main application window

import sys

from PySide6.QtWidgets import QApplication, QMainWindow, QTabWidget

from bank_analyzer import db
from bank_analyzer.ui import (
    categories_view,
    import_view,
    reports_view,
    rules_view,
    transactions_view,
)

# * Application

class App(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(self.tr("Bank Statement Analyzer"))

        tabs = QTabWidget()

        import_tab = import_view.ImportView()
        transactions_tab = transactions_view.TransactionsView()
        categories_tab = categories_view.CategoriesView()
        import_tab.import_succeeded.connect(transactions_tab.refresh)
        categories_tab.categories_changed.connect(transactions_tab.refresh)

        tabs.addTab(import_tab, self.tr('Import'))
        tabs.addTab(transactions_tab, self.tr('Transactions'))
        tabs.addTab(reports_view.ReportsView(), self.tr('Reports'))
        tabs.addTab(categories_tab, self.tr('Categories'))
        tabs.addTab(rules_view.RulesView(), self.tr('Rules'))

        self.setCentralWidget(tabs)

# * Entry point

def run() -> None:
    with db.manage_connection() as conn:
        db.create_schema(conn)
    qt_app = QApplication(sys.argv)
    window = App()
    window.show()
    sys.exit(qt_app.exec())
