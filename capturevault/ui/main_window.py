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
from capturevault.core.search import SearchEngine
from capturevault.core.thumbnails import ThumbnailService
from capturevault.database.manager import DatabaseManager
from capturevault.ui.dialogs.metadata_dialog import MetadataDialog
from capturevault.core.autodiscover import ensure_laptop_coverage
from capturevault.ui.dialogs.welcome_dialog import WelcomeDialog
from capturevault.ui.dialogs.settings_dialog import SettingsDialog
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

        self.setWindowTitle(f"CaptureVault v{config.version}")
        self.setMinimumSize(1100, 700)
        self.resize(1280, 800)

        self._apply_theme()
        self._setup_ui()
        self._connect_signals()
        self._refresh_folder_filters()
        self._bootstrap_automation()

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
        self._search_bar = SearchBar(default_type_filter=config.default_search_filter)
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
        self._search_bar.search_triggered.connect(self._run_search)

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
            self._refresh_folder_filters()
            self._search_bar.focus_input()
            self._run_search()

    def _refresh_folder_filters(self) -> None:
        folders = [f["path"] for f in self._db.get_monitored_folders()]
        self._search_bar.set_folder_choices(folders)

    def _bootstrap_automation(self) -> None:
        """Auto-discover folders, open search immediately, index in background."""
        added = ensure_laptop_coverage(self._db)

        first_launch = not self._config.first_run_complete
        if first_launch:
            self._config.first_run_complete = True
            folder_count = len(self._db.get_monitored_folders())
            QTimer.singleShot(
                400,
                lambda: WelcomeDialog(
                    folder_count,
                    photographer_mode=self._config.photographer_mode,
                    parent=self,
                ).exec(),
            )

        self._sidebar.select("search")
        self._stack.setCurrentIndex(1)
        self._search_bar.focus_input()
        self._run_search()

        if added:
            self._status_label.setText(
                f"Indexing your laptop ({len(added)} location(s))..."
            )
            self._start_scan(full=True)
        else:
            self._start_initial_index()

    def _start_initial_index(self) -> None:
        """Quick scan on normal startup; full scan only when library is empty."""
        stats = self._db.get_dashboard_stats()
        self._start_scan(full=stats["total_files"] == 0)

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
            self._config.db_path,
            folders,
            full_scan=full,
            photos_only=self._config.photographer_mode,
            skip_dev_folders=self._config.skip_dev_folders,
            parent=self,
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
        self._refresh_folder_filters()
        SearchEngine.clear_cache()
        self._run_search()

    def _on_index_error(self, message: str) -> None:
        self._scan_btn.setEnabled(True)
        self._rescan_btn.setEnabled(True)
        self._progress.setVisible(False)
        self._status_label.setText("Indexing error")
        QMessageBox.critical(self, "Indexing Error", message)

    def _run_search(self) -> None:
        self._search_generation += 1
        generation = self._search_generation
        query = self._search_bar.query()
        filters = self._search_bar.get_filters()

        self._sidebar.select("search")
        self._stack.setCurrentIndex(1)

        self._search_worker = SearchWorker(
            self._config.db_path,
            query,
            generation,
            filters=filters,
            parent=self,
        )
        self._search_worker.results_ready.connect(self._on_search_results)
        self._search_worker.start()

    def _on_search_results(self, generation: int, results: list) -> None:
        if generation != self._search_generation:
            return

        query = self._search_bar.query().strip()
        filters = self._search_bar.get_filters()
        total = self._db.get_dashboard_stats()["total_files"]
        scope = f"{filters.type_label()} · {filters.folder_label()}"

        if not results and query:
            empty_msg = (
                f'No matches for "{query}" ({filters.type_label()}, '
                f'{filters.folder_label()}).\n'
                "The file may not be indexed yet — wait for scanning to finish,\n"
                "try Word (.doc/.docx) filter, or click Full Rescan."
            )
        elif not results and total == 0:
            empty_msg = (
                "Still indexing your files — search again in a moment,\n"
                "or click Full Rescan in the toolbar."
            )
        elif not results:
            empty_msg = (
                f"{total:,} files indexed.\n"
                "Type any part of a file name — exact names not required."
            )
        else:
            empty_msg = ""

        self._search_view.set_results(results, empty_msg)

        if results:
            self._status_label.setText(
                f"{len(results):,} results · {scope}"
            )
        elif query:
            self._status_label.setText(
                f'No matches for "{query}" · {scope}'
            )
        elif total == 0:
            self._status_label.setText("Indexing in progress...")
        else:
            self._status_label.setText(f"{total:,} files · {scope}")

    def _edit_metadata(self, file_id: int) -> None:
        dialog = MetadataDialog(self._db, file_id, self)
        if dialog.exec():
            self._run_search()
            self._dashboard.refresh()

    def _open_settings(self) -> None:
        prev_photographer = self._config.photographer_mode
        prev_skip_dev = self._config.skip_dev_folders
        dialog = SettingsDialog(self._config, self._db, self)
        if dialog.exec():
            self._apply_theme()
            self._thumb_service.size = self._config.thumbnail_size
            self._search_bar.set_default_type_filter(
                dialog.default_search_filter_changed
            )
            self._refresh_folder_filters()
            self._dashboard.refresh()
            self._run_search()

            mode_changed = (
                prev_photographer != dialog.photographer_mode_changed
                or prev_skip_dev != dialog.skip_dev_folders_changed
            )
            if mode_changed:
                reply = QMessageBox.question(
                    self,
                    "Rescan Recommended",
                    "Library mode changed. Run a full rescan now to update "
                    "which files are indexed?",
                    QMessageBox.StandardButton.Yes
                    | QMessageBox.StandardButton.No,
                )
                if reply == QMessageBox.StandardButton.Yes:
                    self._start_scan(full=True)

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
