"""
LAN-only phone camera scanning bridge. Runs a small Flask server that
serves one mobile page (html5-qrcode) which opens the phone's camera;
on scan, the phone POSTs the decoded item_code back here, which is
pushed into a thread-safe queue for the POS screen to drain via a Qt
timer. No internet access is used or required -- this only works on
the shop's local Wi-Fi/LAN.
"""
from __future__ import annotations

import queue
import socket
import threading

from flask import Flask, jsonify, render_template_string, request

_scanned_code_queue: "queue.Queue[str]" = queue.Queue()

_MOBILE_PAGE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>KaratPOS Scanner</title>
    <!-- html5-qrcode is loaded from /static/html5-qrcode.min.js, bundled
         locally (see app/scanning/static/) so the phone does not need
         internet access -- only LAN connectivity to this desktop PC. -->
    <script src="/static/html5-qrcode.min.js"></script>
</head>
<body style="font-family: sans-serif; text-align: center; padding: 12px;">
    <h2>KaratPOS Item Scanner</h2>
    <div id="reader" style="width: 100%; max-width: 400px; margin: 0 auto;"></div>
    <p id="status">Point the camera at an item's QR tag.</p>
    <script>
        function onScanSuccess(decodedText) {
            document.getElementById("status").innerText = "Scanned: " + decodedText;
            fetch("/scan", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({code: decodedText}),
            });
        }
        const scanner = new Html5Qrcode("reader");
        scanner.start({facingMode: "environment"}, {fps: 10, qrbox: 250}, onScanSuccess);
    </script>
</body>
</html>
"""


def get_lan_ip() -> str:
    """
    Best-effort LAN IP for staff to reach this server from their phone.
    The UDP "connect" here never actually sends a packet (UDP connect
    just resolves local routing), so this works fully offline and
    makes no real network call.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def create_flask_app() -> Flask:
    import os

    static_dir = os.path.join(os.path.dirname(__file__), "static")
    flask_app = Flask(__name__, static_folder=static_dir, static_url_path="/static")

    @flask_app.route("/")
    def index():
        return render_template_string(_MOBILE_PAGE_HTML)

    @flask_app.route("/scan", methods=["POST"])
    def scan():
        payload = request.get_json(silent=True) or {}
        code = (payload.get("code") or "").strip()
        if code:
            _scanned_code_queue.put(code)
        return jsonify({"status": "ok"})

    return flask_app


class PhoneBridgeServer:
    """Runs the Flask app in a background thread so it never blocks the Qt event loop."""

    def __init__(self, port: int = 5000) -> None:
        self.port = port
        self._flask_app = create_flask_app()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._thread = threading.Thread(
            target=self._flask_app.run,
            kwargs={"host": "0.0.0.0", "port": self.port, "debug": False, "use_reloader": False},
            daemon=True,
        )
        self._thread.start()

    def get_url(self) -> str:
        return f"http://{get_lan_ip()}:{self.port}/"

    def drain_scanned_codes(self) -> list[str]:
        """Non-blocking: pull all codes scanned since the last drain."""
        codes = []
        while True:
            try:
                codes.append(_scanned_code_queue.get_nowait())
            except queue.Empty:
                break
        return codes
