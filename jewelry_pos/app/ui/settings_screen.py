"""
Settings screen (ADMIN only): shop details, tax %, discount-approval
threshold, old-gold margin, low-stock thresholds per category,
thermal printer config, block-sale-without-todays-rate toggle, and a
manual "Backup Now" button.
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.services.backup_service import list_backups, run_backup_now
from app.services.settings_service import get_bool_setting, get_setting, set_bool_setting, set_setting
