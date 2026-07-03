"""
Gold Rate Management screen (ADMIN only). Lets the admin enter today's
rate per purity and view the full append-only rate history.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.database.models import Purity
from app.services.gold_rate_service import DuplicateRateError, add_rate, get_rate_history


class GoldRateScreen(QWidget):
    def __init__(self, current_user_id: int, on_rate_added=None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.current_user_id = current_user_id
        self.on_rate_added = on_rate_added
        self._build_ui()
        self._reload_history()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        title = QLabel("Gold Rate Management")
        title.setStyleSheet("font-size: 22px; font-weight: bold;")
        layout.addWidget(title)

        layout.addWidget(self._build_entry_form())
        layout.addWidget(QLabel("Rate History"))
        layout.addWidget(self._build_history_table())

    def _build_entry_form(self) -> QWidget:
        form = QWidget()
        row = QHBoxLayout(form)

        self.purity_combo = QComboBox()
        for purity in Purity:
            self.purity_combo.addItem(purity.value, purity)

        self.rate_input = QLineEdit()
        self.rate_input.setPlaceholderText("Rate per gram (Rs.)")

        add_button = QPushButton("Add Today's Rate")
        add_button.clicked.connect(self._handle_add_rate)

        row.addWidget(QLabel("Purity:"))
        row.addWidget(self.purity_combo)
        row.addWidget(QLabel("Rate (Rs./g):"))
        row.addWidget(self.rate_input)
        row.addWidget(add_button)
        row.addStretch()

        return form
