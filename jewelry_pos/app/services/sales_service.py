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


def complete_sale(
    *,
    cart: Cart,
    cashier_user_id: int,
    customer_id: int | None,
    invoice_discount: Decimal,
    tax_percent: Decimal,
    payments: list[PaymentInput],
    old_gold: OldGoldExchangeInput | None = None,
    old_gold_credit: Decimal = Decimal("0"),
) -> SaleResult:
    """
    Complete a POS sale as a single atomic transaction. On any failure,
    the whole thing rolls back -- no invoice, no item status change, no
    payment record survives a partial failure. Raises SaleError for any
    validation failure (never lets a raw exception reach the UI).
    """
    _validate_sale_inputs(cart, invoice_discount, tax_percent, payments, old_gold_credit)

    subtotal = cart.subtotal
    tax_total = (subtotal - invoice_discount) * tax_percent / Decimal("100")
    tax_total = tax_total.quantize(Decimal("0.01"))
    grand_total = subtotal - invoice_discount + tax_total - old_gold_credit

    amount_paid = sum((p.amount for p in payments), Decimal("0")) + old_gold_credit
    if amount_paid < grand_total:
        raise SaleError(
            f"Insufficient payment: Rs. {amount_paid:,.2f} paid against a total of Rs. {grand_total:,.2f}."
        )
    balance_returned = amount_paid - grand_total

    with get_session() as session:
        today = date.today()
        invoice_no = _next_invoice_no(session, today.year)

        invoice = Invoice(
            invoice_no=invoice_no,
            invoice_datetime=datetime.utcnow(),
            customer_id=customer_id,
            user_id=cashier_user_id,
            subtotal=subtotal,
            discount_total=invoice_discount,
            tax_total=tax_total,
            old_gold_credit=old_gold_credit,
            grand_total=grand_total,
            amount_paid=amount_paid,
            balance_returned=balance_returned,
            status=InvoiceStatus.COMPLETED,
        )
        session.add(invoice)
        session.flush()  # populate invoice.id

        # Distribute the invoice-level discount proportionally across lines
        # so each snapshot's line_total still sums to the invoice subtotal.
        for line in cart.lines:
            item = session.get(Item, line.item.id)
            if item is None or item.status != ItemStatus.RESERVED:
                raise SaleError(
                    f"Item {line.item.item_code} is no longer reserved for this sale. "
                    "It may have been sold by another terminal. Sale aborted."
                )

            line_share = (line.line_total / subtotal * invoice_discount) if subtotal > 0 else Decimal("0")
            line_share = line_share.quantize(Decimal("0.01"))

            session.add(
                InvoiceItem(
                    invoice_id=invoice.id,
                    item_id=item.id,
                    gold_rate_used=line.price.gold_rate_used,
                    purity=item.purity,
                    net_weight_g=line.price.net_weight_g,
                    gold_value=line.price.gold_value,
                    making_charge=line.price.making_charge,
                    stone_value=line.price.stone_value,
                    line_discount=line.line_discount + line_share,
                    line_total=line.line_total - line_share,
                )
            )

            item.status = ItemStatus.SOLD
            item.sold_at = datetime.utcnow()
            item.sold_to_customer_id = customer_id
            item.sold_by_user_id = cashier_user_id
            item.reserved_by_id = None
            item.reserved_at = None

        for payment in payments:
            session.add(Payment(invoice_id=invoice.id, method=payment.method, amount=payment.amount))

        if old_gold is not None and old_gold_credit > 0:
            session.add(
                OldGoldReceipt(
                    invoice_id=invoice.id,
                    customer_id=customer_id,
                    description=old_gold.description,
                    gross_weight_g=old_gold.gross_weight_g,
                    assessed_purity=old_gold.assessed_purity,
                    buy_rate_per_gram=old_gold.buy_rate_per_gram,
                    credit_value=old_gold.credit_value,
                    received_by_id=cashier_user_id,
                    status=ScrapStatus.IN_SCRAP_STOCK,
                )
            )
            session.add(
                Payment(invoice_id=invoice.id, method=PaymentMethod.OLD_GOLD, amount=old_gold_credit)
            )

        if customer_id is not None:
            customer = session.get(Customer, customer_id)
            if customer is not None:
                customer.total_spent = Decimal(customer.total_spent) + grand_total

        session.add(
            AuditLog(
                user_id=cashier_user_id,
                action=f"Completed sale {invoice_no} for Rs. {grand_total:,.2f}",
                entity_type="Invoice",
                entity_id=invoice.id,
            )
        )

        return SaleResult(
            invoice_id=invoice.id,
            invoice_no=invoice_no,
            grand_total=grand_total,
            balance_returned=balance_returned,
        )
