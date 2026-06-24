"""Search results grid widget."""

from datetime import datetime

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QAction, QPixmap
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMenu,
    QTableWidget,
    QTableWidgetItem,
    QWidget,
)

from capturevault.core.thumbnails import ThumbnailService
from capturevault.utils import copy_to_clipboard, open_containing_folder, open_file
from capturevault.workers.thumbnail_loader import ThumbnailLoader

COLOR_DOT = {
    "red": "#E53935",
    "yellow": "#FDD835",
    "green": "#43A047",
    "blue": "#1E88E5",
    "purple": "#8E24AA",
}


class ResultsGrid(QTableWidget):
    """Table displaying search results with lazy-loaded thumbnails."""

    metadata_requested = pyqtSignal(int)
    file_opened = pyqtSignal(str)

    COLUMNS = [
        ("thumbnail", "Preview", 80),
        ("virtual_name", "Virtual Name", 180),
        ("file_name", "Original Name", 160),
        ("folder_name", "Folder", 120),
        ("file_type", "Type", 70),
        ("date_modified", "Modified", 130),
        ("rating", "Rating", 80),
    ]

    MAX_THUMBS_PER_BATCH = 40
    INITIAL_ROWS = 60

    def __init__(self, thumb_service: ThumbnailService, parent=None) -> None:
        super().__init__(parent)
        self._thumb_service = thumb_service
        self._files: list[dict] = []
        self._thumb_labels: dict[int, QLabel] = {}
        self._loader = ThumbnailLoader(thumb_service, self)
        self._loader.thumbnail_ready.connect(self._on_thumbnail_ready)
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setObjectName("resultsGrid")
        self.setColumnCount(len(self.COLUMNS))
        self.setHorizontalHeaderLabels([c[1] for c in self.COLUMNS])
        self.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Interactive
        )
        self.horizontalHeader().setStretchLastSection(True)
        self.verticalHeader().setVisible(False)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.setAlternatingRowColors(True)
        self.setShowGrid(False)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        self.cellDoubleClicked.connect(self._on_double_click)
        self.cellClicked.connect(self._on_cell_clicked)

        for i, (_, _, width) in enumerate(self.COLUMNS):
            self.setColumnWidth(i, width)

    def _on_cell_clicked(self, row: int, _col: int) -> None:
        """Always highlight the full row when any cell is clicked."""
        self.selectRow(row)

    def set_results(self, files: list[dict]) -> None:
        self._loader._run_id += 1
        self._thumb_labels.clear()
        self._files = files

        if not files:
            self.setRowCount(0)
            return

        # Paint first batch immediately, defer the rest for responsiveness
        first_end = min(self.INITIAL_ROWS, len(files))
        self._fill_rows(0, first_end, start_thumbs=True)

        if len(files) > first_end:
            QTimer.singleShot(
                0,
                lambda: self._fill_rows(
                    first_end, len(files), start_thumbs=False
                ),
            )

    def _fill_rows(
        self,
        start: int,
        end: int,
        start_thumbs: bool = True,
    ) -> None:
        self.setUpdatesEnabled(False)
        try:
            if start == 0:
                self.setRowCount(len(self._files))

            thumb_size = self._thumb_service.size
            thumb_batch: list[tuple[int, str, str, str]] = []

            for row in range(start, end):
                file_data = self._files[row]
                self.setRowHeight(row, max(thumb_size + 16, 72))

                if row not in self._thumb_labels:
                    label = QLabel("…")
                    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    label.setFixedSize(thumb_size, thumb_size)
                    label.setFocusPolicy(Qt.FocusPolicy.NoFocus)
                    container = QWidget()
                    container.setFocusPolicy(Qt.FocusPolicy.NoFocus)
                    lay = QHBoxLayout(container)
                    lay.setContentsMargins(4, 4, 4, 4)
                    lay.addWidget(label)

                    color = file_data.get("color_label")
                    if color and color in COLOR_DOT:
                        dot = QLabel("●")
                        dot.setFocusPolicy(Qt.FocusPolicy.NoFocus)
                        dot.setStyleSheet(
                            f"color: {COLOR_DOT[color]}; font-size: 14px;"
                        )
                        lay.addWidget(dot)

                    thumb_item = QTableWidgetItem()
                    thumb_item.setFlags(
                        Qt.ItemFlag.ItemIsEnabled
                        | Qt.ItemFlag.ItemIsSelectable
                    )
                    self.setItem(row, 0, thumb_item)
                    self.setCellWidget(row, 0, container)
                    self._thumb_labels[row] = label

                if start_thumbs and row < self.MAX_THUMBS_PER_BATCH:
                    thumb_batch.append(
                        (
                            row,
                            file_data["path"],
                            file_data["file_type"],
                            file_data.get("extension", ""),
                        )
                    )

                virtual = file_data.get("virtual_name") or "—"
                self._set_item(
                    row, 1, virtual, bold=bool(file_data.get("virtual_name"))
                )
                self._set_item(row, 2, file_data.get("file_name", ""))
                self._set_item(row, 3, file_data.get("folder_name", ""))
                self._set_item(row, 4, file_data.get("file_type", "").upper())
                self._set_item(
                    row, 5, self._format_date(file_data.get("date_modified", ""))
                )

                rating = file_data.get("rating", 0) or 0
                stars = "★" * rating + "☆" * (5 - rating) if rating else "—"
                fav = " ♥" if file_data.get("is_favorite") else ""
                self._set_item(row, 6, stars + fav)

                for col in range(self.columnCount()):
                    item = self.item(row, col)
                    if item:
                        item.setData(Qt.ItemDataRole.UserRole, file_data["id"])
        finally:
            self.setUpdatesEnabled(True)

        if start_thumbs and thumb_batch:
            self._loader.load_batch(thumb_batch)

    def _on_thumbnail_ready(self, row: int, thumb_path: str) -> None:
        label = self._thumb_labels.get(row)
        if not label:
            return
        pix = QPixmap(thumb_path)
        if pix.isNull():
            return
        size = self._thumb_service.size
        label.setPixmap(
            pix.scaled(
                size,
                size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        label.setText("")

    def _set_item(self, row: int, col: int, text: str, bold: bool = False) -> None:
        item = QTableWidgetItem(text)
        item.setFlags(
            Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        )
        if bold:
            font = item.font()
            font.setBold(True)
            item.setFont(font)
        self.setItem(row, col, item)

    @staticmethod
    def _format_date(iso_str: str) -> str:
        if not iso_str:
            return "—"
        try:
            dt = datetime.fromisoformat(iso_str)
            return dt.strftime("%b %d, %Y %H:%M")
        except ValueError:
            return iso_str[:16]

    def _get_file_at_row(self, row: int) -> dict | None:
        if 0 <= row < len(self._files):
            return self._files[row]
        return None

    def _on_double_click(self, row: int, _col: int) -> None:
        file_data = self._get_file_at_row(row)
        if file_data and open_file(file_data["path"]):
            self.file_opened.emit(file_data["path"])

    def _show_context_menu(self, pos) -> None:
        row = self.rowAt(pos.y())
        file_data = self._get_file_at_row(row)
        if not file_data:
            return

        menu = QMenu(self)
        menu.addAction("Open File", lambda: open_file(file_data["path"]))
        menu.addAction(
            "Open Containing Folder",
            lambda: open_containing_folder(file_data["path"]),
        )
        menu.addAction(
            "Copy Path", lambda: copy_to_clipboard(file_data["path"])
        )
        menu.addSeparator()
        menu.addAction(
            "Edit Metadata",
            lambda: self.metadata_requested.emit(file_data["id"]),
        )
        menu.exec(self.mapToGlobal(pos))

    def current_file_id(self) -> int | None:
        row = self.currentRow()
        file_data = self._get_file_at_row(row)
        return file_data["id"] if file_data else None
