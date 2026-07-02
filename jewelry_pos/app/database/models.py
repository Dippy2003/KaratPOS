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
from decimal import Decimal

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


# ---------------------------------------------------------------------------
# 5. items
# ---------------------------------------------------------------------------
# NOTE: this table intentionally has NO price column. Sale price is always
# computed live from (net_weight_g, purity, making_charge, stone_value_total)
# against the latest GoldRate -- see app.services.pricing.calculate_item_price().
class Item(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    item_code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), nullable=False)
    purity: Mapped[Purity] = mapped_column(Enum(Purity), nullable=False)

    gross_weight_g: Mapped[Numeric] = mapped_column(Numeric(10, 3), nullable=False)
    net_weight_g: Mapped[Numeric] = mapped_column(Numeric(10, 3), nullable=False)

    making_charge_type: Mapped[MakingChargeType] = mapped_column(Enum(MakingChargeType), nullable=False)
    # FLAT -> absolute Rs. value. PERCENT -> percentage of gold value (e.g. 12.5 = 12.5%).
    making_charge_value: Mapped[Money] = mapped_column(Money, nullable=False, default=0)

    stone_value_total: Mapped[Money] = mapped_column(Money, nullable=False, default=0)
    stone_details: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON-encoded list

    hallmark_certificate_no: Mapped[str | None] = mapped_column(String(100), nullable=True)
    supplier_id: Mapped[int | None] = mapped_column(ForeignKey("suppliers.id"), nullable=True)
    cost_price: Mapped[Money] = mapped_column(Money, nullable=False, default=0)
    photo_path: Mapped[str | None] = mapped_column(String(255), nullable=True)

    status: Mapped[ItemStatus] = mapped_column(Enum(ItemStatus), default=ItemStatus.AVAILABLE, nullable=False, index=True)
    date_added: Mapped[date_] = mapped_column(Date, default=date_.today, nullable=False)

    # Reservation bookkeeping so a crashed app releases items back to AVAILABLE on startup.
    reserved_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    reserved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Sale bookkeeping (set when status flips RESERVED -> SOLD in Complete Sale).
    sold_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    sold_to_customer_id: Mapped[int | None] = mapped_column(ForeignKey("customers.id"), nullable=True)
    sold_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    category: Mapped["Category"] = relationship(back_populates="items")
    supplier: Mapped["Supplier | None"] = relationship(back_populates="items")
    invoice_items: Mapped[list["InvoiceItem"]] = relationship(back_populates="item")

    def __repr__(self) -> str:
        return f"<Item {self.item_code} {self.name} ({self.status.value})>"


# ---------------------------------------------------------------------------
# 6. customers
# ---------------------------------------------------------------------------
class Customer(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    nic: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # Cached/derived total; recomputed from invoices, kept for fast dashboard lookups.
    total_spent: Mapped[Money] = mapped_column(Money, nullable=False, default=0)

    invoices: Mapped[list["Invoice"]] = relationship(back_populates="customer")

    def __repr__(self) -> str:
        return f"<Customer {self.name} ({self.phone})>"


# ---------------------------------------------------------------------------
# 7. invoices
# ---------------------------------------------------------------------------
class Invoice(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    invoice_no: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    invoice_datetime: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    customer_id: Mapped[int | None] = mapped_column(ForeignKey("customers.id"), nullable=True)  # walk-in allowed
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)  # cashier

    subtotal: Mapped[Money] = mapped_column(Money, nullable=False, default=0)
    discount_total: Mapped[Money] = mapped_column(Money, nullable=False, default=0)
    tax_total: Mapped[Money] = mapped_column(Money, nullable=False, default=0)
    old_gold_credit: Mapped[Money] = mapped_column(Money, nullable=False, default=0)
    grand_total: Mapped[Money] = mapped_column(Money, nullable=False, default=0)
    amount_paid: Mapped[Money] = mapped_column(Money, nullable=False, default=0)
    balance_returned: Mapped[Money] = mapped_column(Money, nullable=False, default=0)

    status: Mapped[InvoiceStatus] = mapped_column(Enum(InvoiceStatus), default=InvoiceStatus.COMPLETED, nullable=False)
    cancel_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    customer: Mapped["Customer | None"] = relationship(back_populates="invoices")
    cashier: Mapped["User"] = relationship(foreign_keys=[user_id])
    items: Mapped[list["InvoiceItem"]] = relationship(back_populates="invoice", cascade="all, delete-orphan")
    payments: Mapped[list["Payment"]] = relationship(back_populates="invoice", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Invoice {self.invoice_no} {self.status.value}>"


# ---------------------------------------------------------------------------
# 8. invoice_items -- FULL PRICE SNAPSHOT frozen at sale time
# ---------------------------------------------------------------------------
class InvoiceItem(Base, TimestampMixin):
    __tablename__ = "invoice_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id"), nullable=False)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"), nullable=False)

    # --- frozen snapshot: never recompute these from current rates ---
    gold_rate_used: Mapped[Money] = mapped_column(Money, nullable=False)
    purity: Mapped[Purity] = mapped_column(Enum(Purity), nullable=False)
    net_weight_g: Mapped[Numeric] = mapped_column(Numeric(10, 3), nullable=False)
    gold_value: Mapped[Money] = mapped_column(Money, nullable=False)
    making_charge: Mapped[Money] = mapped_column(Money, nullable=False)
    stone_value: Mapped[Money] = mapped_column(Money, nullable=False)
    line_discount: Mapped[Money] = mapped_column(Money, nullable=False, default=0)
    line_total: Mapped[Money] = mapped_column(Money, nullable=False)
    # --- end snapshot ---

    is_returned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    invoice: Mapped["Invoice"] = relationship(back_populates="items")
    item: Mapped["Item"] = relationship(back_populates="invoice_items")

    def __repr__(self) -> str:
        return f"<InvoiceItem invoice={self.invoice_id} item={self.item_id} total={self.line_total}>"


