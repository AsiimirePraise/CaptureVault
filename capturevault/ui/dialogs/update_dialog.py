"""Update notification dialog."""

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from capturevault.updates.update_manager import ReleaseInfo, UpdateManager


class DownloadWorker(QThread):
    progress = pyqtSignal(int, int)
    finished_download = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, manager: UpdateManager, release: ReleaseInfo, parent=None):
        super().__init__(parent)
        self._manager = manager
        self._release = release

    def run(self) -> None:
        path = self._manager.download_update(
            self._release,
            progress_callback=lambda d, t: self.progress.emit(d, t),
        )
        if path:
            self.finished_download.emit(path)
        else:
            self.error.emit("Download failed. Please try again later.")


class UpdateDialog(QDialog):
    """Notify user of available update with download option."""

    def __init__(
        self,
        release: ReleaseInfo,
        manager: UpdateManager,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._release = release
        self._manager = manager
        self._worker: DownloadWorker | None = None
        self.setWindowTitle("Update Available")
        self.setMinimumSize(440, 300)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)

        title = QLabel("A new version of CaptureVault is available.")
        title.setObjectName("titleLabel")
        title.setWordWrap(True)
        layout.addWidget(title)

        version = QLabel(
            f"Installed: v{self._manager.current_version}  →  "
            f"Latest: v{self._release.version}"
        )
        version.setObjectName("subtitleLabel")
        layout.addWidget(version)

        if self._release.release_notes:
            notes = QTextEdit()
            notes.setReadOnly(True)
            notes.setPlainText(self._release.release_notes[:2000])
            notes.setMaximumHeight(120)
            layout.addWidget(notes)

        self._progress = QProgressBar()
        self._progress.setVisible(False)
        layout.addWidget(self._progress)

        footer = QHBoxLayout()
        footer.addStretch()

        self._download_btn = QPushButton("Download Update")
        self._download_btn.setObjectName("primaryButton")
        self._download_btn.clicked.connect(self._start_download)
        footer.addWidget(self._download_btn)

        later_btn = QPushButton("Remind Me Later")
        later_btn.clicked.connect(self.reject)
        footer.addWidget(later_btn)

        layout.addLayout(footer)

    def _start_download(self) -> None:
        self._download_btn.setEnabled(False)
        self._progress.setVisible(True)
        self._progress.setValue(0)

        self._worker = DownloadWorker(self._manager, self._release, self)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished_download.connect(self._on_downloaded)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_progress(self, downloaded: int, total: int) -> None:
        if total > 0:
            self._progress.setValue(int(downloaded * 100 / total))

    def _on_downloaded(self, path) -> None:
        self._progress.setValue(100)
        reply = QMessageBox.question(
            self,
            "Install Update",
            "Download complete. Install now? The application will close.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            if self._manager.launch_installer(path):
                self.accept()
                from PyQt6.QtWidgets import QApplication
                QApplication.instance().quit()
            else:
                QMessageBox.critical(self, "Error", "Could not launch installer.")
        self._download_btn.setEnabled(True)

    def _on_error(self, message: str) -> None:
        self._progress.setVisible(False)
        self._download_btn.setEnabled(True)
        QMessageBox.warning(self, "Download Failed", message)
