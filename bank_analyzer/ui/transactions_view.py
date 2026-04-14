# * Transactions view

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from bank_analyzer import categories, db

# * Helpers

NUM_COLUMNS = 4
_ROLE_TRANSACTION_ID = Qt.ItemDataRole.UserRole
_ROLE_CATEGORY_ID = Qt.ItemDataRole.UserRole + 1

class _SortableItem(QTableWidgetItem):
    """QTableWidgetItem that sorts by a numeric key rather than display text."""
    def __init__(self, text: str, sort_key: int | float) -> None:
        super().__init__(text)
        self._sort_key = sort_key

    def __lt__(self, other: QTableWidgetItem) -> bool:
        if isinstance(other, _SortableItem):
            return self._sort_key < other._sort_key
        return super().__lt__(other)

# * View

class TransactionsView(QWidget):
    def __init__(self) -> None:
        super().__init__()

        # ** Table
        columns = [
            self.tr('Date'),
            self.tr('Description'),
            self.tr('Amount (PLN)'),
            self.tr('Category'),
        ]
        self._table = QTableWidget(0, NUM_COLUMNS)
        self._table.setHorizontalHeaderLabels(columns)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.verticalHeader().setVisible(False)
        self._table.setSortingEnabled(True)
        self._table.selectionModel().selectionChanged.connect(self._on_selection_changed)

        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # Date
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)           # Description
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # Amount
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)             # Category

        # ** Category assignment panel
        self._category_label = QLabel(self.tr('Assign category:'))
        self._category_combo = QComboBox()
        self._assign_button = QPushButton(self.tr('Assign'))
        self._assign_button.clicked.connect(self._assign_category)

        assign_row = QHBoxLayout()
        assign_row.addWidget(self._category_label)
        assign_row.addWidget(self._category_combo, stretch=1)
        assign_row.addWidget(self._assign_button)

        self._set_panel_enabled(False)

        # ** Outer layout
        layout = QVBoxLayout()
        layout.addWidget(self._table)
        layout.addLayout(assign_row)
        self.setLayout(layout)

        self.refresh()

    # ** Helpers

    def _set_panel_enabled(self, enabled: bool) -> None:
        self._category_label.setEnabled(enabled)
        self._category_combo.setEnabled(enabled)
        self._assign_button.setEnabled(enabled)

    def _populate_categories(self) -> None:
        self._category_combo.clear()
        self._category_combo.addItem(self.tr('(none)'), userData=None)
        for cat in categories.get_all_categories():
            self._category_combo.addItem(cat['name'], userData=cat['category_id'])

    def _selected_transaction_ids(self) -> list[int]:
        seen: set[int] = set()
        result: list[int] = []
        for index in self._table.selectedIndexes():
            row = index.row()
            if row not in seen:
                seen.add(row)
                item = self._table.item(row, 0)
                if item is not None:
                    result.append(item.data(_ROLE_TRANSACTION_ID))
        return result

    # ** Event handlers

    def showEvent(self, event) -> None:  # type: ignore[override]  # noqa: N802
        super().showEvent(event)
        if self._category_combo.isEnabled():
            self._populate_categories()

    # ** Slots

    def _on_selection_changed(self) -> None:
        selected_rows = {idx.row() for idx in self._table.selectedIndexes()}
        if not selected_rows:
            self._set_panel_enabled(False)
            return
        self._populate_categories()
        self._set_panel_enabled(True)
        if len(selected_rows) == 1:
            row = next(iter(selected_rows))
            item = self._table.item(row, 0)
            if item is not None:
                category_id = item.data(_ROLE_CATEGORY_ID)
                for i in range(self._category_combo.count()):
                    if self._category_combo.itemData(i) == category_id:
                        self._category_combo.setCurrentIndex(i)
                        break

    def _assign_category(self) -> None:
        transaction_ids = self._selected_transaction_ids()
        if not transaction_ids:
            return
        category_id: int | None = self._category_combo.currentData()
        with db.manage_connection() as conn:
            for transaction_id in transaction_ids:
                db.set_transaction_category(conn, transaction_id, category_id)
        self.refresh()

    def refresh(self) -> None:
        with db.manage_connection() as conn:
            rows = db.get_all_transactions(conn)

        self._table.setSortingEnabled(False)
        self._table.setRowCount(len(rows))
        for row_idx, row in enumerate(rows):
            amount_pln = f"{row['amount'] / 100:.2f}"
            category = row['category'] or ''
            items = [
                QTableWidgetItem(row['date']),
                QTableWidgetItem(row['description']),
                _SortableItem(amount_pln, row['amount']),
                QTableWidgetItem(category),
            ]
            for col_idx, item in enumerate(items):
                if col_idx == 0:
                    item.setData(_ROLE_TRANSACTION_ID, row['transaction_id'])
                    item.setData(_ROLE_CATEGORY_ID, row['category_id'])
                if col_idx == 2:  # amount — right-align
                    align = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                    item.setTextAlignment(align)
                self._table.setItem(row_idx, col_idx, item)
        self._table.setSortingEnabled(True)

        header = self._table.horizontalHeader()
        amount_width = header.sectionSize(2)
        header.resizeSection(3, 2 * amount_width)
