"""
Goods-receiving from suppliers. Creating a purchase immediately creates
the new inventory items it contains (with their cost prices), so the
Suppliers & Purchases screen can offer batch QR tag printing right
after a purchase is recorded, per the project brief.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.database.db import get_session
from app.database.models import (
    AuditLog,
    Item,
    ItemStatus,
    MakingChargeType,
    Purchase,
    PurchaseItem,
    Purity,
)


class ValidationError(Exception):
    pass


@dataclass(frozen=True)
class PurchaseLineInput:
    name: str
    category_id: int
    purity: Purity
    gross_weight_g: Decimal
    net_weight_g: Decimal
    making_charge_type: MakingChargeType
    making_charge_value: Decimal
    stone_value_total: Decimal
    cost_price: Decimal


@dataclass(frozen=True)
class PurchaseResult:
    purchase_id: int
    created_item_codes: list[str]


def _next_item_code(session) -> str:
    from sqlalchemy import select

    last = session.scalars(select(Item).order_by(Item.id.desc())).first()
    next_num = (last.id + 1) if last else 1
    return f"ITM-{next_num:06d}"
