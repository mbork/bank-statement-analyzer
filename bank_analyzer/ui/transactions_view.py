# * Transactions view

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHeaderView, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from bank_analyzer import db

# * Helpers

COLUMNS = ['Date', 'Description', 'Amount (PLN)', 'Category']

# * View

class TransactionsView(QWidget):
    def __init__(self) -> None:
        super().__init__()

        self._table = QTableWidget(0, len(COLUMNS))
        self._table.setHorizontalHeaderLabels(COLUMNS)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.verticalHeader().setVisible(False)

        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # Date
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)           # Description
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # Amount
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)            # Category

        layout = QVBoxLayout()
        layout.addWidget(self._table)
        self.setLayout(layout)

        self.refresh()

    # ** Slots

    def refresh(self) -> None:
        with db.manage_connection() as conn:
            rows = db.get_all_transactions(conn)

        self._table.setRowCount(len(rows))
        for row_idx, row in enumerate(rows):
            amount_pln = f"{row['amount'] / 100:.2f}"
            category = row['category'] or ''
            values = [row['date'], row['description'], amount_pln, category]
            for col_idx, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col_idx == 2:  # amount — right-align
                    align = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                    item.setTextAlignment(align)
                self._table.setItem(row_idx, col_idx, item)

        header = self._table.horizontalHeader()
        amount_width = header.sectionSize(2)
        header.resizeSection(3, 2 * amount_width)
