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
