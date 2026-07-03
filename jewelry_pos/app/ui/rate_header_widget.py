"""
Compact header bar showing today's latest gold rate per purity on
every screen. Shows a warning banner if today's rate is missing for
any purity, per the "Using rate from <date>" requirement.
"""
from __future__ import annotations

from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QWidget

from app.services.gold_rate_service import get_latest_rates_all_purities


class RateHeaderWidget(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setStyleSheet("background-color: #f4f6f8; border-bottom: 1px solid #d0d7de;")
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(16, 8, 16, 8)
        self._layout.setSpacing(24)
        self.refresh()

    def refresh(self) -> None:
        """Re-fetch latest rates and rebuild the display. Call after any rate entry."""
        while self._layout.count():
            child = self._layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        rates = get_latest_rates_all_purities()
        stale_dates = set()

        for purity, row in rates.items():
            if row is None:
                label = QLabel(f"{purity.value}: no rate yet")
                label.setStyleSheet("color: #c0392b; font-weight: bold;")
            else:
                label = QLabel(f"{purity.value}: Rs. {row.rate_per_gram:,.2f}/g")
                # Explicit dark text: this bar always has a light background
                # regardless of OS theme, so text must not inherit the
                # app-wide (possibly white, under a dark theme) palette color.
                label.setStyleSheet("font-weight: bold; color: #1a1a1a;")
                if row.rate_date != date.today():
                    stale_dates.add(row.rate_date)
            self._layout.addWidget(label)

        self._layout.addStretch()

        if stale_dates:
            warn_date = max(stale_dates)
            warning = QLabel(f"⚠ Using rate from {warn_date.strftime('%d/%m/%Y')} — enter today's rate")
            warning.setStyleSheet("color: #b8860b; font-weight: bold;")
            self._layout.addWidget(warning)
