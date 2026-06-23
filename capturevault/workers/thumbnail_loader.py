"""Background thumbnail generation."""

from PyQt6.QtCore import QThread, pyqtSignal

from capturevault.core.thumbnails import ThumbnailService


class ThumbnailLoader(QThread):
    """Generate thumbnails off the UI thread."""

    thumbnail_ready = pyqtSignal(int, str)

    def __init__(self, thumb_service: ThumbnailService, parent=None) -> None:
        super().__init__(parent)
        self._service = thumb_service
        self._batch: list[tuple[int, str, str, str]] = []
        self._run_id = 0

    def load_batch(self, items: list[tuple[int, str, str, str]]) -> None:
        """Queue rows as (row, path, file_type, extension)."""
        self._run_id += 1
        current_run = self._run_id
        if self.isRunning():
            self.wait(2000)
        if current_run != self._run_id:
            return
        self._batch = items
        self.start()

    def run(self) -> None:
        run_id = self._run_id
        for row, path, file_type, extension in self._batch:
            if run_id != self._run_id:
                break
            try:
                thumb_path = self._service.get_thumbnail_path(
                    path, file_type, extension
                )
                self.thumbnail_ready.emit(row, str(thumb_path))
            except OSError:
                continue
