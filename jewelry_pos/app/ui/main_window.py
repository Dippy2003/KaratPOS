"""
Main application shell shown after login. Provides a role-based
sidebar navigation menu; each menu item swaps the central QStackedWidget
page. Screens beyond the Dashboard placeholder are added in later phases.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from app.database.models import UserRole
from app.services.auth_service import AuthResult, log_logout
from app.ui.customers_screen import CustomersScreen
from app.ui.dashboard_screen import DashboardScreen
from app.ui.gold_rate_screen import GoldRateScreen
from app.ui.inventory_screen import InventoryScreen
from app.ui.pos_screen import POSScreen
from app.ui.rate_header_widget import RateHeaderWidget
from app.ui.returns_screen import ReturnsScreen
from app.ui.transaction_history_screen import TransactionHistoryScreen
from app.utils.config import APP_NAME

# Each nav entry: (label, roles allowed to see it)
NAV_ITEMS: list[tuple[str, tuple[UserRole, ...]]] = [
    ("Dashboard", (UserRole.ADMIN, UserRole.CASHIER, UserRole.SALES)),
    ("Gold Rates", (UserRole.ADMIN,)),
    ("Inventory", (UserRole.ADMIN, UserRole.SALES)),
    ("Point of Sale", (UserRole.ADMIN, UserRole.CASHIER)),
    ("Customers", (UserRole.ADMIN, UserRole.CASHIER, UserRole.SALES)),
    ("Suppliers & Purchases", (UserRole.ADMIN,)),
    ("Transaction History", (UserRole.ADMIN, UserRole.CASHIER)),
    ("Returns & Exchanges", (UserRole.ADMIN, UserRole.CASHIER)),
    ("Repairs", (UserRole.ADMIN, UserRole.SALES)),
    ("Reports", (UserRole.ADMIN,)),
    ("Audit Log", (UserRole.ADMIN,)),
    ("Settings", (UserRole.ADMIN,)),
]


class MainWindow(QMainWindow):
    def __init__(self, auth_result: AuthResult) -> None:
        super().__init__()
        self.auth_result = auth_result
        self.setWindowTitle(f"{APP_NAME} - {auth_result.full_name} ({auth_result.role.value})")
        self.resize(1366, 768)
        self._build_ui()

    def _build_ui(self) -> None:
        central = QWidget()
        outer_layout = QVBoxLayout(central)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        self.rate_header = RateHeaderWidget()
        outer_layout.addWidget(self.rate_header)

        body = QWidget()
        root_layout = QHBoxLayout(body)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        root_layout.addWidget(self._build_sidebar())
        root_layout.addWidget(self._build_content_area(), stretch=1)
        outer_layout.addWidget(body, stretch=1)

        self.setCentralWidget(central)
        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage(
            f"Logged in as {self.auth_result.username} ({self.auth_result.role.value})"
        )

    def _build_sidebar(self) -> QWidget:
        sidebar = QFrame()
        sidebar.setFixedWidth(220)
        sidebar.setStyleSheet("background-color: #1e2a38;")

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QLabel(APP_NAME)
        header.setStyleSheet("color: white; font-size: 18px; font-weight: bold; padding: 20px;")
        layout.addWidget(header)

        user_label = QLabel(f"{self.auth_result.full_name}\n{self.auth_result.role.value}")
        user_label.setStyleSheet("color: #b0bec5; padding: 0 20px 20px 20px;")
        layout.addWidget(user_label)

        self.nav_list = QListWidget()
        self.nav_list.setStyleSheet(
            "QListWidget { background-color: #1e2a38; color: white; border: none; font-size: 14px; }"
            "QListWidget::item { padding: 12px 20px; }"
            "QListWidget::item:selected { background-color: #2c3e50; }"
        )
        self.allowed_pages: list[str] = []
        for label, roles in NAV_ITEMS:
            if self.auth_result.role in roles:
                self.nav_list.addItem(QListWidgetItem(label))
                self.allowed_pages.append(label)
        self.nav_list.currentRowChanged.connect(self._on_nav_changed)
        layout.addWidget(self.nav_list, stretch=1)

        logout_button = QPushButton("Logout")
        logout_button.setStyleSheet("padding: 12px; margin: 10px;")
        logout_button.clicked.connect(self._handle_logout)
        layout.addWidget(logout_button)

        return sidebar

    def _build_content_area(self) -> QWidget:
        self.stack = QStackedWidget()
        for label in self.allowed_pages:
            self.stack.addWidget(self._build_page_for(label))
        if self.allowed_pages:
            self.nav_list.setCurrentRow(0)
        return self.stack

    def _build_page_for(self, label: str) -> QWidget:
        if label == "Dashboard":
            self.dashboard_screen = DashboardScreen()
            return self.dashboard_screen
        if label == "Gold Rates":
            return GoldRateScreen(self.auth_result.user_id, on_rate_added=self.rate_header.refresh)
        if label == "Inventory":
            return InventoryScreen(self.auth_result.user_id)
        if label == "Point of Sale":
            return POSScreen(
                self.auth_result.user_id,
                self.auth_result.full_name,
                on_sale_completed=self._handle_sale_completed,
            )
        if label == "Customers":
            return CustomersScreen()
        if label == "Transaction History":
            return TransactionHistoryScreen(self.auth_result.user_id, self.auth_result.role)
        if label == "Returns & Exchanges":
            return ReturnsScreen(self.auth_result.user_id)
        return self._placeholder_page(label)

    def _handle_sale_completed(self) -> None:
        if hasattr(self, "dashboard_screen"):
            self.dashboard_screen.refresh()

    def _placeholder_page(self, label: str) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        title = QLabel(label)
        title.setStyleSheet("font-size: 22px; font-weight: bold;")
        note = QLabel(f'"{label}" screen will be implemented in a later phase.')
        note.setStyleSheet("color: #607d8b;")
        layout.addWidget(title)
        layout.addWidget(note)
        layout.addStretch()
        return page

    def _on_nav_changed(self, index: int) -> None:
        if index >= 0:
            self.stack.setCurrentIndex(index)

    def _handle_logout(self) -> None:
        confirm = QMessageBox.question(
            self, "Logout", "Are you sure you want to log out?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.Yes:
            log_logout(self.auth_result.user_id, self.auth_result.username)
            self.close()
