# * Reports view

import csv
import datetime
from typing import Literal, cast

from PySide6.QtCore import QDate, Qt, QTimer
from PySide6.QtWidgets import (
    QButtonGroup,
    QDateEdit,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QRadioButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from bank_analyzer import categories, db, export, reports
from bank_analyzer.money import format_amount_ui
from bank_analyzer.ui.constants import MAX_DATE, MIN_DATE

# * Helpers

_GRANULARITIES = ['month', 'quarter', 'year', 'century']
_REPORT_CSV_HEADERS = ('period', 'category', 'total')

# * View

class ReportsView(QWidget):
    def __init__(self) -> None:
        super().__init__()

        self._debounce_timer = QTimer()
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.setInterval(200)
        self._debounce_timer.timeout.connect(self.refresh)

        # ** Date range
        today = QDate.currentDate()
        first_of_month = QDate(today.year(), today.month(), 1)

        self._date_from = QDateEdit()
        self._date_from.setCalendarPopup(True)
        self._date_from.setSpecialValueText(self.tr('(any)'))
        self._date_from.setMinimumDate(MIN_DATE)
        self._date_from.setDate(first_of_month)
        self._date_from.setDisplayFormat('yyyy-MM-dd')
        self._date_from.dateChanged.connect(self.refresh)

        self._date_to = QDateEdit()
        self._date_to.setCalendarPopup(True)
        self._date_to.setSpecialValueText(self.tr('(any)'))
        self._date_to.setMinimumDate(MIN_DATE)
        self._date_to.setMaximumDate(MAX_DATE)
        self._date_to.setDate(today)
        self._date_to.setDisplayFormat('yyyy-MM-dd')
        self._date_to.dateChanged.connect(self.refresh)

        export_button = QPushButton(self.tr('Export CSV\u2026'))
        export_button.clicked.connect(self._export_csv)

        date_row = QHBoxLayout()
        date_row.addWidget(QLabel(self.tr('From:')))
        date_row.addWidget(self._date_from)
        date_row.addWidget(QLabel(self.tr('To:')))
        date_row.addWidget(self._date_to)
        date_row.addStretch()
        date_row.addWidget(export_button)

        # ** Granularity
        granularity_box = QGroupBox(self.tr('Granularity'))
        granularity_layout = QVBoxLayout()
        self._granularity_group = QButtonGroup()
        granularity_labels = [
            self.tr('Month'), self.tr('Quarter'), self.tr('Year'), self.tr('Century'),
        ]
        for i, (gran, label) in enumerate(zip(_GRANULARITIES, granularity_labels, strict=True)):
            btn = QRadioButton(label)
            btn.setProperty('granularity', gran)
            self._granularity_group.addButton(btn, i)
            granularity_layout.addWidget(btn)
        self._granularity_group.button(0).setChecked(True)
        self._granularity_group.buttonClicked.connect(self.refresh)
        granularity_box.setLayout(granularity_layout)

        # ** Category list
        self._category_list = QListWidget()
        self._category_list.itemChanged.connect(self._on_category_changed)
        self._category_list.itemClicked.connect(self._on_category_clicked)

        select_all_button = QPushButton(self.tr('All'))
        select_all_button.clicked.connect(lambda: self._set_all_categories(Qt.CheckState.Checked))
        select_none_button = QPushButton(self.tr('None'))
        select_none_button.clicked.connect(
            lambda: self._set_all_categories(Qt.CheckState.Unchecked)
        )

        category_buttons_row = QHBoxLayout()
        category_buttons_row.addWidget(select_all_button)
        category_buttons_row.addWidget(select_none_button)
        category_buttons_row.addStretch()

        category_box = QGroupBox(self.tr('Categories'))
        category_layout = QVBoxLayout()
        category_layout.addWidget(self._category_list)
        category_layout.addLayout(category_buttons_row)
        category_box.setLayout(category_layout)
        category_box.setMaximumHeight(160)

        controls_row = QHBoxLayout()
        controls_row.addWidget(granularity_box)
        controls_row.addWidget(category_box, stretch=1)

        # ** Table
        self._table = QTableWidget(0, 3)
        self._table.setHorizontalHeaderLabels([
            self.tr('Category'),
            self.tr('Amount (PLN)'),
            self.tr('%'),
        ])
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self._table.verticalHeader().setVisible(False)
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)

        self._report_rows: list[dict] = []

        # ** Outer layout
        layout = QVBoxLayout()
        layout.addLayout(date_row)
        layout.addLayout(controls_row)
        layout.addWidget(self._table)
        self.setLayout(layout)

    # ** Helpers

    def _granularity(self) -> Literal['month', 'quarter', 'year', 'century']:
        checked = self._granularity_group.checkedButton()
        assert checked is not None
        return cast(Literal['month', 'quarter', 'year', 'century'], checked.property('granularity'))

    def _selected_category_ids(self) -> list[int | None]:
        result: list[int | None] = []
        for i in range(self._category_list.count()):
            item = self._category_list.item(i)
            if item is not None and item.checkState() == Qt.CheckState.Checked:
                result.append(item.data(Qt.ItemDataRole.UserRole))
        return result

    def _populate_categories(self) -> None:
        self._category_list.blockSignals(True)
        prev_checked: set = {
            self._category_list.item(i).data(Qt.ItemDataRole.UserRole)
            for i in range(self._category_list.count())
            if self._category_list.item(i) is not None
            and self._category_list.item(i).checkState() == Qt.CheckState.Checked
        }
        is_first_load = self._category_list.count() == 0
        self._category_list.clear()

        uncat = QListWidgetItem(self.tr('(uncategorized)'))
        uncat.setData(Qt.ItemDataRole.UserRole, None)
        uncat.setFlags(uncat.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        is_checked = True if is_first_load else (None in prev_checked)
        uncat.setCheckState(Qt.CheckState.Checked if is_checked else Qt.CheckState.Unchecked)
        self._category_list.addItem(uncat)

        for cat in categories.get_all_categories():
            cat_item = QListWidgetItem(cat['name'])
            cat_item.setData(Qt.ItemDataRole.UserRole, cat['category_id'])
            cat_item.setFlags(cat_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            is_cat_checked = True if is_first_load else (cat['category_id'] in prev_checked)
            cat_item.setCheckState(
                Qt.CheckState.Checked if is_cat_checked else Qt.CheckState.Unchecked
            )
            self._category_list.addItem(cat_item)

        self._category_list.blockSignals(False)

    def _populate_table(self, grouped: list[tuple[str, list[dict]]]) -> None:
        self._table.setRowCount(0)
        for period, rows in grouped:
            header_row = self._table.rowCount()
            self._table.insertRow(header_row)
            period_item = QTableWidgetItem(period)
            period_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            font = period_item.font()
            font.setBold(True)
            period_item.setFont(font)
            self._table.setItem(header_row, 0, period_item)
            self._table.setSpan(header_row, 0, 1, 3)

            for row in rows:
                data_row = self._table.rowCount()
                self._table.insertRow(data_row)
                category = row['category'] or self.tr('(uncategorized)')
                amount_pln = format_amount_ui(row['total_grosz'])
                percentage = f"{row['percentage']:.1f}"
                self._table.setItem(data_row, 0, QTableWidgetItem(category))
                amount_item = QTableWidgetItem(amount_pln)
                amount_item.setTextAlignment(
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                )
                self._table.setItem(data_row, 1, amount_item)
                pct_item = QTableWidgetItem(percentage)
                pct_item.setTextAlignment(
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                )
                self._table.setItem(data_row, 2, pct_item)

    # ** Event handlers

    def showEvent(self, event) -> None:  # type: ignore[override]  # noqa: N802
        super().showEvent(event)
        self._populate_categories()
        self.refresh()

    # ** Slots

    def _set_all_categories(self, state: Qt.CheckState) -> None:
        self._category_list.blockSignals(True)
        for i in range(self._category_list.count()):
            item = self._category_list.item(i)
            if item is not None:
                item.setCheckState(state)
        self._category_list.blockSignals(False)
        self.refresh()

    def _on_category_clicked(self, item: QListWidgetItem) -> None:
        new_state = (
            Qt.CheckState.Unchecked
            if item.checkState() == Qt.CheckState.Checked
            else Qt.CheckState.Checked
        )
        item.setCheckState(new_state)

    def _on_category_changed(self) -> None:
        self._debounce_timer.start()

    def refresh(self) -> None:
        date_from: datetime.date | None = (
            cast(datetime.date, self._date_from.date().toPython())
            if self._date_from.date() != MIN_DATE else None
        )
        date_to: datetime.date | None = (
            cast(datetime.date, self._date_to.date().toPython())
            if self._date_to.date() != MAX_DATE else None
        )
        granularity = self._granularity()
        category_ids = self._selected_category_ids()
        if not category_ids:
            self._table.setRowCount(0)
            return
        with db.manage_connection() as conn:
            rows = reports.spending_report(conn, date_from, date_to, category_ids, granularity)
        self._report_rows = rows
        grouped = reports.group_rows_by_period(rows)
        if granularity == 'century':
            grouped = [
                (reports.arabic_to_roman(int(period)), period_rows)
                for period, period_rows in grouped
            ]
        self._populate_table(grouped)

    def _csv_filename(self, base: str) -> str:
        from_str = self._date_from.date().toString('yyyy-MM-dd')
        to_str = self._date_to.date().toString('yyyy-MM-dd')
        granularity = self._granularity()
        return f'{base}--{granularity}--{from_str}--{to_str}.csv'

    def _export_csv(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            self.tr('Export report'),
            self._csv_filename('report'),
            self.tr('CSV files (*.csv)'),
        )
        if not path:
            return
        headers = [self.tr(h) for h in _REPORT_CSV_HEADERS]
        with open(path, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f, delimiter=';')
            writer.writerow(headers)
            export.report_to_csv(self._report_rows, f)
