"""
Cart reservation locking. The moment an item is added to a POS cart it
flips AVAILABLE -> RESERVED so a second cashier/terminal cannot sell it
concurrently. Removing it from the cart (or the cart being abandoned)
must release it back to AVAILABLE -- see also
app.services.startup_service.release_orphaned_reservations() for the
crash-recovery counterpart.
"""
from __future__ import annotations

from datetime import datetime

from app.database.db import get_session
from app.database.models import Item, ItemStatus


class ReservationError(Exception):
    """Raised when an item cannot be reserved (already sold/reserved/deleted)."""


def reserve_item(item_id: int, user_id: int) -> None:
    with get_session() as session:
        item = session.get(Item, item_id)
        if item is None or item.is_deleted:
            raise ReservationError("Item not found.")
        if item.status != ItemStatus.AVAILABLE:
            raise ReservationError(
                f"Item {item.item_code} is not available (status: {item.status.value})."
            )
        item.status = ItemStatus.RESERVED
        item.reserved_by_id = user_id
        item.reserved_at = datetime.utcnow()


def release_item(item_id: int) -> None:
    """Release a RESERVED item back to AVAILABLE (removed from cart / cart abandoned)."""
    with get_session() as session:
        item = session.get(Item, item_id)
        if item is None:
            return
        if item.status == ItemStatus.RESERVED:
            item.status = ItemStatus.AVAILABLE
            item.reserved_by_id = None
            item.reserved_at = None
