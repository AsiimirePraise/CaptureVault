"""Main application window."""

from PyQt6.QtCore import QThread, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from capturevault.config import AppConfig
from capturevault.core.thumbnails import ThumbnailService
from capturevault.database.manager import DatabaseManager
from capturevault.ui.dialogs.metadata_dialog import MetadataDialog
from capturevault.ui.dialogs.settings_dialog import SettingsDialog
from capturevault.ui.dialogs.setup_wizard import SetupWizard
from capturevault.ui.dialogs.update_dialog import UpdateDialog
from capturevault.ui.styles import get_stylesheet
from capturevault.ui.views.collections_view import CollectionsView
from capturevault.ui.views.dashboard import DashboardView
from capturevault.ui.views.favorites_view import FavoritesView
from capturevault.ui.views.search_view import SearchView
from capturevault.ui.widgets.search_bar import SearchBar
from capturevault.ui.widgets.sidebar import Sidebar
from capturevault.updates.update_manager import UpdateManager
from capturevault.workers.indexer_worker import IndexerWorker
from capturevault.workers.search_worker import SearchWorker


class UpdateCheckWorker(QThread):
    update_found = pyqtSignal(object)

    def __init__(self, manager: UpdateManager, parent=None):
        super().__init__(parent)
        self._manager = manager

    def run(self) -> None:
        release = self._manager.check_for_updates()
        if release:
            self.update_found.emit(release)


