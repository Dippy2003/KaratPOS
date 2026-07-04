"""
Old gold exchange dialog, opened from the POS screen. Records a
description, weight, assessed purity, and buy-back rate (defaulted
from today's rate minus the configured margin, but editable), then
returns an OldGoldExchangeInput + credit value for the caller to
apply as a payment line on the current sale.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from app.database.models import Purity
from app.services.old_gold_service import OldGoldError, calculate_credit_value, get_default_buy_rate
from app.services.sales_service import OldGoldExchangeInput


class OldGoldDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Old Gold Exchange")
        self.resize(420, 320)
        self.result_input: OldGoldExchangeInput | None = None
        self.result_credit_value: Decimal | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.description_input = QLineEdit()
        self.weight_input = QDoubleSpinBox()
        self.weight_input.setRange(0, 10000)
        self.weight_input.setDecimals(3)
        self.weight_input.valueChanged.connect(self._update_default_rate)

        self.purity_combo = QComboBox()
        for purity in Purity:
            self.purity_combo.addItem(purity.value, purity)
        self.purity_combo.currentIndexChanged.connect(self._update_default_rate)

        self.rate_input = QDoubleSpinBox()
        self.rate_input.setRange(0, 999_999)
        self.rate_input.setDecimals(2)
        self.rate_input.valueChanged.connect(self._update_credit_preview)

        self.credit_preview_label = QLabel("Credit value: Rs. 0.00")
        self.credit_preview_label.setStyleSheet("font-weight: bold;")

        form.addRow("Description:", self.description_input)
        form.addRow("Gross weight (g):", self.weight_input)
        form.addRow("Assessed purity:", self.purity_combo)
        form.addRow("Buy-back rate (Rs./g):", self.rate_input)
        form.addRow(self.credit_preview_label)
        layout.addLayout(form)

        confirm_button = QPushButton("Add as Payment")
        confirm_button.clicked.connect(self._handle_confirm)
        layout.addWidget(confirm_button)

        self._update_default_rate()
