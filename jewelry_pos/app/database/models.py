"""
SQLAlchemy ORM models for the Jewelry Shop ERP/POS system.

Design rules enforced throughout this file (see project brief):
  * Money is NEVER a float. All currency columns use Numeric(12, 2)
    and are handled as Python Decimal in the service layer.
  * Item prices are never stored on the item -- only the raw inputs
    (weight, purity, making charge, stone value) that feed the live
    pricing formula. See app.services.pricing.
  * Invoice line items freeze a full price SNAPSHOT at sale time so
    historical invoices never change when gold rates change later.
  * Financial/inventory records use soft delete (is_deleted) --
    invoices, items, and customers are never hard-deleted.
  * Every table has id, created_at, updated_at via TimestampMixin.
"""
from __future__ import annotations

import enum
from datetime import datetime, date as date_

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    """created_at / updated_at columns shared by every table."""

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class SoftDeleteMixin:
    """is_deleted flag for financial/inventory records that must never be hard-deleted."""

    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    CASHIER = "CASHIER"
    SALES = "SALES"


class Purity(str, enum.Enum):
    K24 = "24K"
    K22 = "22K"
    K21 = "21K"
    K18 = "18K"


class MakingChargeType(str, enum.Enum):
    FLAT = "FLAT"
    PERCENT = "PERCENT"


class ItemStatus(str, enum.Enum):
    AVAILABLE = "AVAILABLE"
    RESERVED = "RESERVED"
    SOLD = "SOLD"
    RETURNED_SCRAP = "RETURNED_SCRAP"
    IN_REPAIR = "IN_REPAIR"


class InvoiceStatus(str, enum.Enum):
    COMPLETED = "COMPLETED"
    RETURNED = "RETURNED"
    PARTIALLY_RETURNED = "PARTIALLY_RETURNED"
    CANCELLED = "CANCELLED"


class PaymentMethod(str, enum.Enum):
    CASH = "CASH"
    CARD = "CARD"
    BANK_TRANSFER = "BANK_TRANSFER"
    MOBILE = "MOBILE"
    OLD_GOLD = "OLD_GOLD"


class ScrapStatus(str, enum.Enum):
    IN_SCRAP_STOCK = "IN_SCRAP_STOCK"
    MELTED = "MELTED"


class RepairStatus(str, enum.Enum):
    RECEIVED = "RECEIVED"
    IN_PROGRESS = "IN_PROGRESS"
    READY = "READY"
    DELIVERED = "DELIVERED"


class AdvanceOrderStatus(str, enum.Enum):
    OPEN = "OPEN"
    FULFILLED = "FULFILLED"
    CANCELLED = "CANCELLED"


# Money columns: 12 total digits, 2 decimal places -> up to Rs. 9,999,999,999.99
Money = Numeric(12, 2)


# ---------------------------------------------------------------------------
# 1. users
# ---------------------------------------------------------------------------
class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    gold_rates_entered: Mapped[list["GoldRate"]] = relationship(back_populates="entered_by_user")

    def __repr__(self) -> str:
        return f"<User {self.username} ({self.role.value})>"


# ---------------------------------------------------------------------------
# 2. gold_rates -- append-only history, NEVER overwritten/updated in place
# ---------------------------------------------------------------------------
class GoldRate(Base, TimestampMixin):
    __tablename__ = "gold_rates"
    __table_args__ = (UniqueConstraint("rate_date", "purity", name="uq_gold_rate_date_purity"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rate_date: Mapped[date_] = mapped_column(Date, nullable=False, default=date_.today, index=True)
    purity: Mapped[Purity] = mapped_column(Enum(Purity), nullable=False)
    rate_per_gram: Mapped[Money] = mapped_column(Money, nullable=False)
    entered_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    entered_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    entered_by_user: Mapped["User"] = relationship(back_populates="gold_rates_entered")

    def __repr__(self) -> str:
        return f"<GoldRate {self.rate_date} {self.purity.value}={self.rate_per_gram}>"


# ---------------------------------------------------------------------------
# 3. categories
# ---------------------------------------------------------------------------
class Category(Base, TimestampMixin):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    low_stock_threshold: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    items: Mapped[list["Item"]] = relationship(back_populates="category")

    def __repr__(self) -> str:
        return f"<Category {self.name}>"


# ---------------------------------------------------------------------------
# 4. suppliers
# ---------------------------------------------------------------------------
class Supplier(Base, TimestampMixin):
    __tablename__ = "suppliers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    items: Mapped[list["Item"]] = relationship(back_populates="supplier")
    purchases: Mapped[list["Purchase"]] = relationship(back_populates="supplier")

    def __repr__(self) -> str:
        return f"<Supplier {self.name}>"
