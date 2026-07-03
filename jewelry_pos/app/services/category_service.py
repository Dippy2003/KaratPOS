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
