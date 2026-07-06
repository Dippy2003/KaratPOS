"""
Optional 80mm thermal receipt printing via python-escpos. Only used
when Settings > thermal_printer_enabled is on; a failure here must
never affect the sale itself (the sale is already committed and a
PDF receipt already exists by the time this runs) -- callers should
catch exceptions and just warn, not roll back anything.
"""
from __future__ import annotations

from app.printing.receipt_pdf import ReceiptData


def print_thermal_receipt(data: ReceiptData, printer_port: str) -> None:
    """
    Send a plain-text ESC/POS receipt to a USB/serial thermal printer.
    Raises on failure -- caller is responsible for catching and showing
    a non-blocking warning (the sale itself must never be affected).
    """
    from escpos.printer import Usb  # imported lazily: only needed if thermal printing is enabled

    if not printer_port:
        raise ValueError("No thermal printer port configured in Settings.")

    # printer_port format expected: "VENDOR_ID:PRODUCT_ID" (hex), e.g. "04b8:0202"
    vendor_hex, _, product_hex = printer_port.partition(":")
    printer = Usb(int(vendor_hex, 16), int(product_hex, 16))

    try:
        printer.set(align="center", bold=True)
        printer.text(f"{data.shop_name}\n")
        printer.set(align="center", bold=False)
        printer.text(f"{data.shop_address}\n{data.shop_phone}\n")
        printer.text("-" * 32 + "\n")

        printer.set(align="left")
        printer.text(f"Invoice : {data.invoice_no}\n")
        printer.text(f"Date    : {data.invoice_datetime.strftime('%d/%m/%Y %I:%M %p')}\n")
        printer.text(f"Cashier : {data.cashier_name}\n")
        if data.customer_name:
            printer.text(f"Customer: {data.customer_name}\n")
        printer.text("-" * 32 + "\n")

        for line in data.lines:
            printer.text(f"{line.item_name} ({line.item_code})\n")
            printer.text(f"  Weight {line.net_weight_g}g @ Rs.{line.gold_rate_used:,.2f}/g\n")
            printer.text(f"  Line total  Rs. {line.line_total:,.2f}\n")

        printer.text("-" * 32 + "\n")
        printer.text(f"GRAND TOTAL  Rs. {data.grand_total:,.2f}\n")
        printer.text(f"Balance returned  Rs. {data.balance_returned:,.2f}\n")
        printer.text("-" * 32 + "\n")
        printer.set(align="center")
        printer.text(f"{data.footer_text}\n")
        printer.cut()
    finally:
        printer.close()
