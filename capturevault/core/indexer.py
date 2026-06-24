"""File indexing utilities."""

import os
from pathlib import Path

from capturevault.core.exclusions import should_skip_dir
from capturevault.database.manager import DatabaseManager


def _iter_files(
    folder_path: Path,
    cancel_check=None,
):
    """Walk folder tree, skipping system and cache directories."""
    folder_path = folder_path.resolve()
    if not folder_path.exists():
        return

    for dirpath, dirnames, filenames in os.walk(folder_path, topdown=True):
        if cancel_check and cancel_check():
            break

        dirnames[:] = [
            d
            for d in dirnames
            if not should_skip_dir(Path(dirpath) / d)
        ]

        for name in filenames:
            if cancel_check and cancel_check():
                break
            yield Path(dirpath) / name


def scan_folder(
    folder_path: Path,
    db: DatabaseManager,
    progress_callback=None,
    cancel_check=None,
) -> tuple[int, int]:
    """
    Recursively scan a folder and index supported files.
    Returns (files_indexed, files_skipped).
    """
    indexed = 0
    skipped = 0

    for file_path in _iter_files(folder_path, cancel_check):
        if not file_path.is_file():
            continue
        if not DatabaseManager.is_supported_file(file_path):
            skipped += 1
            continue
        result = db.upsert_file(file_path)
        if result:
            indexed += 1
            if progress_callback:
                progress_callback(str(file_path), indexed)
        else:
            skipped += 1

    return indexed, skipped


def quick_scan_folder(
    folder_path: Path,
    db: DatabaseManager,
    progress_callback=None,
    cancel_check=None,
) -> tuple[int, int, int]:
    """
    Quick scan: add new files and update changed files.
    Remove entries for deleted files under this folder.
    Returns (added_or_updated, removed, skipped).
    """
    folder_path = folder_path.resolve()
    prefix = str(folder_path)
    existing = {
        p: info
        for p, info in db.get_all_indexed_paths().items()
        if p.startswith(prefix)
    }
    found_paths: set[str] = set()
    updated = 0
    skipped = 0

    if not folder_path.exists():
        for path in existing:
            db.remove_file_by_path(path)
        return 0, len(existing), 0

    for file_path in _iter_files(folder_path, cancel_check):
        if not file_path.is_file():
            continue
        resolved = str(file_path.resolve())
        if not DatabaseManager.is_supported_file(file_path):
            skipped += 1
            continue

        found_paths.add(resolved)
        stat = file_path.stat()
        modified = stat.st_mtime

        if resolved in existing:
            stored = existing[resolved].get("date_modified", "")
            try:
                from datetime import datetime

                stored_mtime = datetime.fromisoformat(stored).timestamp()
            except (ValueError, TypeError):
                stored_mtime = 0
            if abs(modified - stored_mtime) < 1:
                continue

        db.upsert_file(file_path)
        updated += 1
        if progress_callback:
            progress_callback(resolved, updated)

    removed = 0
    for path in existing:
        if path not in found_paths:
            db.remove_file_by_path(path)
            removed += 1

    return updated, removed, skipped
