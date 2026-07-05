"""
Stock take: staff scan every physical AVAILABLE item; this compares
scanned codes against the expected AVAILABLE set and reports any
missing (expected but not scanned) or unexpected (scanned but not
AVAILABLE in the system, e.g. already sold) items.
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select

from app.database.db import get_session
from app.database.models import Item, ItemStatus


@dataclass(frozen=True)
class StockTakeResult:
    expected_count: int
    scanned_count: int
    matched_count: int
    missing_codes: list[str]  # expected AVAILABLE but never scanned
    unexpected_codes: list[str]  # scanned but not currently AVAILABLE (sold/reserved/unknown)


def get_expected_available_codes() -> set[str]:
    with get_session() as session:
        rows = session.scalars(
            select(Item.item_code).where(Item.status == ItemStatus.AVAILABLE, Item.is_deleted.is_(False))
        ).all()
        return set(rows)


def reconcile_stock_take(scanned_codes: list[str]) -> StockTakeResult:
    expected = get_expected_available_codes()
    scanned = set(scanned_codes)

    matched = expected & scanned
    missing = expected - scanned
    unexpected = scanned - expected

    return StockTakeResult(
        expected_count=len(expected),
        scanned_count=len(scanned),
        matched_count=len(matched),
        missing_codes=sorted(missing),
        unexpected_codes=sorted(unexpected),
    )
