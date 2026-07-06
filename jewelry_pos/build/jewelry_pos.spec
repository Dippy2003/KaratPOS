# PyInstaller spec for KaratPOS -- one-folder build.
#
# Build with (from the jewelry_pos/ directory, inside the venv):
#   pyinstaller build/jewelry_pos.spec --distpath dist --workpath build/work
#
# Produces dist/KaratPOS/KaratPOS.exe plus all its dependencies in the
# same folder. The database and backups are NOT bundled -- they are
# created next to the .exe on first run (see app/utils/config.py,
# which resolves paths relative to sys.executable when frozen).

import sys
from pathlib import Path

block_cipher = None

PROJECT_ROOT = Path(SPECPATH).parent  # jewelry_pos/

# pyzbar and opencv ship native DLLs that PyInstaller's default hooks
# sometimes miss on Windows; collect them explicitly to avoid a
# "DLL load failed" crash on a machine without the dev environment.
from PyInstaller.utils.hooks import collect_dynamic_libs

binaries = []
binaries += collect_dynamic_libs("pyzbar")
binaries += collect_dynamic_libs("cv2")

datas = [
    (str(PROJECT_ROOT / "app" / "scanning" / "static"), "app/scanning/static"),
    (str(PROJECT_ROOT / "assets"), "assets"),
]

a = Analysis(
    [str(PROJECT_ROOT / "main.py")],
    pathex=[str(PROJECT_ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=[
        "pyzbar.pyzbar",
        "cv2",
        "escpos.printer",
        "reportlab.graphics.barcode",
    ],
    hookspath=[],
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
    exclude_binaries=True,
    name="KaratPOS",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # no console window -- this is a desktop GUI app
    icon=str(PROJECT_ROOT / "assets" / "icon.ico") if (PROJECT_ROOT / "assets" / "icon.ico").exists() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    name="KaratPOS",
)
