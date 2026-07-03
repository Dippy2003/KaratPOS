"""
Inventory Management screen: add/edit items with a live computed price
preview (using today's gold rate), search/filter the catalog, and
print QR tags (single or batch) for selected items.
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
from PySide6.QtCore import Qt

from app.database.models import Item, ItemStatus, MakingChargeType, Purity
from app.services.category_service import get_all_categories
from app.services.gold_rate_service import get_latest_rate
from app.services.item_service import ValidationError, create_item, search_items
from app.services.pricing_service import calculate_item_price
from app.printing.tag_printer import TagData, generate_tag_sheet_pdf


class InventoryScreen(QWidget):
    def __init__(self, current_user_id: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.current_user_id = current_user_id
        self._build_ui()
        self._reload_list()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        title = QLabel("Inventory Management")
        title.setStyleSheet("font-size: 22px; font-weight: bold;")
        layout.addWidget(title)

        splitter = QSplitter()
        splitter.addWidget(self._build_add_item_form())
        splitter.addWidget(self._build_list_panel())
        splitter.setSizes([420, 900])
        layout.addWidget(splitter, stretch=1)

    def _build_add_item_form(self) -> QWidget:
        box = QGroupBox("Add New Item")
        form = QFormLayout(box)

        self.name_input = QLineEdit()
        self.category_combo = QComboBox()
        for cat in get_all_categories():
            self.category_combo.addItem(cat.name, cat.id)

        self.purity_combo = QComboBox()
        for purity in Purity:
            self.purity_combo.addItem(purity.value, purity)
        self.purity_combo.currentIndexChanged.connect(self._update_price_preview)

        self.gross_weight_input = QLineEdit()
        self.gross_weight_input.textChanged.connect(self._update_price_preview)
        self.net_weight_input = QLineEdit()
        self.net_weight_input.textChanged.connect(self._update_price_preview)

        self.making_charge_type_combo = QComboBox()
        self.making_charge_type_combo.addItem("Flat (Rs.)", MakingChargeType.FLAT)
        self.making_charge_type_combo.addItem("Percent of gold value", MakingChargeType.PERCENT)
        self.making_charge_type_combo.currentIndexChanged.connect(self._update_price_preview)

        self.making_charge_value_input = QLineEdit()
        self.making_charge_value_input.textChanged.connect(self._update_price_preview)

        self.stone_value_input = QLineEdit()
        self.stone_value_input.setText("0")
        self.stone_value_input.textChanged.connect(self._update_price_preview)

        self.cost_price_input = QLineEdit()
        self.cost_price_input.setText("0")

        self.hallmark_input = QLineEdit()

        form.addRow("Name:", self.name_input)
        form.addRow("Category:", self.category_combo)
        form.addRow("Purity:", self.purity_combo)
        form.addRow("Gross weight (g):", self.gross_weight_input)
        form.addRow("Net weight (g):", self.net_weight_input)
        form.addRow("Making charge type:", self.making_charge_type_combo)
        form.addRow("Making charge value:", self.making_charge_value_input)
        form.addRow("Stone value (Rs.):", self.stone_value_input)
        form.addRow("Cost price (Rs.):", self.cost_price_input)
        form.addRow("Hallmark/cert no:", self.hallmark_input)

        self.price_preview_label = QLabel("Price preview: --")
        self.price_preview_label.setStyleSheet("font-weight: bold; color: #1b5e20;")
        form.addRow(self.price_preview_label)

        save_button = QPushButton("Save Item")
        save_button.clicked.connect(self._handle_save_item)
        form.addRow(save_button)

        return box