# ---------------------------------------------------------------------------
# 9. payments -- multiple rows per invoice enables mixed payments
# ---------------------------------------------------------------------------
class Payment(Base, TimestampMixin):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id"), nullable=False)
    method: Mapped[PaymentMethod] = mapped_column(Enum(PaymentMethod), nullable=False)
    amount: Mapped[Money] = mapped_column(Money, nullable=False)

    invoice: Mapped["Invoice"] = relationship(back_populates="payments")

    def __repr__(self) -> str:
        return f"<Payment {self.method.value} {self.amount}>"


# ---------------------------------------------------------------------------
# 10. old_gold_receipts -- can be tied to a sale (exchange) or standalone buy-back
# ---------------------------------------------------------------------------
class OldGoldReceipt(Base, TimestampMixin):
    __tablename__ = "old_gold_receipts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    invoice_id: Mapped[int | None] = mapped_column(ForeignKey("invoices.id"), nullable=True)
    customer_id: Mapped[int | None] = mapped_column(ForeignKey("customers.id"), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    gross_weight_g: Mapped[Numeric] = mapped_column(Numeric(10, 3), nullable=False)
    assessed_purity: Mapped[Purity] = mapped_column(Enum(Purity), nullable=False)
    buy_rate_per_gram: Mapped[Money] = mapped_column(Money, nullable=False)
    credit_value: Mapped[Money] = mapped_column(Money, nullable=False)
    received_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    status: Mapped[ScrapStatus] = mapped_column(Enum(ScrapStatus), default=ScrapStatus.IN_SCRAP_STOCK, nullable=False)

    invoice: Mapped["Invoice | None"] = relationship()
    customer: Mapped["Customer | None"] = relationship()
    received_by: Mapped["User"] = relationship()

    def __repr__(self) -> str:
        return f"<OldGoldReceipt {self.gross_weight_g}g {self.assessed_purity.value} credit={self.credit_value}>"


# ---------------------------------------------------------------------------
# 11. returns
# ---------------------------------------------------------------------------
class Return(Base, TimestampMixin):
    __tablename__ = "returns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id"), nullable=False)
    invoice_item_id: Mapped[int] = mapped_column(ForeignKey("invoice_items.id"), nullable=False)
    return_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    refund_method: Mapped[PaymentMethod] = mapped_column(Enum(PaymentMethod), nullable=False)
    refund_amount: Mapped[Money] = mapped_column(Money, nullable=False)
    restocked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    processed_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    invoice: Mapped["Invoice"] = relationship()
    invoice_item: Mapped["InvoiceItem"] = relationship()
    processed_by: Mapped["User"] = relationship()

    def __repr__(self) -> str:
        return f"<Return invoice_item={self.invoice_item_id} refund={self.refund_amount}>"


