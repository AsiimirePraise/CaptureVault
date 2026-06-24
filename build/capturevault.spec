# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec file for CaptureVault."""

import sys
from pathlib import Path

block_cipher = None
# SPECPATH is the build/ directory when running: pyinstaller build/capturevault.spec
project_root = Path(SPECPATH).parent

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
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="CaptureVault",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(project_root / "assets" / "icon.ico") if (project_root / "assets" / "icon.ico").exists() else None,
)
