"""
Transaction History screen: search/filter all invoices, view full
snapshot detail, reprint (with REPRINT watermark, audit-logged), and
(ADMIN only) cancel a same-day invoice.
"""
from __future__ import annotations

from datetime import date, timedelta

from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
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
from PySide6.QtCore import QDate

from app.database.models import AuditLog, InvoiceStatus, UserRole
from app.database.db import get_session
from app.services.settings_service import get_setting
from app.services.transaction_service import (
    TransactionError,
    cancel_invoice,
    get_invoice_detail,
    search_invoices,
)
from app.printing.receipt_pdf import ReceiptData, ReceiptLine, ReceiptPaymentLine, generate_receipt_pdf
