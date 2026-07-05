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


def _invoices_in_range(session, start: datetime, end: datetime) -> list[Invoice]:
    return session.scalars(
        select(Invoice).where(
            Invoice.invoice_datetime >= start,
            Invoice.invoice_datetime < end,
            Invoice.status.in_([InvoiceStatus.COMPLETED, InvoiceStatus.PARTIALLY_RETURNED]),
            Invoice.is_deleted.is_(False),
        )
    ).all()


def get_daily_sales_report(report_date: date) -> DailySalesReport:
    start = datetime.combine(report_date, datetime.min.time())
    end = start + timedelta(days=1)

    with get_session() as session:
        invoices = _invoices_in_range(session, start, end)

        total_sales = Decimal("0")
        total_profit = Decimal("0")
        item_counts: dict[str, int] = defaultdict(int)
        category_counts: dict[str, int] = defaultdict(int)
        payment_breakdown: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
        sales_by_employee: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))

        for invoice in invoices:
            if not invoice.items:
                continue
            total_sales += Decimal(invoice.grand_total)
            sales_by_employee[invoice.cashier.full_name] += Decimal(invoice.grand_total)

            for line in invoice.items:
                if line.is_returned:
                    continue
                item_counts[line.item.name] += 1
                category_counts[line.item.category.name] += 1
                total_profit += Decimal(line.line_total) - Decimal(line.item.cost_price)

            for payment in invoice.payments:
                payment_breakdown[payment.method.value] += Decimal(payment.amount)

        best_items = sorted(item_counts.items(), key=lambda kv: kv[1], reverse=True)[:5]
        best_categories = sorted(category_counts.items(), key=lambda kv: kv[1], reverse=True)[:5]

        return DailySalesReport(
            report_date=report_date,
            total_sales=total_sales,
            total_profit=total_profit,
            invoice_count=len(invoices),
            best_selling_items=best_items,
            best_selling_categories=best_categories,
            payment_breakdown=dict(payment_breakdown),
            sales_by_employee=dict(sales_by_employee),
        )
