"""
Transaction History search/detail/cancellation. Cancellation is
distinct from a return: it fully reverses a same-day sale (SOLD items
go back to AVAILABLE) and is ADMIN-only, whereas returns (a later
phase) handle partial/per-item refunds on any past invoice.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select

from app.database.db import get_session
from app.database.models import AuditLog, Invoice, InvoiceStatus, Item, ItemStatus, UserRole


class TransactionError(Exception):
    pass


@dataclass(frozen=True)
class InvoiceSummaryRow:
    id: int
    invoice_no: str
    invoice_datetime: datetime
    customer_name: str | None
    cashier_name: str
    grand_total: Decimal
    status: InvoiceStatus


def search_invoices(
    *,
    invoice_no: str = "",
    date_from: date | None = None,
    date_to: date | None = None,
    customer_name: str = "",
    cashier_user_id: int | None = None,
    status: InvoiceStatus | None = None,
) -> list[InvoiceSummaryRow]:
    with get_session() as session:
        stmt = select(Invoice).where(Invoice.is_deleted.is_(False))

        if invoice_no:
            stmt = stmt.where(Invoice.invoice_no.ilike(f"%{invoice_no.strip()}%"))
        if date_from:
            stmt = stmt.where(Invoice.invoice_datetime >= datetime.combine(date_from, datetime.min.time()))
        if date_to:
            stmt = stmt.where(Invoice.invoice_datetime < datetime.combine(date_to + timedelta(days=1), datetime.min.time()))
        if cashier_user_id is not None:
            stmt = stmt.where(Invoice.user_id == cashier_user_id)
        if status is not None:
            stmt = stmt.where(Invoice.status == status)

        stmt = stmt.order_by(Invoice.invoice_datetime.desc())
        invoices = session.scalars(stmt).all()

        rows = []
        for inv in invoices:
            cust_name = inv.customer.name if inv.customer else None
            if customer_name and (not cust_name or customer_name.strip().lower() not in cust_name.lower()):
                continue
            rows.append(
                InvoiceSummaryRow(
                    id=inv.id,
                    invoice_no=inv.invoice_no,
                    invoice_datetime=inv.invoice_datetime,
                    customer_name=cust_name,
                    cashier_name=inv.cashier.full_name,
                    grand_total=Decimal(inv.grand_total),
                    status=inv.status,
                )
            )
        return rows
