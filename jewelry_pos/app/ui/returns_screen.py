"""
Returns & Exchanges screen: search for an invoice, pick a line item
that hasn't already been returned, and process a return with a
refund amount/method and a restock-or-scrap decision.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.database.models import PaymentMethod
from app.services.returns_service import ReturnError, process_return
from app.services.transaction_service import get_invoice_detail, search_invoices


class ReturnsScreen(QWidget):
    def __init__(self, current_user_id: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.current_user_id = current_user_id
        self.current_invoice_detail = None
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        title = QLabel("Returns & Exchanges")
        title.setStyleSheet("font-size: 22px; font-weight: bold;")
        layout.addWidget(title)

        search_row = QHBoxLayout()
        self.invoice_no_input = QLineEdit()
        self.invoice_no_input.setPlaceholderText("Invoice number...")
        search_button = QPushButton("Find Invoice")
        search_button.clicked.connect(self._handle_find_invoice)
        search_row.addWidget(self.invoice_no_input)
        search_row.addWidget(search_button)
        layout.addLayout(search_row)

        splitter = QSplitter()
        splitter.addWidget(self._build_lines_panel())
        splitter.addWidget(self._build_return_form())
        splitter.setSizes([700, 450])
        layout.addWidget(splitter, stretch=1)

    def _build_lines_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)

        self.invoice_summary_label = QLabel("Search for an invoice to begin.")
        layout.addWidget(self.invoice_summary_label)

        self.lines_table = QTableWidget(0, 5)
        self.lines_table.setHorizontalHeaderLabels(["Item", "Code", "Line Total", "Returned?", ""])
        self.lines_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.lines_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.lines_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.lines_table.itemSelectionChanged.connect(self._on_line_selected)
        layout.addWidget(self.lines_table)

        return panel

    def _build_return_form(self) -> QWidget:
        box = QGroupBox("Process Return")
        layout = QVBoxLayout(box)

        self.selected_line_label = QLabel("Select a line item to return.")
        self.selected_line_label.setWordWrap(True)
        layout.addWidget(self.selected_line_label)

        self.reason_input = QTextEdit()
        self.reason_input.setPlaceholderText("Reason for return...")
        self.reason_input.setFixedHeight(60)
        layout.addWidget(self.reason_input)

        self.refund_method_combo = QComboBox()
        for method in PaymentMethod:
            if method != PaymentMethod.OLD_GOLD:
                self.refund_method_combo.addItem(method.value, method)
        layout.addWidget(QLabel("Refund method:"))
        layout.addWidget(self.refund_method_combo)

        self.refund_amount_input = QDoubleSpinBox()
        self.refund_amount_input.setRange(0, 999_999_999)
        self.refund_amount_input.setDecimals(2)
        layout.addWidget(QLabel("Refund amount (Rs.):"))
        layout.addWidget(self.refund_amount_input)

        self.restock_checkbox = QCheckBox("Item is resellable (restock to AVAILABLE)")
        self.restock_checkbox.setChecked(True)
        layout.addWidget(self.restock_checkbox)

        process_button = QPushButton("Process Return")
        process_button.clicked.connect(self._handle_process_return)
        layout.addWidget(process_button)

        layout.addStretch()
        return box

    def _handle_find_invoice(self) -> None:
        invoice_no = self.invoice_no_input.text().strip()
        if not invoice_no:
            return

        matches = search_invoices(invoice_no=invoice_no)
        if not matches:
            QMessageBox.warning(self, "Not Found", f"No invoice found matching '{invoice_no}'.")
            return

        detail = get_invoice_detail(matches[0].id)
        if detail is None:
            return

        self.current_invoice_detail = detail
        self.invoice_summary_label.setText(
            f"{detail.invoice_no} - {detail.customer_name or 'Walk-in'} - "
            f"Grand total: Rs. {detail.grand_total:,.2f} - Status: {detail.status.value}"
        )

        self.lines_table.setRowCount(len(detail.lines))
        for i, line in enumerate(detail.lines):
            self.lines_table.setItem(i, 0, QTableWidgetItem(line.item_name))
            self.lines_table.setItem(i, 1, QTableWidgetItem(line.item_code))
            self.lines_table.setItem(i, 2, QTableWidgetItem(f"Rs. {line.line_total:,.2f}"))
            self.lines_table.setItem(i, 3, QTableWidgetItem("Yes" if line.is_returned else "No"))
            self.lines_table.item(i, 0).setData(Qt.ItemDataRole.UserRole, line.id)

    def _selected_line(self):
        selected = self.lines_table.selectedItems()
        if not selected or self.current_invoice_detail is None:
            return None
        row = selected[0].row()
        return self.current_invoice_detail.lines[row]

    def _on_line_selected(self) -> None:
        line = self._selected_line()
        if line is None:
            self.selected_line_label.setText("Select a line item to return.")
            return

        if line.is_returned:
            self.selected_line_label.setText(f"{line.item_name} ({line.item_code}) has already been returned.")
            self.refund_amount_input.setValue(0)
            return

        self.selected_line_label.setText(
            f"{line.item_name} ({line.item_code}) - Line total: Rs. {line.line_total:,.2f}"
        )
        self.refund_amount_input.setValue(float(line.line_total))
