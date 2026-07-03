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


def add_rate(rate_date: date, purity: Purity, rate_per_gram: Decimal, entered_by_id: int) -> None:
    """Add today's (or a backdated) rate for one purity. Fails if one already exists."""
    with get_session() as session:
        existing = session.scalar(
            select(GoldRate).where(GoldRate.rate_date == rate_date, GoldRate.purity == purity)
        )
        if existing:
            raise DuplicateRateError(
                f"A rate for {purity.value} on {rate_date.isoformat()} already exists "
                f"(Rs. {existing.rate_per_gram}/g). Rates cannot be edited, only added going forward."
            )

        session.add(
            GoldRate(
                rate_date=rate_date,
                purity=purity,
                rate_per_gram=rate_per_gram,
                entered_by_id=entered_by_id,
            )
        )
        session.add(
            AuditLog(
                user_id=entered_by_id,
                action=f"Entered gold rate {purity.value} = Rs.{rate_per_gram}/g for {rate_date.isoformat()}",
                entity_type="GoldRate",
                entity_id=None,
            )
        )
