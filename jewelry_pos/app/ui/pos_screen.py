"""
Point of Sale screen -- the main cashier workflow. Item entry via a
focused code input (USB scanner or manual typing), cart table with
per-line pricing, invoice-level discount/tax, mixed payments, and an
atomic Complete Sale that prints a receipt afterward.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
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
    QVBoxLayout,
    QWidget,
)

from app.database.models import Item, ItemStatus, PaymentMethod
from app.services.cart import Cart, CartLine
from app.services.customer_service import find_by_phone
from app.services.gold_rate_service import get_latest_rate
from app.services.item_service import get_item_by_code
from app.services.pricing_service import calculate_item_price
from app.services.reservation_service import ReservationError, release_item, reserve_item
from app.services.sales_service import PaymentInput, SaleError, complete_sale
from app.services.settings_service import get_setting
from app.printing.receipt_pdf import ReceiptData, ReceiptLine, ReceiptPaymentLine, generate_receipt_pdf


class POSScreen(QWidget):
    def __init__(self, current_user_id: int, cashier_name: str, on_sale_completed=None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.current_user_id = current_user_id
        self.cashier_name = cashier_name
        self.on_sale_completed = on_sale_completed
        self.cart = Cart()
        self.selected_customer = None  # CustomerRow | None
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        title = QLabel("Point of Sale")
        title.setStyleSheet("font-size: 22px; font-weight: bold;")
        layout.addWidget(title)

        splitter = QSplitter()
        splitter.addWidget(self._build_left_panel())
        splitter.addWidget(self._build_right_panel())
        splitter.setSizes([850, 450])
        layout.addWidget(splitter, stretch=1)
