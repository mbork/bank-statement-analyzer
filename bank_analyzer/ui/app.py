# * Main application window

import sys

from PySide6.QtWidgets import QApplication, QMainWindow, QTabWidget

from bank_analyzer import db
from bank_analyzer.ui import categories_view, import_view, reports_view, transactions_view

# * Application

class App(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Bank Statement Analyzer")

        tabs = QTabWidget()

        import_tab = import_view.ImportView()
        transactions_tab = transactions_view.TransactionsView()
        import_tab.import_succeeded.connect(transactions_tab.refresh)

        tabs.addTab(import_tab, 'Import')
        tabs.addTab(transactions_tab, 'Transactions')
        tabs.addTab(reports_view.ReportsView(), 'Reports')
        tabs.addTab(categories_view.CategoriesView(), 'Categories')
        # TODO Rules tab will be here

        self.setCentralWidget(tabs)

# * Entry point

def run() -> None:
    with db.manage_connection() as conn:
        db.create_schema(conn)
    qt_app = QApplication(sys.argv)
    window = App()
    window.show()
    sys.exit(qt_app.exec())
