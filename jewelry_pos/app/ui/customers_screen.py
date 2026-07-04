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

    def _build_list_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)

        search_row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by name or phone...")
        self.search_input.textChanged.connect(self._reload_list)
        search_row.addWidget(self.search_input)
        layout.addLayout(search_row)

        self.customer_table = QTableWidget(0, 4)
        self.customer_table.setHorizontalHeaderLabels(["Name", "Phone", "Address", "Total Spent"])
        self.customer_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.customer_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.customer_table)

        return panel

    def _handle_save_customer(self) -> None:
        try:
            create_customer(
                name=self.name_input.text(),
                phone=self.phone_input.text() or None,
                address=self.address_input.text() or None,
                nic=self.nic_input.text() or None,
            )
        except ValidationError as exc:
            QMessageBox.warning(self, "Validation Error", str(exc))
            return

        self.name_input.clear()
        self.phone_input.clear()
        self.address_input.clear()
        self.nic_input.clear()
        self._reload_list()
        QMessageBox.information(self, "Customer Added", "Customer created successfully.")

    def _reload_list(self) -> None:
        rows = search_customers(self.search_input.text())
        self.customer_table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            self.customer_table.setItem(i, 0, QTableWidgetItem(row.name))
            self.customer_table.setItem(i, 1, QTableWidgetItem(row.phone or ""))
            self.customer_table.setItem(i, 2, QTableWidgetItem(row.address or ""))
            self.customer_table.setItem(i, 3, QTableWidgetItem(f"Rs. {row.total_spent:,.2f}"))
