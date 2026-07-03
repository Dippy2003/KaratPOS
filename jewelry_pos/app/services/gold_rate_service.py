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


def get_latest_rate(purity: Purity) -> RateRow | None:
    """The most recent rate on or before today for one purity, or None if none exists yet."""
    with get_session() as session:
        row = session.scalar(
            select(GoldRate)
            .where(GoldRate.purity == purity, GoldRate.rate_date <= date.today())
            .order_by(GoldRate.rate_date.desc(), GoldRate.id.desc())
        )
        if row is None:
            return None
        return RateRow(
            id=row.id,
            rate_date=row.rate_date,
            purity=row.purity,
            rate_per_gram=Decimal(row.rate_per_gram),
            entered_by=row.entered_by_user.full_name,
            entered_at=row.entered_at,
        )


def get_latest_rates_all_purities() -> dict[Purity, RateRow | None]:
    """Latest rate per purity, for the always-visible header display."""
    return {purity: get_latest_rate(purity) for purity in Purity}


def has_todays_rate_for_all_purities() -> bool:
    rates = get_latest_rates_all_purities()
    return all(row is not None and row.rate_date == date.today() for row in rates.values())


def get_rate_history(limit: int = 200) -> list[RateRow]:
    """Full rate history, most recent first, for the Gold Rate Management screen."""
    with get_session() as session:
        rows = session.scalars(
            select(GoldRate).order_by(GoldRate.rate_date.desc(), GoldRate.id.desc()).limit(limit)
        ).all()
        return [
            RateRow(
                id=r.id,
                rate_date=r.rate_date,
                purity=r.purity,
                rate_per_gram=Decimal(r.rate_per_gram),
                entered_by=r.entered_by_user.full_name,
                entered_at=r.entered_at,
            )
            for r in rows
        ]
