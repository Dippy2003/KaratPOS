"""
Returns & exchanges. A return targets one invoice_item line (not the
whole invoice) so multi-item invoices support partial returns. This
is deliberately distinct from cancel_invoice() in transaction_service:
cancellation is a same-day, full, no-refund-tracking undo; a return
can happen on any past invoice, tracks a refund amount/method, and
lets staff decide per-item whether the piece is resellable (back to
AVAILABLE) or scrap (RETURNED_SCRAP).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from app.database.db import get_session
from app.database.models import (
    AuditLog,
    Customer,
    Invoice,
    InvoiceItem,
    InvoiceStatus,
    Item,
    ItemStatus,
    PaymentMethod,
    Return,
)


class ReturnError(Exception):
    pass


@dataclass(frozen=True)
class ReturnResult:
    return_id: int
    invoice_status: InvoiceStatus
    item_status: ItemStatus


def process_return(
    *,
    invoice_item_id: int,
    reason: str,
    refund_method: PaymentMethod,
    refund_amount: Decimal,
    restocked: bool,
    processed_by_user_id: int,
) -> ReturnResult:
    """
    Process a return for one invoice line. Single atomic transaction:
    marks the line returned, creates the Return record, flips the item
    to AVAILABLE (restock) or RETURNED_SCRAP, updates invoice status to
    RETURNED or PARTIALLY_RETURNED depending on whether other lines are
    still active, and reduces the customer's cached total_spent.
    """
    if not reason or not reason.strip():
        raise ReturnError("A return reason is required.")
    if refund_amount < 0:
        raise ReturnError("Refund amount cannot be negative.")

    with get_session() as session:
        invoice_item = session.get(InvoiceItem, invoice_item_id)
        if invoice_item is None:
            raise ReturnError("Invoice line not found.")
        if invoice_item.is_returned:
            raise ReturnError("This item has already been returned.")

        invoice = session.get(Invoice, invoice_item.invoice_id)
        if invoice is None or invoice.is_deleted:
            raise ReturnError("Invoice not found.")
        if invoice.status == InvoiceStatus.CANCELLED:
            raise ReturnError("Cannot return an item from a cancelled invoice.")
        if refund_amount > invoice_item.line_total:
            raise ReturnError("Refund amount cannot exceed the original line total.")

        item = session.get(Item, invoice_item.item_id)
        if item is None:
            raise ReturnError("Item record not found.")

        invoice_item.is_returned = True
        item.status = ItemStatus.AVAILABLE if restocked else ItemStatus.RETURNED_SCRAP
        if restocked:
            item.sold_at = None
            item.sold_to_customer_id = None
            item.sold_by_user_id = None

        return_record = Return(
            invoice_id=invoice.id,
            invoice_item_id=invoice_item.id,
            return_date=datetime.utcnow(),
            reason=reason.strip(),
            refund_method=refund_method,
            refund_amount=refund_amount,
            restocked=restocked,
            processed_by_id=processed_by_user_id,
        )
        session.add(return_record)

        remaining_active_lines = [li for li in invoice.items if not li.is_returned]
        if not remaining_active_lines:
            invoice.status = InvoiceStatus.RETURNED
        else:
            invoice.status = InvoiceStatus.PARTIALLY_RETURNED

        if invoice.customer_id is not None:
            customer = session.get(Customer, invoice.customer_id)
            if customer is not None:
                customer.total_spent = max(Decimal(customer.total_spent) - refund_amount, Decimal("0"))

        session.add(
            AuditLog(
                user_id=processed_by_user_id,
                action=(
                    f"Processed return for item {item.item_code} on invoice {invoice.invoice_no}: "
                    f"Rs. {refund_amount:,.2f} via {refund_method.value} "
                    f"({'restocked' if restocked else 'scrapped'})"
                ),
                entity_type="Return",
                entity_id=invoice_item.id,
            )
        )
        session.flush()

        return ReturnResult(
            return_id=return_record.id,
            invoice_status=invoice.status,
            item_status=item.status,
        )
