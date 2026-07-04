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


@dataclass(frozen=True)
class InvoiceLineDetail:
    item_code: str
    item_name: str
    net_weight_g: Decimal
    purity: str
    gold_rate_used: Decimal
    gold_value: Decimal
    making_charge: Decimal
    stone_value: Decimal
    line_discount: Decimal
    line_total: Decimal
    is_returned: bool


@dataclass(frozen=True)
class PaymentDetail:
    method: str
    amount: Decimal


@dataclass(frozen=True)
class InvoiceDetail:
    id: int
    invoice_no: str
    invoice_datetime: datetime
    customer_name: str | None
    cashier_name: str
    subtotal: Decimal
    discount_total: Decimal
    tax_total: Decimal
    old_gold_credit: Decimal
    grand_total: Decimal
    amount_paid: Decimal
    balance_returned: Decimal
    status: InvoiceStatus
    lines: list[InvoiceLineDetail]
    payments: list[PaymentDetail]


def get_invoice_detail(invoice_id: int) -> InvoiceDetail | None:
    """Full snapshot detail view -- reads only frozen invoice_items data, never recalculates."""
    with get_session() as session:
        invoice = session.get(Invoice, invoice_id)
        if invoice is None or invoice.is_deleted:
            return None

        lines = [
            InvoiceLineDetail(
                item_code=line.item.item_code,
                item_name=line.item.name,
                net_weight_g=Decimal(line.net_weight_g),
                purity=line.purity.value,
                gold_rate_used=Decimal(line.gold_rate_used),
                gold_value=Decimal(line.gold_value),
                making_charge=Decimal(line.making_charge),
                stone_value=Decimal(line.stone_value),
                line_discount=Decimal(line.line_discount),
                line_total=Decimal(line.line_total),
                is_returned=line.is_returned,
            )
            for line in invoice.items
        ]
        payments = [PaymentDetail(method=p.method.value, amount=Decimal(p.amount)) for p in invoice.payments]

        return InvoiceDetail(
            id=invoice.id,
            invoice_no=invoice.invoice_no,
            invoice_datetime=invoice.invoice_datetime,
            customer_name=invoice.customer.name if invoice.customer else None,
            cashier_name=invoice.cashier.full_name,
            subtotal=Decimal(invoice.subtotal),
            discount_total=Decimal(invoice.discount_total),
            tax_total=Decimal(invoice.tax_total),
            old_gold_credit=Decimal(invoice.old_gold_credit),
            grand_total=Decimal(invoice.grand_total),
            amount_paid=Decimal(invoice.amount_paid),
            balance_returned=Decimal(invoice.balance_returned),
            status=invoice.status,
            lines=lines,
            payments=payments,
        )


def cancel_invoice(invoice_id: int, reason: str, cancelled_by_user_id: int, cancelled_by_role: UserRole) -> None:
    """
    Same-day, ADMIN-only invoice cancellation. Reverses SOLD -> AVAILABLE
    on every line item and marks the invoice CANCELLED. Distinct from a
    Return: cancellation is a full same-day undo, not a partial refund.
    """
    if cancelled_by_role != UserRole.ADMIN:
        raise TransactionError("Only an administrator can cancel an invoice.")
    if not reason or not reason.strip():
        raise TransactionError("A cancellation reason is required.")

    with get_session() as session:
        invoice = session.get(Invoice, invoice_id)
        if invoice is None or invoice.is_deleted:
            raise TransactionError("Invoice not found.")
        if invoice.status == InvoiceStatus.CANCELLED:
            raise TransactionError("This invoice has already been cancelled.")
        if invoice.invoice_datetime.date() != date.today():
            raise TransactionError("Only same-day invoices can be cancelled.")

        for line in invoice.items:
            item = session.get(Item, line.item_id)
            if item is not None and item.status == ItemStatus.SOLD:
                item.status = ItemStatus.AVAILABLE
                item.sold_at = None
                item.sold_to_customer_id = None
                item.sold_by_user_id = None

        invoice.status = InvoiceStatus.CANCELLED
        invoice.cancel_reason = reason.strip()

        session.add(
            AuditLog(
                user_id=cancelled_by_user_id,
                action=f"Cancelled invoice {invoice.invoice_no}: {reason.strip()}",
                entity_type="Invoice",
                entity_id=invoice.id,
            )
        )
