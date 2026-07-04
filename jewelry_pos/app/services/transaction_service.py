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
