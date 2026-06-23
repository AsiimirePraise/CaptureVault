"""Application update management via GitHub Releases."""

import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

import requests

from capturevault.config import read_version


@dataclass
class ReleaseInfo:
    version: str
    tag_name: str
    download_url: str
    release_notes: str
    published_at: str


def parse_version(version: str) -> tuple[int, ...]:
    """Parse semantic version string to comparable tuple."""
    cleaned = version.lstrip("vV").strip()
    parts = re.findall(r"\d+", cleaned)
    return tuple(int(p) for p in parts[:3]) or (0, 0, 0)


def is_newer_version(current: str, latest: str) -> bool:
    return parse_version(latest) > parse_version(current)


class UpdateManager:
    """
    Checks GitHub Releases for updates and downloads installer assets.
    Separated from main application logic per architecture requirements.
    """

    INSTALLER_NAMES = (
        "CaptureVaultSetup.exe",
        "CaptureVault-Setup.exe",
        "setup.exe",
    )

    def __init__(self, github_repo: str, current_version: str | None = None) -> None:
        self._repo = github_repo.strip().strip("/")
        self._current_version = current_version or read_version()
        self._api_url = f"https://api.github.com/repos/{self._repo}/releases/latest"

    @property
    def current_version(self) -> str:
        return self._current_version

    def check_for_updates(self, timeout: int = 10) -> ReleaseInfo | None:
        """
        Query GitHub for the latest release.
        Returns ReleaseInfo if a newer version exists, else None.
        """
        try:
            response = requests.get(
                self._api_url,
                timeout=timeout,
                headers={"Accept": "application/vnd.github+json"},
            )
            if response.status_code != 200:
                return None

            data = response.json()
            tag = data.get("tag_name", "")
            latest_version = tag.lstrip("vV")

            if not is_newer_version(self._current_version, latest_version):
                return None

            download_url = self._find_installer_url(data.get("assets", []))
            if not download_url:
                return None

            return ReleaseInfo(
                version=latest_version,
                tag_name=tag,
                download_url=download_url,
                release_notes=data.get("body", "") or "",
                published_at=data.get("published_at", "") or "",
            )
        except requests.RequestException:
            return None

    def _find_installer_url(self, assets: list) -> str | None:
        for asset in assets:
            name = asset.get("name", "")
            for pattern in self.INSTALLER_NAMES:
                if name.lower() == pattern.lower():
                    return asset.get("browser_download_url")
        # Fallback: first .exe asset
        for asset in assets:
            if asset.get("name", "").lower().endswith(".exe"):
                return asset.get("browser_download_url")
        return None

    def download_update(
        self,
        release: ReleaseInfo,
        dest_dir: Path | None = None,
        progress_callback=None,
    ) -> Path | None:
        """Download the installer to a temp directory."""
        try:
            target_dir = dest_dir or Path(tempfile.gettempdir())
            target_dir.mkdir(parents=True, exist_ok=True)
            filename = release.download_url.split("/")[-1] or "CaptureVaultSetup.exe"
            dest_path = target_dir / filename

            response = requests.get(release.download_url, stream=True, timeout=60)
            response.raise_for_status()

            total = int(response.headers.get("content-length", 0))
            downloaded = 0

            with open(dest_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if progress_callback and total:
                            progress_callback(downloaded, total)

            return dest_path
        except (requests.RequestException, OSError):
            return None

    def launch_installer(self, installer_path: Path) -> bool:
        """Launch the downloaded installer and exit the app."""
        if not installer_path.exists():
            return False
        try:
            if sys.platform == "win32":
                subprocess.Popen(
                    [str(installer_path)],
                    shell=True,
                    creationflags=subprocess.DETACHED_PROCESS,
                )
            else:
                subprocess.Popen([str(installer_path)])
            return True
        except OSError:
            return False
