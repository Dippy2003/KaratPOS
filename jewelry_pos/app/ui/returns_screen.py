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


class ReturnsScreen(QWidget):
    def __init__(self, current_user_id: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.current_user_id = current_user_id
        self.current_invoice_detail = None
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        title = QLabel("Returns & Exchanges")
        title.setStyleSheet("font-size: 22px; font-weight: bold;")
        layout.addWidget(title)

        search_row = QHBoxLayout()
        self.invoice_no_input = QLineEdit()
        self.invoice_no_input.setPlaceholderText("Invoice number...")
        search_button = QPushButton("Find Invoice")
        search_button.clicked.connect(self._handle_find_invoice)
        search_row.addWidget(self.invoice_no_input)
        search_row.addWidget(search_button)
        layout.addLayout(search_row)

        splitter = QSplitter()
        splitter.addWidget(self._build_lines_panel())
        splitter.addWidget(self._build_return_form())
        splitter.setSizes([700, 450])
        layout.addWidget(splitter, stretch=1)
