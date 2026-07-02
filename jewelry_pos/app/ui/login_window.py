"""
Login window: username/password entry, bcrypt verification via
app.services.auth_service. Emits `login_successful` with the AuthResult
so main.py can hand off to the MainWindow.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QKeyEvent
from PySide6.QtWidgets import (
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.services.auth_service import AuthResult, authenticate
from app.utils.config import APP_NAME


class LoginWindow(QWidget):
    login_successful = Signal(object)  # emits AuthResult

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} - Login")
        self.setFixedSize(380, 320)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(14)

        title = QLabel(APP_NAME)
        title_font = QFont()
        title_font.setPointSize(20)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle = QLabel("Jewelry Shop ERP / POS")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Username")

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)

        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #c0392b;")
        self.error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.error_label.setWordWrap(True)

        self.login_button = QPushButton("Login")
        self.login_button.setDefault(True)
        self.login_button.clicked.connect(self._attempt_login)

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(10)
        layout.addWidget(self.username_input)
        layout.addWidget(self.password_input)
        layout.addWidget(self.error_label)
        layout.addWidget(self.login_button)
        layout.addStretch()

        self.username_input.setFocus()

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802 (Qt override)
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._attempt_login()
        else:
            super().keyPressEvent(event)

    def _attempt_login(self) -> None:
        username = self.username_input.text()
        password = self.password_input.text()

        result: AuthResult = authenticate(username, password)

        if not result.success:
            self.error_label.setText(result.error or "Login failed.")
            self.password_input.clear()
            self.password_input.setFocus()
            return

        self.error_label.setText("")

        if result.must_change_password:
            QMessageBox.information(
                self,
                "Change Password",
                "This is a default account. Please change your password after logging in.",
            )

        self.login_successful.emit(result)
