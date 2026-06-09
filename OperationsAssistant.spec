# -*- mode: python ; coding: utf-8 -*-
# PyInstaller build recipe for the Operations Assistant.
# Produces a single self-contained Windows executable.

from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

hidden = (
    collect_submodules("sklearn")
    + collect_submodules("scipy")
    + ["waitress", "rapidfuzz", "pypdf", "docx", "openpyxl"]
)

a = Analysis(
    ["run.py"],
    pathex=[],
    binaries=[],
    datas=[("src/static", "static")],
    hiddenimports=hidden,
    hookspath=[],
    runtime_hooks=[],
    excludes=["matplotlib", "tkinter", "PyQt5", "PySide2", "IPython", "pytest"],
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
    name="OperationsAssistant",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    icon=None,
)
