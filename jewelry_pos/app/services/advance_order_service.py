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
