"""Simple read-side helpers for categories, used to populate combo boxes."""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select

from app.database.db import get_session
from app.database.models import Category


@dataclass(frozen=True)
class CategoryRow:
    id: int
    name: str
    low_stock_threshold: int


def get_all_categories() -> list[CategoryRow]:
    with get_session() as session:
        rows = session.scalars(select(Category).order_by(Category.name)).all()
        return [CategoryRow(id=c.id, name=c.name, low_stock_threshold=c.low_stock_threshold) for c in rows]


def get_low_stock_categories() -> list[tuple[str, int, int]]:
    """Categories where AVAILABLE item count has dropped below the threshold. Returns (name, count, threshold)."""
    from app.services.item_service import count_available_by_category

    with get_session() as session:
        categories = session.scalars(select(Category)).all()
        low_stock = []
        for cat in categories:
            count = count_available_by_category(cat.id)
            if count < cat.low_stock_threshold:
                low_stock.append((cat.name, count, cat.low_stock_threshold))
        return low_stock
