"""Collections view."""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from capturevault.core.thumbnails import ThumbnailService
from capturevault.database.manager import DatabaseManager
from capturevault.ui.widgets.results_grid import ResultsGrid


class CollectionsView(QWidget):
    """Manage virtual collections and browse their files."""

    collection_changed = pyqtSignal()

    def __init__(
        self,
        db: DatabaseManager,
        thumb_service: ThumbnailService,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._db = db
        self._grid = ResultsGrid(thumb_service)
        self._current_id: int | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)

        header = QHBoxLayout()
        title = QLabel("Collections")
        title.setObjectName("titleLabel")
        header.addWidget(title)
        header.addStretch()

        add_btn = QPushButton("New Collection")
        add_btn.setObjectName("primaryButton")
        add_btn.clicked.connect(self._create_collection)
        header.addWidget(add_btn)

        del_btn = QPushButton("Delete")
        del_btn.clicked.connect(self._delete_collection)
        header.addWidget(del_btn)

        layout.addLayout(header)

        splitter = QSplitter()
        self._list = QListWidget()
        self._list.setMaximumWidth(260)
        self._list.currentItemChanged.connect(self._on_collection_selected)
        splitter.addWidget(self._list)
        splitter.addWidget(self._grid)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter)

    @property
    def grid(self) -> ResultsGrid:
        return self._grid

    def refresh(self) -> None:
        self._list.clear()
        for col in self._db.get_collections():
            item = QListWidgetItem(
                f"{col['name']} ({col['file_count']})"
            )
            item.setData(256, col["id"])
            self._list.addItem(item)

        if self._list.count() > 0:
            self._list.setCurrentRow(0)
        else:
            self._grid.set_results([])

    def _on_collection_selected(self, current: QListWidgetItem, _prev) -> None:
        if not current:
            self._grid.set_results([])
            return
        col_id = current.data(256)
        self._current_id = col_id
        files = self._db.get_files_by_collection(col_id)
        for f in files:
            f["tags"] = self._db.get_file_tags(f["id"])
            f["collections"] = self._db.get_file_collections(f["id"])
        self._grid.set_results(files)

    def _create_collection(self) -> None:
        name, ok = QInputDialog.getText(
            self, "New Collection", "Collection name:"
        )
        if ok and name.strip():
            result = self._db.create_collection(name.strip())
            if result:
                self.refresh()
                self.collection_changed.emit()
            else:
                QMessageBox.warning(
                    self, "Error", "A collection with that name already exists."
                )

    def _delete_collection(self) -> None:
        item = self._list.currentItem()
        if not item:
            return
        col_id = item.data(256)
        reply = QMessageBox.question(
            self,
            "Delete Collection",
            "Remove this collection? Files will not be deleted from disk.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._db.delete_collection(col_id)
            self.refresh()
            self.collection_changed.emit()
