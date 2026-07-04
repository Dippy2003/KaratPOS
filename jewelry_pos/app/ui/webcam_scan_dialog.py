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
