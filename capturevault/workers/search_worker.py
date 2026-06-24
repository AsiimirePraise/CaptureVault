"""Background search worker."""

from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

from capturevault.core.search import SearchEngine
from capturevault.core.search_filters import SearchFilters
from capturevault.database.manager import DatabaseManager


class SearchWorker(QThread):
    """Runs search queries off the main thread with its own DB connection."""

    results_ready = pyqtSignal(int, list)

    def __init__(
        self,
        db_path: Path,
        query: str,
        generation: int,
        filters: SearchFilters | None = None,
        limit: int = 200,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._db_path = db_path
        self._query = query
        self._generation = generation
        self._filters = filters or SearchFilters()
        self._limit = limit

    def run(self) -> None:
        db = DatabaseManager(self._db_path)
        try:
            engine = SearchEngine(db)
            results = engine.search(
                self._query, self._limit, filters=self._filters
            )
            self.results_ready.emit(self._generation, results)
        finally:
            db.close()
