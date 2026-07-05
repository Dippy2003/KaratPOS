"""Filterable audit log queries for the Audit Log Viewer screen (ADMIN only)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta

from sqlalchemy import select

from app.database.db import get_session
from app.database.models import AuditLog


@dataclass(frozen=True)
class AuditLogRow:
    id: int
    username: str
    action: str
    entity_type: str | None
    entity_id: int | None
    timestamp: datetime


def search_audit_log(
    user_id: int | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    action_contains: str | None = None,
    limit: int = 500,
) -> list[AuditLogRow]:
    with get_session() as session:
        stmt = select(AuditLog).order_by(AuditLog.timestamp.desc())

        if user_id is not None:
            stmt = stmt.where(AuditLog.user_id == user_id)
        if start_date is not None:
            stmt = stmt.where(AuditLog.timestamp >= datetime.combine(start_date, datetime.min.time()))
        if end_date is not None:
            stmt = stmt.where(AuditLog.timestamp < datetime.combine(end_date, datetime.min.time()) + timedelta(days=1))
        if action_contains:
            stmt = stmt.where(AuditLog.action.ilike(f"%{action_contains}%"))

        stmt = stmt.limit(limit)
        rows = session.scalars(stmt).all()
        return [
            AuditLogRow(
                id=r.id,
                username=r.user.username if r.user else "system",
                action=r.action,
                entity_type=r.entity_type,
                entity_id=r.entity_id,
                timestamp=r.timestamp,
            )
            for r in rows
        ]
