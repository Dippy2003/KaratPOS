"""
Authentication service: username/password verification against bcrypt
hashes, plus login/logout audit logging. No SQL or bcrypt calls belong
in UI code -- the login window only calls functions in this module.
"""
from __future__ import annotations

from dataclasses import dataclass

import bcrypt
from sqlalchemy import select

from app.database.db import get_session
from app.database.models import AuditLog, User, UserRole


@dataclass(frozen=True)
class AuthResult:
    success: bool
    user_id: int | None = None
    username: str | None = None
    full_name: str | None = None
    role: UserRole | None = None
    must_change_password: bool = False
    error: str | None = None


def authenticate(username: str, password: str) -> AuthResult:
    """Verify credentials and log the attempt. Never raises on bad input."""
    username = (username or "").strip()
    if not username or not password:
        return AuthResult(success=False, error="Username and password are required.")

    with get_session() as session:
        user = session.scalar(select(User).where(User.username == username))

        if user is None or not bcrypt.checkpw(password.encode("utf-8"), user.password_hash.encode("utf-8")):
            session.add(
                AuditLog(
                    user_id=user.id if user else None,
                    action=f"Failed login attempt for username '{username}'",
                    entity_type="User",
                    entity_id=user.id if user else None,
                )
            )
            return AuthResult(success=False, error="Invalid username or password.")

        if not user.is_active:
            session.add(
                AuditLog(
                    user_id=user.id,
                    action=f"Login blocked: user '{username}' is inactive",
                    entity_type="User",
                    entity_id=user.id,
                )
            )
            return AuthResult(success=False, error="This account has been deactivated.")

        session.add(
            AuditLog(
                user_id=user.id,
                action=f"User '{username}' logged in",
                entity_type="User",
                entity_id=user.id,
            )
        )

        return AuthResult(
            success=True,
            user_id=user.id,
            username=user.username,
            full_name=user.full_name,
            role=user.role,
            must_change_password=user.must_change_password,
        )


def log_logout(user_id: int, username: str) -> None:
    with get_session() as session:
        session.add(
            AuditLog(
                user_id=user_id,
                action=f"User '{username}' logged out",
                entity_type="User",
                entity_id=user_id,
            )
        )


def change_password(user_id: int, new_password: str) -> None:
    with get_session() as session:
        user = session.get(User, user_id)
        user.password_hash = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        user.must_change_password = False
        session.add(
            AuditLog(
                user_id=user_id,
                action=f"User '{user.username}' changed their password",
                entity_type="User",
                entity_id=user_id,
            )
        )
