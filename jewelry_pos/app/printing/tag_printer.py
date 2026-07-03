"""
Printable QR tag sheets for jewelry items ("dumbbell" sticker layout:
small QR + item code + weight + purity). Renders a grid of tags onto
A4 pages sized for common sticker sheets, exported as PDF via ReportLab.
"""
from __future__ import annotations

import io
from dataclasses import dataclass
from decimal import Decimal

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm, mm
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

from app.printing.qr_service import generate_item_qr_image
from app.utils.config import TAGS_DIR

# Tag geometry: ~2x2cm QR plus a text strip beneath it.
TAG_WIDTH = 4.2 * cm
TAG_HEIGHT = 2.4 * cm
QR_SIZE = 2 * cm
MARGIN = 1 * cm
GAP = 0.3 * cm


@dataclass(frozen=True)
class TagData:
    item_code: str
    name: str
    net_weight_g: Decimal
    purity: str


def _draw_single_tag(pdf_canvas: canvas.Canvas, x: float, y: float, tag: TagData) -> None:
    """Draw one dumbbell tag with its top-left corner at (x, y)."""
    qr_image = generate_item_qr_image(tag.item_code, box_size=6, border=1)
    qr_reader = ImageReader(qr_image)

    # Border around the whole tag for cut-guide visibility on sticker sheets.
    pdf_canvas.setLineWidth(0.3)
    pdf_canvas.rect(x, y - TAG_HEIGHT, TAG_WIDTH, TAG_HEIGHT)

    # QR code on the left.
    qr_x = x + 0.15 * cm
    qr_y = y - TAG_HEIGHT + (TAG_HEIGHT - QR_SIZE) / 2
    pdf_canvas.drawImage(qr_reader, qr_x, qr_y, width=QR_SIZE, height=QR_SIZE)

    # Text block on the right: item code, weight, purity.
    text_x = qr_x + QR_SIZE + 0.2 * cm
    pdf_canvas.setFont("Helvetica-Bold", 7)
    pdf_canvas.drawString(text_x, y - 0.5 * cm, tag.item_code)
    pdf_canvas.setFont("Helvetica", 6)
    pdf_canvas.drawString(text_x, y - 1.0 * cm, f"{tag.net_weight_g}g {tag.purity}")
    pdf_canvas.drawString(text_x, y - 1.5 * cm, tag.name[:16])


def generate_tag_sheet_pdf(tags: list[TagData], output_path: str | None = None) -> str:
    """
    Render a grid of tags across as many A4 pages as needed. Returns the
    path to the generated PDF (defaults to data/tags/tags_<n>.pdf).
    """
    if not tags:
        raise ValueError("At least one tag is required.")

    if output_path is None:
        output_path = str(TAGS_DIR / f"tags_batch_{len(tags)}items.pdf")

    page_width, page_height = A4
    cols = int((page_width - 2 * MARGIN) // (TAG_WIDTH + GAP))
    rows = int((page_height - 2 * MARGIN) // (TAG_HEIGHT + GAP))
    per_page = max(cols * rows, 1)

    pdf_canvas = canvas.Canvas(output_path, pagesize=A4)

    for index, tag in enumerate(tags):
        pos_in_page = index % per_page
        if pos_in_page == 0 and index != 0:
            pdf_canvas.showPage()

        row = pos_in_page // cols
        col = pos_in_page % cols

        x = MARGIN + col * (TAG_WIDTH + GAP)
        y = page_height - MARGIN - row * (TAG_HEIGHT + GAP)

        _draw_single_tag(pdf_canvas, x, y, tag)

    pdf_canvas.save()
    return output_path
