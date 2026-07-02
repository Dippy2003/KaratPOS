"""
Startup recovery: on every launch, any item left RESERVED by a cart that
never completed (app crash, force-close) must be released back to
AVAILABLE. There is no "open cart" table -- reservation lifetime is
tied to the POS session in memory, so any RESERVED item found at
startup is, by definition, an orphaned reservation from a previous run.
"""
from __future__ import annotations

from sqlalchemy import select

from app.database.db import get_session
from app.database.models import AuditLog, Item, ItemStatus


def release_orphaned_reservations() -> int:
    with get_session() as session:
        orphaned = session.scalars(
            select(Item).where(Item.status == ItemStatus.RESERVED)
        ).all()
        for item in orphaned:
            item.status = ItemStatus.AVAILABLE
            item.reserved_by_id = None
            item.reserved_at = None
            session.add(
                AuditLog(
                    user_id=None,
                    action=f"Released orphaned reservation on startup for item {item.item_code}",
                    entity_type="Item",
                    entity_id=item.id,
                )
            )
        return len(orphaned)
