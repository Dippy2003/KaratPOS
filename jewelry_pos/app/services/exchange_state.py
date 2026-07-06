"""
Transient (in-memory, not persisted) state carrying a pending exchange
credit from the Returns screen to the POS screen. The Returns screen
sets this after processing a return the customer wants to exchange;
POSScreen checks for it on construction and, if present, pre-fills a
STORE_CREDIT payment row with the refund amount, then clears it.

Module-level singleton by design (mirrors app.scanning.bridge_singleton):
there is only ever one active POS session in this single-workstation
desktop app, so a single pending value is sufficient.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.database.models import PaymentMethod


@dataclass(frozen=True)
class PendingExchangeCredit:
    amount: Decimal
    source_return_id: int
    note: str


_pending: PendingExchangeCredit | None = None


def set_pending_exchange_credit(amount: Decimal, source_return_id: int, note: str = "") -> None:
    global _pending
    _pending = PendingExchangeCredit(amount=amount, source_return_id=source_return_id, note=note)


def take_pending_exchange_credit() -> PendingExchangeCredit | None:
    """Returns and clears the pending credit, if any -- one-shot consumption."""
    global _pending
    value = _pending
    _pending = None
    return value
