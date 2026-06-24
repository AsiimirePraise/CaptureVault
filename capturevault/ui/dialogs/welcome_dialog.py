"""One-time welcome tip — non-blocking, automation-first."""

from PyQt6.QtWidgets import (
    QDialog,
    QLabel,
    QPushButton,
    QVBoxLayout,
)


class WelcomeDialog(QDialog):
    """Brief intro shown once after automatic folder setup."""

    def __init__(self, folder_count: int, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Welcome to CaptureVault")
        self.setMinimumWidth(480)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        title = QLabel("Searching your entire laptop")
        title.setObjectName("titleLabel")
        title.setWordWrap(True)
        layout.addWidget(title)

        body = QLabel(
            f"CaptureVault is indexing {folder_count} location(s): "
            "your user folder plus every drive on this PC "
            "(USB, Google Drive, external disks, etc.).\n\n"
            "This runs in the background. Just type to search — "
            "double-click any result to open it.\n\n"
            "Windows and Program Files are skipped automatically. "
            "Your original files are never changed."
        )
        body.setWordWrap(True)
        body.setObjectName("subtitleLabel")
        layout.addWidget(body)

        btn = QPushButton("Start Searching")
        btn.setObjectName("primaryButton")
        btn.clicked.connect(self.accept)
        layout.addWidget(btn)
