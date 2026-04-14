# * Categories view

from sqlite3 import IntegrityError

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from bank_analyzer import categories

# * View

class CategoriesView(QWidget):
    categories_changed = Signal()

    def __init__(self) -> None:
        super().__init__()

        # ** Category list
        self._list = QListWidget()
        self._list.currentItemChanged.connect(self._on_selection_changed)

        # ** Add row
        self._name_input = QLineEdit()
        self._name_input.setPlaceholderText(self.tr('New category name'))
        self._name_input.returnPressed.connect(self._add_category)
        add_button = QPushButton(self.tr('Add'))
        add_button.clicked.connect(self._add_category)

        add_row = QHBoxLayout()
        add_row.addWidget(self._name_input, stretch=1)
        add_row.addWidget(add_button)

        # ** Action buttons
        self._rename_button = QPushButton(self.tr('Rename'))
        self._rename_button.setEnabled(False)
        self._rename_button.clicked.connect(self._rename_category)

        self._delete_button = QPushButton(self.tr('Delete'))
        self._delete_button.setEnabled(False)
        self._delete_button.clicked.connect(self._delete_category)

        button_row = QHBoxLayout()
        button_row.addWidget(self._rename_button)
        button_row.addWidget(self._delete_button)
        button_row.addStretch()

        # ** Status label
        self._status_label = QLabel()

        # ** Outer layout
        layout = QVBoxLayout()
        layout.addWidget(self._list)
        layout.addLayout(add_row)
        layout.addLayout(button_row)
        layout.addWidget(self._status_label)
        self.setLayout(layout)

        self._refresh()

    # ** Helpers

    def _refresh(self) -> None:
        self._list.clear()
        for cat in categories.get_all_categories():
            item = QListWidgetItem(cat['name'])
            item.setData(Qt.ItemDataRole.UserRole, cat['category_id'])
            self._list.addItem(item)

    def _current_id(self) -> int | None:
        item = self._list.currentItem()
        if item is None:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    # ** Slots

    def _on_selection_changed(self) -> None:
        has_selection = self._list.currentItem() is not None
        self._rename_button.setEnabled(has_selection)
        self._delete_button.setEnabled(has_selection)

    def _add_category(self) -> None:
        name = self._name_input.text().strip()
        if not name:
            return
        try:
            categories.add_category(name)
            self._name_input.clear()
            self._status_label.clear()
            self._refresh()
            self.categories_changed.emit()
        except Exception as e:
            self._status_label.setText(self.tr('Error: {error}').format(error=e))

    def _rename_category(self) -> None:
        category_id = self._current_id()
        if category_id is None:
            return
        current_name = self._list.currentItem().text()  # type: ignore[union-attr]
        new_name, ok = QInputDialog.getText(
            self, self.tr('Rename category'), self.tr('New name:'),
            QLineEdit.EchoMode.Normal, current_name,
        )
        if not ok or not new_name.strip():
            return
        try:
            categories.rename_category(category_id, new_name.strip())
            self._status_label.clear()
            self._refresh()
            self.categories_changed.emit()
        except Exception as e:
            self._status_label.setText(self.tr('Error: {error}').format(error=e))

    def _delete_category(self) -> None:
        category_id = self._current_id()
        if category_id is None:
            return
        name = self._list.currentItem().text()  # type: ignore[union-attr]
        answer = QMessageBox.question(
            self,
            self.tr('Delete category'),
            self.tr("Delete '{name}'?").format(name=name),
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            categories.delete_category(category_id)
            self._status_label.clear()
            self._refresh()
            self.categories_changed.emit()
        except IntegrityError:
            self._status_label.setText(
                self.tr("Cannot delete: '{name}' is used by existing transactions.").format(
                    name=name
                )
            )
        except Exception as e:
            self._status_label.setText(self.tr('Error: {error}').format(error=e))
