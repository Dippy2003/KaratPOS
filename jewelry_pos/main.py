"""
Entry point for the Jewelry Shop ERP/POS system.

Startup sequence:
  1. Initialize the SQLite database (create tables if missing).
  2. Run the idempotent seed script (first-run demo data).
  3. Release any orphaned RESERVED item locks from a previous crash.
  4. Run the daily backup if one hasn't been made yet today.
  5. Show the login window; on success, open the role-based main window.
"""
from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from app.database.db import init_db
from app.database.seed import run_seed
from app.services.backup_service import run_daily_backup_if_needed
from app.services.startup_service import release_orphaned_reservations
from app.ui.login_window import LoginWindow
from app.ui.main_window import MainWindow


def main() -> None:
    init_db()
    run_seed()
    release_orphaned_reservations()
    run_daily_backup_if_needed()

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Keep references alive on the app object; local vars would be
    # garbage-collected as soon as main() control flow moves past them.
    login_window = LoginWindow()
    app.main_window = None  # type: ignore[attr-defined]

    def handle_login(auth_result):
        login_window.close()
        app.main_window = MainWindow(auth_result)  # type: ignore[attr-defined]
        app.main_window.show()

    login_window.login_successful.connect(handle_login)
    login_window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
