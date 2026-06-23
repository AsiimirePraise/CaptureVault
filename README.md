# CaptureVault

**CaptureVault** is a virtual media library and file finder for photographers, videographers, content creators, and office users. Find files across multiple folders and drives instantly — without moving, renaming, or modifying your originals.

## Core Principle

CaptureVault **never** renames, moves, deletes, or modifies files on disk. All organization (virtual names, tags, notes, ratings, collections, favorites) is stored in a local SQLite database.

## Features

- **Folder monitoring** — Add multiple folders; recursive scanning of subfolders
- **Fast search** — Instant, case-insensitive, partial and fuzzy matching across names, tags, notes, and collections
- **Virtual naming** — Assign friendly names without touching original files
- **Tags, notes, ratings, color labels** — Full metadata in the database only
- **Collections** — Virtual playlists; files can belong to multiple collections
- **Favorites** — Quick access to starred files
- **Thumbnails** — Cached previews for images
- **Dashboard** — Stats and recent files at a glance
- **Background indexing** — Responsive UI while scanning tens of thousands of files
- **Auto-updates** — Optional GitHub Releases check on startup

## Requirements (Development)

- Python 3.10+
- Windows 10/11 (target platform)

## Installation (Development)

```powershell
cd CaptureVault
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
python -m capturevault
```

## Building for Distribution

### 1. Build standalone executable

```powershell
pip install -r requirements.txt
pyinstaller build/capturevault.spec --noconfirm
```

Output: `dist/CaptureVault.exe`

Users do **not** need Python installed.

### 2. Build Windows installer

Install [Inno Setup 6](https://jrsoftware.org/isinfo.php), then:

```powershell
# Update version in installer/CaptureVault.iss if needed
& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer/CaptureVault.iss
```

Output: `dist/installer/CaptureVaultSetup.exe`

The installer creates a Start Menu entry and optional desktop shortcut.

## GitHub Releases Workflow

1. Update `version.txt` with semantic version (e.g. `1.1.0`)
2. Commit and tag: `git tag v1.1.0 && git push origin v1.1.0`
3. GitHub Actions (`.github/workflows/release.yml`) builds and uploads:
   - `CaptureVault.exe`
   - `CaptureVaultSetup.exe`

### Configure update checks

In Settings or `config.json` (at `%LOCALAPPDATA%\CaptureVault\config.json`), set:

```json
{
  "github_repo": "your-org/CaptureVault"
}
```

On startup (if enabled), the app compares the installed version with the latest GitHub Release and offers to download `CaptureVaultSetup.exe`.

## Project Structure

```
CaptureVault/
├── capturevault/
│   ├── config.py           # User settings
│   ├── constants.py        # File types, labels
│   ├── database/           # SQLite schema & manager
│   ├── core/               # Indexer, search, thumbnails
│   ├── workers/            # Background threads
│   ├── updates/            # GitHub update manager
│   └── ui/                 # PyQt6 interface
├── build/capturevault.spec # PyInstaller config
├── installer/              # Inno Setup script
├── version.txt             # Semantic version
└── requirements.txt
```

## Search Tips

| Query | Result |
|-------|--------|
| `wedding` | Fuzzy match across all fields |
| `rating:5` or `5 stars` | Files with 5-star rating |
| `red` | Red color label |
| `favorites` | Favorited files |
| `photos` / `videos` | Filter by type |

## License

MIT (or your chosen license)
