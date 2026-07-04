"""
Old gold buy-back helpers for the POS exchange flow. The default
buy-back rate is today's gold rate for the assessed purity minus a
configurable margin (app.services.settings_service key
"old_gold_margin_percent"), but the cashier can override it in the
exchange dialog before the credit is applied to the sale.
"""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from app.database.models import Purity
from app.services.gold_rate_service import get_latest_rate
from app.services.settings_service import get_setting

TWO_PLACES = Decimal("0.01")


class OldGoldError(Exception):
    pass


def get_default_buy_rate(purity: Purity) -> Decimal:
    """Today's rate for this purity minus the configured old-gold margin."""
    rate_row = get_latest_rate(purity)
    if rate_row is None:
        raise OldGoldError(f"No gold rate has been entered yet for {purity.value}.")

    margin_percent = Decimal(get_setting("old_gold_margin_percent") or "0")
    discount = (rate_row.rate_per_gram * margin_percent / Decimal("100")).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
    return (rate_row.rate_per_gram - discount).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def calculate_credit_value(gross_weight_g: Decimal, buy_rate_per_gram: Decimal) -> Decimal:
    if gross_weight_g <= 0:
        raise OldGoldError("Weight must be greater than zero.")
    if buy_rate_per_gram <= 0:
        raise OldGoldError("Buy-back rate must be greater than zero.")
    return (gross_weight_g * buy_rate_per_gram).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
