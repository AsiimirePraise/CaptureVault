"""Discover all user-accessible locations on this computer."""

import os
import string
import sys
from pathlib import Path

from capturevault.database.manager import DatabaseManager


def _windows_drive_roots() -> list[Path]:
    """All mounted drive letters on Windows."""
    if sys.platform != "win32":
        return []
    try:
        import ctypes

        bitmask = ctypes.windll.kernel32.GetLogicalDrives()
        drives: list[Path] = []
        for i, letter in enumerate(string.ascii_uppercase):
            if bitmask & (1 << i):
                drive = Path(f"{letter}:\\")
                if drive.exists():
                    drives.append(drive)
        return drives
    except OSError:
        return []


def _dedupe_roots(paths: list[Path]) -> list[Path]:
    """Keep broadest roots; drop paths nested inside another root."""
    unique: list[Path] = []
    seen: set[str] = set()
    for path in paths:
        try:
            resolved = path.resolve()
            key = str(resolved).lower()
            if key in seen or not resolved.is_dir():
                continue
            seen.add(key)
            unique.append(resolved)
        except OSError:
            continue

    unique.sort(key=lambda p: len(str(p)))
    roots: list[Path] = []
    for path in unique:
        if not any(
            str(path).startswith(str(root) + os.sep) for root in roots
        ):
            roots.append(path)
    return roots


def discover_laptop_folders() -> list[Path]:
    """
    Locations to index so search covers the whole laptop:
    - Entire user profile (Desktop, Documents, Pictures, Downloads, etc.)
    - Every other drive (D:, E:, USB, Google Drive, etc.)
    System folders are skipped during the scan, not listed here.
    """
    roots: list[Path] = []
    home = Path.home()
    try:
        roots.append(home.resolve())
    except OSError:
        pass

    home_drive = home.drive.upper() if home.drive else "C:"

    for drive in _windows_drive_roots():
        # On C: only scan the user profile (not all of Windows)
        if drive.drive.upper() == home_drive:
            continue
        roots.append(drive)

    return _dedupe_roots(roots)


def auto_setup_folders(db: DatabaseManager) -> list[str]:
    """First launch: register all laptop locations."""
    if db.has_monitored_folders():
        return []

    added: list[str] = []
    for folder in discover_laptop_folders():
        if db.add_monitored_folder(str(folder)):
            added.append(str(folder))
    return added


def ensure_laptop_coverage(db: DatabaseManager) -> list[str]:
    """
    Make sure user profile + all drives are monitored.
    Returns newly added folder paths.
    """
    if not db.has_monitored_folders():
        return auto_setup_folders(db)
    return add_missing_laptop_folders(db)


def add_missing_laptop_folders(db: DatabaseManager) -> list[str]:
    """Add laptop locations not already in the database."""
    existing = {f["path"].lower() for f in db.get_monitored_folders()}
    added: list[str] = []
    for folder in discover_laptop_folders():
        path = str(folder)
        if path.lower() not in existing and db.add_monitored_folder(path):
            added.append(path)
    return added


# Backward-compatible alias
def discover_default_folders() -> list[Path]:
    return discover_laptop_folders()


def add_missing_default_folders(db: DatabaseManager) -> list[str]:
    return add_missing_laptop_folders(db)
