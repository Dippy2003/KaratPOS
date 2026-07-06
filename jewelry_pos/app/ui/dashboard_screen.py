"""
Dashboard landing screen: today's sales total, invoice count, and
items sold. Call refresh() after any completed sale so the numbers
update immediately, per the project brief.
"""
from __future__ import annotations

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from app.services.category_service import get_low_stock_categories
from app.services.dashboard_service import get_dashboard_chart_data, get_today_stats


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

        charts_row = QHBoxLayout()
        self.sales_figure = Figure(figsize=(4, 3))
        self.sales_canvas = FigureCanvas(self.sales_figure)
        self.payment_figure = Figure(figsize=(4, 3))
        self.payment_canvas = FigureCanvas(self.payment_figure)
        self.category_figure = Figure(figsize=(4, 3))
        self.category_canvas = FigureCanvas(self.category_figure)
        charts_row.addWidget(self.sales_canvas)
        charts_row.addWidget(self.payment_canvas)
        charts_row.addWidget(self.category_canvas)
        layout.addLayout(charts_row, stretch=1)

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

        self._refresh_charts()

    def _refresh_charts(self) -> None:
        chart_data = get_dashboard_chart_data(days=7)

        self.sales_figure.clear()
        ax1 = self.sales_figure.add_subplot(111)
        days = [d.strftime("%d %b") for d, _ in chart_data.daily_totals]
        totals = [float(v) for _, v in chart_data.daily_totals]
        ax1.bar(days, totals, color="#1976d2")
        ax1.set_title("Last 7 Days Sales")
        ax1.tick_params(axis="x", rotation=45, labelsize=7)
        self.sales_figure.tight_layout()
        self.sales_canvas.draw()

        self.payment_figure.clear()
        ax2 = self.payment_figure.add_subplot(111)
        if chart_data.payment_breakdown:
            labels = list(chart_data.payment_breakdown.keys())
            values = [float(v) for v in chart_data.payment_breakdown.values()]
            ax2.pie(values, labels=labels, autopct="%1.0f%%", textprops={"fontsize": 7})
        else:
            ax2.text(0.5, 0.5, "No sales yet", ha="center", va="center")
        ax2.set_title("Payment Methods (7 days)")
        self.payment_figure.tight_layout()
        self.payment_canvas.draw()

        self.category_figure.clear()
        ax3 = self.category_figure.add_subplot(111)
        if chart_data.top_categories:
            names = [name for name, _ in chart_data.top_categories]
            counts = [count for _, count in chart_data.top_categories]
            ax3.barh(names, counts, color="#2e7d32")
        else:
            ax3.text(0.5, 0.5, "No sales yet", ha="center", va="center")
        ax3.set_title("Top 5 Categories (7 days)")
        self.category_figure.tight_layout()
        self.category_canvas.draw()
