"""
In-memory POS cart. Not a database table -- the cart only exists for
the duration of one sale in progress. Each line freezes the price
breakdown at the moment the item was added (using the rate at that
time), matching what will be written to invoice_items on Complete Sale.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from app.services.item_service import ItemRow
from app.services.pricing_service import PriceBreakdown


@dataclass
class CartLine:
    item: ItemRow
    price: PriceBreakdown
    line_discount: Decimal = Decimal("0")

    @property
    def line_total(self) -> Decimal:
        return self.price.subtotal - self.line_discount


@dataclass
class Cart:
    lines: list[CartLine] = field(default_factory=list)

    def add_line(self, line: CartLine) -> None:
        self.lines.append(line)

    def remove_line(self, item_id: int) -> CartLine | None:
        for i, line in enumerate(self.lines):
            if line.item.id == item_id:
                return self.lines.pop(i)
        return None

    def has_item(self, item_id: int) -> bool:
        return any(line.item.id == item_id for line in self.lines)

    def clear(self) -> list[CartLine]:
        removed = self.lines
        self.lines = []
        return removed

    @property
    def subtotal(self) -> Decimal:
        return sum((line.line_total for line in self.lines), Decimal("0"))
