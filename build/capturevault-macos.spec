# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec file for CaptureVault — macOS build (.app bundle).

Run from the repo root:
    pyinstaller build/capturevault-macos.spec --noconfirm

Output: dist/CaptureVault.app
"""

from pathlib import Path

block_cipher = None
# SPECPATH is the build/ directory when running: pyinstaller build/capturevault-macos.spec
project_root = Path(SPECPATH).parent

# Keep the .dmg / bundle version in sync with version.txt
version = (project_root / "version.txt").read_text().strip()

# Optional icon: macOS uses .icns (not .ico). Falls back to no icon if absent.
icns = project_root / "assets" / "icon.icns"
icon_path = str(icns) if icns.exists() else None

a = Analysis(
    [str(project_root / "capturevault" / "main.py")],
    pathex=[str(project_root)],
    binaries=[],
    datas=[
        (str(project_root / "version.txt"), "."),
        (str(project_root / "capturevault" / "database" / "schema.sql"),
         "capturevault/database"),
    ],
    hiddenimports=[
        "PIL._tkinter_finder",
        "rapidfuzz",
        "rapidfuzz.fuzz",
        "rapidfuzz.process",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,      # binaries are gathered by COLLECT below
    name="CaptureVault",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,                  # UPX is unreliable on macOS (esp. Apple Silicon)
    console=False,              # GUI app, no terminal window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,           # builds for the runner's arch (arm64 on macos-latest)
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_path,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="CaptureVault",
)

app = BUNDLE(
    coll,
    name="CaptureVault.app",
    icon=icon_path,
    bundle_identifier="com.capturevault.app",
    version=version,
    info_plist={
        "CFBundleShortVersionString": version,
        "CFBundleVersion": version,
        "NSHighResolutionCapable": True,     # crisp on Retina displays
        "LSApplicationCategoryType": "public.app-category.photography",
    },
)
