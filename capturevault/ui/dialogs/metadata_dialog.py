"""Metadata editing dialog."""

from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from capturevault.constants import COLOR_LABELS
from capturevault.database.manager import DatabaseManager


from capturevault.ui.widgets.star_rating import StarRatingWidget


class MetadataDialog(QDialog):
    """Edit virtual name, tags, notes, rating, color, favorites, collections."""

    def __init__(
        self,
        db: DatabaseManager,
        file_id: int,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._db = db
        self._file_id = file_id
        self._file = db.get_file_by_id(file_id)
        self.setWindowTitle("Edit Metadata")
        self.setMinimumSize(480, 460)
        self._setup_ui()
        self._load_data()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        if self._file:
            path_label = QLabel(self._file["path"])
            path_label.setWordWrap(True)
            path_label.setObjectName("subtitleLabel")
            layout.addWidget(path_label)

        form = QFormLayout()

        self._virtual_name = QLineEdit()
        self._virtual_name.setPlaceholderText("e.g. Bride Walking Down Aisle")
        form.addRow("Virtual Name:", self._virtual_name)

        self._tags = QLineEdit()
        self._tags.setPlaceholderText("#wedding #uganda #client-john")
        form.addRow("Tags:", self._tags)

        self._notes = QTextEdit()
        self._notes.setPlaceholderText("Add notes about this file...")
        self._notes.setMaximumHeight(100)
        form.addRow("Notes:", self._notes)

        self._stars = StarRatingWidget()
        form.addRow("Rating:", self._stars)

        self._color = QComboBox()
        self._color.addItem("None", "")
        for c in COLOR_LABELS:
            self._color.addItem(c.capitalize(), c)
        form.addRow("Color Label:", self._color)

        self._favorite = QCheckBox("Mark as Favorite")
        form.addRow("", self._favorite)

        self._collections = QLineEdit()
        self._collections.setPlaceholderText("Portfolio, Client Deliverables")
        form.addRow("Collections:", self._collections)

        layout.addLayout(form)

        footer = QHBoxLayout()
        footer.addStretch()
        save_btn = QPushButton("Save")
        save_btn.setObjectName("primaryButton")
        save_btn.clicked.connect(self._save)
        footer.addWidget(save_btn)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        footer.addWidget(cancel_btn)
        layout.addLayout(footer)

    def _load_data(self) -> None:
        if not self._file:
            return
        self._virtual_name.setText(self._file.get("virtual_name") or "")
        tags = self._db.get_file_tags(self._file_id)
        self._tags.setText(" ".join(f"#{t}" for t in tags))
        self._notes.setPlainText(self._file.get("notes") or "")
        self._stars.set_rating(self._file.get("rating") or 0)

        color = self._file.get("color_label") or ""
        idx = self._color.findData(color)
        if idx >= 0:
            self._color.setCurrentIndex(idx)

        self._favorite.setChecked(bool(self._file.get("is_favorite")))
        collections = self._db.get_file_collections(self._file_id)
        self._collections.setText(", ".join(collections))

    def _save(self) -> None:
        self._db.update_file_metadata(
            self._file_id,
            virtual_name=self._virtual_name.text(),
            notes=self._notes.toPlainText(),
            rating=self._stars.rating(),
            color_label=self._color.currentData(),
            is_favorite=self._favorite.isChecked(),
        )

        tag_text = self._tags.text()
        tags = []
        for part in tag_text.replace(",", " ").split():
            tags.append(part.lstrip("#"))
        self._db.set_file_tags(self._file_id, tags)

        col_text = self._collections.text()
        collections = [c.strip() for c in col_text.split(",") if c.strip()]
        self._db.set_file_collections(self._file_id, collections)

        self.accept()
