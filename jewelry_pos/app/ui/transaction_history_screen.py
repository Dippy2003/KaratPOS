"""
Transaction History screen: search/filter all invoices, view full
snapshot detail, reprint (with REPRINT watermark, audit-logged), and
(ADMIN only) cancel a same-day invoice.
"""
from __future__ import annotations

from datetime import date, timedelta

from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
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
from PySide6.QtCore import QDate, Qt

from app.database.models import AuditLog, InvoiceStatus, UserRole
from app.database.db import get_session
from app.services.settings_service import get_setting
from app.services.transaction_service import (
    TransactionError,
    cancel_invoice,
    get_invoice_detail,
    search_invoices,
)
from app.printing.receipt_pdf import ReceiptData, ReceiptLine, ReceiptPaymentLine, generate_receipt_pdf
from app.utils.qt_helpers import combo_enum_data


class TransactionHistoryScreen(QWidget):
    def __init__(self, current_user_id: int, current_user_role: UserRole, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.current_user_id = current_user_id
        self.current_user_role = current_user_role
        self._build_ui()
        self._reload_list()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        title = QLabel("Transaction History")
        title.setStyleSheet("font-size: 22px; font-weight: bold;")
        layout.addWidget(title)

        layout.addWidget(self._build_filter_row())

        splitter = QSplitter()
        splitter.addWidget(self._build_list_panel())
        splitter.addWidget(self._build_detail_panel())
        splitter.setSizes([700, 550])
        layout.addWidget(splitter, stretch=1)

    def _build_filter_row(self) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)

        self.invoice_no_input = QLineEdit()
        self.invoice_no_input.setPlaceholderText("Invoice no...")

        self.customer_input = QLineEdit()
        self.customer_input.setPlaceholderText("Customer name...")

        self.date_from_input = QDateEdit()
        self.date_from_input.setDate(QDate.currentDate().addMonths(-1))
        self.date_from_input.setCalendarPopup(True)

        self.date_to_input = QDateEdit()
        self.date_to_input.setDate(QDate.currentDate())
        self.date_to_input.setCalendarPopup(True)

        self.status_filter_combo = QComboBox()
        self.status_filter_combo.addItem("All statuses", None)
        for status in InvoiceStatus:
            self.status_filter_combo.addItem(status.value, status)

        search_button = QPushButton("Search")
        search_button.clicked.connect(self._reload_list)

        layout.addWidget(self.invoice_no_input)
        layout.addWidget(self.customer_input)
        layout.addWidget(QLabel("From:"))
        layout.addWidget(self.date_from_input)
        layout.addWidget(QLabel("To:"))
        layout.addWidget(self.date_to_input)
        layout.addWidget(self.status_filter_combo)
        layout.addWidget(search_button)

        return row

    def _build_list_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)

        self.invoice_table = QTableWidget(0, 5)
        self.invoice_table.setHorizontalHeaderLabels(["Invoice No", "Date", "Customer", "Total", "Status"])
        self.invoice_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.invoice_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.invoice_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.invoice_table.itemSelectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self.invoice_table)

        return panel

    def _build_detail_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)

        self.detail_text = QTextEdit()
        self.detail_text.setReadOnly(True)
        layout.addWidget(self.detail_text)

        button_row = QHBoxLayout()
        self.reprint_button = QPushButton("Reprint Receipt")
        self.reprint_button.clicked.connect(self._handle_reprint)
        self.reprint_button.setEnabled(False)
        button_row.addWidget(self.reprint_button)

        self.cancel_button = QPushButton("Cancel Invoice (Admin, same-day)")
        self.cancel_button.clicked.connect(self._handle_cancel)
        self.cancel_button.setEnabled(False)
        self.cancel_button.setVisible(self.current_user_role == UserRole.ADMIN)
        button_row.addWidget(self.cancel_button)

        layout.addLayout(button_row)
        return panel

    def _reload_list(self) -> None:
        qdate_from = self.date_from_input.date().toPython()
        qdate_to = self.date_to_input.date().toPython()
        status = combo_enum_data(self.status_filter_combo, InvoiceStatus)

        rows = search_invoices(
            invoice_no=self.invoice_no_input.text(),
            customer_name=self.customer_input.text(),
            date_from=qdate_from,
            date_to=qdate_to,
            status=status,
        )

        self.invoice_table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            self.invoice_table.setItem(i, 0, QTableWidgetItem(row.invoice_no))
            self.invoice_table.setItem(i, 1, QTableWidgetItem(row.invoice_datetime.strftime("%d/%m/%Y %I:%M %p")))
            self.invoice_table.setItem(i, 2, QTableWidgetItem(row.customer_name or "Walk-in"))
            self.invoice_table.setItem(i, 3, QTableWidgetItem(f"Rs. {row.grand_total:,.2f}"))
            self.invoice_table.setItem(i, 4, QTableWidgetItem(row.status.value))
            self.invoice_table.item(i, 0).setData(Qt.ItemDataRole.UserRole, row.id)

    def _selected_invoice_id(self) -> int | None:
        selected = self.invoice_table.selectedItems()
        if not selected:
            return None
        return self.invoice_table.item(selected[0].row(), 0).data(Qt.ItemDataRole.UserRole)

    def _on_selection_changed(self) -> None:
        invoice_id = self._selected_invoice_id()
        if invoice_id is None:
            self.detail_text.clear()
            self.reprint_button.setEnabled(False)
            self.cancel_button.setEnabled(False)
            return

        detail = get_invoice_detail(invoice_id)
        if detail is None:
            return

        lines_text = "\n".join(
            f"  {line.item_name} ({line.item_code}) - {line.net_weight_g}g {line.purity} "
            f"@ Rs.{line.gold_rate_used:,.2f}/g -> Rs. {line.line_total:,.2f}"
            + (" [RETURNED]" if line.is_returned else "")
            for line in detail.lines
        )
        payments_text = ", ".join(f"{p.method} Rs.{p.amount:,.2f}" for p in detail.payments)

        self.detail_text.setPlainText(
            f"Invoice: {detail.invoice_no}\n"
            f"Date: {detail.invoice_datetime.strftime('%d/%m/%Y %I:%M %p')}\n"
            f"Customer: {detail.customer_name or 'Walk-in'}\n"
            f"Cashier: {detail.cashier_name}\n"
            f"Status: {detail.status.value}\n\n"
            f"Items:\n{lines_text}\n\n"
            f"Subtotal: Rs. {detail.subtotal:,.2f}\n"
            f"Discount: Rs. {detail.discount_total:,.2f}\n"
            f"Tax: Rs. {detail.tax_total:,.2f}\n"
            f"Old gold credit: Rs. {detail.old_gold_credit:,.2f}\n"
            f"GRAND TOTAL: Rs. {detail.grand_total:,.2f}\n"
            f"Paid: {payments_text}\n"
            f"Balance returned: Rs. {detail.balance_returned:,.2f}"
        )

        self.reprint_button.setEnabled(True)
        can_cancel = (
            self.current_user_role == UserRole.ADMIN
            and detail.status != InvoiceStatus.CANCELLED
            and detail.invoice_datetime.date() == date.today()
        )
        self.cancel_button.setEnabled(can_cancel)

    def _handle_reprint(self) -> None:
        invoice_id = self._selected_invoice_id()
        if invoice_id is None:
            return
        detail = get_invoice_detail(invoice_id)
        if detail is None:
            return

        receipt_lines = [
            ReceiptLine(
                item_name=line.item_name,
                item_code=line.item_code,
                net_weight_g=line.net_weight_g,
                purity=line.purity,
                gold_rate_used=line.gold_rate_used,
                gold_value=line.gold_value,
                making_charge=line.making_charge,
                stone_value=line.stone_value,
                line_total=line.line_total,
            )
            for line in detail.lines
        ]
        data = ReceiptData(
            shop_name=get_setting("shop_name"),
            shop_address=get_setting("shop_address"),
            shop_phone=get_setting("shop_phone"),
            invoice_no=detail.invoice_no,
            invoice_datetime=detail.invoice_datetime,
            cashier_name=detail.cashier_name,
            customer_name=detail.customer_name,
            lines=receipt_lines,
            subtotal=detail.subtotal,
            discount_total=detail.discount_total,
            tax_total=detail.tax_total,
            old_gold_credit=detail.old_gold_credit,
            grand_total=detail.grand_total,
            payments=[ReceiptPaymentLine(method=p.method, amount=p.amount) for p in detail.payments],
            balance_returned=detail.balance_returned,
            footer_text=get_setting("invoice_footer_text"),
            is_reprint=True,
        )
        path = generate_receipt_pdf(data)

        with get_session() as session:
            session.add(
                AuditLog(
                    user_id=self.current_user_id,
                    action=f"Reprinted receipt for invoice {detail.invoice_no}",
                    entity_type="Invoice",
                    entity_id=detail.id,
                )
            )

        QMessageBox.information(self, "Reprinted", f"Reprint saved to:\n{path}")

    def _handle_cancel(self) -> None:
        invoice_id = self._selected_invoice_id()
        if invoice_id is None:
            return

        reason, ok = QInputDialog.getText(self, "Cancel Invoice", "Reason for cancellation:")
        if not ok or not reason.strip():
            return

        confirm = QMessageBox.question(
            self, "Confirm Cancellation",
            "This will reverse all sold items back to available stock. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        try:
            cancel_invoice(invoice_id, reason, self.current_user_id, self.current_user_role)
        except TransactionError as exc:
            QMessageBox.warning(self, "Cannot Cancel", str(exc))
            return

        QMessageBox.information(self, "Invoice Cancelled", "The invoice has been cancelled and stock reversed.")
        self._reload_list()
        self.detail_text.clear()
