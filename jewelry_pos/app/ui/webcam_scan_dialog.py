"""
Qt dialog showing a live webcam feed with QR/barcode decoding overlaid.
On a successful decode, emits code_scanned(str) -- the dialog stays
open so multiple items can be scanned in a row (per the project brief:
"the dialog can stay open for scanning the next item").
"""
from __future__ import annotations

import cv2
from PySide6.QtCore import QTimer, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QDialog, QLabel, QMessageBox, QPushButton, QVBoxLayout

from app.scanning.webcam_scanner import WebcamScanner


class WebcamScanDialog(QDialog):
    code_scanned = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Scan Item QR Code")
        self.resize(640, 520)
        self.scanner = WebcamScanner()
        self._last_scanned_code: str | None = None
        self._build_ui()
        self._start_camera()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        self.video_label = QLabel("Opening camera...")
        self.video_label.setFixedSize(600, 420)
        self.video_label.setStyleSheet("background-color: black; color: white;")
        layout.addWidget(self.video_label)

        self.status_label = QLabel("Point the camera at an item's QR tag.")
        layout.addWidget(self.status_label)

        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)

    def _start_camera(self) -> None:
        if not self.scanner.open():
            self.status_label.setText("Could not open the webcam. Check that it's connected and not in use.")
            QMessageBox.warning(self, "Camera Unavailable", "Could not open the webcam.")
            return

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_frame)
        self.timer.start(30)  # ~33 fps
