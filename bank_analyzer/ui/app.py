# * Main application window

import ttkbootstrap as ttk
from bank_analyzer import db
from bank_analyzer.ui import categories_view
from bank_analyzer.ui import import_view
from bank_analyzer.ui import reports_view
from bank_analyzer.ui import transactions_view

# * Application

class App(ttk.Window):
    def __init__(self) -> None:
        super().__init__(title="Bank Statement Analyzer")
        notebook = ttk.Notebook(self)
        notebook.pack(fill='both', expand=True)

        import_tab = import_view.ImportView(notebook)
        notebook.add(import_tab, text='Import')

        transactions_tab = transactions_view.TransactionsView(notebook)
        notebook.add(transactions_tab, text='Transactions')

        reports_tab = reports_view.ReportsView(notebook)
        notebook.add(reports_tab, text='Reports')

        categories_tab = categories_view.CategoriesView(notebook)
        notebook.add(categories_tab, text='Categories')

        # TODO Rules tab will be here

# * Entry point

def run() -> None:
    with db.manage_connection() as conn:
        db.create_schema(conn)
    app = App()
    app.mainloop()
