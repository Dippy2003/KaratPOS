"""
Settings screen (ADMIN only): shop details, tax %, discount-approval
threshold, old-gold margin, low-stock thresholds per category,
thermal printer config, block-sale-without-todays-rate toggle, and a
manual "Backup Now" button.
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.services.backup_service import list_backups, run_backup_now
from app.services.settings_service import get_bool_setting, get_setting, set_bool_setting, set_setting


class SettingsScreen(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()
        self._load_current_values()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        title = QLabel("Settings")
        title.setStyleSheet("font-size: 22px; font-weight: bold;")
        layout.addWidget(title)

        layout.addWidget(self._build_shop_details_box())
        layout.addWidget(self._build_sales_rules_box())
        layout.addWidget(self._build_printer_box())
        layout.addWidget(self._build_backup_box())
        layout.addStretch()

    def _build_shop_details_box(self) -> QWidget:
        box = QGroupBox("Shop Details")
        form = QFormLayout(box)

        self.shop_name_input = QLineEdit()
        self.shop_address_input = QLineEdit()
        self.shop_phone_input = QLineEdit()
        self.footer_text_input = QLineEdit()

        form.addRow("Shop name:", self.shop_name_input)
        form.addRow("Address:", self.shop_address_input)
        form.addRow("Phone:", self.shop_phone_input)
        form.addRow("Receipt footer text:", self.footer_text_input)

        save_button = QPushButton("Save Shop Details")
        save_button.clicked.connect(self._handle_save_shop_details)
        form.addRow(save_button)

        return box

    def _build_sales_rules_box(self) -> QWidget:
        box = QGroupBox("Sales Rules")
        form = QFormLayout(box)

        self.tax_percent_input = QLineEdit()
        self.discount_threshold_input = QLineEdit()
        self.old_gold_margin_input = QLineEdit()
        self.block_sale_checkbox = QCheckBox("Block sales until today's gold rate is entered for all purities")

        form.addRow("Tax (%):", self.tax_percent_input)
        form.addRow("Discount approval threshold (%):", self.discount_threshold_input)
        form.addRow("Old gold buy-back margin (%):", self.old_gold_margin_input)
        form.addRow(self.block_sale_checkbox)

        save_button = QPushButton("Save Sales Rules")
        save_button.clicked.connect(self._handle_save_sales_rules)
        form.addRow(save_button)

        return box
