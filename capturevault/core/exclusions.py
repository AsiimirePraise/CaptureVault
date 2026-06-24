"""Paths to skip while indexing — keeps scans fast and safe."""

from pathlib import Path

# Directory names to never descend into
SKIP_DIR_NAMES = frozenset(
    {
        "windows",
        "program files",
        "program files (x86)",
        "$recycle.bin",
        "system volume information",
        "node_modules",
        ".git",
        "__pycache__",
        "venv",
        ".venv",
        "winxsx",
        "installer",
        "cache2",
        "microsoft",
        "packages",
        "winsxs",
    }
)


def should_skip_dir(dir_path: Path) -> bool:
    """Return True if a directory should not be scanned."""
    name = dir_path.name.lower()
    if name in SKIP_DIR_NAMES:
        return True
    # Skip heavy AppData caches (keep Roaming/Documents reachable via user home)
    parts = [p.lower() for p in dir_path.parts]
    if "appdata" in parts:
        if "local" in parts and any(
            p in parts
            for p in ("temp", "packages", "cache", "microsoft", "google", "mozilla")
        ):
            return True
    return False
