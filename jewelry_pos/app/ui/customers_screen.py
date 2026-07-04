"""
Customer Management screen: create customers and browse/search the
customer list with each customer's cached total spend. Full purchase
history drill-down is added once Transaction History exists.
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QFormLayout,
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

from app.services.customer_service import ValidationError, create_customer, search_customers


class CustomersScreen(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()
        self._reload_list()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        title = QLabel("Customer Management")
        title.setStyleSheet("font-size: 22px; font-weight: bold;")
        layout.addWidget(title)

        splitter = QSplitter()
        splitter.addWidget(self._build_add_form())
        splitter.addWidget(self._build_list_panel())
        splitter.setSizes([380, 900])
        layout.addWidget(splitter, stretch=1)

    def _build_add_form(self) -> QWidget:
        box = QGroupBox("Add New Customer")
        form = QFormLayout(box)

        self.name_input = QLineEdit()
        self.phone_input = QLineEdit()
        self.address_input = QLineEdit()
        self.nic_input = QLineEdit()

        form.addRow("Name:", self.name_input)
        form.addRow("Phone:", self.phone_input)
        form.addRow("Address:", self.address_input)
        form.addRow("NIC (optional):", self.nic_input)

        save_button = QPushButton("Save Customer")
        save_button.clicked.connect(self._handle_save_customer)
        form.addRow(save_button)

        return box
