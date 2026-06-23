"""First-run setup wizard."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from capturevault.database.manager import DatabaseManager


class SetupWizard(QDialog):
    """Prompt user to select folders on first launch."""

    def __init__(self, db: DatabaseManager, parent=None) -> None:
        super().__init__(parent)
        self._db = db
        self.setWindowTitle("Welcome to CaptureVault")
        self.setMinimumSize(520, 400)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        title = QLabel("Welcome to CaptureVault")
        title.setObjectName("titleLabel")
        layout.addWidget(title)

        desc = QLabel(
            "Select one or more folders to monitor. CaptureVault will index "
            "your files without moving, renaming, or modifying them."
        )
        desc.setWordWrap(True)
        desc.setObjectName("subtitleLabel")
        layout.addWidget(desc)

        self._folder_list = QListWidget()
        layout.addWidget(self._folder_list)

        btn_row = QHBoxLayout()
        add_btn = QPushButton("Add Folder...")
        add_btn.clicked.connect(self._add_folder)
        btn_row.addWidget(add_btn)

        remove_btn = QPushButton("Remove Selected")
        remove_btn.clicked.connect(self._remove_folder)
        btn_row.addWidget(remove_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        footer = QHBoxLayout()
        footer.addStretch()
        start_btn = QPushButton("Start Indexing")
        start_btn.setObjectName("primaryButton")
        start_btn.clicked.connect(self._finish)
        footer.addWidget(start_btn)
        layout.addLayout(footer)

    def _add_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self, "Select Folder to Monitor"
        )
        if folder:
            if self._folder_list.findItems(folder, Qt.MatchFlag.MatchExactly):
                return
            self._folder_list.addItem(folder)

    def _remove_folder(self) -> None:
        for item in self._folder_list.selectedItems():
            self._folder_list.takeItem(self._folder_list.row(item))

    def _finish(self) -> None:
        if self._folder_list.count() == 0:
            QMessageBox.warning(
                self,
                "No Folders",
                "Please add at least one folder to continue.",
            )
            return

        for i in range(self._folder_list.count()):
            path = self._folder_list.item(i).text()
            self._db.add_monitored_folder(path)

        self.accept()
