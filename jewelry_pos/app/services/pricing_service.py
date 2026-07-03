"""
Live item pricing. Prices are NEVER stored on an item -- every screen
that displays a price calls calculate_item_price() against the latest
gold rate at render time. See app.database.models.Item for the raw
inputs this formula consumes.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from app.database.models import Item, MakingChargeType

TWO_PLACES = Decimal("0.01")


def _round(value: Decimal) -> Decimal:
    return value.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class PriceBreakdown:
    gold_rate_used: Decimal
    net_weight_g: Decimal
    gold_value: Decimal
    making_charge: Decimal
    stone_value: Decimal
    subtotal: Decimal  # gold_value + making_charge + stone_value, before discount/tax

    def as_dict(self) -> dict:
        return {
            "gold_rate_used": self.gold_rate_used,
            "net_weight_g": self.net_weight_g,
            "gold_value": self.gold_value,
            "making_charge": self.making_charge,
            "stone_value": self.stone_value,
            "subtotal": self.subtotal,
        }


def calculate_item_price(item: Item, rate_per_gram: Decimal) -> PriceBreakdown:
    """
    Compute the live price breakdown for one item at a given gold rate.

    gold_value    = net_weight_g * rate_per_gram
    making_charge = flat value, OR percent of gold_value
    subtotal      = gold_value + making_charge + stone_value
    (discount/tax are applied later, at POS/invoice level -- not here)
    """
    net_weight = Decimal(item.net_weight_g)
    rate = Decimal(rate_per_gram)

    gold_value = _round(net_weight * rate)

    if item.making_charge_type == MakingChargeType.FLAT:
        making_charge = _round(Decimal(item.making_charge_value))
    else:  # PERCENT of gold value
        percent = Decimal(item.making_charge_value)
        making_charge = _round(gold_value * percent / Decimal(100))

    stone_value = _round(Decimal(item.stone_value_total))

    subtotal = _round(gold_value + making_charge + stone_value)

    return PriceBreakdown(
        gold_rate_used=rate,
        net_weight_g=net_weight,
        gold_value=gold_value,
        making_charge=making_charge,
        stone_value=stone_value,
        subtotal=subtotal,
    )
