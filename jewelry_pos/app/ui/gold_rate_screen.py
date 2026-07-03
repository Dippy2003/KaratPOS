"""
Gold Rate Management screen (ADMIN only). Lets the admin enter today's
rate per purity and view the full append-only rate history.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.database.models import Purity
from app.services.gold_rate_service import DuplicateRateError, add_rate, get_rate_history
