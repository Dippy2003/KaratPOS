"""
A4 PDF receipt generation via ReportLab, matching the layout specified
in the project brief. Renders directly from the frozen invoice_items
snapshot -- never recalculates prices at print/reprint time.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas

from app.utils.config import RECEIPTS_DIR


@dataclass(frozen=True)
class ReceiptLine:
    item_name: str
    item_code: str
    net_weight_g: Decimal
    purity: str
    gold_rate_used: Decimal
    gold_value: Decimal
    making_charge: Decimal
    stone_value: Decimal
    line_total: Decimal


@dataclass(frozen=True)
class ReceiptPaymentLine:
    method: str
    amount: Decimal


@dataclass(frozen=True)
class ReceiptData:
    shop_name: str
    shop_address: str
    shop_phone: str
    invoice_no: str
    invoice_datetime: datetime
    cashier_name: str
    customer_name: str | None
    lines: list[ReceiptLine]
    subtotal: Decimal
    discount_total: Decimal
    tax_total: Decimal
    old_gold_credit: Decimal
    grand_total: Decimal
    payments: list[ReceiptPaymentLine]
    balance_returned: Decimal
    footer_text: str
    is_reprint: bool = False


def generate_receipt_pdf(data: ReceiptData, output_path: str | None = None) -> str:
    """Render the A4 receipt PDF and return its file path."""
    if output_path is None:
        suffix = "_REPRINT" if data.is_reprint else ""
        output_path = str(RECEIPTS_DIR / f"{data.invoice_no}{suffix}.pdf")

    page_width, page_height = A4
    pdf = canvas.Canvas(output_path, pagesize=A4)
    x_margin = 2 * cm
    y = page_height - 2 * cm
    line_height = 0.5 * cm

    def line(text: str, font: str = "Helvetica", size: int = 9, center: bool = False) -> None:
        nonlocal y
        pdf.setFont(font, size)
        if center:
            pdf.drawCentredString(page_width / 2, y, text)
        else:
            pdf.drawString(x_margin, y, text)
        y -= line_height

    def divider() -> None:
        nonlocal y
        pdf.line(x_margin, y, page_width - x_margin, y)
        y -= line_height * 0.6

    if data.is_reprint:
        pdf.setFillColorRGB(0.85, 0.85, 0.85)
        pdf.setFont("Helvetica-Bold", 60)
        pdf.saveState()
        pdf.translate(page_width / 2, page_height / 2)
        pdf.rotate(45)
        pdf.drawCentredString(0, 0, "REPRINT")
        pdf.restoreState()
        pdf.setFillColorRGB(0, 0, 0)

    line(data.shop_name, font="Helvetica-Bold", size=14, center=True)
    line(data.shop_address, center=True)
    line(data.shop_phone, center=True)
    divider()

    line(f"Invoice : {data.invoice_no}")
    line(f"Date    : {data.invoice_datetime.strftime('%d/%m/%Y %I:%M %p')}")
    line(f"Cashier : {data.cashier_name}")
    if data.customer_name:
        line(f"Customer: {data.customer_name}")
    divider()

    for item_line in data.lines:
        line(f"{item_line.item_name}  ({item_line.item_code})", font="Helvetica-Bold")
        line(f"  Weight {item_line.net_weight_g} g @ Rs.{item_line.gold_rate_used:,.2f}/g")
        line(f"  Gold value        Rs. {item_line.gold_value:,.2f}")
        line(f"  Making charge     Rs. {item_line.making_charge:,.2f}")
        line(f"  Stone value       Rs. {item_line.stone_value:,.2f}")
        line(f"  Line total        Rs. {item_line.line_total:,.2f}")
        divider()

    line(f"Subtotal            Rs. {data.subtotal:,.2f}")
    line(f"Discount            Rs. {data.discount_total:,.2f}")
    line(f"Tax                 Rs. {data.tax_total:,.2f}")
    line(f"Old gold credit    -Rs. {data.old_gold_credit:,.2f}")
    line(f"GRAND TOTAL         Rs. {data.grand_total:,.2f}", font="Helvetica-Bold")

    paid_str = " / ".join(f"{p.method} Rs.{p.amount:,.2f}" for p in data.payments)
    line(f"Paid: {paid_str}")
    line(f"Balance returned    Rs. {data.balance_returned:,.2f}")
    divider()

    line(data.footer_text, center=True)

    pdf.save()
    return output_path
