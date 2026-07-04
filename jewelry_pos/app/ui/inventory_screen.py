"""
Inventory Management screen: add/edit items with a live computed price
preview (using today's gold rate), search/filter the catalog, and
print QR tags (single or batch) for selected items.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation

from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
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
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Qt

from app.database.models import Item, ItemStatus, MakingChargeType, Purity
from app.services.category_service import get_all_categories
from app.services.gold_rate_service import get_latest_rate
from app.services.item_service import ValidationError, create_item, search_items
from app.services.pricing_service import calculate_item_price
from app.printing.tag_printer import TagData, generate_tag_sheet_pdf
from app.utils.qt_helpers import combo_enum_data


class InventoryScreen(QWidget):
    def __init__(self, current_user_id: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.current_user_id = current_user_id
        self._build_ui()
        self._reload_list()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        title = QLabel("Inventory Management")
        title.setStyleSheet("font-size: 22px; font-weight: bold;")
        layout.addWidget(title)

        splitter = QSplitter()
        splitter.addWidget(self._build_add_item_form())
        splitter.addWidget(self._build_list_panel())
        splitter.setSizes([420, 900])
        layout.addWidget(splitter, stretch=1)

    def _build_add_item_form(self) -> QWidget:
        box = QGroupBox("Add New Item")
        form = QFormLayout(box)

        self.name_input = QLineEdit()
        self.category_combo = QComboBox()
        for cat in get_all_categories():
            self.category_combo.addItem(cat.name, cat.id)

        self.purity_combo = QComboBox()
        for purity in Purity:
            self.purity_combo.addItem(purity.value, purity)
        self.purity_combo.currentIndexChanged.connect(self._update_price_preview)

        self.gross_weight_input = QLineEdit()
        self.gross_weight_input.textChanged.connect(self._update_price_preview)
        self.net_weight_input = QLineEdit()
        self.net_weight_input.textChanged.connect(self._update_price_preview)

        self.making_charge_type_combo = QComboBox()
        self.making_charge_type_combo.addItem("Flat (Rs.)", MakingChargeType.FLAT)
        self.making_charge_type_combo.addItem("Percent of gold value", MakingChargeType.PERCENT)
        self.making_charge_type_combo.currentIndexChanged.connect(self._update_price_preview)

        self.making_charge_value_input = QLineEdit()
        self.making_charge_value_input.textChanged.connect(self._update_price_preview)

        self.stone_value_input = QLineEdit()
        self.stone_value_input.setText("0")
        self.stone_value_input.textChanged.connect(self._update_price_preview)

        self.cost_price_input = QLineEdit()
        self.cost_price_input.setText("0")

        self.hallmark_input = QLineEdit()

        form.addRow("Name:", self.name_input)
        form.addRow("Category:", self.category_combo)
        form.addRow("Purity:", self.purity_combo)
        form.addRow("Gross weight (g):", self.gross_weight_input)
        form.addRow("Net weight (g):", self.net_weight_input)
        form.addRow("Making charge type:", self.making_charge_type_combo)
        form.addRow("Making charge value:", self.making_charge_value_input)
        form.addRow("Stone value (Rs.):", self.stone_value_input)
        form.addRow("Cost price (Rs.):", self.cost_price_input)
        form.addRow("Hallmark/cert no:", self.hallmark_input)

        self.price_preview_label = QLabel("Price preview: --")
        self.price_preview_label.setStyleSheet("font-weight: bold; color: #1b5e20;")
        form.addRow(self.price_preview_label)

        save_button = QPushButton("Save Item")
        save_button.clicked.connect(self._handle_save_item)
        form.addRow(save_button)

        return box

    def _update_price_preview(self) -> None:
        try:
            purity: Purity = combo_enum_data(self.purity_combo, Purity)
            net_weight = Decimal(self.net_weight_input.text() or "0")
            making_value = Decimal(self.making_charge_value_input.text() or "0")
            stone_value = Decimal(self.stone_value_input.text() or "0")
        except (InvalidOperation, ValueError):
            self.price_preview_label.setText("Price preview: (enter valid numbers)")
            return

        rate_row = get_latest_rate(purity)
        if rate_row is None:
            self.price_preview_label.setText(f"Price preview: no {purity.value} rate entered yet")
            return

        fake_item = Item(
            net_weight_g=net_weight,
            making_charge_type=combo_enum_data(self.making_charge_type_combo, MakingChargeType),
            making_charge_value=making_value,
            stone_value_total=stone_value,
        )
        breakdown = calculate_item_price(fake_item, rate_row.rate_per_gram)
        self.price_preview_label.setText(
            f"Price preview: Rs. {breakdown.subtotal:,.2f}  "
            f"(gold Rs.{breakdown.gold_value:,.2f} + making Rs.{breakdown.making_charge:,.2f} "
            f"+ stones Rs.{breakdown.stone_value:,.2f}) @ Rs.{rate_row.rate_per_gram:,.2f}/g"
        )

    def _handle_save_item(self) -> None:
        try:
            gross_weight = Decimal(self.gross_weight_input.text() or "0")
            net_weight = Decimal(self.net_weight_input.text() or "0")
            making_value = Decimal(self.making_charge_value_input.text() or "0")
            stone_value = Decimal(self.stone_value_input.text() or "0")
            cost_price = Decimal(self.cost_price_input.text() or "0")
        except (InvalidOperation, ValueError):
            QMessageBox.warning(self, "Invalid Input", "Please enter valid numbers for weights and charges.")
            return

        try:
            item_code = create_item(
                name=self.name_input.text(),
                category_id=self.category_combo.currentData(),
                purity=combo_enum_data(self.purity_combo, Purity),
                gross_weight_g=gross_weight,
                net_weight_g=net_weight,
                making_charge_type=combo_enum_data(self.making_charge_type_combo, MakingChargeType),
                making_charge_value=making_value,
                stone_value_total=stone_value,
                hallmark_certificate_no=self.hallmark_input.text() or None,
                cost_price=cost_price,
                created_by_user_id=self.current_user_id,
            )
        except ValidationError as exc:
            QMessageBox.warning(self, "Validation Error", str(exc))
            return

        QMessageBox.information(self, "Item Added", f"Item created with code {item_code}.")
        self._clear_form()
        self._reload_list()

    def _clear_form(self) -> None:
        self.name_input.clear()
        self.gross_weight_input.clear()
        self.net_weight_input.clear()
        self.making_charge_value_input.clear()
        self.stone_value_input.setText("0")
        self.cost_price_input.setText("0")
        self.hallmark_input.clear()

    def _build_list_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)

        search_row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by code or name...")
        self.search_input.textChanged.connect(self._reload_list)

        self.status_filter_combo = QComboBox()
        self.status_filter_combo.addItem("All statuses", None)
        for status in ItemStatus:
            self.status_filter_combo.addItem(status.value, status)
        self.status_filter_combo.currentIndexChanged.connect(self._reload_list)

        print_tags_button = QPushButton("Print QR Tags for Selected")
        print_tags_button.clicked.connect(self._handle_print_selected_tags)

        search_row.addWidget(self.search_input)
        search_row.addWidget(self.status_filter_combo)
        search_row.addWidget(print_tags_button)
        layout.addLayout(search_row)

        self.item_table = QTableWidget(0, 6)
        self.item_table.setHorizontalHeaderLabels(
            ["Code", "Name", "Category", "Purity", "Net Wt (g)", "Status"]
        )
        self.item_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.item_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.item_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.item_table)

        return panel

    def _reload_list(self) -> None:
        query = self.search_input.text()
        status = self.status_filter_combo.currentData()
        rows = search_items(query=query, status=status)

        self.item_table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            self.item_table.setItem(i, 0, QTableWidgetItem(row.item_code))
            self.item_table.setItem(i, 1, QTableWidgetItem(row.name))
            self.item_table.setItem(i, 2, QTableWidgetItem(row.category_name))
            self.item_table.setItem(i, 3, QTableWidgetItem(row.purity.value))
            self.item_table.setItem(i, 4, QTableWidgetItem(str(row.net_weight_g)))
            self.item_table.setItem(i, 5, QTableWidgetItem(row.status.value))
            # Stash the full row on the first cell for later retrieval (tag printing).
            self.item_table.item(i, 0).setData(Qt.ItemDataRole.UserRole, row)

    def _handle_print_selected_tags(self) -> None:
        selected_rows = {index.row() for index in self.item_table.selectedIndexes()}
        if not selected_rows:
            QMessageBox.warning(self, "No Selection", "Select one or more items in the table first.")
            return

        tags = []
        for row_index in sorted(selected_rows):
            item_row = self.item_table.item(row_index, 0).data(Qt.ItemDataRole.UserRole)
            tags.append(
                TagData(
                    item_code=item_row.item_code,
                    name=item_row.name,
                    net_weight_g=item_row.net_weight_g,
                    purity=item_row.purity.value,
                )
            )

        pdf_path = generate_tag_sheet_pdf(tags)
        QMessageBox.information(self, "Tags Generated", f"QR tag sheet saved to:\n{pdf_path}")
