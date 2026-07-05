"""Printable repair job ticket (small slip with job number and details)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from reportlab.lib.pagesizes import A6
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas

from app.utils.config import DATA_DIR

TICKETS_DIR = DATA_DIR / "repair_tickets"
TICKETS_DIR.mkdir(parents=True, exist_ok=True)


@dataclass(frozen=True)
class RepairTicketData:
    repair_id: int
    customer_name: str
    item_description: str
    issue: str
    received_date: date
    promised_date: date | None
    estimated_cost: Decimal


def generate_repair_ticket_pdf(data: RepairTicketData) -> str:
    output_path = str(TICKETS_DIR / f"repair_{data.repair_id}.pdf")
    page_width, page_height = A6
    pdf = canvas.Canvas(output_path, pagesize=A6)
    x = 1 * cm
    y = page_height - 1 * cm

    def line(text: str, font: str = "Helvetica", size: int = 10) -> None:
        nonlocal y
        pdf.setFont(font, size)
        pdf.drawString(x, y, text)
        y -= 0.55 * cm

    line(f"REPAIR JOB #{data.repair_id}", font="Helvetica-Bold", size=13)
    line(f"Customer: {data.customer_name}")
    line(f"Item: {data.item_description}")
    line(f"Issue: {data.issue}")
    line(f"Received: {data.received_date.strftime('%d/%m/%Y')}")
    line(f"Promised: {data.promised_date.strftime('%d/%m/%Y') if data.promised_date else 'Not set'}")
    line(f"Estimated cost: Rs. {data.estimated_cost:,.2f}")
    line("Please bring this ticket when collecting your item.", size=8)

    pdf.save()
    return output_path
