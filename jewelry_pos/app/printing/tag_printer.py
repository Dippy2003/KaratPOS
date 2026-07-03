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
