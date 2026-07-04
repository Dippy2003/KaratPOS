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
