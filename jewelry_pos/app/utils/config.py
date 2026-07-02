"""
Central path and constant configuration for the Jewelry POS system.

All filesystem paths used across the app (database file, backups,
assets, generated PDFs/tags) are resolved from here so that behaviour
is identical whether running from source (`python main.py`) or from
a PyInstaller-frozen executable.
"""
from __future__ import annotations

import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Base directory resolution
# ---------------------------------------------------------------------------
# When frozen by PyInstaller, sys.executable points at the .exe and bundled
# data lives under sys._MEIPASS (temp extraction dir) or next to the exe for
# writable data. We keep writable data (db, backups) NEXT TO the executable
# (or project root when running from source) rather than in Program Files,
# per the packaging requirement that the DB must live in a writable location.

if getattr(sys, "frozen", False):
    APP_ROOT = Path(sys.executable).resolve().parent
else:
    # jewelry_pos/app/utils/config.py -> jewelry_pos/
    APP_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = APP_ROOT / "data"
BACKUP_DIR = DATA_DIR / "backups"
ASSETS_DIR = APP_ROOT / "assets"
TAGS_DIR = DATA_DIR / "tags"
RECEIPTS_DIR = DATA_DIR / "receipts"
REPORTS_DIR = DATA_DIR / "reports"

DATABASE_FILE = DATA_DIR / "jewelry_pos.db"
DATABASE_URL = f"sqlite:///{DATABASE_FILE.as_posix()}"

# Ensure required directories exist on import (idempotent).
for _dir in (DATA_DIR, BACKUP_DIR, TAGS_DIR, RECEIPTS_DIR, REPORTS_DIR):
    _dir.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Application-wide constants
# ---------------------------------------------------------------------------
APP_NAME = "KaratPOS"
APP_VERSION = "0.1.0"
CURRENCY_SYMBOL = "Rs."
DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "admin123"  # must be changed on first login
MAX_BACKUPS_TO_KEEP = 30
