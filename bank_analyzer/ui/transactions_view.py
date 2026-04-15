# * Transactions view

import csv
import datetime
from typing import cast

from PySide6.QtCore import QDate, Qt, QTimer
from PySide6.QtGui import QColor, QDoubleValidator
from PySide6.QtWidgets import (
    QCalendarWidget,
    QComboBox,
    QDateEdit,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from bank_analyzer import categories, db, export
from bank_analyzer.money import format_amount_ui
from bank_analyzer.ui.constants import MAX_DATE, MIN_DATE

# * Helpers

NUM_COLUMNS = 4
_TRANSACTIONS_CSV_HEADERS = ('date', 'description', 'amount', 'category')
_ROLE_TRANSACTION_ID = Qt.ItemDataRole.UserRole
_ROLE_CATEGORY_ID = Qt.ItemDataRole.UserRole + 1
_ROLE_IS_INCOME = Qt.ItemDataRole.UserRole + 2
_COLOR_INCOME = QColor(160, 160, 160)

class _DefaultPageCalendar(QCalendarWidget):
    """Calendar widget that navigates to a default page when the owning date edit has no date."""
    def __init__(self, owner: QDateEdit, default_page: QDate) -> None:
        super().__init__()
        self._owner = owner
        self._default_page = default_page

    def showEvent(self, event) -> None:  # type: ignore[override]  # noqa: N802
        super().showEvent(event)
        is_at_sentinel = self._owner.date() in (
            self._owner.minimumDate(), self._owner.maximumDate()
        )
        if is_at_sentinel:
            default = self._default_page
            def navigate() -> None:
                self.blockSignals(True)
                self.setSelectedDate(default)
                self.blockSignals(False)
            QTimer.singleShot(0, navigate)

class _DateFilterEdit(QDateEdit):
    """QDateEdit that opens its calendar at a given default when no date is set.

    If `any_at_max` is True, displays '(any)' when the date equals the widget's
    maximum (i.e. the MAX_DATE sentinel meaning 'no upper bound').
    """
    def __init__(self, popup_default: QDate, any_at_max: bool = False) -> None:
        super().__init__()
        self._any_at_max = any_at_max
        self.setCalendarPopup(True)
        self.setCalendarWidget(_DefaultPageCalendar(self, popup_default))

    def textFromDateTime(self, dt) -> str:  # type: ignore[override]  # noqa: N802
        if self._any_at_max and self.date() == self.maximumDate():
            return self.tr('(any)')
        return super().textFromDateTime(dt)

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

        # ** Filter bar
        today = QDate.currentDate()
        first_of_month = QDate(today.year(), today.month(), 1)

        self._date_from = _DateFilterEdit(popup_default=first_of_month)
        self._date_from.setSpecialValueText(self.tr('(any)'))
        self._date_from.setMinimumDate(MIN_DATE)
        self._date_from.setDate(MIN_DATE)
        self._date_from.setDisplayFormat('yyyy-MM-dd')
        self._date_from.dateChanged.connect(self.refresh)

        self._date_to = _DateFilterEdit(popup_default=today, any_at_max=True)
        self._date_to.setSpecialValueText(self.tr('(any)'))
        self._date_to.setMinimumDate(MIN_DATE)
        self._date_to.setMaximumDate(MAX_DATE)
        self._date_to.setDate(MAX_DATE)
        self._date_to.setDisplayFormat('yyyy-MM-dd')
        self._date_to.setFixedWidth(self._date_from.sizeHint().width())
        self._date_to.dateChanged.connect(self.refresh)

        self._filter_category_combo = QComboBox()
        self._filter_category_combo.currentIndexChanged.connect(self.refresh)

        self._description_input = QLineEdit()
        self._description_input.setPlaceholderText(self.tr('Description…'))
        self._description_input.textChanged.connect(self.refresh)

        amount_validator = QDoubleValidator(0.0, 1e9, 2)
        amount_validator.setNotation(QDoubleValidator.Notation.StandardNotation)

        self._amount_min_input = QLineEdit()
        self._amount_min_input.setPlaceholderText(self.tr('min'))
        self._amount_min_input.setValidator(amount_validator)
        self._amount_min_input.setFixedWidth(80)
        self._amount_min_input.textChanged.connect(self.refresh)

        self._amount_max_input = QLineEdit()
        self._amount_max_input.setPlaceholderText(self.tr('max'))
        self._amount_max_input.setValidator(amount_validator)
        self._amount_max_input.setFixedWidth(80)
        self._amount_max_input.textChanged.connect(self.refresh)

        clear_button = QPushButton(self.tr('Clear filters'))
        clear_button.clicked.connect(self._clear_filters)

        export_button = QPushButton(self.tr('Export CSV\u2026'))
        export_button.clicked.connect(self._export_csv)

        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel(self.tr('From:')))
        filter_row.addWidget(self._date_from)
        filter_row.addWidget(QLabel(self.tr('To:')))
        filter_row.addWidget(self._date_to)
        filter_row.addWidget(QLabel(self.tr('Amount:')))
        filter_row.addWidget(self._amount_min_input)
        filter_row.addWidget(QLabel(self.tr('–')))
        filter_row.addWidget(self._amount_max_input)
        filter_row.addWidget(QLabel(self.tr('Category:')))
        filter_row.addWidget(self._filter_category_combo, stretch=1)
        filter_row.addWidget(self._description_input, stretch=2)
        filter_row.addWidget(clear_button)
        filter_row.addWidget(export_button)

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
        self._rows: list[dict] = []

        # ** Outer layout
        layout = QVBoxLayout()
        layout.addLayout(filter_row)
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

    def _populate_filter_categories(self) -> None:
        current_id = self._filter_category_combo.currentData()
        self._filter_category_combo.blockSignals(True)
        self._filter_category_combo.clear()
        self._filter_category_combo.addItem(self.tr('(all)'), userData=None)
        for cat in categories.get_all_categories():
            self._filter_category_combo.addItem(cat['name'], userData=cat['category_id'])
        for i in range(self._filter_category_combo.count()):
            if self._filter_category_combo.itemData(i) == current_id:
                self._filter_category_combo.setCurrentIndex(i)
                break
        self._filter_category_combo.blockSignals(False)

    def _parse_amount(self, text: str) -> int | None:
        stripped = text.strip()
        if not stripped:
            return None
        try:
            return round(float(stripped) * 100)
        except ValueError:
            return None

    def _build_filters(self) -> db.TransactionFilters | None:
        date_from: datetime.date | None = (
            cast(datetime.date, self._date_from.date().toPython())
            if self._date_from.date() != MIN_DATE else None
        )
        date_to: datetime.date | None = (
            cast(datetime.date, self._date_to.date().toPython())
            if self._date_to.date() != MAX_DATE else None
        )
        category_id: int | None = self._filter_category_combo.currentData()
        description_text = self._description_input.text().strip()
        description = description_text if description_text else None
        amount_min = self._parse_amount(self._amount_min_input.text())
        amount_max = self._parse_amount(self._amount_max_input.text())
        is_active = any(
            v is not None
            for v in [date_from, date_to, category_id, description, amount_min, amount_max]
        )
        if is_active:
            return db.TransactionFilters(
                date_from=date_from,
                date_to=date_to,
                category_id=category_id,
                description=description,
                amount_min=amount_min,
                amount_max=amount_max,
            )
        return None

    def _selected_transaction_ids(self) -> list[int]:
        seen: set[int] = set()
        result: list[int] = []
        for index in self._table.selectedIndexes():
            row = index.row()
            if row not in seen:
                seen.add(row)
                item = self._table.item(row, 0)
                if item is not None and not item.data(_ROLE_IS_INCOME):
                    result.append(item.data(_ROLE_TRANSACTION_ID))
        return result

    # ** Event handlers

    def showEvent(self, event) -> None:  # type: ignore[override]  # noqa: N802
        super().showEvent(event)
        self._populate_filter_categories()
        if self._category_combo.isEnabled():
            self._populate_categories()

    # ** Slots

    def _clear_filters(self) -> None:
        for widget in [self._date_from, self._date_to, self._filter_category_combo,
                       self._description_input, self._amount_min_input, self._amount_max_input]:
            widget.blockSignals(True)
        self._date_from.setDate(MIN_DATE)
        self._date_to.setDate(MAX_DATE)
        self._filter_category_combo.setCurrentIndex(0)
        self._description_input.clear()
        self._amount_min_input.clear()
        self._amount_max_input.clear()
        for widget in [self._date_from, self._date_to, self._filter_category_combo,
                       self._description_input, self._amount_min_input, self._amount_max_input]:
            widget.blockSignals(False)
        self.refresh()

    def _on_selection_changed(self) -> None:
        selected_rows = {idx.row() for idx in self._table.selectedIndexes()}
        expense_rows = {
            row for row in selected_rows
            if (item := self._table.item(row, 0)) is not None
            and not item.data(_ROLE_IS_INCOME)
        }
        if not expense_rows:
            self._set_panel_enabled(False)
            return
        self._populate_categories()
        self._set_panel_enabled(True)
        if len(expense_rows) == 1:
            row = next(iter(expense_rows))
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
        self._populate_filter_categories()
        filters = self._build_filters()
        with db.manage_connection() as conn:
            rows = db.get_all_transactions(conn, filters)
        self._rows = rows

        self._table.setSortingEnabled(False)
        self._table.setRowCount(len(rows))
        for row_idx, row in enumerate(rows):
            amount_pln = format_amount_ui(row['amount'])
            category = row['category'] or ''
            is_income = row['amount'] > 0
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
                    item.setData(_ROLE_IS_INCOME, is_income)
                if col_idx == 2:  # amount — right-align
                    align = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                    item.setTextAlignment(align)
                if is_income:
                    item.setForeground(_COLOR_INCOME)
                self._table.setItem(row_idx, col_idx, item)
        self._table.setSortingEnabled(True)

        header = self._table.horizontalHeader()
        amount_width = header.sectionSize(2)
        header.resizeSection(3, 2 * amount_width)

    def _csv_filename(self, base: str) -> str:
        from_str = self._date_from.date().toString('yyyy-MM-dd')
        to_str = self._date_to.date().toString('yyyy-MM-dd')
        return f'{base}--{from_str}--{to_str}.csv'

    def _export_csv(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            self.tr('Export transactions'),
            self._csv_filename('transactions'),
            self.tr('CSV files (*.csv)'),
        )
        if not path:
            return
        headers = [self.tr(h) for h in _TRANSACTIONS_CSV_HEADERS]
        with open(path, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f, delimiter=';')
            writer.writerow(headers)
            export.transactions_to_csv(self._rows, f)
