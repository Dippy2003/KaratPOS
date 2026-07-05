"""Custom/advance orders with installment payments toward a final balance."""
from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation

from PySide6.QtCore import QDate, Qt
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

from app.database.models import PaymentMethod
from app.services.advance_order_service import (
    ValidationError,
    create_advance_order,
    get_all_advance_orders,
    record_installment_payment,
)
from app.services.customer_service import find_by_phone
from app.utils.qt_helpers import combo_enum_data


class AdvanceOrdersScreen(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()
        self._reload_list()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        title = QLabel("Advance Orders")
        title.setStyleSheet("font-size: 22px; font-weight: bold;")
        layout.addWidget(title)

        splitter = QSplitter()
        splitter.addWidget(self._build_create_form())
        splitter.addWidget(self._build_list_panel())
        splitter.setSizes([420, 900])
        layout.addWidget(splitter, stretch=1)

    def _build_create_form(self) -> QWidget:
        box = QGroupBox("New Advance Order")
        form = QFormLayout(box)

        self.customer_phone_input = QLineEdit()
        form.addRow("Customer phone:", self.customer_phone_input)

        self.description_input = QLineEdit()
        form.addRow("Description:", self.description_input)

        self.estimated_total_input = QLineEdit()
        form.addRow("Estimated total (Rs.):", self.estimated_total_input)

        self.initial_advance_input = QLineEdit()
        self.initial_advance_input.setText("0")
        form.addRow("Initial advance (Rs.):", self.initial_advance_input)

        self.due_date_input = QDateEdit()
        self.due_date_input.setCalendarPopup(True)
        self.due_date_input.setDate(QDate.currentDate().addDays(30))
        form.addRow("Due date:", self.due_date_input)

        self.payment_method_combo = QComboBox()
        for method in PaymentMethod:
            if method != PaymentMethod.OLD_GOLD:
                self.payment_method_combo.addItem(method.value, method)
        form.addRow("Payment method:", self.payment_method_combo)

        create_button = QPushButton("Create Order")
        create_button.clicked.connect(self._handle_create_order)
        form.addRow(create_button)

        return box

    def _build_list_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)

        self.orders_table = QTableWidget(0, 6)
        self.orders_table.setHorizontalHeaderLabels(
            ["Customer", "Description", "Estimated Total", "Paid", "Balance", "Status"]
        )
        self.orders_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.orders_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.orders_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.orders_table)

        installment_form = QFormLayout()
        self.installment_amount_input = QLineEdit()
        self.installment_method_combo = QComboBox()
        for method in PaymentMethod:
            if method != PaymentMethod.OLD_GOLD:
                self.installment_method_combo.addItem(method.value, method)
        record_button = QPushButton("Record Installment for Selected Order")
        record_button.clicked.connect(self._handle_record_installment)
        installment_form.addRow("Amount (Rs.):", self.installment_amount_input)
        installment_form.addRow("Method:", self.installment_method_combo)
        installment_form.addRow(record_button)
        layout.addLayout(installment_form)

        return panel

    def _handle_create_order(self) -> None:
        phone = self.customer_phone_input.text().strip()
        customer = find_by_phone(phone) if phone else None
        if customer is None:
            QMessageBox.warning(self, "Customer Not Found", "Enter a valid, existing customer phone number.")
            return

        try:
            estimated_total = Decimal(self.estimated_total_input.text() or "0")
            initial_advance = Decimal(self.initial_advance_input.text() or "0")
        except (InvalidOperation, ValueError):
            QMessageBox.warning(self, "Invalid Input", "Enter valid numeric amounts.")
            return

        try:
            order = create_advance_order(
                customer_id=customer.id,
                description=self.description_input.text(),
                estimated_total=estimated_total,
                initial_advance=initial_advance,
                due_date=self.due_date_input.date().toPython(),
                payment_method=combo_enum_data(self.payment_method_combo, PaymentMethod),
            )
        except ValidationError as exc:
            QMessageBox.warning(self, "Validation Error", str(exc))
            return

        QMessageBox.information(self, "Order Created", f"Advance order #{order.id} created. Balance: Rs. {order.balance:,.2f}")
        self.description_input.clear()
        self.estimated_total_input.clear()
        self.initial_advance_input.setText("0")
        self._reload_list()

    def _reload_list(self) -> None:
        orders = get_all_advance_orders()
        self.orders_table.setRowCount(len(orders))
        for i, o in enumerate(orders):
            self.orders_table.setItem(i, 0, QTableWidgetItem(o.customer_name))
            self.orders_table.setItem(i, 1, QTableWidgetItem(o.description))
            self.orders_table.setItem(i, 2, QTableWidgetItem(f"{o.estimated_total:,.2f}"))
            self.orders_table.setItem(i, 3, QTableWidgetItem(f"{o.advance_paid:,.2f}"))
            self.orders_table.setItem(i, 4, QTableWidgetItem(f"{o.balance:,.2f}"))
            self.orders_table.setItem(i, 5, QTableWidgetItem(o.status.value))
            self.orders_table.item(i, 0).setData(Qt.ItemDataRole.UserRole, o.id)

    def _handle_record_installment(self) -> None:
        selected = self.orders_table.selectedIndexes()
        if not selected:
            QMessageBox.warning(self, "No Selection", "Select an advance order row first.")
            return
        row = selected[0].row()
        order_id = self.orders_table.item(row, 0).data(Qt.ItemDataRole.UserRole)

        try:
            amount = Decimal(self.installment_amount_input.text() or "0")
        except (InvalidOperation, ValueError):
            QMessageBox.warning(self, "Invalid Input", "Enter a valid payment amount.")
            return

        try:
            order = record_installment_payment(order_id, amount, combo_enum_data(self.installment_method_combo, PaymentMethod))
        except ValidationError as exc:
            QMessageBox.warning(self, "Error", str(exc))
            return

        QMessageBox.information(self, "Payment Recorded", f"New balance: Rs. {order.balance:,.2f} ({order.status.value})")
        self.installment_amount_input.clear()
        self._reload_list()
