"""Application configuration management."""

import json
import sys
from pathlib import Path

from capturevault.constants import (
    DEFAULT_GITHUB_REPO,
    DEFAULT_SEARCH_FILTER,
    DEFAULT_THUMBNAIL_SIZE,
    GENERAL_SEARCH_FILTER,
    THEME_LIGHT,
)


def _app_data_dir() -> Path:
    """Return per-user application data directory."""
    if sys.platform == "win32":
        base = Path.home() / "AppData" / "Local" / "CaptureVault"
    else:
        base = Path.home() / ".capturevault"
    base.mkdir(parents=True, exist_ok=True)
    return base


def _bundled_version_path() -> Path:
    """Locate version file in dev or frozen bundle."""
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "version.txt"  # type: ignore[attr-defined]
    return Path(__file__).resolve().parent.parent / "version.txt"


def read_version() -> str:
    """Read semantic version from version.txt."""
    path = _bundled_version_path()
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    return "1.0.0"


class AppConfig:
    """Persistent user settings stored as JSON."""

    DEFAULTS = {
        "first_run_complete": False,
        "theme": THEME_LIGHT,
        "thumbnail_size": DEFAULT_THUMBNAIL_SIZE,
        "check_updates_on_startup": True,
        "github_repo": DEFAULT_GITHUB_REPO,
        "window_geometry": None,
        "last_update_reminder": None,
        "photographer_mode": True,
        "default_search_filter": DEFAULT_SEARCH_FILTER,
        "skip_dev_folders": True,
    }

    def __init__(self) -> None:
        self._data_dir = _app_data_dir()
        self._config_path = self._data_dir / "config.json"
        self._db_path = self._data_dir / "capturevault.db"
        self._thumb_cache_dir = self._data_dir / "thumbnails"
        self._thumb_cache_dir.mkdir(parents=True, exist_ok=True)
        self._settings: dict = {}
        self.load()

    @property
    def data_dir(self) -> Path:
        return self._data_dir

    @property
    def db_path(self) -> Path:
        return self._db_path

    @property
    def thumbnail_cache_dir(self) -> Path:
        return self._thumb_cache_dir

    @property
    def version(self) -> str:
        return read_version()

    def load(self) -> None:
        if self._config_path.exists():
            try:
                self._settings = json.loads(
                    self._config_path.read_text(encoding="utf-8")
                )
            except (json.JSONDecodeError, OSError):
                self._settings = {}
        else:
            self._settings = {}
        for key, value in self.DEFAULTS.items():
            self._settings.setdefault(key, value)

    def save(self) -> None:
        self._config_path.write_text(
            json.dumps(self._settings, indent=2),
            encoding="utf-8",
        )

    def get(self, key: str, default=None):
        return self._settings.get(key, default)

    def set(self, key: str, value) -> None:
        self._settings[key] = value
        self.save()

    @property
    def first_run_complete(self) -> bool:
        return bool(self.get("first_run_complete"))

    @first_run_complete.setter
    def first_run_complete(self, value: bool) -> None:
        self.set("first_run_complete", value)

    @property
    def theme(self) -> str:
        return self.get("theme", THEME_LIGHT)

    @theme.setter
    def theme(self, value: str) -> None:
        self.set("theme", value)

    @property
    def thumbnail_size(self) -> int:
        return int(self.get("thumbnail_size", DEFAULT_THUMBNAIL_SIZE))

    @thumbnail_size.setter
    def thumbnail_size(self, value: int) -> None:
        self.set("thumbnail_size", value)

    @property
    def check_updates_on_startup(self) -> bool:
        return bool(self.get("check_updates_on_startup", True))

    @check_updates_on_startup.setter
    def check_updates_on_startup(self, value: bool) -> None:
        self.set("check_updates_on_startup", value)

    @property
    def github_repo(self) -> str:
        return self.get("github_repo", DEFAULT_GITHUB_REPO)

    @github_repo.setter
    def github_repo(self, value: str) -> None:
        self.set("github_repo", value)

    @property
    def photographer_mode(self) -> bool:
        return bool(self.get("photographer_mode", True))

    @photographer_mode.setter
    def photographer_mode(self, value: bool) -> None:
        self.set("photographer_mode", value)
        if value:
            self.default_search_filter = DEFAULT_SEARCH_FILTER
        else:
            self.default_search_filter = GENERAL_SEARCH_FILTER

    @property
    def default_search_filter(self) -> str:
        return self.get("default_search_filter", DEFAULT_SEARCH_FILTER)

    @default_search_filter.setter
    def default_search_filter(self, value: str) -> None:
        self.set("default_search_filter", value)

    @property
    def skip_dev_folders(self) -> bool:
        return bool(self.get("skip_dev_folders", True))

    @skip_dev_folders.setter
    def skip_dev_folders(self, value: bool) -> None:
        self.set("skip_dev_folders", value)
