"""
Small Qt helper utilities shared across UI screens.

PySide6's QVariant storage silently downcasts str-subclassed Python
enums (Purity, MakingChargeType, ItemStatus, InvoiceStatus,
PaymentMethod -- all `class X(str, enum.Enum)`) back to plain `str`
when read back via QComboBox.currentData(). Reconstructing the enum
explicitly avoids `.value`/`.name` access crashing downstream and
avoids silently writing plain strings into enum-typed DB columns.
"""
from __future__ import annotations

from typing import TypeVar

from PySide6.QtWidgets import QComboBox

EnumT = TypeVar("EnumT")


def combo_enum_data(combo: QComboBox, enum_cls: type[EnumT]) -> EnumT | None:
    """Read currentData() from a combo box, re-coercing it into enum_cls.

    Returns None if the combo's current item stores None (e.g. an
    "All ..." filter option), otherwise always returns a real enum_cls
    member -- never the raw str PySide hands back.
    """
    raw = combo.currentData()
    if raw is None:
        return None
    return enum_cls(raw)
