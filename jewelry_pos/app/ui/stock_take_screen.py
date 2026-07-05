"""
Stock take mode: staff scan every physical AVAILABLE item (via the
same USB-scanner-friendly focused input pattern as POS); on finish,
shows scanned vs expected and flags missing/unexpected items.
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.services.stock_take_service import reconcile_stock_take


class StockTakeScreen(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.scanned_codes: list[str] = []
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        title = QLabel("Stock Take")
        title.setStyleSheet("font-size: 22px; font-weight: bold;")
        layout.addWidget(title)

        instructions = QLabel("Scan every physical item's QR/barcode below, then click Finish Stock Take.")
        layout.addWidget(instructions)

        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText("Scan item code, then press Enter...")
        self.code_input.returnPressed.connect(self._handle_scan)
        self.code_input.setFocus()
        layout.addWidget(self.code_input)

        self.scanned_list = QListWidget()
        layout.addWidget(self.scanned_list, stretch=1)

        button_row = QHBoxLayout()
        finish_button = QPushButton("Finish Stock Take")
        finish_button.clicked.connect(self._handle_finish)
        reset_button = QPushButton("Reset")
        reset_button.clicked.connect(self._handle_reset)
        button_row.addWidget(finish_button)
        button_row.addWidget(reset_button)
        layout.addLayout(button_row)

        self.result_summary_label = QLabel("")
        layout.addWidget(self.result_summary_label)

        self.discrepancy_table = QTableWidget(0, 2)
        self.discrepancy_table.setHorizontalHeaderLabels(["Item Code", "Discrepancy"])
        self.discrepancy_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.discrepancy_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.discrepancy_table)

    def _handle_scan(self) -> None:
        code = self.code_input.text().strip()
        self.code_input.clear()
        if not code or code in self.scanned_codes:
            return
        self.scanned_codes.append(code)
        self.scanned_list.addItem(code)

    def _handle_reset(self) -> None:
        self.scanned_codes = []
        self.scanned_list.clear()
        self.result_summary_label.setText("")
        self.discrepancy_table.setRowCount(0)

    def _handle_finish(self) -> None:
        result = reconcile_stock_take(self.scanned_codes)
        self.result_summary_label.setText(
            f"Expected: {result.expected_count}  |  Scanned: {result.scanned_count}  |  "
            f"Matched: {result.matched_count}  |  Missing: {len(result.missing_codes)}  |  "
            f"Unexpected: {len(result.unexpected_codes)}"
        )

        rows = [(code, "MISSING (expected but not scanned)") for code in result.missing_codes]
        rows += [(code, "UNEXPECTED (scanned but not AVAILABLE)") for code in result.unexpected_codes]

        self.discrepancy_table.setRowCount(len(rows))
        for i, (code, note) in enumerate(rows):
            self.discrepancy_table.setItem(i, 0, QTableWidgetItem(code))
            self.discrepancy_table.setItem(i, 1, QTableWidgetItem(note))
