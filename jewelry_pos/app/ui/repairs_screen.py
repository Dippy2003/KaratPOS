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
from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QColor

from app.database.models import RepairStatus
from app.services.customer_service import find_by_phone
from app.services.repair_service import ValidationError, create_repair, get_all_repairs, update_repair_status
from app.printing.repair_ticket import RepairTicketData, generate_repair_ticket_pdf


class RepairsScreen(QWidget):
    def __init__(self, current_user_id: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.current_user_id = current_user_id
        self._last_created_repair_id: int | None = None
        self._build_ui()
        self._reload_list()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        title = QLabel("Repairs")
        title.setStyleSheet("font-size: 22px; font-weight: bold;")
        layout.addWidget(title)

        splitter = QSplitter()
        splitter.addWidget(self._build_intake_form())
        splitter.addWidget(self._build_list_panel())
        splitter.setSizes([420, 900])
        layout.addWidget(splitter, stretch=1)

    def _build_intake_form(self) -> QWidget:
        box = QGroupBox("Log New Repair")
        form = QFormLayout(box)

        self.customer_phone_input = QLineEdit()
        self.customer_phone_input.setPlaceholderText("Customer phone")
        form.addRow("Customer phone:", self.customer_phone_input)

        self.item_description_input = QLineEdit()
        form.addRow("Item:", self.item_description_input)

        self.issue_input = QLineEdit()
        form.addRow("Issue:", self.issue_input)

        self.promised_date_input = QDateEdit()
        self.promised_date_input.setCalendarPopup(True)
        self.promised_date_input.setDate(QDate.currentDate().addDays(7))
        form.addRow("Promised date:", self.promised_date_input)

        self.estimated_cost_input = QLineEdit()
        self.estimated_cost_input.setText("0")
        form.addRow("Estimated cost (Rs.):", self.estimated_cost_input)

        submit_button = QPushButton("Log Repair")
        submit_button.clicked.connect(self._handle_create_repair)
        form.addRow(submit_button)

        print_ticket_button = QPushButton("Print Ticket for Last Repair")
        print_ticket_button.clicked.connect(self._handle_print_last_ticket)
        form.addRow(print_ticket_button)

        return box

    def _build_list_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)

        self.repairs_table = QTableWidget(0, 6)
        self.repairs_table.setHorizontalHeaderLabels(
            ["Customer", "Item", "Received", "Promised", "Status", "Est. Cost"]
        )
        self.repairs_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.repairs_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.repairs_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.repairs_table)

        status_row = QFormLayout()
        self.status_combo = QComboBox()
        for status in RepairStatus:
            self.status_combo.addItem(status.value, status)
        update_button = QPushButton("Update Selected Repair's Status")
        update_button.clicked.connect(self._handle_update_status)
        status_row.addRow("New status:", self.status_combo)
        status_row.addRow(update_button)
        layout.addLayout(status_row)

        return panel

    def _handle_create_repair(self) -> None:
        phone = self.customer_phone_input.text().strip()
        customer = find_by_phone(phone) if phone else None
        if customer is None:
            QMessageBox.warning(self, "Customer Not Found", "Enter a valid, existing customer phone number.")
            return

        try:
            cost = Decimal(self.estimated_cost_input.text() or "0")
        except (InvalidOperation, ValueError):
            QMessageBox.warning(self, "Invalid Input", "Enter a valid estimated cost.")
            return

        promised = self.promised_date_input.date().toPython()

        try:
            repair = create_repair(
                customer_id=customer.id,
                item_description=self.item_description_input.text(),
                issue=self.issue_input.text(),
                promised_date=promised,
                estimated_cost=cost,
                received_by_user_id=self.current_user_id,
            )
        except ValidationError as exc:
            QMessageBox.warning(self, "Validation Error", str(exc))
            return

        self._last_created_repair_id = repair.id
        QMessageBox.information(self, "Repair Logged", f"Repair #{repair.id} logged for {customer.name}.")
        self.item_description_input.clear()
        self.issue_input.clear()
        self._reload_list()

    def _reload_list(self) -> None:
        repairs = get_all_repairs()
        today = date.today()

        self.repairs_table.setRowCount(len(repairs))
        for i, r in enumerate(repairs):
            self.repairs_table.setItem(i, 0, QTableWidgetItem(r.customer_name))
            self.repairs_table.setItem(i, 1, QTableWidgetItem(r.item_description))
            self.repairs_table.setItem(i, 2, QTableWidgetItem(r.received_date.strftime("%d/%m/%Y")))
            promised_text = r.promised_date.strftime("%d/%m/%Y") if r.promised_date else "-"
            self.repairs_table.setItem(i, 3, QTableWidgetItem(promised_text))
            self.repairs_table.setItem(i, 4, QTableWidgetItem(r.status.value))
            self.repairs_table.setItem(i, 5, QTableWidgetItem(f"{r.estimated_cost:,.2f}"))
            self.repairs_table.item(i, 0).setData(Qt.ItemDataRole.UserRole, r.id)

            is_overdue = r.promised_date and r.promised_date < today and r.status != RepairStatus.DELIVERED
            if is_overdue:
                # Explicit dark foreground: this highlight is always a light
                # pink background regardless of the app's theme, so text must
                # not inherit a (possibly white, under dark mode) palette color.
                for col in range(6):
                    cell = self.repairs_table.item(i, col)
                    cell.setBackground(QColor("#ffcdd2"))
                    cell.setForeground(QColor("#1a1a1a"))

    def _handle_update_status(self) -> None:
        selected_rows = self.repairs_table.selectedIndexes()
        if not selected_rows:
            QMessageBox.warning(self, "No Selection", "Select a repair row first.")
            return
        row = selected_rows[0].row()
        repair_id = self.repairs_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        new_status = self.status_combo.currentData()

        try:
            update_repair_status(repair_id, new_status, updated_by_user_id=self.current_user_id)
        except ValidationError as exc:
            QMessageBox.warning(self, "Error", str(exc))
            return
        self._reload_list()

    def _handle_print_last_ticket(self) -> None:
        if self._last_created_repair_id is None:
            QMessageBox.information(self, "No Repair", "Log a repair first.")
            return

        repairs = get_all_repairs()
        repair = next((r for r in repairs if r.id == self._last_created_repair_id), None)
        if repair is None:
            return

        data = RepairTicketData(
            repair_id=repair.id,
            customer_name=repair.customer_name,
            item_description=repair.item_description,
            issue=repair.issue,
            received_date=repair.received_date,
            promised_date=repair.promised_date,
            estimated_cost=repair.estimated_cost,
        )
        pdf_path = generate_repair_ticket_pdf(data)
        QMessageBox.information(self, "Ticket Generated", f"Repair ticket saved to:\n{pdf_path}")
