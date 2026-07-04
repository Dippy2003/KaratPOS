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
