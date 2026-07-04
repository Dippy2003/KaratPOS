"""
Webcam QR decoding using OpenCV for camera capture and pyzbar for
barcode/QR decode. Kept free of any Qt dependency so it can be unit
tested without a display or camera hardware attached.
"""
from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np
from pyzbar import pyzbar


@dataclass(frozen=True)
class DecodedCode:
    data: str
    rect: tuple[int, int, int, int]  # x, y, width, height in frame coordinates


class WebcamScanner:
    """Thin wrapper around cv2.VideoCapture that yields frames and decoded codes."""

    def __init__(self, camera_index: int = 0) -> None:
        self.camera_index = camera_index
        self._capture: cv2.VideoCapture | None = None

    def open(self) -> bool:
        self._capture = cv2.VideoCapture(self.camera_index)
        return self._capture.isOpened()

    def read_frame(self) -> np.ndarray | None:
        if self._capture is None or not self._capture.isOpened():
            return None
        ok, frame = self._capture.read()
        return frame if ok else None

    def decode_frame(self, frame: np.ndarray) -> list[DecodedCode]:
        results = pyzbar.decode(frame)
        return [
            DecodedCode(data=r.data.decode("utf-8", errors="ignore"), rect=(r.rect.left, r.rect.top, r.rect.width, r.rect.height))
            for r in results
        ]

    def release(self) -> None:
        if self._capture is not None:
            self._capture.release()
            self._capture = None

    def __enter__(self) -> "WebcamScanner":
        self.open()
        return self

    def __exit__(self, *exc_info) -> None:
        self.release()
