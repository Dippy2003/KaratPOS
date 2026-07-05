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
