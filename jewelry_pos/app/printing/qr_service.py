"""
QR code image generation for item tags. The QR encodes ONLY the
item_code (e.g. "ITM-000042") -- never a price, since prices are
computed live and would go stale on a printed sticker.
"""
from __future__ import annotations

import io

import qrcode
from PIL import Image


def generate_item_qr_image(item_code: str, box_size: int = 10, border: int = 2) -> Image.Image:
    """Return a PIL Image of a QR code encoding just the item_code."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=box_size,
        border=border,
    )
    qr.add_data(item_code)
    qr.make(fit=True)
    return qr.make_image(fill_color="black", back_color="white").convert("RGB")


def qr_image_to_png_bytes(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()
