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
