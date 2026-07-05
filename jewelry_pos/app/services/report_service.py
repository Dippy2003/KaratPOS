"""
Sales, profit, and stock reports. All reports read from invoice_items'
frozen price snapshots (never recalculated against current rates)
except stock valuation, which is explicitly defined to use TODAY's
rate on AVAILABLE inventory, per the project brief.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select

from app.database.models import (
    Invoice,
    InvoiceItem,
    InvoiceStatus,
    Item,
    ItemStatus,
    Payment,
)
from app.database.db import get_session


@dataclass(frozen=True)
class DailySalesReport:
    report_date: date
    total_sales: Decimal
    total_profit: Decimal
    invoice_count: int
    best_selling_items: list[tuple[str, int]]  # (item name, qty)
    best_selling_categories: list[tuple[str, int]]
    payment_breakdown: dict[str, Decimal]
    sales_by_employee: dict[str, Decimal]
