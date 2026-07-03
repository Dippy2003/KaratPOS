"""
Item CRUD, item_code generation, and search/filter for the Inventory
screen. Live pricing is NOT computed here -- callers combine an Item
with app.services.pricing_service.calculate_item_price() and the
current gold rate.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import select

from app.database.db import get_session
from app.database.models import AuditLog, Item, ItemStatus, MakingChargeType, Purity


class ValidationError(Exception):
    """Raised for invalid item field values (never let raw exceptions reach the UI)."""


def _next_item_code(session) -> str:
    last = session.scalars(select(Item).order_by(Item.id.desc())).first()
    next_num = (last.id + 1) if last else 1
    return f"ITM-{next_num:06d}"


def _validate_item_fields(
    name: str,
    gross_weight_g: Decimal,
    net_weight_g: Decimal,
    making_charge_value: Decimal,
    stone_value_total: Decimal,
    cost_price: Decimal,
) -> None:
    if not name or not name.strip():
        raise ValidationError("Item name is required.")
    if gross_weight_g <= 0:
        raise ValidationError("Gross weight must be greater than zero.")
    if net_weight_g <= 0:
        raise ValidationError("Net weight must be greater than zero.")
    if net_weight_g > gross_weight_g:
        raise ValidationError("Net weight cannot exceed gross weight.")
    if making_charge_value < 0:
        raise ValidationError("Making charge cannot be negative.")
    if stone_value_total < 0:
        raise ValidationError("Stone value cannot be negative.")
    if cost_price < 0:
        raise ValidationError("Cost price cannot be negative.")
