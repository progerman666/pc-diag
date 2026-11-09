# -*- mode: python ; coding: utf-8 -*-
# Сборка pc-diag: два exe в одной папке (GUI + консольный) и общий _internal.
import os
from pathlib import Path

# Путь к smartctl можно переопределить через SMARTCTL_PATH — нужно в CI,
# где smartmontools ставится в другое место. Если файла нет, сборка
# продолжится без него (SMART-детали просто останутся пустыми).
SMARTCTL = os.environ.get(
    'SMARTCTL_PATH', 'C:/Program Files/smartmontools/bin/smartctl.exe',
)
BINARIES = [(SMARTCTL, 'smartctl')] if Path(SMARTCTL).is_file() else []

COMMON = dict(
    pathex=[],
    binaries=BINARIES,
    datas=[('assets', 'assets')],
    hiddenimports=[
        'psutil', 'requests', 'dotenv', 'anthropic', 'customtkinter',
        'diag.fixer', 'diag.llm',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

# ── GUI (для обычных людей) ──────────────────────────────────────
a_gui = Analysis(['run_gui.py'], **COMMON)
pyz_gui = PYZ(a_gui.pure)

exe_gui = EXE(
    pyz_gui,
    a_gui.scripts,
    [],
    exclude_binaries=True,
    name='pc-diag',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['assets/icon.ico'],
    version='version_info.txt',
)

# ── CLI (для тех, кто хочет текст/--json) ────────────────────────
a_cli = Analysis(['run_diag.py'], **COMMON)
pyz_cli = PYZ(a_cli.pure)

exe_cli = EXE(
    pyz_cli,
    a_cli.scripts,
    [],
    exclude_binaries=True,
    name='pc-diag-cli',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['assets/icon.ico'],
    version='version_info.txt',
)

coll = COLLECT(
    exe_gui,
    exe_cli,
    a_gui.binaries,
    a_gui.datas,
    a_cli.binaries,
    a_cli.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='pc-diag',
)
