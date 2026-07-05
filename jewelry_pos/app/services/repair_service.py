"""Repair job tracking: intake, status progression, and overdue detection for the dashboard."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import select

from app.database.db import get_session
from app.database.models import AuditLog, Repair, RepairStatus


class ValidationError(Exception):
    pass


@dataclass(frozen=True)
class RepairRow:
    id: int
    customer_name: str
    item_description: str
    issue: str
    received_date: date
    promised_date: date | None
    status: RepairStatus
    estimated_cost: Decimal
    final_cost: Decimal | None


def _to_row(repair: Repair) -> RepairRow:
    return RepairRow(
        id=repair.id,
        customer_name=repair.customer.name,
        item_description=repair.item_description,
        issue=repair.issue,
        received_date=repair.received_date,
        promised_date=repair.promised_date,
        status=repair.status,
        estimated_cost=Decimal(repair.estimated_cost),
        final_cost=Decimal(repair.final_cost) if repair.final_cost is not None else None,
    )


def create_repair(
    customer_id: int,
    item_description: str,
    issue: str,
    promised_date: date | None,
    estimated_cost: Decimal,
    received_by_user_id: int,
) -> RepairRow:
    if not item_description or not item_description.strip():
        raise ValidationError("Item description is required.")
    if not issue or not issue.strip():
        raise ValidationError("Issue description is required.")
    if estimated_cost < 0:
        raise ValidationError("Estimated cost cannot be negative.")

    with get_session() as session:
        repair = Repair(
            customer_id=customer_id,
            item_description=item_description.strip(),
            issue=issue.strip(),
            received_date=date.today(),
            promised_date=promised_date,
            status=RepairStatus.RECEIVED,
            estimated_cost=estimated_cost,
            received_by_id=received_by_user_id,
        )
        session.add(repair)
        session.flush()
        session.add(
            AuditLog(
                user_id=received_by_user_id,
                action=f"Logged repair #{repair.id}: {item_description}",
                entity_type="Repair",
                entity_id=repair.id,
            )
        )
        return _to_row(repair)
