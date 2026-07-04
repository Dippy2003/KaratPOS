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
