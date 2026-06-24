"""Settings dialog."""

from pathlib import Path

from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from capturevault.config import AppConfig
from capturevault.constants import (
    MAX_THUMBNAIL_SIZE,
    MIN_THUMBNAIL_SIZE,
    THEME_DARK,
    THEME_LIGHT,
)
from capturevault.database.manager import DatabaseManager
from capturevault.core.autodiscover import add_missing_laptop_folders


class SettingsDialog(QDialog):
    """Application settings including folders, theme, and database backup."""

    def __init__(
        self,
        config: AppConfig,
        db: DatabaseManager,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._config = config
        self._db = db
        self.setWindowTitle("Settings")
        self.setMinimumSize(560, 520)
        self._setup_ui()
        self._load_folders()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        # Folders (optional — defaults are added automatically on first launch)
        folder_group = QGroupBox("Monitored Folders")
        folder_layout = QVBoxLayout(folder_group)
        folder_hint = QLabel(
            "CaptureVault searches your user folder and every drive on this PC. "
            "Use Add to include a specific folder, or Scan Entire Laptop to "
            "pick up new drives."
        )
        folder_hint.setWordWrap(True)
        folder_hint.setObjectName("subtitleLabel")
        folder_layout.addWidget(folder_hint)
        self._folder_list = QListWidget()
        folder_layout.addWidget(self._folder_list)

        folder_btns = QHBoxLayout()
        add_btn = QPushButton("Add...")
        add_btn.clicked.connect(self._add_folder)
        folder_btns.addWidget(add_btn)
        remove_btn = QPushButton("Remove")
        remove_btn.clicked.connect(self._remove_folder)
        folder_btns.addWidget(remove_btn)
        detect_btn = QPushButton("Scan Entire Laptop")
        detect_btn.clicked.connect(self._add_laptop_folders)
        folder_btns.addWidget(detect_btn)
        folder_btns.addStretch()
        folder_layout.addLayout(folder_btns)
        layout.addWidget(folder_group)

        # Appearance
        appear_group = QGroupBox("Appearance")
        form = QFormLayout(appear_group)

        self._theme_combo = QComboBox()
        self._theme_combo.addItem("Light (Grayscale)", THEME_LIGHT)
        self._theme_combo.addItem("Dark", THEME_DARK)
        idx = self._theme_combo.findData(self._config.theme)
        if idx >= 0:
            self._theme_combo.setCurrentIndex(idx)
        form.addRow("Theme:", self._theme_combo)

        self._thumb_spin = QSpinBox()
        self._thumb_spin.setRange(MIN_THUMBNAIL_SIZE, MAX_THUMBNAIL_SIZE)
        self._thumb_spin.setSingleStep(16)
        self._thumb_spin.setValue(self._config.thumbnail_size)
        form.addRow("Thumbnail Size:", self._thumb_spin)

        layout.addWidget(appear_group)

        # Updates
        update_group = QGroupBox("Updates")
        update_layout = QVBoxLayout(update_group)
        self._check_updates = QCheckBox("Check for updates on startup")
        self._check_updates.setChecked(self._config.check_updates_on_startup)
        update_layout.addWidget(self._check_updates)
        layout.addWidget(update_group)

        # Database
        db_group = QGroupBox("Database")
        db_layout = QHBoxLayout(db_group)
        backup_btn = QPushButton("Backup Database...")
        backup_btn.clicked.connect(self._backup_db)
        db_layout.addWidget(backup_btn)
        restore_btn = QPushButton("Restore Database...")
        restore_btn.clicked.connect(self._restore_db)
        db_layout.addWidget(restore_btn)
        db_layout.addStretch()
        layout.addWidget(db_group)

        # Footer
        footer = QHBoxLayout()
        footer.addStretch()
        save_btn = QPushButton("Save")
        save_btn.setObjectName("primaryButton")
        save_btn.clicked.connect(self._save)
        footer.addWidget(save_btn)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        footer.addWidget(cancel_btn)
        layout.addLayout(footer)

    def _load_folders(self) -> None:
        self._folder_list.clear()
        for folder in self._db.get_monitored_folders():
            self._folder_list.addItem(folder["path"])

    def _add_laptop_folders(self) -> None:
        added = add_missing_laptop_folders(self._db)
        self._load_folders()
        if added:
            QMessageBox.information(
                self,
                "Laptop Scan",
                f"Added {len(added)} location(s):\n"
                + "\n".join(added[:5])
                + ("\n..." if len(added) > 5 else "")
                + "\n\nClick Full Rescan on the main window to index them.",
            )
        else:
            QMessageBox.information(
                self,
                "Already Covered",
                "Your user folder and all drives are already being monitored.",
            )

    def _add_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Add Folder")
        if folder:
            if self._db.add_monitored_folder(folder):
                self._folder_list.addItem(folder)
            else:
                QMessageBox.information(
                    self, "Already Added", "This folder is already monitored."
                )

    def _remove_folder(self) -> None:
        item = self._folder_list.currentItem()
        if not item:
            return
        path = item.text()
        folders = self._db.get_monitored_folders()
        folder_id = next(
            (f["id"] for f in folders if f["path"] == path), None
        )
        if folder_id:
            reply = QMessageBox.question(
                self,
                "Remove Folder",
                "Remove this folder from monitoring? Indexed metadata will be removed.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self._db.remove_files_under_folder(path)
                self._db.remove_monitored_folder(folder_id)
                self._folder_list.takeItem(self._folder_list.row(item))

    def _backup_db(self) -> None:
        dest, _ = QFileDialog.getSaveFileName(
            self,
            "Backup Database",
            "capturevault_backup.db",
            "SQLite Database (*.db)",
        )
        if dest:
            try:
                self._db.backup_database(Path(dest))
                QMessageBox.information(self, "Backup", "Database backed up successfully.")
            except OSError as exc:
                QMessageBox.critical(self, "Error", str(exc))

    def _restore_db(self) -> None:
        source, _ = QFileDialog.getOpenFileName(
            self, "Restore Database", "", "SQLite Database (*.db)"
        )
        if source:
            reply = QMessageBox.warning(
                self,
                "Restore Database",
                "This will replace your current database. Continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                try:
                    self._db.restore_database(Path(source))
                    QMessageBox.information(
                        self, "Restored", "Database restored. Please restart the application."
                    )
                    self.accept()
                except OSError as exc:
                    QMessageBox.critical(self, "Error", str(exc))

    def _save(self) -> None:
        self._config.theme = self._theme_combo.currentData()
        self._config.thumbnail_size = self._thumb_spin.value()
        self._config.check_updates_on_startup = self._check_updates.isChecked()
        self.accept()

    @property
    def theme_changed(self) -> str:
        return self._theme_combo.currentData()

    @property
    def thumbnail_size_changed(self) -> int:
        return self._thumb_spin.value()
