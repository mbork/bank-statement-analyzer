# * Settings view

from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from bank_analyzer import db

# * Available languages

# Language names are intentionally not wrapped in tr() — they must always
# display in their own script so users can find their language regardless
# of the current UI language.
_LANGUAGE_CHOICES: list[tuple[str, str]] = [
    ('', ''),       # display name filled in __init__ via tr()
    ('en', 'English'),
    ('pl', 'Polski'),
]

# * View

class SettingsView(QWidget):
    def __init__(self) -> None:
        super().__init__()

        # ** Language selector
        self._language_combo = QComboBox()
        self._language_combo.addItem(self.tr('(system default)'), userData='')
        for code, name in _LANGUAGE_CHOICES[1:]:
            self._language_combo.addItem(name, userData=code)
        self._language_combo.currentIndexChanged.connect(self._on_language_changed)

        self._restart_label = QLabel(self.tr('Restart the app to apply changes.'))
        self._restart_label.setVisible(False)

        form = QFormLayout()
        form.addRow(self.tr('Language:'), self._language_combo)

        # ** Outer layout
        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addWidget(self._restart_label)
        layout.addStretch()
        self.setLayout(layout)

    # ** Event handlers

    def showEvent(self, event) -> None:  # type: ignore[override]  # noqa: N802
        super().showEvent(event)
        with db.manage_connection() as conn:
            current = db.get_setting(conn, 'language') or ''
        self._language_combo.blockSignals(True)
        for i in range(self._language_combo.count()):
            if self._language_combo.itemData(i) == current:
                self._language_combo.setCurrentIndex(i)
                break
        self._language_combo.blockSignals(False)

    # ** Slots

    def _on_language_changed(self) -> None:
        code: str = self._language_combo.currentData()
        with db.manage_connection() as conn:
            if code:
                db.set_setting(conn, 'language', code)
            else:
                db.delete_setting(conn, 'language')
        self._restart_label.setVisible(True)
