"""
Customer lookup/create used by the POS screen (quick phone-number
lookup, walk-in sales create no customer at all) and Customer
Management screen in a later phase.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select

from app.database.db import get_session
from app.database.models import Customer


class ValidationError(Exception):
    pass


@dataclass(frozen=True)
class CustomerRow:
    id: int
    name: str
    phone: str | None
    address: str | None
    nic: str | None
    total_spent: Decimal


def _to_row(customer: Customer) -> CustomerRow:
    return CustomerRow(
        id=customer.id,
        name=customer.name,
        phone=customer.phone,
        address=customer.address,
        nic=customer.nic,
        total_spent=Decimal(customer.total_spent),
    )


def find_by_phone(phone: str) -> CustomerRow | None:
    with get_session() as session:
        customer = session.scalar(
            select(Customer).where(Customer.phone == phone, Customer.is_deleted.is_(False))
        )
        return _to_row(customer) if customer else None


def search_customers(query: str) -> list[CustomerRow]:
    with get_session() as session:
        like = f"%{query.strip()}%"
        rows = session.scalars(
            select(Customer).where(
                Customer.is_deleted.is_(False),
                (Customer.name.ilike(like)) | (Customer.phone.ilike(like)),
            )
        ).all()
        return [_to_row(c) for c in rows]


def create_customer(name: str, phone: str | None = None, address: str | None = None, nic: str | None = None) -> CustomerRow:
    if not name or not name.strip():
        raise ValidationError("Customer name is required.")
    with get_session() as session:
        customer = Customer(name=name.strip(), phone=phone, address=address, nic=nic)
        session.add(customer)
        session.flush()
        return _to_row(customer)
