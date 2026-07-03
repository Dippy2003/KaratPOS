"""
A4 PDF receipt generation via ReportLab, matching the layout specified
in the project brief. Renders directly from the frozen invoice_items
snapshot -- never recalculates prices at print/reprint time.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas

from app.utils.config import RECEIPTS_DIR


@dataclass(frozen=True)
class ReceiptLine:
    item_name: str
    item_code: str
    net_weight_g: Decimal
    purity: str
    gold_rate_used: Decimal
    gold_value: Decimal
    making_charge: Decimal
    stone_value: Decimal
    line_total: Decimal


@dataclass(frozen=True)
class ReceiptPaymentLine:
    method: str
    amount: Decimal


@dataclass(frozen=True)
class ReceiptData:
    shop_name: str
    shop_address: str
    shop_phone: str
    invoice_no: str
    invoice_datetime: datetime
    cashier_name: str
    customer_name: str | None
    lines: list[ReceiptLine]
    subtotal: Decimal
    discount_total: Decimal
    tax_total: Decimal
    old_gold_credit: Decimal
    grand_total: Decimal
    payments: list[ReceiptPaymentLine]
    balance_returned: Decimal
    footer_text: str
    is_reprint: bool = False
