"""
Returns & Exchanges screen: search for an invoice, pick a line item
that hasn't already been returned, and process a return with a
refund amount/method and a restock-or-scrap decision.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.database.models import PaymentMethod
from app.services.returns_service import ReturnError, process_return
from app.services.transaction_service import get_invoice_detail, search_invoices
