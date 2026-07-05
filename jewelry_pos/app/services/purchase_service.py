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


def create_purchase(
    supplier_id: int,
    lines: list[PurchaseLineInput],
    notes: str | None = None,
    created_by_user_id: int | None = None,
) -> PurchaseResult:
    """Record a goods-receiving purchase, creating one new Item per line."""
    if not lines:
        raise ValidationError("A purchase must have at least one item line.")
    for line in lines:
        if line.net_weight_g > line.gross_weight_g:
            raise ValidationError(f"Net weight cannot exceed gross weight for '{line.name}'.")
        if line.gross_weight_g <= 0 or line.net_weight_g <= 0:
            raise ValidationError(f"Weights must be greater than zero for '{line.name}'.")

    with get_session() as session:
        purchase = Purchase(supplier_id=supplier_id, purchase_date=date.today(), notes=notes)
        session.add(purchase)
        session.flush()

        created_codes = []
        for line in lines:
            item_code = _next_item_code(session)
            item = Item(
                item_code=item_code,
                name=line.name,
                category_id=line.category_id,
                purity=line.purity,
                gross_weight_g=line.gross_weight_g,
                net_weight_g=line.net_weight_g,
                making_charge_type=line.making_charge_type,
                making_charge_value=line.making_charge_value,
                stone_value_total=line.stone_value_total,
                supplier_id=supplier_id,
                cost_price=line.cost_price,
                status=ItemStatus.AVAILABLE,
                date_added=date.today(),
            )
            session.add(item)
            session.flush()  # populate item.id

            session.add(PurchaseItem(purchase_id=purchase.id, item_id=item.id, cost=line.cost_price))
            created_codes.append(item_code)

        session.add(
            AuditLog(
                user_id=created_by_user_id,
                action=f"Recorded purchase #{purchase.id} from supplier {supplier_id}: {len(lines)} item(s) received",
                entity_type="Purchase",
                entity_id=purchase.id,
            )
        )

        return PurchaseResult(purchase_id=purchase.id, created_item_codes=created_codes)
