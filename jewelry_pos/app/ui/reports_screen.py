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
