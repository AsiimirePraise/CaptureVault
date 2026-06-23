"""Favorites view."""

from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget

from capturevault.core.thumbnails import ThumbnailService
from capturevault.database.manager import DatabaseManager
from capturevault.ui.widgets.results_grid import ResultsGrid


class FavoritesView(QWidget):
    """Displays favorited files."""

    def __init__(
        self,
        db: DatabaseManager,
        thumb_service: ThumbnailService,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._db = db
        self._grid = ResultsGrid(thumb_service)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)

        title = QLabel("Favorites")
        title.setObjectName("titleLabel")
        layout.addWidget(title)

        layout.addWidget(self._grid)

    @property
    def grid(self) -> ResultsGrid:
        return self._grid

    def refresh(self) -> None:
        files = self._db.get_favorites()
        for f in files:
            f["tags"] = self._db.get_file_tags(f["id"])
            f["collections"] = self._db.get_file_collections(f["id"])
        self._grid.set_results(files)
