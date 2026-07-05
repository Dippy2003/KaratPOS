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
from PySide6.QtCore import QDate

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
