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


def create_item(
    *,
    name: str,
    category_id: int,
    purity: Purity,
    gross_weight_g: Decimal,
    net_weight_g: Decimal,
    making_charge_type: MakingChargeType,
    making_charge_value: Decimal,
    stone_value_total: Decimal = Decimal("0"),
    stone_details: str | None = None,
    hallmark_certificate_no: str | None = None,
    supplier_id: int | None = None,
    cost_price: Decimal = Decimal("0"),
    photo_path: str | None = None,
    created_by_user_id: int | None = None,
) -> str:
    """Create a new item. Returns the generated item_code."""
    _validate_item_fields(name, gross_weight_g, net_weight_g, making_charge_value, stone_value_total, cost_price)

    with get_session() as session:
        item_code = _next_item_code(session)
        item = Item(
            item_code=item_code,
            name=name.strip(),
            category_id=category_id,
            purity=purity,
            gross_weight_g=gross_weight_g,
            net_weight_g=net_weight_g,
            making_charge_type=making_charge_type,
            making_charge_value=making_charge_value,
            stone_value_total=stone_value_total,
            stone_details=stone_details,
            hallmark_certificate_no=hallmark_certificate_no,
            supplier_id=supplier_id,
            cost_price=cost_price,
            photo_path=photo_path,
            status=ItemStatus.AVAILABLE,
            date_added=date.today(),
        )
        session.add(item)
        session.flush()  # populate item.id for the audit log
        session.add(
            AuditLog(
                user_id=created_by_user_id,
                action=f"Added item {item_code} ({name})",
                entity_type="Item",
                entity_id=item.id,
            )
        )
        return item_code


def update_item(item_id: int, updated_by_user_id: int | None = None, **fields) -> None:
    """
    Update mutable fields on an existing item. `fields` may include any of:
    name, category_id, purity, gross_weight_g, net_weight_g, making_charge_type,
    making_charge_value, stone_value_total, stone_details, hallmark_certificate_no,
    supplier_id, cost_price, photo_path.

    Price-affecting edits (weight, purity, making charge, stone value) are
    audit-logged individually since they change what customers will be charged.
    """
    price_affecting = {
        "gross_weight_g", "net_weight_g", "making_charge_type",
        "making_charge_value", "stone_value_total", "purity",
    }

    with get_session() as session:
        item = session.get(Item, item_id)
        if item is None or item.is_deleted:
            raise ValidationError("Item not found.")

        gross = fields.get("gross_weight_g", item.gross_weight_g)
        net = fields.get("net_weight_g", item.net_weight_g)
        making_value = fields.get("making_charge_value", item.making_charge_value)
        stone_value = fields.get("stone_value_total", item.stone_value_total)
        cost = fields.get("cost_price", item.cost_price)
        name = fields.get("name", item.name)
        _validate_item_fields(name, Decimal(gross), Decimal(net), Decimal(making_value), Decimal(stone_value), Decimal(cost))

        changed_price_fields = []
        for key, value in fields.items():
            if not hasattr(item, key):
                continue
            old_value = getattr(item, key)
            if key in price_affecting and old_value != value:
                changed_price_fields.append(f"{key}: {old_value} -> {value}")
            setattr(item, key, value)

        if changed_price_fields:
            session.add(
                AuditLog(
                    user_id=updated_by_user_id,
                    action=f"Edited price-affecting fields on {item.item_code}: " + "; ".join(changed_price_fields),
                    entity_type="Item",
                    entity_id=item.id,
                )
            )
