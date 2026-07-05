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
