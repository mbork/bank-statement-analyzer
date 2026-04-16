# * Rules view

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from bank_analyzer import categories, rules

# * View

class RulesView(QWidget):
    rules_changed = Signal()

    def __init__(self) -> None:
        super().__init__()

        # ** Rules table
        self._table = QTableWidget(0, 2)
        self._table.setHorizontalHeaderLabels([self.tr('Pattern'), self.tr('Category')])
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(1, 250)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.itemSelectionChanged.connect(self._on_selection_changed)

        # ** Add-rule form
        self._pattern_input = QLineEdit()
        self._pattern_input.setPlaceholderText(self.tr('Pattern (substring match)'))
        self._pattern_input.returnPressed.connect(self._add_rule)

        self._category_combo = QComboBox()

        add_button = QPushButton(self.tr('Add rule'))
        add_button.clicked.connect(self._add_rule)

        add_row = QHBoxLayout()
        add_row.addWidget(self._pattern_input, stretch=2)
        add_row.addWidget(self._category_combo, stretch=1)
        add_row.addWidget(add_button)

        # ** Action buttons
        self._delete_button = QPushButton(self.tr('Delete rule'))
        self._delete_button.setEnabled(False)
        self._delete_button.clicked.connect(self._delete_rule)

        button_row = QHBoxLayout()
        button_row.addWidget(self._delete_button)
        button_row.addStretch()

        # ** Status label
        self._status_label = QLabel()

        # ** Outer layout
        layout = QVBoxLayout()
        layout.addWidget(self._table)
        layout.addLayout(add_row)
        layout.addLayout(button_row)
        layout.addWidget(self._status_label)
        self.setLayout(layout)

        self.refresh()

    # ** Helpers

    def refresh(self) -> None:
        current_category_id = self._category_combo.currentData()

        self._table.setRowCount(0)
        for rule in rules.get_all_rules():
            row = self._table.rowCount()
            self._table.insertRow(row)
            pattern_item = QTableWidgetItem(rule['pattern'])
            pattern_item.setData(Qt.ItemDataRole.UserRole, rule['rule_id'])
            self._table.setItem(row, 0, pattern_item)
            self._table.setItem(row, 1, QTableWidgetItem(rule['category'] or ''))

        self._category_combo.clear()
        for cat in categories.get_all_categories():
            self._category_combo.addItem(cat['name'], userData=cat['category_id'])
        for i in range(self._category_combo.count()):
            if self._category_combo.itemData(i) == current_category_id:
                self._category_combo.setCurrentIndex(i)
                break

    def _current_rule_id(self) -> int | None:
        row = self._table.currentRow()
        if row < 0:
            return None
        item = self._table.item(row, 0)
        if item is None:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    # ** Slots

    def _on_selection_changed(self) -> None:
        has_selection = bool(self._table.selectedItems())
        self._delete_button.setEnabled(has_selection)

    def _add_rule(self) -> None:
        pattern = self._pattern_input.text().strip()
        if not pattern:
            return
        category_id: int | None = self._category_combo.currentData()
        if category_id is None:
            self._status_label.setText(self.tr('Select a category first.'))
            return
        try:
            rules.insert_rule(pattern, category_id)
            self._pattern_input.clear()
            self._status_label.clear()
            self.refresh()
            self.rules_changed.emit()
        except Exception as e:
            self._status_label.setText(self.tr('Error: {error}').format(error=e))

    def _delete_rule(self) -> None:
        rule_id = self._current_rule_id()
        if rule_id is None:
            return
        pattern = self._table.item(self._table.currentRow(), 0)
        pattern_text = pattern.text() if pattern else ''
        answer = QMessageBox.question(
            self,
            self.tr('Delete rule'),
            self.tr("Delete rule '{pattern}'?").format(pattern=pattern_text),
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            rules.delete_rule(rule_id)
            self._status_label.clear()
            self.refresh()
            self.rules_changed.emit()
        except Exception as e:
            self._status_label.setText(self.tr('Error: {error}').format(error=e))
