"""
Reports & Analytics screen (ADMIN only). Daily/date-range sales,
stock valuation, profit by category, slow-moving stock, old gold and
returns reports -- all exportable to PDF/CSV -- plus a 30-day sales
forecast chart (matplotlib embedded via FigureCanvas).
"""
from __future__ import annotations

from datetime import date, timedelta

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.printing.report_export import export_rows_to_csv, export_rows_to_pdf
from app.services.forecast_service import get_sales_forecast
from app.services.report_service import (
    get_daily_sales_report,
    get_date_range_sales_report,
    get_old_gold_report,
    get_profit_by_category,
    get_returns_report,
    get_slow_moving_stock,
    get_stock_valuation_report,
)


class ReportsScreen(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._current_headers: list[str] = []
        self._current_rows: list[list[str]] = []
        self._current_report_name = "report"
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        title = QLabel("Reports & Analytics")
        title.setStyleSheet("font-size: 22px; font-weight: bold;")
        layout.addWidget(title)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_sales_tab(), "Sales")
        self.tabs.addTab(self._build_stock_tab(), "Stock")
        self.tabs.addTab(self._build_other_tab(), "Old Gold / Returns")
        self.tabs.addTab(self._build_forecast_tab(), "Forecast")
        layout.addWidget(self.tabs, stretch=1)
