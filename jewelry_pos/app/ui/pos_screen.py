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

    def _build_left_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)

        entry_row = QHBoxLayout()
        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText("Scan or type item code, then press Enter...")
        self.code_input.returnPressed.connect(self._handle_add_by_code)
        self.code_input.setFocus()
        entry_row.addWidget(self.code_input)
        layout.addLayout(entry_row)

        self.cart_table = QTableWidget(0, 5)
        self.cart_table.setHorizontalHeaderLabels(["Code", "Name", "Weight/Purity", "Unit Price", "Line Total"])
        self.cart_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.cart_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.cart_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.cart_table, stretch=1)

        remove_button = QPushButton("Remove Selected Line")
        remove_button.clicked.connect(self._handle_remove_selected)
        layout.addWidget(remove_button)

        return panel

    def _handle_add_by_code(self) -> None:
        code = self.code_input.text().strip()
        self.code_input.clear()
        if not code:
            return

        item_row = get_item_by_code(code)
        if item_row is None:
            QMessageBox.warning(self, "Not Found", f"No item found with code '{code}'.")
            return
        if item_row.status != ItemStatus.AVAILABLE:
            QMessageBox.warning(self, "Not Available", f"Item {code} is not available (status: {item_row.status.value}).")
            return
        if self.cart.has_item(item_row.id):
            QMessageBox.information(self, "Already in Cart", f"Item {code} is already in the cart.")
            return

        rate_row = get_latest_rate(item_row.purity)
        if rate_row is None:
            QMessageBox.warning(self, "No Rate", f"No gold rate has been entered yet for {item_row.purity.value}.")
            return

        try:
            reserve_item(item_row.id, self.current_user_id)
        except ReservationError as exc:
            QMessageBox.warning(self, "Cannot Reserve", str(exc))
            return

        fake_item = Item(
            net_weight_g=item_row.net_weight_g,
            making_charge_type=item_row.making_charge_type,
            making_charge_value=item_row.making_charge_value,
            stone_value_total=item_row.stone_value_total,
        )
        price = calculate_item_price(fake_item, rate_row.rate_per_gram)

        self.cart.add_line(CartLine(item=item_row, price=price))
        self._refresh_cart_table()
        self.code_input.setFocus()

    def _refresh_cart_table(self) -> None:
        self.cart_table.setRowCount(len(self.cart.lines))
        for i, line in enumerate(self.cart.lines):
            self.cart_table.setItem(i, 0, QTableWidgetItem(line.item.item_code))
            self.cart_table.setItem(i, 1, QTableWidgetItem(line.item.name))
            self.cart_table.setItem(i, 2, QTableWidgetItem(f"{line.item.net_weight_g}g {line.item.purity.value}"))
            self.cart_table.setItem(i, 3, QTableWidgetItem(f"Rs. {line.price.subtotal:,.2f}"))
            self.cart_table.setItem(i, 4, QTableWidgetItem(f"Rs. {line.line_total:,.2f}"))
        self._update_totals()

    def _handle_remove_selected(self) -> None:
        selected_rows = sorted({index.row() for index in self.cart_table.selectedIndexes()}, reverse=True)
        if not selected_rows:
            return
        for row_index in selected_rows:
            line = self.cart.lines[row_index]
            release_item(line.item.id)
            self.cart.remove_line(line.item.id)
        self._refresh_cart_table()

    def _build_right_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)

        layout.addWidget(self._build_customer_box())
        layout.addWidget(self._build_totals_box())
        layout.addWidget(self._build_payment_box())

        self.complete_sale_button = QPushButton("Complete Sale (F12)")
        self.complete_sale_button.setStyleSheet("font-weight: bold; padding: 12px; background-color: #2e7d32; color: white;")
        self.complete_sale_button.clicked.connect(self._handle_complete_sale)
        layout.addWidget(self.complete_sale_button)

        layout.addStretch()
        return panel

    def _build_customer_box(self) -> QWidget:
        box = QGroupBox("Customer (optional - walk-in allowed)")
        outer = QVBoxLayout(box)

        row = QHBoxLayout()
        self.customer_phone_input = QLineEdit()
        self.customer_phone_input.setPlaceholderText("Phone number")
        lookup_button = QPushButton("Lookup")
        lookup_button.clicked.connect(self._handle_customer_lookup)
        row.addWidget(self.customer_phone_input)
        row.addWidget(lookup_button)
        outer.addLayout(row)

        self.customer_label = QLabel("Walk-in customer")
        self.customer_label.setStyleSheet("color: #607d8b;")
        outer.addWidget(self.customer_label)

        return box
