"""Dashboard view."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QGridLayout, QLabel, QVBoxLayout, QWidget

from capturevault.database.manager import DatabaseManager


class StatCard(QFrame):
    def __init__(self, label: str, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("card")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)

        self._value = QLabel("0")
        self._value.setObjectName("statValue")
        self._value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._value)

        lbl = QLabel(label)
        lbl.setObjectName("statLabel")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl)

    def set_value(self, value: int) -> None:
        self._value.setText(f"{value:,}")


class DashboardView(QWidget):
    """Overview statistics and recent files."""

    def __init__(self, db: DatabaseManager, parent=None) -> None:
        super().__init__(parent)
        self._db = db
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        title = QLabel("Dashboard")
        title.setObjectName("titleLabel")
        layout.addWidget(title)

        grid = QGridLayout()
        grid.setSpacing(16)
        self._cards = {
            "total_files": StatCard("Total Files"),
            "total_photos": StatCard("Photos"),
            "total_videos": StatCard("Videos"),
            "total_documents": StatCard("Documents"),
            "total_favorites": StatCard("Favorites"),
        }
        positions = [
            ("total_files", 0, 0),
            ("total_photos", 0, 1),
            ("total_videos", 0, 2),
            ("total_documents", 1, 0),
            ("total_favorites", 1, 1),
        ]
        for key, r, c in positions:
            grid.addWidget(self._cards[key], r, c)
        layout.addLayout(grid)

        recent_label = QLabel("Recent Files")
        recent_label.setObjectName("subtitleLabel")
        layout.addWidget(recent_label)

        self._recent_list = QLabel()
        self._recent_list.setWordWrap(True)
        self._recent_list.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.addWidget(self._recent_list, stretch=1)

    def refresh(self) -> None:
        stats = self._db.get_dashboard_stats()
        for key, card in self._cards.items():
            card.set_value(stats.get(key, 0))

        recent = self._db.get_recent_files(15)
        if not recent:
            self._recent_list.setText("No files indexed yet. Add folders in Settings.")
            return

        lines = []
        for f in recent:
            name = f.get("virtual_name") or f.get("file_name", "Unknown")
            lines.append(f"• {name}")
        self._recent_list.setText("\n".join(lines))
