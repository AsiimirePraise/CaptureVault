"""Platform utilities."""

import os
import subprocess
import sys
from pathlib import Path


def open_file(path: str) -> bool:
    """Open a file with the system default application."""
    p = Path(path)
    if not p.exists():
        return False
    try:
        if sys.platform == "win32":
            os.startfile(str(p))  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.run(["open", str(p)], check=False)
        else:
            subprocess.run(["xdg-open", str(p)], check=False)
        return True
    except OSError:
        return False


def open_containing_folder(path: str) -> bool:
    """Open the folder containing a file in Explorer."""
    p = Path(path)
    if not p.exists():
        return False
    folder = str(p.parent)
    try:
        if sys.platform == "win32":
            subprocess.run(["explorer", "/select,", str(p)], check=False)
        elif sys.platform == "darwin":
            subprocess.run(["open", "-R", str(p)], check=False)
        else:
            subprocess.run(["xdg-open", folder], check=False)
        return True
    except OSError:
        return False


def copy_to_clipboard(text: str) -> bool:
    """Copy text to clipboard using Qt when available."""
    try:
        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance()
        if app:
            from PyQt6.QtGui import QGuiApplication
            QGuiApplication.clipboard().setText(text)
            return True
    except ImportError:
        pass
    return False
