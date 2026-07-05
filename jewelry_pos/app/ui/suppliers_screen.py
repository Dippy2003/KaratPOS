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
from app.utils.qt_helpers import combo_enum_data
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

    def _build_purchase_panel(self) -> QWidget:
        box = QGroupBox("Record New Purchase (goods received)")
        form = QFormLayout(box)

        self.purchase_supplier_combo = QComboBox()
        form.addRow("Supplier:", self.purchase_supplier_combo)

        self.item_name_input = QLineEdit()
        self.category_combo = QComboBox()
        for cat in get_all_categories():
            self.category_combo.addItem(cat.name, cat.id)
        self.purity_combo = QComboBox()
        for purity in Purity:
            self.purity_combo.addItem(purity.value, purity)
        self.gross_weight_input = QLineEdit()
        self.net_weight_input = QLineEdit()
        self.making_charge_type_combo = QComboBox()
        self.making_charge_type_combo.addItem("Flat (Rs.)", MakingChargeType.FLAT)
        self.making_charge_type_combo.addItem("Percent of gold value", MakingChargeType.PERCENT)
        self.making_charge_value_input = QLineEdit()
        self.stone_value_input = QLineEdit()
        self.stone_value_input.setText("0")
        self.cost_price_input = QLineEdit()

        form.addRow("Item name:", self.item_name_input)
        form.addRow("Category:", self.category_combo)
        form.addRow("Purity:", self.purity_combo)
        form.addRow("Gross weight (g):", self.gross_weight_input)
        form.addRow("Net weight (g):", self.net_weight_input)
        form.addRow("Making charge type:", self.making_charge_type_combo)
        form.addRow("Making charge value:", self.making_charge_value_input)
        form.addRow("Stone value (Rs.):", self.stone_value_input)
        form.addRow("Cost price (Rs.):", self.cost_price_input)

        record_button = QPushButton("Record Purchase")
        record_button.clicked.connect(self._handle_record_purchase)
        form.addRow(record_button)

        return box

    def _handle_add_supplier(self) -> None:
        name = self.supplier_name_input.text()
        phone = self.supplier_phone_input.text() or None
        try:
            create_supplier(name, phone=phone)
        except ValidationError as exc:
            QMessageBox.warning(self, "Validation Error", str(exc))
            return
        self.supplier_name_input.clear()
        self.supplier_phone_input.clear()
        self._reload_suppliers()

    def _reload_suppliers(self) -> None:
        suppliers = get_all_suppliers()

        self.supplier_list_table.setRowCount(len(suppliers))
        for i, s in enumerate(suppliers):
            self.supplier_list_table.setItem(i, 0, QTableWidgetItem(s.name))
            self.supplier_list_table.setItem(i, 1, QTableWidgetItem(s.phone or ""))

        self.purchase_supplier_combo.clear()
        for s in suppliers:
            self.purchase_supplier_combo.addItem(s.name, s.id)

    def _handle_record_purchase(self) -> None:
        supplier_id = self.purchase_supplier_combo.currentData()
        if supplier_id is None:
            QMessageBox.warning(self, "No Supplier", "Add a supplier first.")
            return

        try:
            gross_weight = Decimal(self.gross_weight_input.text() or "0")
            net_weight = Decimal(self.net_weight_input.text() or "0")
            making_value = Decimal(self.making_charge_value_input.text() or "0")
            stone_value = Decimal(self.stone_value_input.text() or "0")
            cost_price = Decimal(self.cost_price_input.text() or "0")
        except (InvalidOperation, ValueError):
            QMessageBox.warning(self, "Invalid Input", "Please enter valid numbers for weights and charges.")
            return

        line = PurchaseLineInput(
            name=self.item_name_input.text(),
            category_id=self.category_combo.currentData(),
            purity=combo_enum_data(self.purity_combo, Purity),
            gross_weight_g=gross_weight,
            net_weight_g=net_weight,
            making_charge_type=combo_enum_data(self.making_charge_type_combo, MakingChargeType),
            making_charge_value=making_value,
            stone_value_total=stone_value,
            cost_price=cost_price,
        )

        try:
            result = create_purchase(supplier_id, [line], created_by_user_id=self.current_user_id)
        except ValidationError as exc:
            QMessageBox.warning(self, "Validation Error", str(exc))
            return

        offer_tags = QMessageBox.question(
            self, "Purchase Recorded",
            f"Purchase #{result.purchase_id} recorded. Created item(s): {', '.join(result.created_item_codes)}.\n\n"
            "Print QR tags for the new item(s) now?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if offer_tags == QMessageBox.StandardButton.Yes:
            tags = [
                TagData(item_code=code, name=line.name, net_weight_g=line.net_weight_g, purity=line.purity.value)
                for code in result.created_item_codes
            ]
            pdf_path = generate_tag_sheet_pdf(tags)
            QMessageBox.information(self, "Tags Generated", f"QR tag sheet saved to:\n{pdf_path}")

        self._clear_purchase_form()

    def _clear_purchase_form(self) -> None:
        self.item_name_input.clear()
        self.gross_weight_input.clear()
        self.net_weight_input.clear()
        self.making_charge_value_input.clear()
        self.stone_value_input.setText("0")
        self.cost_price_input.clear()
