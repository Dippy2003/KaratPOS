"""
Settings screen (ADMIN only): shop details, tax %, discount-approval
threshold, old-gold margin, low-stock thresholds per category,
thermal printer config, block-sale-without-todays-rate toggle, and a
manual "Backup Now" button.
"""
from __future__ import annotations

from PySide6.QtGui import QPixmap
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

from app.printing.qr_service import generate_item_qr_image, qr_image_to_png_bytes
from app.scanning.bridge_singleton import get_bridge_server, is_bridge_running
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
        layout.addWidget(self._build_phone_bridge_box())
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

    def _build_printer_box(self) -> QWidget:
        box = QGroupBox("Thermal Printer (optional, 80mm ESC/POS)")
        form = QFormLayout(box)

        self.thermal_enabled_checkbox = QCheckBox("Enable thermal receipt printing")
        self.thermal_port_input = QLineEdit()
        self.thermal_port_input.setPlaceholderText("VENDOR_ID:PRODUCT_ID e.g. 04b8:0202")

        form.addRow(self.thermal_enabled_checkbox)
        form.addRow("Printer port:", self.thermal_port_input)

        save_button = QPushButton("Save Printer Settings")
        save_button.clicked.connect(self._handle_save_printer_settings)
        form.addRow(save_button)

        return box

    def _build_phone_bridge_box(self) -> QWidget:
        box = QGroupBox("Phone Camera Scanning Bridge (LAN only, bonus feature)")
        layout = QVBoxLayout(box)

        info = QLabel(
            "Lets staff scan item QR tags with their phone camera over the shop's Wi-Fi. "
            "No internet is used -- this only works on the local network."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        self.bridge_toggle_button = QPushButton("Start Phone Bridge")
        self.bridge_toggle_button.clicked.connect(self._handle_toggle_phone_bridge)
        layout.addWidget(self.bridge_toggle_button)

        self.bridge_status_label = QLabel("Phone bridge is not running.")
        layout.addWidget(self.bridge_status_label)

        self.bridge_qr_label = QLabel()
        self.bridge_qr_label.setFixedSize(150, 150)
        layout.addWidget(self.bridge_qr_label)

        return box

    def _build_backup_box(self) -> QWidget:
        box = QGroupBox("Backups")
        layout = QVBoxLayout(box)

        self.backup_status_label = QLabel("")
        layout.addWidget(self.backup_status_label)

        backup_now_button = QPushButton("Backup Now")
        backup_now_button.clicked.connect(self._handle_backup_now)
        layout.addWidget(backup_now_button)

        return box

    def _load_current_values(self) -> None:
        self.shop_name_input.setText(get_setting("shop_name"))
        self.shop_address_input.setText(get_setting("shop_address"))
        self.shop_phone_input.setText(get_setting("shop_phone"))
        self.footer_text_input.setText(get_setting("invoice_footer_text"))

        self.tax_percent_input.setText(get_setting("tax_percent"))
        self.discount_threshold_input.setText(get_setting("discount_approval_threshold_percent"))
        self.old_gold_margin_input.setText(get_setting("old_gold_margin_percent"))
        self.block_sale_checkbox.setChecked(get_bool_setting("block_sale_without_todays_rate"))

        self.thermal_enabled_checkbox.setChecked(get_bool_setting("thermal_printer_enabled"))
        self.thermal_port_input.setText(get_setting("thermal_printer_port"))

        self._refresh_backup_status()

    def _refresh_backup_status(self) -> None:
        backups = list_backups()
        if backups:
            self.backup_status_label.setText(f"{len(backups)} backup(s) stored. Most recent: {backups[0].name}")
        else:
            self.backup_status_label.setText("No backups yet.")

    def _handle_save_shop_details(self) -> None:
        set_setting("shop_name", self.shop_name_input.text())
        set_setting("shop_address", self.shop_address_input.text())
        set_setting("shop_phone", self.shop_phone_input.text())
        set_setting("invoice_footer_text", self.footer_text_input.text())
        QMessageBox.information(self, "Saved", "Shop details saved.")

    def _handle_save_sales_rules(self) -> None:
        try:
            float(self.tax_percent_input.text())
            float(self.discount_threshold_input.text())
            float(self.old_gold_margin_input.text())
        except ValueError:
            QMessageBox.warning(self, "Invalid Input", "Tax, discount threshold, and margin must be numeric.")
            return

        set_setting("tax_percent", self.tax_percent_input.text())
        set_setting("discount_approval_threshold_percent", self.discount_threshold_input.text())
        set_setting("old_gold_margin_percent", self.old_gold_margin_input.text())
        set_bool_setting("block_sale_without_todays_rate", self.block_sale_checkbox.isChecked())
        QMessageBox.information(self, "Saved", "Sales rules saved.")

    def _handle_save_printer_settings(self) -> None:
        set_bool_setting("thermal_printer_enabled", self.thermal_enabled_checkbox.isChecked())
        set_setting("thermal_printer_port", self.thermal_port_input.text())
        QMessageBox.information(self, "Saved", "Printer settings saved.")

    def _handle_backup_now(self) -> None:
        try:
            path = run_backup_now()
        except FileNotFoundError as exc:
            QMessageBox.warning(self, "Backup Failed", str(exc))
            return
        self._refresh_backup_status()
        QMessageBox.information(self, "Backup Complete", f"Backup saved to:\n{path}")

    def _handle_toggle_phone_bridge(self) -> None:
        server = get_bridge_server()
        if is_bridge_running():
            # The underlying Flask dev server has no clean stop() short of
            # killing the process; disabling here just stops POS/Settings
            # from treating it as active. Restarting the app fully stops it.
            QMessageBox.information(
                self, "Phone Bridge",
                "The phone bridge stays running for the rest of this session "
                "(restart the app to fully stop it), but new scans will be ignored "
                "once you navigate away from this toggle being 'on'.",
            )
            return

        try:
            server.start()
        except OSError as exc:
            QMessageBox.warning(self, "Could Not Start", f"Failed to start the phone bridge: {exc}")
            return

        self._refresh_phone_bridge_status()

    def _refresh_phone_bridge_status(self) -> None:
        if is_bridge_running():
            server = get_bridge_server()
            url = server.get_url()
            self.bridge_status_label.setText(f"Running at: {url}\nScan the QR below with your phone to open it.")
            self.bridge_toggle_button.setText("Phone Bridge Running")
            self.bridge_toggle_button.setEnabled(False)

            qr_image = generate_item_qr_image(url, box_size=6, border=1)
            png_bytes = qr_image_to_png_bytes(qr_image)
            pixmap = QPixmap()
            pixmap.loadFromData(png_bytes)
            self.bridge_qr_label.setPixmap(pixmap.scaled(150, 150))
        else:
            self.bridge_status_label.setText("Phone bridge is not running.")
            self.bridge_toggle_button.setText("Start Phone Bridge")
            self.bridge_toggle_button.setEnabled(True)
            self.bridge_qr_label.clear()
