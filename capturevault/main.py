"""Application entry point."""

import sys

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from capturevault.config import AppConfig
from capturevault.ui.main_window import MainWindow


def main() -> int:
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setApplicationName("CaptureVault")
    app.setOrganizationName("CaptureVault")

    config = AppConfig()
    window = MainWindow(config)
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
