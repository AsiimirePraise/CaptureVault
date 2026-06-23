"""Background indexing worker."""

from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

from capturevault.core.indexer import quick_scan_folder, scan_folder
from capturevault.database.manager import DatabaseManager


class IndexerWorker(QThread):
    """Runs full or quick scans in a background thread."""

    progress = pyqtSignal(str, int)  # current_file, count
    finished_scan = pyqtSignal(int, int, int)  # indexed, removed, skipped
    error = pyqtSignal(str)

    def __init__(
        self,
        db_path: Path,
        folders: list[str],
        full_scan: bool = True,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._db_path = db_path
        self._folders = folders
        self._full_scan = full_scan
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def _is_cancelled(self) -> bool:
        return self._cancelled

    def run(self) -> None:
        db = DatabaseManager(self._db_path)
        total_indexed = 0
        total_removed = 0
        total_skipped = 0

        try:
            for folder in self._folders:
                if self._cancelled:
                    break
                path = Path(folder)
                if self._full_scan:
                    indexed, skipped = scan_folder(
                        path,
                        db,
                        progress_callback=lambda f, c: self.progress.emit(f, c),
                        cancel_check=self._is_cancelled,
                    )
                    total_indexed += indexed
                    total_skipped += skipped
                else:
                    updated, removed, skipped = quick_scan_folder(
                        path,
                        db,
                        progress_callback=lambda f, c: self.progress.emit(f, c),
                        cancel_check=self._is_cancelled,
                    )
                    total_indexed += updated
                    total_removed += removed
                    total_skipped += skipped

            if self._full_scan and not self._cancelled:
                db.rebuild_all_fts()
        except Exception as exc:
            self.error.emit(str(exc))
            return
        finally:
            db.close()

        self.finished_scan.emit(total_indexed, total_removed, total_skipped)
