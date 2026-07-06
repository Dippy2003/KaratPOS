"""
Database backups: copies the live SQLite file to data/backups/ with a
date-stamped name, keeping only the most recent MAX_BACKUPS_TO_KEEP.
Runs automatically once per day on first launch (tracked via a
settings key so restarting the app the same day doesn't re-backup).
"""
from __future__ import annotations

import shutil
from datetime import date
from pathlib import Path

from app.services.settings_service import get_setting, set_setting
from app.utils.config import BACKUP_DIR, DATABASE_FILE, MAX_BACKUPS_TO_KEEP

LAST_BACKUP_SETTING_KEY = "last_backup_date"


def _backup_filename(for_date: date) -> str:
    return f"jewelry_pos_{for_date.isoformat()}.db"


def run_backup_now() -> str:
    """Copy the live DB file to data/backups/, prune old backups, return the new backup's path."""
    if not DATABASE_FILE.exists():
        raise FileNotFoundError(f"Database file not found at {DATABASE_FILE}")

    backup_path = BACKUP_DIR / _backup_filename(date.today())
    shutil.copy2(DATABASE_FILE, backup_path)
    _prune_old_backups()
    set_setting(LAST_BACKUP_SETTING_KEY, date.today().isoformat())
    return str(backup_path)


def _prune_old_backups() -> None:
    backups = sorted(BACKUP_DIR.glob("jewelry_pos_*.db"), key=lambda p: p.stat().st_mtime, reverse=True)
    for old_backup in backups[MAX_BACKUPS_TO_KEEP:]:
        old_backup.unlink(missing_ok=True)


def run_daily_backup_if_needed() -> str | None:
    """Called on every startup; backs up once per calendar day. Returns the backup path if one was made."""
    last_backup = get_setting(LAST_BACKUP_SETTING_KEY)
    if last_backup == date.today().isoformat():
        return None
    return run_backup_now()


def list_backups() -> list[Path]:
    return sorted(BACKUP_DIR.glob("jewelry_pos_*.db"), key=lambda p: p.stat().st_mtime, reverse=True)
