# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller build spec for the MyPhoto Windows executable.

Build with:  pyinstaller myphoto.spec
Output:      dist/MyPhoto/MyPhoto.exe (Windows) or dist/MyPhoto/MyPhoto (other OSes)
"""

from pathlib import Path

block_cipher = None

project_root = Path(SPECPATH)

a = Analysis(
    [str(project_root / "src" / "myphoto" / "app.py")],
    pathex=[str(project_root / "src")],
    binaries=[],
    datas=[
        (str(project_root / "presets"), "presets"),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="MyPhoto",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="MyPhoto",
)
