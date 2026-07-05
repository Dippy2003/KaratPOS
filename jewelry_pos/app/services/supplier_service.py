"""Supplier CRUD for the Suppliers & Purchases screen."""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select

from app.database.db import get_session
from app.database.models import Supplier


class ValidationError(Exception):
    pass


@dataclass(frozen=True)
class SupplierRow:
    id: int
    name: str
    phone: str | None
    address: str | None
    notes: str | None


def _to_row(supplier: Supplier) -> SupplierRow:
    return SupplierRow(id=supplier.id, name=supplier.name, phone=supplier.phone, address=supplier.address, notes=supplier.notes)


def get_all_suppliers() -> list[SupplierRow]:
    with get_session() as session:
        rows = session.scalars(select(Supplier).order_by(Supplier.name)).all()
        return [_to_row(s) for s in rows]


def create_supplier(name: str, phone: str | None = None, address: str | None = None, notes: str | None = None) -> SupplierRow:
    if not name or not name.strip():
        raise ValidationError("Supplier name is required.")
    with get_session() as session:
        supplier = Supplier(name=name.strip(), phone=phone, address=address, notes=notes)
        session.add(supplier)
        session.flush()
        return _to_row(supplier)