# ---------------------------------------------------------------------------
# 12. purchases / purchase_items -- goods-receiving from suppliers
# ---------------------------------------------------------------------------
class Purchase(Base, TimestampMixin):
    __tablename__ = "purchases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id"), nullable=False)
    purchase_date: Mapped[date_] = mapped_column(Date, default=date_.today, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    supplier: Mapped["Supplier"] = relationship(back_populates="purchases")
    purchase_items: Mapped[list["PurchaseItem"]] = relationship(back_populates="purchase", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Purchase #{self.id} supplier={self.supplier_id}>"


class PurchaseItem(Base, TimestampMixin):
    __tablename__ = "purchase_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    purchase_id: Mapped[int] = mapped_column(ForeignKey("purchases.id"), nullable=False)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"), nullable=False)
    cost: Mapped[Money] = mapped_column(Money, nullable=False)

    purchase: Mapped["Purchase"] = relationship(back_populates="purchase_items")
    item: Mapped["Item"] = relationship()

    def __repr__(self) -> str:
        return f"<PurchaseItem purchase={self.purchase_id} item={self.item_id} cost={self.cost}>"


# ---------------------------------------------------------------------------
# 13. repairs
# ---------------------------------------------------------------------------
class Repair(Base, TimestampMixin):
    __tablename__ = "repairs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), nullable=False)
    item_description: Mapped[str] = mapped_column(Text, nullable=False)
    issue: Mapped[str] = mapped_column(Text, nullable=False)
    received_date: Mapped[date_] = mapped_column(Date, default=date_.today, nullable=False)
    promised_date: Mapped[date_ | None] = mapped_column(Date, nullable=True)
    status: Mapped[RepairStatus] = mapped_column(Enum(RepairStatus), default=RepairStatus.RECEIVED, nullable=False)
    estimated_cost: Mapped[Money] = mapped_column(Money, nullable=False, default=0)
    final_cost: Mapped[Decimal | None] = mapped_column(Money, nullable=True)
    received_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    customer: Mapped["Customer"] = relationship()
    received_by: Mapped["User"] = relationship()

    def __repr__(self) -> str:
        return f"<Repair #{self.id} {self.status.value}>"


# ---------------------------------------------------------------------------
# 14. audit_logs
# ---------------------------------------------------------------------------
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(Text, nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    user: Mapped["User | None"] = relationship()

    def __repr__(self) -> str:
        return f"<AuditLog {self.timestamp} user={self.user_id} action={self.action!r}>"


# ---------------------------------------------------------------------------
# 15. settings -- simple key/value store
# ---------------------------------------------------------------------------
class Setting(Base, TimestampMixin):
    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    value: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<Setting {self.key}={self.value!r}>"


# ---------------------------------------------------------------------------
# 16. advance_orders / advance_payments -- custom orders with installments
# ---------------------------------------------------------------------------
class AdvanceOrder(Base, TimestampMixin):
    __tablename__ = "advance_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    estimated_total: Mapped[Money] = mapped_column(Money, nullable=False)
    advance_paid: Mapped[Money] = mapped_column(Money, nullable=False, default=0)
    balance: Mapped[Money] = mapped_column(Money, nullable=False)
    due_date: Mapped[date_ | None] = mapped_column(Date, nullable=True)
    status: Mapped[AdvanceOrderStatus] = mapped_column(Enum(AdvanceOrderStatus), default=AdvanceOrderStatus.OPEN, nullable=False)

    customer: Mapped["Customer"] = relationship()
    payments: Mapped[list["AdvancePayment"]] = relationship(back_populates="order", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<AdvanceOrder #{self.id} balance={self.balance} {self.status.value}>"


class AdvancePayment(Base, TimestampMixin):
    __tablename__ = "advance_payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("advance_orders.id"), nullable=False)
    payment_date: Mapped[date_] = mapped_column(Date, default=date_.today, nullable=False)
    amount: Mapped[Money] = mapped_column(Money, nullable=False)
    method: Mapped[PaymentMethod] = mapped_column(Enum(PaymentMethod), nullable=False)

    order: Mapped["AdvanceOrder"] = relationship(back_populates="payments")

    def __repr__(self) -> str:
        return f"<AdvancePayment order={self.order_id} amount={self.amount}>"
