"""
Dashboard landing screen: today's sales total, invoice count, and
items sold. Call refresh() after any completed sale so the numbers
update immediately, per the project brief.
"""
from __future__ import annotations

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from app.services.category_service import get_low_stock_categories
from app.services.dashboard_service import get_today_stats


class DashboardScreen(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        title = QLabel("Dashboard")
        title.setStyleSheet("font-size: 22px; font-weight: bold;")
        layout.addWidget(title)

        cards_row = QHBoxLayout()
        self.sales_card = self._build_stat_card("Today's Sales", "Rs. 0.00")
        self.invoice_card = self._build_stat_card("Invoices Today", "0")
        self.items_card = self._build_stat_card("Items Sold Today", "0")
        cards_row.addWidget(self.sales_card)
        cards_row.addWidget(self.invoice_card)
        cards_row.addWidget(self.items_card)
        layout.addLayout(cards_row)

        self.low_stock_label = QLabel("")
        self.low_stock_label.setStyleSheet("color: #b8860b; font-weight: bold; padding-top: 8px;")
        self.low_stock_label.setWordWrap(True)
        layout.addWidget(self.low_stock_label)

        layout.addStretch()

    def _build_stat_card(self, title: str, initial_value: str) -> QFrame:
        card = QFrame()
        # Explicit text colors are required here regardless of the OS/Qt
        # theme: this card always has a light background, so labels must
        # always use dark text -- letting them inherit the app palette
        # makes them invisible under a dark system theme.
        card.setStyleSheet("background-color: #f4f6f8; border-radius: 8px; padding: 16px;")
        # A fixed pixel height clips its labels under Windows display
        # scaling (e.g. 125%/150%) once scaled font metrics exceed the
        # unscaled height budget. Use a minimum height instead so the
        # card can grow to fit its content at any DPI scale.
        card.setMinimumHeight(100)
        layout = QVBoxLayout(card)

        title_label = QLabel(title)
        title_label.setStyleSheet("color: #607d8b; font-size: 12px;")

        value_label = QLabel(initial_value)
        value_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #1a1a1a;")
        value_label.setObjectName("value_label")

        layout.addWidget(title_label)
        layout.addWidget(value_label)

        card.value_label = value_label  # type: ignore[attr-defined]
        return card

    def refresh(self) -> None:
        stats = get_today_stats()
        self.sales_card.value_label.setText(f"Rs. {stats.total_sales:,.2f}")
        self.invoice_card.value_label.setText(str(stats.invoice_count))
        self.items_card.value_label.setText(str(stats.items_sold))

        low_stock = get_low_stock_categories()
        if low_stock:
            parts = [f"{name} ({count}/{threshold})" for name, count, threshold in low_stock]
            self.low_stock_label.setText("⚠ Low stock: " + ", ".join(parts))
        else:
            self.low_stock_label.setText("")