class MainWindow(QMainWindow):
    """CaptureVault main window."""

    def __init__(self, config: AppConfig) -> None:
        super().__init__()
        self._config = config
        self._db = DatabaseManager(config.db_path)
        self._thumb_service = ThumbnailService(
            config.thumbnail_cache_dir,
            config.thumbnail_size,
        )
        self._indexer: IndexerWorker | None = None
        self._search_worker: SearchWorker | None = None
        self._update_worker: UpdateCheckWorker | None = None
        self._search_generation = 0

        self.setWindowTitle("CaptureVault")
        self.setMinimumSize(1100, 700)
        self.resize(1280, 800)

        self._apply_theme()
        self._setup_ui()
        self._connect_signals()

        if not config.first_run_complete or not self._db.has_monitored_folders():
            self._show_setup_wizard()
        else:
            self._start_initial_index()

        if config.check_updates_on_startup:
            QTimer.singleShot(2000, self._check_updates)

    def _apply_theme(self) -> None:
        self.setStyleSheet(get_stylesheet(self._config.theme))

    def _setup_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._sidebar = Sidebar()
        root.addWidget(self._sidebar)

        right = QVBoxLayout()
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(0)

        # Top bar with search and scan buttons
        top_bar = QHBoxLayout()
        self._search_bar = SearchBar()
        top_bar.addWidget(self._search_bar, stretch=1)

        self._scan_btn = QPushButton("Quick Scan")
        self._scan_btn.clicked.connect(lambda: self._start_scan(full=False))
        top_bar.addWidget(self._scan_btn)

        self._rescan_btn = QPushButton("Full Rescan")
        self._rescan_btn.clicked.connect(lambda: self._start_scan(full=True))
        top_bar.addWidget(self._rescan_btn)

        top_widget = QWidget()
        top_widget.setLayout(top_bar)
        right.addWidget(top_widget)

        self._stack = QStackedWidget()
        self._dashboard = DashboardView(self._db)
        self._search_view = SearchView(self._thumb_service)
        self._favorites = FavoritesView(self._db, self._thumb_service)
        self._collections = CollectionsView(self._db, self._thumb_service)
        self._settings_placeholder = self._create_settings_placeholder()

        self._stack.addWidget(self._dashboard)
        self._stack.addWidget(self._search_view)
        self._stack.addWidget(self._favorites)
        self._stack.addWidget(self._collections)
        self._stack.addWidget(self._settings_placeholder)

        right.addWidget(self._stack, stretch=1)
        root.addLayout(right, stretch=1)

        # Status bar
        status = QStatusBar()
        self.setStatusBar(status)
        self._status_label = QLabel("Ready")
        status.addWidget(self._status_label)
        self._progress = QProgressBar()
        self._progress.setMaximumWidth(200)
        self._progress.setVisible(False)
        status.addPermanentWidget(self._progress)

    def _create_settings_placeholder(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(24, 24, 24, 24)
        title = QLabel("Settings")
        title.setObjectName("titleLabel")
        layout.addWidget(title)
        btn = QPushButton("Open Settings...")
        btn.setObjectName("primaryButton")
        btn.clicked.connect(self._open_settings)
        layout.addWidget(btn)
        layout.addStretch()
        return w

    def _connect_signals(self) -> None:
        self._sidebar.navigation_changed.connect(self._on_navigate)
        self._search_bar.search_requested.connect(self._run_search)
        self._search_bar.clear_requested.connect(lambda: self._run_search(""))

        for grid in (
            self._search_view.grid,
            self._favorites.grid,
            self._collections.grid,
        ):
            grid.metadata_requested.connect(self._edit_metadata)

    def _on_navigate(self, key: str) -> None:
        nav_map = {
            "dashboard": 0,
            "search": 1,
            "favorites": 2,
            "collections": 3,
            "settings": 4,
        }
        if key == "settings":
            self._open_settings()
            return

        idx = nav_map.get(key, 1)
        self._stack.setCurrentIndex(idx)

        if key == "dashboard":
            self._dashboard.refresh()
        elif key == "favorites":
            self._favorites.refresh()
        elif key == "collections":
            self._collections.refresh()
        elif key == "search":
            self._search_bar.focus_input()
            self._run_search(self._search_bar.query())

    def _show_setup_wizard(self) -> None:
        wizard = SetupWizard(self._db, self)
        if wizard.exec():
            self._config.first_run_complete = True
            self._start_scan(full=True)
        else:
            if not self._db.has_monitored_folders():
                QMessageBox.warning(
                    self,
                    "Setup Required",
                    "Please add at least one folder to use CaptureVault.",
                )
                self._show_setup_wizard()

    def _start_initial_index(self) -> None:
        self._start_scan(full=True)

    def _start_scan(self, full: bool = True) -> None:
        if self._indexer and self._indexer.isRunning():
            return

        folders = [f["path"] for f in self._db.get_monitored_folders()]
        if not folders:
            self._status_label.setText("No folders configured")
            return

        self._scan_btn.setEnabled(False)
        self._rescan_btn.setEnabled(False)
        self._progress.setVisible(True)
        self._progress.setRange(0, 0)
        label = "Full rescan" if full else "Quick scan"
        self._status_label.setText(f"{label} in progress...")

        self._indexer = IndexerWorker(
            self._config.db_path, folders, full_scan=full, parent=self
        )
        self._indexer.progress.connect(self._on_index_progress)
        self._indexer.finished_scan.connect(self._on_index_finished)
        self._indexer.error.connect(self._on_index_error)
        self._indexer.start()

    def _on_index_progress(self, file_path: str, count: int) -> None:
        name = file_path.split("\\")[-1].split("/")[-1]
        self._status_label.setText(f"Indexing: {name} ({count:,})")

    def _on_index_finished(self, indexed: int, removed: int, skipped: int) -> None:
        self._scan_btn.setEnabled(True)
        self._rescan_btn.setEnabled(True)
        self._progress.setVisible(False)
        msg = f"Indexed {indexed:,} files"
        if removed:
            msg += f", removed {removed:,}"
        self._status_label.setText(msg)
        self._dashboard.refresh()
        self._run_search(self._search_bar.query())

    def _on_index_error(self, message: str) -> None:
        self._scan_btn.setEnabled(True)
        self._rescan_btn.setEnabled(True)
        self._progress.setVisible(False)
        self._status_label.setText("Indexing error")
        QMessageBox.critical(self, "Indexing Error", message)

    def _run_search(self, query: str) -> None:
        self._search_generation += 1
        generation = self._search_generation

        self._sidebar.select("search")
        self._stack.setCurrentIndex(1)

        self._search_worker = SearchWorker(
            self._config.db_path,
            query,
            generation,
            parent=self,
        )
        self._search_worker.results_ready.connect(self._on_search_results)
        self._search_worker.start()

    def _on_search_results(self, generation: int, results: list) -> None:
        if generation != self._search_generation:
            return
        self._search_view.set_results(results)
        self._status_label.setText(f"{len(results):,} results")

    def _edit_metadata(self, file_id: int) -> None:
        dialog = MetadataDialog(self._db, file_id, self)
        if dialog.exec():
            self._run_search(self._search_bar.query())
            self._dashboard.refresh()

    def _open_settings(self) -> None:
        dialog = SettingsDialog(self._config, self._db, self)
        if dialog.exec():
            self._apply_theme()
            self._thumb_service.size = self._config.thumbnail_size
            self._dashboard.refresh()

    def _check_updates(self) -> None:
        manager = UpdateManager(self._config.github_repo, self._config.version)
        self._update_worker = UpdateCheckWorker(manager, self)
        self._update_worker.update_found.connect(self._show_update_dialog)
        self._update_worker.start()

    def _show_update_dialog(self, release) -> None:
        manager = UpdateManager(self._config.github_repo, self._config.version)
        dialog = UpdateDialog(release, manager, self)
        dialog.exec()

    def closeEvent(self, event) -> None:
        if self._indexer and self._indexer.isRunning():
            self._indexer.cancel()
            self._indexer.wait(3000)
        self._db.close()
        super().closeEvent(event)
