"""Read-only aggregate queries for the Dashboard screen's live totals."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select

from app.database.db import get_session
from app.database.models import Invoice, InvoiceItem, InvoiceStatus


@dataclass(frozen=True)
class TodayStats:
    total_sales: Decimal
    invoice_count: int
    items_sold: int


def get_today_stats() -> TodayStats:
    today_start = datetime.combine(date.today(), datetime.min.time())
    today_end = today_start + timedelta(days=1)

    with get_session() as session:
        invoices = session.scalars(
            select(Invoice).where(
                Invoice.invoice_datetime >= today_start,
                Invoice.invoice_datetime < today_end,
                Invoice.status.in_([InvoiceStatus.COMPLETED, InvoiceStatus.PARTIALLY_RETURNED]),
                Invoice.is_deleted.is_(False),
            )
        ).all()

        total_sales = sum((Decimal(inv.grand_total) for inv in invoices), Decimal("0"))
        invoice_count = len(invoices)
        items_sold = sum(len(inv.items) for inv in invoices)

        return TodayStats(total_sales=total_sales, invoice_count=invoice_count, items_sold=items_sold)
