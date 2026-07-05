"""Custom/advance orders with installment payments toward a final balance."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import select

from app.database.db import get_session
from app.database.models import AdvanceOrder, AdvanceOrderStatus, AdvancePayment, AuditLog, PaymentMethod


class ValidationError(Exception):
    pass


@dataclass(frozen=True)
class AdvanceOrderRow:
    id: int
    customer_name: str
    description: str
    estimated_total: Decimal
    advance_paid: Decimal
    balance: Decimal
    due_date: date | None
    status: AdvanceOrderStatus


def _to_row(order: AdvanceOrder) -> AdvanceOrderRow:
    return AdvanceOrderRow(
        id=order.id,
        customer_name=order.customer.name,
        description=order.description,
        estimated_total=Decimal(order.estimated_total),
        advance_paid=Decimal(order.advance_paid),
        balance=Decimal(order.balance),
        due_date=order.due_date,
        status=order.status,
    )


def create_advance_order(
    customer_id: int,
    description: str,
    estimated_total: Decimal,
    initial_advance: Decimal,
    due_date: date | None,
    payment_method: PaymentMethod,
) -> AdvanceOrderRow:
    if not description or not description.strip():
        raise ValidationError("Description is required.")
    if estimated_total <= 0:
        raise ValidationError("Estimated total must be greater than zero.")
    if initial_advance < 0:
        raise ValidationError("Advance paid cannot be negative.")
    if initial_advance > estimated_total:
        raise ValidationError("Advance paid cannot exceed the estimated total.")

    with get_session() as session:
        order = AdvanceOrder(
            customer_id=customer_id,
            description=description.strip(),
            estimated_total=estimated_total,
            advance_paid=initial_advance,
            balance=estimated_total - initial_advance,
            due_date=due_date,
            status=AdvanceOrderStatus.OPEN,
        )
        session.add(order)
        session.flush()

        if initial_advance > 0:
            session.add(
                AdvancePayment(order_id=order.id, payment_date=date.today(), amount=initial_advance, method=payment_method)
            )

        session.add(
            AuditLog(
                user_id=None,
                action=f"Created advance order #{order.id} for Rs. {estimated_total:,.2f}",
                entity_type="AdvanceOrder",
                entity_id=order.id,
            )
        )
        return _to_row(order)


def record_installment_payment(order_id: int, amount: Decimal, method: PaymentMethod) -> AdvanceOrderRow:
    if amount <= 0:
        raise ValidationError("Payment amount must be greater than zero.")

    with get_session() as session:
        order = session.get(AdvanceOrder, order_id)
        if order is None:
            raise ValidationError("Advance order not found.")
        if order.status != AdvanceOrderStatus.OPEN:
            raise ValidationError(f"Cannot record a payment on a {order.status.value.lower()} order.")
        if amount > Decimal(order.balance):
            raise ValidationError(f"Payment (Rs. {amount:,.2f}) exceeds the remaining balance (Rs. {order.balance:,.2f}).")

        session.add(AdvancePayment(order_id=order.id, payment_date=date.today(), amount=amount, method=method))
        order.advance_paid = Decimal(order.advance_paid) + amount
        order.balance = Decimal(order.balance) - amount
        if order.balance <= 0:
            order.status = AdvanceOrderStatus.FULFILLED

        session.add(
            AuditLog(
                user_id=None,
                action=f"Recorded Rs. {amount:,.2f} installment on advance order #{order.id}",
                entity_type="AdvanceOrder",
                entity_id=order.id,
            )
        )
        return _to_row(order)


def get_all_advance_orders() -> list[AdvanceOrderRow]:
    with get_session() as session:
        rows = session.scalars(select(AdvanceOrder).order_by(AdvanceOrder.id.desc())).all()
        return [_to_row(o) for o in rows]
