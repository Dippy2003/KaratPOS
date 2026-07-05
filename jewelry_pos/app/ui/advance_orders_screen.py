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
