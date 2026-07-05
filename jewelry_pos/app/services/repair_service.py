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
