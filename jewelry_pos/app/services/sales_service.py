"""
Sale completion -- the single most critical transaction in the system.
complete_sale() must be all-or-nothing: invoice + invoice_items (with
frozen price snapshots) + payments + old_gold_receipts + item status
flips (RESERVED -> SOLD) + customer.total_spent update + audit log all
happen in ONE DB transaction. Any failure rolls back everything so no
item is ever left half-sold. Receipt printing happens AFTER commit, in
the UI layer -- a printer failure must never lose the sale itself.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import select

from app.database.db import get_session
from app.database.models import (
    AuditLog,
    Customer,
    Invoice,
    InvoiceItem,
    InvoiceStatus,
    Item,
    ItemStatus,
    OldGoldReceipt,
    Payment,
    PaymentMethod,
    Purity,
    ScrapStatus,
)
from app.services.cart import Cart


class SaleError(Exception):
    """Raised for any condition that must abort Complete Sale before commit."""


@dataclass(frozen=True)
class OldGoldExchangeInput:
    description: str
    gross_weight_g: Decimal
    assessed_purity: Purity
    buy_rate_per_gram: Decimal
    credit_value: Decimal


@dataclass(frozen=True)
class PaymentInput:
    method: PaymentMethod
    amount: Decimal


@dataclass(frozen=True)
class SaleResult:
    invoice_id: int
    invoice_no: str
    grand_total: Decimal
    balance_returned: Decimal


def _next_invoice_no(session, year: int) -> str:
    """INV-<year>-000001, auto-incrementing per calendar year."""
    prefix = f"INV-{year}-"
    last = session.scalar(
        select(Invoice)
        .where(Invoice.invoice_no.like(f"{prefix}%"))
        .order_by(Invoice.id.desc())
    )
    if last is None:
        next_num = 1
    else:
        next_num = int(last.invoice_no.split("-")[-1]) + 1
    return f"{prefix}{next_num:06d}"


def _validate_sale_inputs(
    cart: Cart,
    invoice_discount: Decimal,
    tax_percent: Decimal,
    payments: list[PaymentInput],
    old_gold_credit: Decimal,
) -> None:
    if not cart.lines:
        raise SaleError("Cannot complete a sale with an empty cart.")
    if invoice_discount < 0:
        raise SaleError("Discount cannot be negative.")
    if invoice_discount > cart.subtotal:
        raise SaleError("Discount cannot exceed the cart subtotal.")
    if tax_percent < 0:
        raise SaleError("Tax percent cannot be negative.")
    if not payments and old_gold_credit <= 0:
        raise SaleError("At least one payment method (or old gold credit) is required.")
    if any(p.amount < 0 for p in payments):
        raise SaleError("Payment amounts cannot be negative.")
