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
    get_monthly_comparison,
    get_old_gold_report,
    get_profit_by_category,
    get_returns_report,
    get_slow_moving_stock,
    get_stock_valuation_report,
    get_yearly_comparison,
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
        self.tabs.addTab(self._build_comparison_tab(), "Monthly/Yearly Comparison")
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

    def _build_other_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        controls = QHBoxLayout()
        self.other_start_date = QDateEdit()
        self.other_start_date.setCalendarPopup(True)
        self.other_start_date.setDate(QDate.currentDate().addDays(-30))
        self.other_end_date = QDateEdit()
        self.other_end_date.setCalendarPopup(True)
        self.other_end_date.setDate(QDate.currentDate())

        old_gold_button = QPushButton("Old Gold Purchased Report")
        old_gold_button.clicked.connect(self._handle_show_old_gold_report)
        returns_button = QPushButton("Returns Report")
        returns_button.clicked.connect(self._handle_show_returns_report)

        controls.addWidget(QLabel("From:"))
        controls.addWidget(self.other_start_date)
        controls.addWidget(QLabel("To:"))
        controls.addWidget(self.other_end_date)
        controls.addWidget(old_gold_button)
        controls.addWidget(returns_button)
        layout.addLayout(controls)

        self.other_table = self._build_shared_results_table()
        layout.addWidget(self.other_table, stretch=1)
        layout.addLayout(self._build_export_row())

        return tab

    def _build_forecast_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        refresh_button = QPushButton("Refresh 30-Day Forecast")
        refresh_button.clicked.connect(self._handle_show_forecast)
        layout.addWidget(refresh_button)

        self.forecast_figure = Figure(figsize=(8, 4))
        self.forecast_canvas = FigureCanvas(self.forecast_figure)
        layout.addWidget(self.forecast_canvas, stretch=1)

        return tab

    def _set_table_data(self, table: QTableWidget, headers: list[str], rows: list[list[str]]) -> None:
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            for j, value in enumerate(row):
                table.setItem(i, j, QTableWidgetItem(str(value)))

        self._current_headers = headers
        self._current_rows = rows

    def _handle_show_daily_report(self) -> None:
        report = get_daily_sales_report(date.today())
        self.sales_summary_label.setText(
            f"Total sales: Rs. {report.total_sales:,.2f}  |  Profit: Rs. {report.total_profit:,.2f}  |  "
            f"Invoices: {report.invoice_count}"
        )
        headers = ["Item", "Qty Sold"]
        rows = [[name, str(qty)] for name, qty in report.best_selling_items]
        self._set_table_data(self.sales_table, headers, rows)
        self._current_report_name = "daily_sales_report"

    def _handle_show_range_report(self) -> None:
        start = self.sales_start_date.date().toPython()
        end = self.sales_end_date.date().toPython()
        if start > end:
            QMessageBox.warning(self, "Invalid Range", "Start date must be before end date.")
            return

        report = get_date_range_sales_report(start, end)
        self.sales_summary_label.setText(
            f"Total sales ({start} to {end}): Rs. {report.total_sales:,.2f}  |  "
            f"Profit: Rs. {report.total_profit:,.2f}  |  Invoices: {report.invoice_count}"
        )
        headers = ["Date", "Total Sales"]
        rows = [[d.strftime("%d/%m/%Y"), f"{total:,.2f}"] for d, total in report.daily_totals]
        self._set_table_data(self.sales_table, headers, rows)
        self._current_report_name = "date_range_sales_report"

    def _handle_show_profit_report(self) -> None:
        start = self.sales_start_date.date().toPython()
        end = self.sales_end_date.date().toPython()
        rows_data = get_profit_by_category(start, end)
        self.sales_summary_label.setText(f"Profit by category ({start} to {end})")
        headers = ["Category", "Items Sold", "Profit"]
        rows = [[r.category_name, str(r.items_sold), f"{r.total_profit:,.2f}"] for r in rows_data]
        self._set_table_data(self.sales_table, headers, rows)
        self._current_report_name = "profit_by_category_report"

    def _handle_show_valuation_report(self) -> None:
        report = get_stock_valuation_report()
        self.stock_summary_label.setText(
            f"Stock valuation as of {report.valuation_date.strftime('%d/%m/%Y')}: "
            f"{report.total_items} items, Rs. {report.total_value:,.2f}"
        )
        headers = ["Category", "Value"]
        rows = [[cat, f"{value:,.2f}"] for cat, value in report.value_by_category.items()]
        self._set_table_data(self.stock_table, headers, rows)
        self._current_report_name = "stock_valuation_report"

    def _handle_show_slow_moving_report(self) -> None:
        rows_data = get_slow_moving_stock(min_days=90)
        self.stock_summary_label.setText(f"{len(rows_data)} item(s) in stock 90+ days")
        headers = ["Item Code", "Name", "Category", "Days in Stock"]
        rows = [[r.item_code, r.name, r.category_name, str(r.days_in_stock)] for r in rows_data]
        self._set_table_data(self.stock_table, headers, rows)
        self._current_report_name = "slow_moving_stock_report"

    def _handle_show_old_gold_report(self) -> None:
        start = self.other_start_date.date().toPython()
        end = self.other_end_date.date().toPython()
        rows_data = get_old_gold_report(start, end)
        headers = ["Date", "Description", "Weight (g)", "Credit Value"]
        rows = [
            [r.receipt_date.strftime("%d/%m/%Y"), r.description, str(r.gross_weight_g), f"{r.credit_value:,.2f}"]
            for r in rows_data
        ]
        self._set_table_data(self.other_table, headers, rows)
        self._current_report_name = "old_gold_report"

    def _handle_show_returns_report(self) -> None:
        start = self.other_start_date.date().toPython()
        end = self.other_end_date.date().toPython()
        rows_data = get_returns_report(start, end)
        headers = ["Date", "Invoice No", "Reason", "Refund Amount"]
        rows = [
            [r.return_date.strftime("%d/%m/%Y"), r.invoice_no, r.reason, f"{r.refund_amount:,.2f}"]
            for r in rows_data
        ]
        self._set_table_data(self.other_table, headers, rows)
        self._current_report_name = "returns_report"

    def _handle_show_forecast(self) -> None:
        result = get_sales_forecast()

        self.forecast_figure.clear()
        ax = self.forecast_figure.add_subplot(111)

        if result.historical:
            hist_dates, hist_values = zip(*result.historical)
            ax.plot(hist_dates, [float(v) for v in hist_values], label="Historical", color="#1976d2")
        if result.forecast:
            fc_dates, fc_values = zip(*result.forecast)
            ax.plot(fc_dates, [float(v) for v in fc_values], label="Forecast", color="#e65100", linestyle="--")

        ax.set_title("Sales Forecast (next 30 days)")
        ax.set_ylabel("Rs.")
        ax.legend()
        self.forecast_figure.autofmt_xdate()
        self.forecast_canvas.draw()

    def _handle_export_csv(self) -> None:
        if not self._current_rows:
            QMessageBox.information(self, "No Data", "Generate a report first.")
            return
        path = export_rows_to_csv(self._current_headers, self._current_rows, self._current_report_name)
        QMessageBox.information(self, "Exported", f"CSV saved to:\n{path}")

    def _handle_export_pdf(self) -> None:
        if not self._current_rows:
            QMessageBox.information(self, "No Data", "Generate a report first.")
            return
        path = export_rows_to_pdf(self._current_report_name.replace("_", " ").title(), self._current_headers, self._current_rows, self._current_report_name)
        QMessageBox.information(self, "Exported", f"PDF saved to:\n{path}")
