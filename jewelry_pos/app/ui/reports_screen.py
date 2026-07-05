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

    def _build_shared_results_table(self) -> QTableWidget:
        table = QTableWidget(0, 0)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        return table

    def _build_export_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        export_csv_button = QPushButton("Export CSV")
        export_csv_button.clicked.connect(self._handle_export_csv)
        export_pdf_button = QPushButton("Export PDF")
        export_pdf_button.clicked.connect(self._handle_export_pdf)
        row.addWidget(export_csv_button)
        row.addWidget(export_pdf_button)
        row.addStretch()
        return row

    def _build_sales_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        controls = QHBoxLayout()
        self.sales_start_date = QDateEdit()
        self.sales_start_date.setCalendarPopup(True)
        self.sales_start_date.setDate(QDate.currentDate().addDays(-7))
        self.sales_end_date = QDateEdit()
        self.sales_end_date.setCalendarPopup(True)
        self.sales_end_date.setDate(QDate.currentDate())

        daily_button = QPushButton("Today's Sales Report")
        daily_button.clicked.connect(self._handle_show_daily_report)
        range_button = QPushButton("Date-Range Sales Report")
        range_button.clicked.connect(self._handle_show_range_report)
        profit_button = QPushButton("Profit by Category")
        profit_button.clicked.connect(self._handle_show_profit_report)

        controls.addWidget(QLabel("From:"))
        controls.addWidget(self.sales_start_date)
        controls.addWidget(QLabel("To:"))
        controls.addWidget(self.sales_end_date)
        controls.addWidget(daily_button)
        controls.addWidget(range_button)
        controls.addWidget(profit_button)
        layout.addLayout(controls)

        self.sales_summary_label = QLabel("")
        layout.addWidget(self.sales_summary_label)

        self.sales_table = self._build_shared_results_table()
        layout.addWidget(self.sales_table, stretch=1)
        layout.addLayout(self._build_export_row())

        return tab

    def _build_stock_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        controls = QHBoxLayout()
        valuation_button = QPushButton("Stock Valuation Report")
        valuation_button.clicked.connect(self._handle_show_valuation_report)
        slow_button = QPushButton("Slow-Moving Stock (90+ days)")
        slow_button.clicked.connect(self._handle_show_slow_moving_report)
        controls.addWidget(valuation_button)
        controls.addWidget(slow_button)
        controls.addStretch()
        layout.addLayout(controls)

        self.stock_summary_label = QLabel("")
        layout.addWidget(self.stock_summary_label)

        self.stock_table = self._build_shared_results_table()
        layout.addWidget(self.stock_table, stretch=1)
        layout.addLayout(self._build_export_row())

        return tab
