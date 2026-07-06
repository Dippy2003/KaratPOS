"""
Process-wide singleton PhoneBridgeServer instance. The Settings screen
starts/stops it based on the phone_bridge_enabled setting; the POS
screen polls it (when running) for newly scanned codes. Kept as a
module-level singleton so both screens share the same running server
instance rather than each spinning up their own.
"""
from __future__ import annotations

from app.scanning.phone_bridge import PhoneBridgeServer

_instance: PhoneBridgeServer | None = None


def get_bridge_server() -> PhoneBridgeServer:
    global _instance
    if _instance is None:
        _instance = PhoneBridgeServer(port=5000)
    return _instance


def is_bridge_running() -> bool:
    return _instance is not None and _instance._thread is not None and _instance._thread.is_alive()
