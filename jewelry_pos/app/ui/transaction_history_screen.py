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


class TransactionHistoryScreen(QWidget):
    def __init__(self, current_user_id: int, current_user_role: UserRole, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.current_user_id = current_user_id
        self.current_user_role = current_user_role
        self._build_ui()
        self._reload_list()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        title = QLabel("Transaction History")
        title.setStyleSheet("font-size: 22px; font-weight: bold;")
        layout.addWidget(title)

        layout.addWidget(self._build_filter_row())

        splitter = QSplitter()
        splitter.addWidget(self._build_list_panel())
        splitter.addWidget(self._build_detail_panel())
        splitter.setSizes([700, 550])
        layout.addWidget(splitter, stretch=1)

    def _build_filter_row(self) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)

        self.invoice_no_input = QLineEdit()
        self.invoice_no_input.setPlaceholderText("Invoice no...")

        self.customer_input = QLineEdit()
        self.customer_input.setPlaceholderText("Customer name...")

        self.date_from_input = QDateEdit()
        self.date_from_input.setDate(QDate.currentDate().addMonths(-1))
        self.date_from_input.setCalendarPopup(True)

        self.date_to_input = QDateEdit()
        self.date_to_input.setDate(QDate.currentDate())
        self.date_to_input.setCalendarPopup(True)

        self.status_filter_combo = QComboBox()
        self.status_filter_combo.addItem("All statuses", None)
        for status in InvoiceStatus:
            self.status_filter_combo.addItem(status.value, status)

        search_button = QPushButton("Search")
        search_button.clicked.connect(self._reload_list)

        layout.addWidget(self.invoice_no_input)
        layout.addWidget(self.customer_input)
        layout.addWidget(QLabel("From:"))
        layout.addWidget(self.date_from_input)
        layout.addWidget(QLabel("To:"))
        layout.addWidget(self.date_to_input)
        layout.addWidget(self.status_filter_combo)
        layout.addWidget(search_button)

        return row
