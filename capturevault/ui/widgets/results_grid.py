"""Search results grid widget (Explorer-style thumbnail grid)."""

from datetime import datetime

from PyQt6.QtCore import QPoint, QSize, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QIcon, QPainter, QPixmap
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QListView,
    QListWidget,
    QListWidgetItem,
    QMenu,
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

# Role used to stash the file's database id on each item.
FILE_ID_ROLE = Qt.ItemDataRole.UserRole
# Role used to stash the item's flat index (matches ThumbnailLoader rows).
INDEX_ROLE = Qt.ItemDataRole.UserRole + 1


class ResultsGrid(QListWidget):
    """Icon grid of search results with lazy-loaded thumbnails.

    Drop-in replacement for the former table-based grid: same constructor,
    ``set_results`` method and ``metadata_requested`` / ``file_opened`` signals.
    """

    metadata_requested = pyqtSignal(int)
    file_opened = pyqtSignal(str)

    # Horizontal / vertical padding added around the thumbnail inside a tile.
    TILE_H_PAD = 24
    # Vertical room reserved under the thumbnail for two lines of text.
    TEXT_HEIGHT = 42
    # Load thumbnails a little beyond the visible area for smooth scrolling.
    PREFETCH_MARGIN = 200

    def __init__(self, thumb_service: ThumbnailService, parent=None) -> None:
        super().__init__(parent)
        self._thumb_service = thumb_service
        self._files: list[dict] = []
        self._loaded: set[int] = set()
        self._placeholder: QIcon | None = None

        self._loader = ThumbnailLoader(thumb_service, self)
        self._loader.thumbnail_ready.connect(self._on_thumbnail_ready)

        self._scroll_timer = QTimer(self)
        self._scroll_timer.setSingleShot(True)
        self._scroll_timer.setInterval(80)
        self._scroll_timer.timeout.connect(self._load_visible_thumbnails)

        self._setup_ui()

    # ------------------------------------------------------------------ setup
    def _setup_ui(self) -> None:
        self.setObjectName("resultsGrid")
        self.setViewMode(QListView.ViewMode.IconMode)
        self.setFlow(QListView.Flow.LeftToRight)
        self.setWrapping(True)
        self.setResizeMode(QListView.ResizeMode.Adjust)
        self.setMovement(QListView.Movement.Static)
        self.setUniformItemSizes(True)
        self.setWordWrap(True)
        self.setSpacing(10)

        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setVerticalScrollMode(
            QAbstractItemView.ScrollMode.ScrollPerPixel
        )

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        self.itemDoubleClicked.connect(self._on_double_click)

        self.verticalScrollBar().valueChanged.connect(
            lambda _=0: self._scroll_timer.start()
        )

        self._apply_icon_size()

    def _apply_icon_size(self) -> None:
        size = self._thumb_service.size
        self.setIconSize(QSize(size, size))
        self.setGridSize(
            QSize(size + self.TILE_H_PAD, size + self.TEXT_HEIGHT)
        )
        self._placeholder = self._build_placeholder(size)

    def _build_placeholder(self, size: int) -> QIcon:
        pix = QPixmap(size, size)
        pix.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(0, 0, 0, 18))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(0, 0, size, size, 6, 6)
        painter.end()
        return QIcon(pix)

    # ----------------------------------------------------------- public API
    def set_results(self, files: list[dict]) -> None:
        self._loader._run_id += 1
        self._loaded.clear()
        self.clear()
        self._files = files or []

        if not self._files:
            return

        # Refresh icon size in case thumbnail size changed in settings.
        self._apply_icon_size()

        for index, file_data in enumerate(self._files):
            item = QListWidgetItem(self._placeholder, self._label_for(file_data))
            item.setTextAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
            item.setToolTip(self._tooltip_for(file_data))
            item.setData(FILE_ID_ROLE, file_data["id"])
            item.setData(INDEX_ROLE, index)

            color = file_data.get("color_label")
            if color and color in COLOR_DOT:
                item.setForeground(QColor(COLOR_DOT[color]))

            self.addItem(item)

        # Load thumbnails for whatever is initially visible.
        QTimer.singleShot(0, self._load_visible_thumbnails)

    def setRowCount(self, count: int) -> None:
        """Backwards-compatibility shim for the old table API."""
        if count == 0:
            self.clear()
            self._files = []
            self._loaded.clear()

    def current_file_id(self) -> int | None:
        item = self.currentItem()
        if item is None:
            return None
        return item.data(FILE_ID_ROLE)

    # ------------------------------------------------------- thumbnail load
    def _load_visible_thumbnails(self) -> None:
        if not self._files:
            return

        viewport_rect = self.viewport().rect().adjusted(
            0, -self.PREFETCH_MARGIN, 0, self.PREFETCH_MARGIN
        )
        batch: list[tuple[int, str, str, str]] = []

        for row in range(self.count()):
            if row in self._loaded:
                continue
            item = self.item(row)
            if item is None:
                continue
            if not self.visualItemRect(item).intersects(viewport_rect):
                continue
            index = item.data(INDEX_ROLE)
            file_data = self._files[index]
            self._loaded.add(row)
            batch.append(
                (
                    row,
                    file_data["path"],
                    file_data["file_type"],
                    file_data.get("extension", ""),
                )
            )

        if batch:
            self._loader.load_batch(batch)

    def _on_thumbnail_ready(self, row: int, thumb_path: str) -> None:
        item = self.item(row)
        if item is None:
            return
        pix = QPixmap(thumb_path)
        if pix.isNull():
            return
        item.setIcon(QIcon(pix))

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        # Re-wrapping may expose new tiles; refresh after the layout settles.
        self._scroll_timer.start()

    # ------------------------------------------------------------- helpers
    @staticmethod
    def _label_for(file_data: dict) -> str:
        name = file_data.get("virtual_name") or file_data.get("file_name") or "—"
        if file_data.get("is_favorite"):
            name = f"\u2665 {name}"
        return name

    def _tooltip_for(self, file_data: dict) -> str:
        rating = file_data.get("rating", 0) or 0
        stars = "\u2605" * rating + "\u2606" * (5 - rating) if rating else "\u2014"
        lines = [
            file_data.get("virtual_name") or file_data.get("file_name", ""),
            f"Original: {file_data.get('file_name', '')}",
            f"Folder: {file_data.get('folder_name', '')}",
            f"Type: {file_data.get('file_type', '').upper()}",
            f"Modified: {self._format_date(file_data.get('date_modified', ''))}",
            f"Rating: {stars}",
        ]
        return "\n".join(line for line in lines if line)

    @staticmethod
    def _format_date(iso_str: str) -> str:
        if not iso_str:
            return "\u2014"
        try:
            dt = datetime.fromisoformat(iso_str)
            return dt.strftime("%b %d, %Y %H:%M")
        except ValueError:
            return iso_str[:16]

    def _file_for_item(self, item: QListWidgetItem | None) -> dict | None:
        if item is None:
            return None
        index = item.data(INDEX_ROLE)
        if index is None or not (0 <= index < len(self._files)):
            return None
        return self._files[index]

    # --------------------------------------------------------- interactions
    def _on_double_click(self, item: QListWidgetItem) -> None:
        file_data = self._file_for_item(item)
        if file_data and open_file(file_data["path"]):
            self.file_opened.emit(file_data["path"])

    def _show_context_menu(self, pos: QPoint) -> None:
        item = self.itemAt(pos)
        file_data = self._file_for_item(item)
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
