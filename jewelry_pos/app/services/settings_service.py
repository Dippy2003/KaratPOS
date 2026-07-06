"""Key/value settings store accessors, with sane defaults for a fresh install."""
from __future__ import annotations

from sqlalchemy import select

from app.database.db import get_session
from app.database.models import Setting

DEFAULTS = {
    "shop_name": "KaratPOS Jewelry Shop",
    "shop_address": "123 Galle Road, Colombo",
    "shop_phone": "011-2345678",
    "tax_percent": "0",
    "invoice_footer_text": "Thank you for your business!",
    "discount_approval_threshold_percent": "10",
    "old_gold_margin_percent": "5",
    "block_sale_without_todays_rate": "false",
    "thermal_printer_enabled": "false",
    "thermal_printer_port": "",
}


def get_setting(key: str) -> str:
    with get_session() as session:
        row = session.scalar(select(Setting).where(Setting.key == key))
        if row is not None and row.value is not None:
            return row.value
        return DEFAULTS.get(key, "")


def set_setting(key: str, value: str) -> None:
    with get_session() as session:
        row = session.scalar(select(Setting).where(Setting.key == key))
        if row is None:
            session.add(Setting(key=key, value=value))
        else:
            row.value = value


def get_bool_setting(key: str) -> bool:
    return get_setting(key).strip().lower() in ("true", "1", "yes")


def set_bool_setting(key: str, value: bool) -> None:
    set_setting(key, "true" if value else "false")
