"""
Gold rate history management. Rates are append-only -- there is no
"edit rate" operation, only "add a new rate for today" (unique per
date+purity). This preserves the historical record required for
invoice price snapshots to remain meaningful.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import select

from app.database.db import get_session
from app.database.models import AuditLog, GoldRate, Purity


class DuplicateRateError(Exception):
    """Raised when a rate for this date+purity already exists."""


@dataclass(frozen=True)
class RateRow:
    id: int
    rate_date: date
    purity: Purity
    rate_per_gram: Decimal
    entered_by: str
    entered_at: object
