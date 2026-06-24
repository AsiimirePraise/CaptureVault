"""One-time welcome tip — non-blocking, automation-first."""

from PyQt6.QtWidgets import (
    QDialog,
    QLabel,
    QPushButton,
    QVBoxLayout,
)


class WelcomeDialog(QDialog):
    """Brief intro shown once after automatic folder setup."""

    def __init__(
        self,
        folder_count: int,
        photographer_mode: bool = True,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Welcome to CaptureVault")
        self.setMinimumWidth(480)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        title = QLabel(
            "Your photo library, searchable instantly"
            if photographer_mode
            else "Searching your entire laptop"
        )
        title.setObjectName("titleLabel")
        title.setWordWrap(True)
        layout.addWidget(title)

        if photographer_mode:
            body_text = (
                f"CaptureVault is indexing images and RAW files across "
                f"{folder_count} location(s) on this PC "
                "(Pictures, drives, Google Drive, etc.).\n\n"
                "Search defaults to Images + RAW. Dev folders, Windows, and "
                "Program Files are skipped automatically.\n\n"
                "Indexing runs in the background — type any part of a file "
                "name to find it. Your original files are never changed."
            )
        else:
            body_text = (
                f"CaptureVault is indexing {folder_count} location(s): "
                "your user folder plus every drive on this PC "
                "(USB, Google Drive, external disks, etc.).\n\n"
                "This runs in the background. Just type to search — "
                "double-click any result to open it.\n\n"
                "Windows and Program Files are skipped automatically. "
                "Your original files are never changed."
            )

        body = QLabel(body_text)
        body.setWordWrap(True)
        body.setObjectName("subtitleLabel")
        layout.addWidget(body)

        btn = QPushButton("Start Searching")
        btn.setObjectName("primaryButton")
        btn.clicked.connect(self.accept)
        layout.addWidget(btn)
