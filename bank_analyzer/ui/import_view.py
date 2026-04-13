# * Import view

import pathlib

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from bank_analyzer import importer

# * View

class ImportView(QWidget):
    import_succeeded = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._filepath: pathlib.Path | None = None

        # ** Bank selector
        self._bank_selector = QComboBox()
        for name in sorted(importer.BANKS.keys()):
            self._bank_selector.addItem(name)

        # ** File picker row
        self._file_label = QLabel('(no file selected)')
        browse_button = QPushButton('Browse...')
        browse_button.clicked.connect(self._pick_file)

        file_row = QHBoxLayout()
        file_row.addWidget(self._file_label, stretch=1)
        file_row.addWidget(browse_button)

        # ** Form
        form = QFormLayout()
        form.addRow('Bank:', self._bank_selector)
        form.addRow('File:', file_row)

        # ** Import button and status
        import_button = QPushButton('Import')
        import_button.clicked.connect(self._run_import)

        self._status_label = QLabel()
        self._status_label.setWordWrap(True)

        # ** Outer layout
        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addWidget(import_button)
        layout.addWidget(self._status_label)
        layout.addStretch()
        self.setLayout(layout)

    # ** Callbacks

    def _pick_file(self) -> None:
        path_str, _ = QFileDialog.getOpenFileName(
            self, 'Select CSV file', '', 'CSV files (*.csv);;All files (*)'
        )
        if path_str:
            self._filepath = pathlib.Path(path_str)
            self._file_label.setText(self._filepath.name)

    def _run_import(self) -> None:
        if self._filepath is None:
            self._status_label.setText('Please select a file first.')
            return
        bank = self._bank_selector.currentText()
        try:
            result = importer.import_file(self._filepath, bank)
            self._status_label.setText(
                f"Done: {result['inserted']} inserted, {result['skipped']} skipped "
                f"(total {result['total']})."
            )
            self.import_succeeded.emit()
        except importer.FileAlreadyImportedError:
            self._status_label.setText(f"'{self._filepath.name}' has already been imported.")
        except Exception as e:
            self._status_label.setText(f'Error: {e}')
