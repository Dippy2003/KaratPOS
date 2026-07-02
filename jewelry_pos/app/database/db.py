"""
SQLAlchemy engine/session management for the offline SQLite database.

Exposes:
    engine        - the SQLAlchemy Engine bound to data/jewelry_pos.db
    SessionLocal  - a sessionmaker factory
    get_session() - context manager yielding a Session with commit/rollback
    init_db()     - creates all tables (idempotent) and enables FK constraints
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.utils.config import DATABASE_URL

# `check_same_thread=False` is required because Qt may hand work to the
# main thread's session from callbacks; we still keep one session per
# unit-of-work via get_session() to avoid cross-thread sharing of a single
# Session instance.
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    future=True,
)


@event.listens_for(Engine, "connect")
def _enable_sqlite_foreign_keys(dbapi_connection, connection_record):
    """SQLite ignores FK constraints unless explicitly enabled per-connection."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """Unit-of-work context manager: commits on success, rolls back on error."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db() -> None:
    """Create all tables that don't already exist. Safe to call every startup."""
    from app.database import models  # noqa: F401  (ensure models are registered)

    models.Base.metadata.create_all(bind=engine)
