"""
Suppliers & Purchases screen (ADMIN only). Manage supplier contacts
and record goods-receiving purchases; each purchase line immediately
creates a new inventory item, and the screen offers batch QR tag
printing for the items just received.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation

from PySide6.QtWidgets import (
    QComboBox,
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

from app.database.models import MakingChargeType, Purity
from app.services.category_service import get_all_categories
from app.services.purchase_service import PurchaseLineInput, ValidationError, create_purchase
from app.services.supplier_service import create_supplier, get_all_suppliers
from app.printing.tag_printer import TagData, generate_tag_sheet_pdf


class SuppliersScreen(QWidget):
    def __init__(self, current_user_id: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.current_user_id = current_user_id
        self._build_ui()
        self._reload_suppliers()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        title = QLabel("Suppliers & Purchases")
        title.setStyleSheet("font-size: 22px; font-weight: bold;")
        layout.addWidget(title)

        splitter = QSplitter()
        splitter.addWidget(self._build_supplier_panel())
        splitter.addWidget(self._build_purchase_panel())
        splitter.setSizes([420, 900])
        layout.addWidget(splitter, stretch=1)

    def _build_supplier_panel(self) -> QWidget:
        box = QGroupBox("Suppliers")
        layout = QVBoxLayout(box)

        form = QFormLayout()
        self.supplier_name_input = QLineEdit()
        self.supplier_phone_input = QLineEdit()
        form.addRow("Name:", self.supplier_name_input)
        form.addRow("Phone:", self.supplier_phone_input)
        add_supplier_button = QPushButton("Add Supplier")
        add_supplier_button.clicked.connect(self._handle_add_supplier)
        form.addRow(add_supplier_button)
        layout.addLayout(form)

        self.supplier_list_table = QTableWidget(0, 2)
        self.supplier_list_table.setHorizontalHeaderLabels(["Name", "Phone"])
        self.supplier_list_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.supplier_list_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.supplier_list_table)

        return box
