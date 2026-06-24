"""Paths to skip while indexing — keeps scans fast and safe."""

from pathlib import Path

# Always skip — Windows system locations
SYSTEM_SKIP_DIR_NAMES = frozenset(
    {
        "windows",
        "program files",
        "program files (x86)",
        "programdata",
        "$recycle.bin",
        "system volume information",
        "recovery",
        "winreagent",
        "perflogs",
        "boot",
        "efi",
        "msocache",
        "config.msi",
        "inetpub",
        "windowsapps",
        "winsxs",
        "winxsx",
    }
)

# Skipped when skip_dev_folders is enabled (dev caches, build output, etc.)
DEV_SKIP_DIR_NAMES = frozenset(
    {
        "node_modules",
        ".git",
        ".svn",
        ".hg",
        ".gradle",
        ".idea",
        ".vs",
        ".vscode",
        ".terraform",
        ".npm",
        ".yarn",
        ".cargo",
        ".rustup",
        "__pycache__",
        "venv",
        ".venv",
        "env",
        "site-packages",
        "bower_components",
        "vendor",
        "third_party",
        "third-party",
        "build",
        "dist",
        "target",
        "out",
        "obj",
        "bin",
        "debug",
        "release",
        "cmakefiles",
        ".next",
        ".nuxt",
        ".output",
        ".turbo",
        "coverage",
        ".pytest_cache",
        ".mypy_cache",
        ".tox",
        "Pods",
        "DerivedData",
        "gradle",
        ".android",
        "NuGet",
        "anaconda3",
        "miniconda3",
        "conda",
        ".conda",
        "pip",
        "installer",
        "cache2",
        "packages",
        "drivers",
        "driverstore",
        "npm-cache",
    }
)

DEV_SKIP_PATH_PARTS = frozenset(
    {
        "windows kits",
        "microsoft sdk",
        "microsoft sdks",
        "onedrivetemp",
        "dotnet",
    }
)


def should_skip_dir(dir_path: Path, skip_dev: bool = True) -> bool:
    """Return True if a directory should not be scanned."""
    name = dir_path.name.lower()
    if name in SYSTEM_SKIP_DIR_NAMES:
        return True
    if skip_dev:
        if name in DEV_SKIP_DIR_NAMES:
            return True
        if name.startswith(".") and name not in (".", ".."):
            return True

        parts = [p.lower() for p in dir_path.parts]
        if any(part in DEV_SKIP_PATH_PARTS for part in parts):
            return True

        # Skip heavy AppData caches (Documents/Pictures stay reachable)
        if "appdata" in parts and "local" in parts:
            if any(
                p in parts
                for p in (
                    "temp",
                    "packages",
                    "cache",
                    "microsoft",
                    "google",
                    "mozilla",
                    "npm-cache",
                    "pip",
                )
            ):
                return True
    return False
