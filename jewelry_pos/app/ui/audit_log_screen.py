"""Audit Log Viewer (ADMIN only): filterable by date range and action-text search."""
from __future__ import annotations

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QDateEdit,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.services.audit_log_service import search_audit_log


class AuditLogScreen(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()
        self._handle_search()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        title = QLabel("Audit Log")
        title.setStyleSheet("font-size: 22px; font-weight: bold;")
        layout.addWidget(title)

        controls = QHBoxLayout()
        self.start_date_input = QDateEdit()
        self.start_date_input.setCalendarPopup(True)
        self.start_date_input.setDate(QDate.currentDate().addDays(-30))
        self.end_date_input = QDateEdit()
        self.end_date_input.setCalendarPopup(True)
        self.end_date_input.setDate(QDate.currentDate())
        self.action_search_input = QLineEdit()
        self.action_search_input.setPlaceholderText("Filter by action text...")
        search_button = QPushButton("Search")
        search_button.clicked.connect(self._handle_search)

        controls.addWidget(QLabel("From:"))
        controls.addWidget(self.start_date_input)
        controls.addWidget(QLabel("To:"))
        controls.addWidget(self.end_date_input)
        controls.addWidget(self.action_search_input)
        controls.addWidget(search_button)
        layout.addLayout(controls)

        self.log_table = QTableWidget(0, 4)
        self.log_table.setHorizontalHeaderLabels(["Timestamp", "User", "Action", "Entity"])
        self.log_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.log_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.log_table, stretch=1)

    def _handle_search(self) -> None:
        start = self.start_date_input.date().toPython()
        end = self.end_date_input.date().toPython()
        action_text = self.action_search_input.text().strip() or None

        rows = search_audit_log(start_date=start, end_date=end, action_contains=action_text)
        self.log_table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            self.log_table.setItem(i, 0, QTableWidgetItem(r.timestamp.strftime("%d/%m/%Y %I:%M %p")))
            self.log_table.setItem(i, 1, QTableWidgetItem(r.username))
            self.log_table.setItem(i, 2, QTableWidgetItem(r.action))
            entity_text = f"{r.entity_type} #{r.entity_id}" if r.entity_type else ""
            self.log_table.setItem(i, 3, QTableWidgetItem(entity_text))
