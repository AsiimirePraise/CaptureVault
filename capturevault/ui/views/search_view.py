"""Search view."""

from PyQt6.QtWidgets import QVBoxLayout, QWidget

from capturevault.core.thumbnails import ThumbnailService
from capturevault.ui.widgets.results_grid import ResultsGrid


class SearchView(QWidget):
    """Main search results view."""

    def __init__(self, thumb_service: ThumbnailService, parent=None) -> None:
        super().__init__(parent)
        self._grid = ResultsGrid(thumb_service)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._grid)

    @property
    def grid(self) -> ResultsGrid:
        return self._grid

    def set_results(self, files: list[dict]) -> None:
        self._grid.set_results(files)
