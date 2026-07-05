"""Repair job intake, status management, and printable ticket generation."""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QFormLayout,
    QGroupBox,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import QDate

from app.database.models import RepairStatus
from app.services.customer_service import find_by_phone
from app.services.repair_service import ValidationError, create_repair, get_all_repairs, update_repair_status
from app.printing.repair_ticket import RepairTicketData, generate_repair_ticket_pdf
