"""Search view."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget

from capturevault.core.thumbnails import ThumbnailService
from capturevault.ui.widgets.results_grid import ResultsGrid


class SearchView(QWidget):
    """Main search results view."""

    def __init__(self, thumb_service: ThumbnailService, parent=None) -> None:
        super().__init__(parent)
        self._empty_label = QLabel()
        self._empty_label.setObjectName("subtitleLabel")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setWordWrap(True)
        self._empty_label.hide()

        self._grid = ResultsGrid(thumb_service)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._empty_label)
        layout.addWidget(self._grid)

    @property
    def grid(self) -> ResultsGrid:
        return self._grid

    def set_results(self, files: list[dict], empty_message: str = "") -> None:
        if files:
            self._empty_label.hide()
            self._grid.show()
        else:
            self._grid.setRowCount(0)
            self._empty_label.setText(
                empty_message or "No files to show yet."
            )
            self._empty_label.show()
        self._grid.set_results(files)
