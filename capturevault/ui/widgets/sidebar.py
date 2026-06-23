"""Navigation sidebar widget."""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QFrame, QLabel, QListWidget, QListWidgetItem, QVBoxLayout


class Sidebar(QFrame):
    """Left navigation panel."""

    navigation_changed = pyqtSignal(str)

    NAV_ITEMS = [
        ("dashboard", "Dashboard"),
        ("search", "Search"),
        ("favorites", "Favorites"),
        ("collections", "Collections"),
        ("settings", "Settings"),
    ]

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(200)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 20, 12, 12)
        layout.setSpacing(8)

        logo = QLabel("CaptureVault")
        logo.setObjectName("titleLabel")
        layout.addWidget(logo)

        subtitle = QLabel("Virtual Media Library")
        subtitle.setObjectName("subtitleLabel")
        layout.addWidget(subtitle)
        layout.addSpacing(16)

        self._list = QListWidget()
        self._list.setFrameShape(QFrame.Shape.NoFrame)
        for key, label in self.NAV_ITEMS:
            item = QListWidgetItem(label)
            item.setData(256, key)  # Qt.ItemDataRole.UserRole
            self._list.addItem(item)

        self._list.setCurrentRow(1)
        self._list.currentRowChanged.connect(self._on_selection)
        layout.addWidget(self._list)
        layout.addStretch()

    def _on_selection(self, row: int) -> None:
        item = self._list.item(row)
        if item:
            key = item.data(256)
            self.navigation_changed.emit(key)

    def select(self, key: str) -> None:
        for i in range(self._list.count()):
            item = self._list.item(i)
            if item and item.data(256) == key:
                self._list.setCurrentRow(i)
                break
