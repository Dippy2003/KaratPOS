"""
Point of Sale screen -- the main cashier workflow. Item entry via a
focused code input (USB scanner or manual typing), cart table with
per-line pricing, invoice-level discount/tax, mixed payments, and an
atomic Complete Sale that prints a receipt afterward.
"""
from __future__ import annotations

from datetime import datetime
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
from app.services.gold_rate_service import get_latest_rate, has_todays_rate_for_all_purities
from app.services.item_service import get_item_by_code
from app.services.pricing_service import calculate_item_price
from app.services.reservation_service import ReservationError, release_item, reserve_item
from app.services.sales_service import OldGoldExchangeInput, PaymentInput, SaleError, complete_sale
from app.services.settings_service import get_bool_setting, get_setting
from app.printing.receipt_pdf import ReceiptData, ReceiptLine, ReceiptPaymentLine, generate_receipt_pdf
from app.ui.old_gold_dialog import OldGoldDialog
from app.ui.webcam_scan_dialog import WebcamScanDialog
from app.utils.qt_helpers import combo_enum_data


class POSScreen(QWidget):
    def __init__(self, current_user_id: int, cashier_name: str, on_sale_completed=None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.current_user_id = current_user_id
        self.cashier_name = cashier_name
        self.on_sale_completed = on_sale_completed
        self.cart = Cart()
        self.selected_customer = None  # CustomerRow | None
        self.old_gold_input: OldGoldExchangeInput | None = None
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

        scan_button = QPushButton("Scan with Webcam")
        scan_button.clicked.connect(self._handle_open_webcam_scan)
        entry_row.addWidget(scan_button)

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

    def _handle_add_by_code(self, code: str | None = None) -> None:
        if code is None:
            code = self.code_input.text().strip()
            self.code_input.clear()
        else:
            code = code.strip()
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

    def _handle_open_webcam_scan(self) -> None:
        dialog = WebcamScanDialog(self)
        dialog.code_scanned.connect(self._handle_add_by_code)
        dialog.exec()

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

    def _build_totals_box(self) -> QWidget:
        box = QGroupBox("Totals")
        layout = QVBoxLayout(box)

        self.subtotal_label = QLabel("Subtotal: Rs. 0.00")
        layout.addWidget(self.subtotal_label)

        discount_row = QHBoxLayout()
        discount_row.addWidget(QLabel("Discount (Rs.):"))
        self.discount_input = QDoubleSpinBox()
        self.discount_input.setRange(0, 999_999_999)
        self.discount_input.setDecimals(2)
        self.discount_input.valueChanged.connect(self._update_totals)
        discount_row.addWidget(self.discount_input)
        layout.addLayout(discount_row)

        tax_row = QHBoxLayout()
        tax_row.addWidget(QLabel("Tax (%):"))
        self.tax_input = QDoubleSpinBox()
        self.tax_input.setRange(0, 100)
        self.tax_input.setDecimals(2)
        try:
            self.tax_input.setValue(float(get_setting("tax_percent")))
        except (ValueError, TypeError):
            self.tax_input.setValue(0)
        self.tax_input.valueChanged.connect(self._update_totals)
        tax_row.addWidget(self.tax_input)
        layout.addLayout(tax_row)

        self.grand_total_label = QLabel("GRAND TOTAL: Rs. 0.00")
        self.grand_total_label.setStyleSheet("font-weight: bold; font-size: 16px;")
        layout.addWidget(self.grand_total_label)

        return box

    def _build_payment_box(self) -> QWidget:
        box = QGroupBox("Payments (mixed payments supported)")
        layout = QVBoxLayout(box)

        self.payment_rows: list[tuple[QComboBox, QDoubleSpinBox]] = []
        self.payments_layout = QVBoxLayout()
        layout.addLayout(self.payments_layout)
        self._add_payment_row()

        add_payment_button = QPushButton("+ Add Payment Method")
        add_payment_button.clicked.connect(lambda: self._add_payment_row())
        layout.addWidget(add_payment_button)

        old_gold_button = QPushButton("Old Gold Exchange")
        old_gold_button.clicked.connect(self._handle_open_old_gold_dialog)
        layout.addWidget(old_gold_button)

        self.old_gold_credit_label = QLabel("")
        self.old_gold_credit_label.setStyleSheet("color: #1b5e20; font-weight: bold;")
        layout.addWidget(self.old_gold_credit_label)

        self.paid_total_label = QLabel("Total Paid: Rs. 0.00")
        self.balance_label = QLabel("Balance to Return: Rs. 0.00")
        layout.addWidget(self.paid_total_label)
        layout.addWidget(self.balance_label)

        return box

    def _handle_open_old_gold_dialog(self) -> None:
        dialog = OldGoldDialog(self)
        if dialog.exec() == OldGoldDialog.DialogCode.Accepted and dialog.result_input:
            self.old_gold_input = dialog.result_input
            self.old_gold_credit_label.setText(
                f"Old gold credit: Rs. {dialog.result_credit_value:,.2f} ({dialog.result_input.description})"
            )
            self._update_totals()

    def _add_payment_row(self) -> None:
        row = QHBoxLayout()
        method_combo = QComboBox()
        for method in PaymentMethod:
            if method != PaymentMethod.OLD_GOLD:  # old gold handled via a separate exchange flow later
                method_combo.addItem(method.value, method)

        amount_input = QDoubleSpinBox()
        amount_input.setRange(0, 999_999_999)
        amount_input.setDecimals(2)
        amount_input.valueChanged.connect(self._update_totals)

        row.addWidget(method_combo)
        row.addWidget(amount_input)
        self.payments_layout.addLayout(row)
        self.payment_rows.append((method_combo, amount_input))

    def _handle_customer_lookup(self) -> None:
        phone = self.customer_phone_input.text().strip()
        if not phone:
            self.selected_customer = None
            self.customer_label.setText("Walk-in customer")
            return

        customer = find_by_phone(phone)
        if customer is None:
            QMessageBox.information(self, "Not Found", f"No customer found with phone '{phone}'.")
            self.selected_customer = None
            self.customer_label.setText("Walk-in customer")
            return

        self.selected_customer = customer
        self.customer_label.setText(f"{customer.name} ({customer.phone})")

    def _update_totals(self) -> None:
        subtotal = self.cart.subtotal
        discount = Decimal(str(self.discount_input.value()))
        tax_percent = Decimal(str(self.tax_input.value()))
        tax_total = ((subtotal - discount) * tax_percent / Decimal("100")).quantize(Decimal("0.01"))
        grand_total = subtotal - discount + tax_total

        self.subtotal_label.setText(f"Subtotal: Rs. {subtotal:,.2f}")
        self.grand_total_label.setText(f"GRAND TOTAL: Rs. {grand_total:,.2f}")

        old_gold_credit = self.old_gold_input.credit_value if self.old_gold_input else Decimal("0")
        paid_total = sum((Decimal(str(amount.value())) for _, amount in self.payment_rows), Decimal("0")) + old_gold_credit
        balance = paid_total - grand_total
        self.paid_total_label.setText(f"Total Paid: Rs. {paid_total:,.2f}")
        self.balance_label.setText(f"Balance to Return: Rs. {max(balance, Decimal('0')):,.2f}")

    def _handle_complete_sale(self) -> None:
        if not self.cart.lines:
            QMessageBox.warning(self, "Empty Cart", "Add at least one item before completing the sale.")
            return

        discount = Decimal(str(self.discount_input.value()))
        tax_percent = Decimal(str(self.tax_input.value()))
        payments = [
            PaymentInput(method=combo_enum_data(method_combo, PaymentMethod), amount=Decimal(str(amount.value())))
            for method_combo, amount in self.payment_rows
            if amount.value() > 0
        ]

        old_gold_credit = self.old_gold_input.credit_value if self.old_gold_input else Decimal("0")

        try:
            result = complete_sale(
                cart=self.cart,
                cashier_user_id=self.current_user_id,
                customer_id=self.selected_customer.id if self.selected_customer else None,
                invoice_discount=discount,
                tax_percent=tax_percent,
                payments=payments,
                old_gold=self.old_gold_input,
                old_gold_credit=old_gold_credit,
            )
        except SaleError as exc:
            QMessageBox.warning(self, "Cannot Complete Sale", str(exc))
            return

        QMessageBox.information(
            self, "Sale Completed",
            f"Invoice {result.invoice_no} completed.\nGrand total: Rs. {result.grand_total:,.2f}\n"
            f"Balance returned: Rs. {result.balance_returned:,.2f}",
        )

        # Receipt printing happens AFTER commit -- a printer/PDF failure must
        # never lose the sale, since the invoice is already safely in the DB.
        try:
            self._print_receipt(result, payments, discount, tax_percent)
        except Exception as exc:  # noqa: BLE001 - any print failure must not look like a lost sale
            QMessageBox.warning(
                self, "Receipt Printing Failed",
                f"The sale was saved successfully (invoice {result.invoice_no}), "
                f"but generating the receipt failed:\n{exc}\n\nUse Transaction History to reprint.",
            )

        self._reset_for_next_sale()

    def _print_receipt(self, result, payments: list[PaymentInput], discount: Decimal, tax_percent: Decimal) -> None:
        receipt_lines = [
            ReceiptLine(
                item_name=line.item.name,
                item_code=line.item.item_code,
                net_weight_g=line.price.net_weight_g,
                purity=line.item.purity.value,
                gold_rate_used=line.price.gold_rate_used,
                gold_value=line.price.gold_value,
                making_charge=line.price.making_charge,
                stone_value=line.price.stone_value,
                line_total=line.line_total,
            )
            for line in self.cart.lines
        ]
        tax_total = ((self.cart.subtotal - discount) * tax_percent / Decimal("100")).quantize(Decimal("0.01"))

        data = ReceiptData(
            shop_name=get_setting("shop_name"),
            shop_address=get_setting("shop_address"),
            shop_phone=get_setting("shop_phone"),
            invoice_no=result.invoice_no,
            invoice_datetime=datetime.now(),
            cashier_name=self.cashier_name,
            customer_name=self.selected_customer.name if self.selected_customer else None,
            lines=receipt_lines,
            subtotal=self.cart.subtotal,
            discount_total=discount,
            tax_total=tax_total,
            old_gold_credit=self.old_gold_input.credit_value if self.old_gold_input else Decimal("0"),
            grand_total=result.grand_total,
            payments=[ReceiptPaymentLine(method=p.method.value, amount=p.amount) for p in payments],
            balance_returned=result.balance_returned,
            footer_text=get_setting("invoice_footer_text"),
        )
        generate_receipt_pdf(data)

    def _reset_for_next_sale(self) -> None:
        self.cart.clear()
        self._refresh_cart_table()
        self.discount_input.setValue(0)
        for _, amount in self.payment_rows:
            amount.setValue(0)
        self.selected_customer = None
        self.customer_phone_input.clear()
        self.customer_label.setText("Walk-in customer")
        self.old_gold_input = None
        self.old_gold_credit_label.setText("")
        if self.on_sale_completed:
            self.on_sale_completed()
        self.code_input.setFocus()
