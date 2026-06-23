"""Large search bar widget."""

from PyQt6.QtCore import QTimer, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLineEdit, QPushButton


class SearchBar(QFrame):
    """Prominent search input with debounced typing."""

    search_requested = pyqtSignal(str)
    clear_requested = pyqtSignal()

    DEBOUNCE_MS = 350

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("searchBarFrame")
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._emit_search)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 12, 20, 12)

        self._input = QLineEdit()
        self._input.setObjectName("searchInput")
        self._input.setPlaceholderText(
            "Search files, virtual names, tags, notes, collections..."
        )
        font = QFont("Segoe UI", 14)
        self._input.setFont(font)
        self._input.textChanged.connect(self._on_text_changed)
        self._input.returnPressed.connect(self._emit_search)
        layout.addWidget(self._input, stretch=1)

        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self._clear)
        layout.addWidget(clear_btn)

    def _on_text_changed(self, text: str) -> None:
        self._timer.stop()
        self._timer.start(self.DEBOUNCE_MS)

    def _emit_search(self) -> None:
        self.search_requested.emit(self._input.text())

    def _clear(self) -> None:
        self._input.clear()
        self.clear_requested.emit()

    def set_query(self, text: str) -> None:
        self._input.setText(text)

    def query(self) -> str:
        return self._input.text()

    def focus_input(self) -> None:
        self._input.setFocus()
