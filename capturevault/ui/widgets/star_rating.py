"""Clickable 1-5 star rating widget."""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QPushButton, QWidget


class StarRatingWidget(QWidget):
    """Clickable 1-5 star rating."""

    rating_changed = pyqtSignal(int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._rating = 0
        self._buttons: list[QPushButton] = []
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        for i in range(1, 6):
            btn = QPushButton("☆")
            btn.setFixedSize(32, 32)
            btn.clicked.connect(lambda checked, n=i: self.set_rating(n))
            self._buttons.append(btn)
            layout.addWidget(btn)
        layout.addStretch()

    def set_rating(self, rating: int) -> None:
        self._rating = rating
        for i, btn in enumerate(self._buttons, 1):
            btn.setText("★" if i <= rating else "☆")
        self.rating_changed.emit(rating)

    def rating(self) -> int:
        return self._rating
