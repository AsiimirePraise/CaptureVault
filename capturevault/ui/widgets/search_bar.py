"""Search bar with file-type and folder filters."""

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from capturevault.constants import DEFAULT_SEARCH_FILTER
from capturevault.core.search_filters import TYPE_FILTER_OPTIONS, SearchFilters


class SearchBar(QFrame):
    """Search input with type and folder scope filters."""

    search_triggered = pyqtSignal()

    DEBOUNCE_MS = 120

    def __init__(self, default_type_filter: str = DEFAULT_SEARCH_FILTER, parent=None) -> None:
        super().__init__(parent)
        self._default_type_filter = default_type_filter
        self.setObjectName("searchBarFrame")
        self._custom_folder: str | None = None
        self._monitored_folders: list[str] = []
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._emit_search)
        self._setup_ui()

    def _setup_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 10, 20, 10)
        outer.setSpacing(8)

        # Filter row
        filter_row = QHBoxLayout()
        filter_row.setSpacing(10)

        type_label = QComboBox()
        type_label.setMinimumWidth(130)
        for label, key in TYPE_FILTER_OPTIONS:
            type_label.addItem(label, key)
        type_label.currentIndexChanged.connect(self._on_filter_changed)
        filter_row.addWidget(type_label)
        self._type_combo = type_label
        self.set_type_filter(self._default_type_filter)

        folder_combo = QComboBox()
        folder_combo.setMinimumWidth(200)
        folder_combo.currentIndexChanged.connect(self._on_filter_changed)
        filter_row.addWidget(folder_combo)
        self._folder_combo = folder_combo

        browse_btn = QPushButton("Choose Folder...")
        browse_btn.clicked.connect(self._browse_folder)
        filter_row.addWidget(browse_btn)

        filter_row.addStretch()
        outer.addLayout(filter_row)

        # Search row
        search_row = QHBoxLayout()
        self._input = QLineEdit()
        self._input.setObjectName("searchInput")
        self._input.setPlaceholderText(
            "Type any part of a name — files appear instantly as you type"
        )
        font = QFont("Segoe UI", 14)
        self._input.setFont(font)
        self._input.textChanged.connect(self._on_text_changed)
        self._input.returnPressed.connect(self._emit_search)
        search_row.addWidget(self._input, stretch=1)

        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self._clear)
        search_row.addWidget(clear_btn)

        outer.addLayout(search_row)

        self.set_folder_choices([])

    def set_folder_choices(self, folders: list[str]) -> None:
        """Populate folder dropdown from monitored locations."""
        self._monitored_folders = list(folders)
        current = self._folder_combo.currentData()
        self._folder_combo.blockSignals(True)
        self._folder_combo.clear()
        self._folder_combo.addItem("All folders", None)

        if self._custom_folder:
            label = self._short_path(self._custom_folder)
            self._folder_combo.addItem(f"Custom: {label}", self._custom_folder)

        for path in folders:
            self._folder_combo.addItem(self._short_path(path), path)

        # Restore selection
        for i in range(self._folder_combo.count()):
            if self._folder_combo.itemData(i) == current:
                self._folder_combo.setCurrentIndex(i)
                break

        self._folder_combo.blockSignals(False)

    @staticmethod
    def _short_path(path: str) -> str:
        if len(path) <= 48:
            return path
        return "..." + path[-45:]

    def _browse_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self, "Search in this folder only"
        )
        if not folder:
            return
        self._custom_folder = folder
        self.set_folder_choices(self._monitored_folders)
        for i in range(self._folder_combo.count()):
            if self._folder_combo.itemData(i) == folder:
                self._folder_combo.setCurrentIndex(i)
                self._on_filter_changed()
                return

    def get_filters(self) -> SearchFilters:
        return SearchFilters(
            type_filter=self._type_combo.currentData() or self._default_type_filter,
            folder_path=self._folder_combo.currentData(),
        )

    def _on_filter_changed(self) -> None:
        self._emit_search()

    def _on_text_changed(self, _text: str) -> None:
        self._timer.stop()
        self._timer.start(self.DEBOUNCE_MS)

    def _emit_search(self) -> None:
        self.search_triggered.emit()

    def set_type_filter(self, filter_key: str) -> None:
        """Select file type filter by key (e.g. images, all)."""
        idx = self._type_combo.findData(filter_key)
        if idx >= 0:
            self._type_combo.blockSignals(True)
            self._type_combo.setCurrentIndex(idx)
            self._type_combo.blockSignals(False)

    def set_default_type_filter(self, filter_key: str) -> None:
        self._default_type_filter = filter_key
        self.set_type_filter(filter_key)

    def _clear(self) -> None:
        self._input.clear()
        self.set_type_filter(self._default_type_filter)
        self._folder_combo.setCurrentIndex(0)
        self._custom_folder = None
        self.search_triggered.emit()

    def set_query(self, text: str) -> None:
        self._input.setText(text)

    def query(self) -> str:
        return self._input.text()

    def focus_input(self) -> None:
        self._input.setFocus()
