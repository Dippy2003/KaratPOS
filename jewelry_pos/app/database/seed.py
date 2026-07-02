"""
First-run seed data so the app is demoable immediately after install.

Idempotent: safe to call on every startup. Only inserts rows that are
missing (checked by natural keys) so re-running never duplicates data.
"""
from __future__ import annotations

from datetime import date

import bcrypt
from sqlalchemy import select

from app.database.db import get_session
from app.database.models import (
    Category,
    Customer,
    GoldRate,
    Item,
    ItemStatus,
    MakingChargeType,
    Purity,
    User,
    UserRole,
)

DEFAULT_CATEGORIES = ["Ring", "Chain", "Necklace", "Bangle", "Earring", "Pendant", "Bracelet", "Other"]

# Rough starting LKR/gram rates for a Sri Lankan jewelry shop demo.
SAMPLE_RATES = {
    Purity.K24: 19500,
    Purity.K22: 17900,
    Purity.K21: 17100,
    Purity.K18: 14650,
}

SAMPLE_ITEMS = [
    ("22K Gold Ring - Floral", "Ring", Purity.K22, 6.800, 6.500, MakingChargeType.FLAT, 12000, 4000),
    ("22K Gold Chain - Rope", "Chain", Purity.K22, 15.200, 15.000, MakingChargeType.PERCENT, 10, 0),
    ("21K Gold Necklace - Kasu Malai", "Necklace", Purity.K21, 28.500, 28.000, MakingChargeType.FLAT, 35000, 8000),
    ("22K Gold Bangle - Plain", "Bangle", Purity.K22, 20.000, 19.700, MakingChargeType.PERCENT, 8, 0),
    ("18K Gold Earring - Stud", "Earring", Purity.K18, 3.200, 3.000, MakingChargeType.FLAT, 5000, 6000),
    ("22K Gold Pendant - Om", "Pendant", Purity.K22, 4.500, 4.300, MakingChargeType.FLAT, 4500, 0),
    ("21K Gold Bracelet - Chain Link", "Bracelet", Purity.K21, 9.800, 9.500, MakingChargeType.PERCENT, 9, 0),
    ("24K Gold Coin - 1g", "Other", Purity.K24, 1.000, 1.000, MakingChargeType.FLAT, 500, 0),
    ("22K Gold Ring - Solitaire Look", "Ring", Purity.K22, 5.100, 4.900, MakingChargeType.FLAT, 9500, 15000),
    ("22K Gold Chain - Box Link", "Chain", Purity.K22, 12.000, 11.800, MakingChargeType.PERCENT, 10, 0),
]

SAMPLE_CUSTOMERS = [
    ("Kasun Perera", "0771234567", "Colombo 05"),
    ("Nimali Fernando", "0719876543", "Kandy"),
    ("Ruwan Silva", "0765551234", "Galle"),
]


def _hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def run_seed() -> None:
    with get_session() as session:
        _seed_users(session)
        _seed_categories(session)
        _seed_gold_rates(session)
        _seed_items(session)
        _seed_customers(session)


def _seed_users(session) -> None:
    from app.utils.config import DEFAULT_ADMIN_USERNAME, DEFAULT_ADMIN_PASSWORD

    existing = session.scalar(select(User).where(User.username == DEFAULT_ADMIN_USERNAME))
    if existing:
        return
    admin = User(
        username=DEFAULT_ADMIN_USERNAME,
        password_hash=_hash_password(DEFAULT_ADMIN_PASSWORD),
        full_name="Shop Administrator",
        role=UserRole.ADMIN,
        is_active=True,
        must_change_password=True,
    )
    cashier = User(
        username="cashier",
        password_hash=_hash_password("cashier123"),
        full_name="Demo Cashier",
        role=UserRole.CASHIER,
        is_active=True,
        must_change_password=True,
    )
    sales = User(
        username="sales",
        password_hash=_hash_password("sales123"),
        full_name="Demo Sales Staff",
        role=UserRole.SALES,
        is_active=True,
        must_change_password=True,
    )
    session.add_all([admin, cashier, sales])
    session.flush()


def _seed_categories(session) -> None:
    existing_names = {c.name for c in session.scalars(select(Category))}
    for name in DEFAULT_CATEGORIES:
        if name not in existing_names:
            session.add(Category(name=name, low_stock_threshold=3))
    session.flush()


def _seed_gold_rates(session) -> None:
    today = date.today()
    admin = session.scalar(select(User).where(User.username == "admin"))
    for purity, rate in SAMPLE_RATES.items():
        exists = session.scalar(
            select(GoldRate).where(GoldRate.rate_date == today, GoldRate.purity == purity)
        )
        if exists:
            continue
        session.add(
            GoldRate(rate_date=today, purity=purity, rate_per_gram=rate, entered_by_id=admin.id)
        )
    session.flush()


def _next_item_code(session) -> str:
    count = session.scalar(select(Item))
    last = session.scalars(select(Item).order_by(Item.id.desc())).first()
    next_num = (last.id + 1) if last else 1
    return f"ITM-{next_num:06d}"


def _seed_items(session) -> None:
    existing_count = len(session.scalars(select(Item)).all())
    if existing_count > 0:
        return
    categories = {c.name: c for c in session.scalars(select(Category))}
    for idx, (name, cat_name, purity, gross, net, mc_type, mc_value, stone_value) in enumerate(SAMPLE_ITEMS, start=1):
        session.add(
            Item(
                item_code=f"ITM-{idx:06d}",
                name=name,
                category_id=categories[cat_name].id,
                purity=purity,
                gross_weight_g=gross,
                net_weight_g=net,
                making_charge_type=mc_type,
                making_charge_value=mc_value,
                stone_value_total=stone_value,
                cost_price=0,
                status=ItemStatus.AVAILABLE,
                date_added=date.today(),
            )
        )
    session.flush()


def _seed_customers(session) -> None:
    existing_phones = {c.phone for c in session.scalars(select(Customer))}
    for name, phone, address in SAMPLE_CUSTOMERS:
        if phone not in existing_phones:
            session.add(Customer(name=name, phone=phone, address=address))
    session.flush()
