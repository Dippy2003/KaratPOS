"""
Change Password dialog, available to every logged-in user regardless
of role. Requires re-entering the current password (verified via
authenticate()) before accepting a new one, so a user who steps away
from an unlocked session can't have their password silently changed
by someone else at the keyboard.
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from app.services.auth_service import authenticate, change_password


class ChangePasswordDialog(QDialog):
    def __init__(self, user_id: int, username: str, parent=None) -> None:
        super().__init__(parent)
        self.user_id = user_id
        self.username = username
        self.setWindowTitle("Change Password")
        self.setMinimumWidth(340)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.current_password_input = QLineEdit()
        self.current_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.new_password_input = QLineEdit()
        self.new_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_password_input = QLineEdit()
        self.confirm_password_input.setEchoMode(QLineEdit.EchoMode.Password)

        form.addRow("Current password:", self.current_password_input)
        form.addRow("New password:", self.new_password_input)
        form.addRow("Confirm new password:", self.confirm_password_input)
        layout.addLayout(form)

        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #c0392b;")
        self.error_label.setWordWrap(True)
        layout.addWidget(self.error_label)

        save_button = QPushButton("Change Password")
        save_button.setDefault(True)
        save_button.clicked.connect(self._handle_change_password)
        layout.addWidget(save_button)

    def _handle_change_password(self) -> None:
        current = self.current_password_input.text()
        new = self.new_password_input.text()
        confirm = self.confirm_password_input.text()

        if not current or not new or not confirm:
            self.error_label.setText("All fields are required.")
            return

        result = authenticate(self.username, current)
        if not result.success:
            self.error_label.setText("Current password is incorrect.")
            return

        if len(new) < 6:
            self.error_label.setText("New password must be at least 6 characters.")
            return

        if new != confirm:
            self.error_label.setText("New password and confirmation do not match.")
            return

        if new == current:
            self.error_label.setText("New password must be different from the current one.")
            return

        change_password(self.user_id, new)
        QMessageBox.information(self, "Password Changed", "Your password has been changed successfully.")
        self.accept()
