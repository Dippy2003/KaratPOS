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


@dataclass(frozen=True)
class DateRangeSalesReport:
    start_date: date
    end_date: date
    total_sales: Decimal
    total_profit: Decimal
    invoice_count: int
    daily_totals: list[tuple[date, Decimal]]  # for charting


def get_date_range_sales_report(start_date: date, end_date: date) -> DateRangeSalesReport:
    start = datetime.combine(start_date, datetime.min.time())
    end = datetime.combine(end_date, datetime.min.time()) + timedelta(days=1)

    with get_session() as session:
        invoices = _invoices_in_range(session, start, end)

        total_sales = Decimal("0")
        total_profit = Decimal("0")
        daily_sales: dict[date, Decimal] = defaultdict(lambda: Decimal("0"))

        for invoice in invoices:
            invoice_day = invoice.invoice_datetime.date()
            total_sales += Decimal(invoice.grand_total)
            daily_sales[invoice_day] += Decimal(invoice.grand_total)
            for line in invoice.items:
                if not line.is_returned:
                    total_profit += Decimal(line.line_total) - Decimal(line.item.cost_price)

        daily_totals = sorted(daily_sales.items())

        return DateRangeSalesReport(
            start_date=start_date,
            end_date=end_date,
            total_sales=total_sales,
            total_profit=total_profit,
            invoice_count=len(invoices),
            daily_totals=daily_totals,
        )


@dataclass(frozen=True)
class StockValuationReport:
    valuation_date: date
    total_items: int
    total_value: Decimal
    value_by_category: dict[str, Decimal]


def get_stock_valuation_report() -> StockValuationReport:
    """Value of all AVAILABLE inventory at TODAY's gold rate -- recomputes as rates change."""
    from app.services.gold_rate_service import get_latest_rate
    from app.services.pricing_service import calculate_item_price

    with get_session() as session:
        items = session.scalars(
            select(Item).where(Item.status == ItemStatus.AVAILABLE, Item.is_deleted.is_(False))
        ).all()

        total_value = Decimal("0")
        value_by_category: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
        rate_cache: dict = {}

        for item in items:
            if item.purity not in rate_cache:
                rate_row = get_latest_rate(item.purity)
                rate_cache[item.purity] = rate_row.rate_per_gram if rate_row else None
            rate = rate_cache[item.purity]
            if rate is None:
                continue  # no rate entered yet for this purity -- skip from valuation

            breakdown = calculate_item_price(item, rate)
            total_value += breakdown.subtotal
            value_by_category[item.category.name] += breakdown.subtotal

        return StockValuationReport(
            valuation_date=date.today(),
            total_items=len(items),
            total_value=total_value,
            value_by_category=dict(value_by_category),
        )
