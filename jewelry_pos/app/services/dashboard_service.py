"""Read-only aggregate queries for the Dashboard screen's live totals and charts."""
from __future__ import annotations

from collections import defaultdict
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


@dataclass(frozen=True)
class DashboardChartData:
    daily_totals: list[tuple[date, Decimal]]  # last 7 days, oldest first
    payment_breakdown: dict[str, Decimal]  # last 7 days
    top_categories: list[tuple[str, int]]  # top 5 by items sold, last 7 days


def get_dashboard_chart_data(days: int = 7) -> DashboardChartData:
    """Data for the Dashboard's 7-day sales bar, payment-method pie, and top-5 categories charts."""
    end = datetime.combine(date.today(), datetime.min.time()) + timedelta(days=1)
    start = end - timedelta(days=days)

    with get_session() as session:
        invoices = session.scalars(
            select(Invoice).where(
                Invoice.invoice_datetime >= start,
                Invoice.invoice_datetime < end,
                Invoice.status.in_([InvoiceStatus.COMPLETED, InvoiceStatus.PARTIALLY_RETURNED]),
                Invoice.is_deleted.is_(False),
            )
        ).all()

        daily_sales: dict[date, Decimal] = defaultdict(lambda: Decimal("0"))
        payment_breakdown: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
        category_counts: dict[str, int] = defaultdict(int)

        for invoice in invoices:
            invoice_day = invoice.invoice_datetime.date()
            daily_sales[invoice_day] += Decimal(invoice.grand_total)

            for payment in invoice.payments:
                payment_breakdown[payment.method.value] += Decimal(payment.amount)

            for line in invoice.items:
                if not line.is_returned:
                    category_counts[line.item.category.name] += 1

        # Fill in every day of the window so the bar chart shows zero-sale days too.
        daily_totals = []
        for i in range(days):
            day = (start + timedelta(days=i)).date()
            daily_totals.append((day, daily_sales.get(day, Decimal("0"))))

        top_categories = sorted(category_counts.items(), key=lambda kv: kv[1], reverse=True)[:5]

        return DashboardChartData(
            daily_totals=daily_totals,
            payment_breakdown=dict(payment_breakdown),
            top_categories=top_categories,
        )


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
