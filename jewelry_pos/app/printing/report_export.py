"""Generic CSV and simple PDF export helpers for the Reports screen."""
from __future__ import annotations

import csv
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas

from app.utils.config import REPORTS_DIR


def export_rows_to_csv(headers: list[str], rows: list[list[str]], filename_prefix: str) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = str(REPORTS_DIR / f"{filename_prefix}_{timestamp}.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)
    return path


def export_rows_to_pdf(title: str, headers: list[str], rows: list[list[str]], filename_prefix: str) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = str(REPORTS_DIR / f"{filename_prefix}_{timestamp}.pdf")

    page_width, page_height = A4
    pdf = canvas.Canvas(path, pagesize=A4)
    x_margin = 1.5 * cm
    y = page_height - 1.5 * cm

    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(x_margin, y, title)
    y -= 0.8 * cm

    pdf.setFont("Helvetica-Bold", 9)
    pdf.drawString(x_margin, y, "  |  ".join(headers))
    y -= 0.5 * cm
    pdf.line(x_margin, y, page_width - x_margin, y)
    y -= 0.4 * cm

    pdf.setFont("Helvetica", 8)
    for row in rows:
        if y < 1.5 * cm:
            pdf.showPage()
            y = page_height - 1.5 * cm
            pdf.setFont("Helvetica", 8)
        pdf.drawString(x_margin, y, "  |  ".join(str(v) for v in row))
        y -= 0.45 * cm

    pdf.save()
    return path
