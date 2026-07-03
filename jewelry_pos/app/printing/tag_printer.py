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
