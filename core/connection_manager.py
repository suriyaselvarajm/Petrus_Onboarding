"""
core/connection_manager.py
Monitors O365 and AD connections; notifies UI via callbacks.
"""

import threading
import time
from dataclasses import dataclass, field
from typing import Callable, List, Optional

from config import CONNECTION_POLL_INTERVAL


@dataclass
class ConnectionStatus:
    o365_connected:   bool = False
    o365_message:     str  = "Not checked"
    o365_tenant:      str  = ""
    ad_connected:     bool = False
    ad_message:       str  = "Not checked"
    ad_sync_running:  bool = False
    ad_sync_message:  str  = "Unknown"
    last_checked:     float = 0.0


class ConnectionManager:
    """
    Tests O365 (via Graph) and AD (via PowerShell) connections.
    Starts a background polling thread and calls registered callbacks
    whenever the status updates — safe to call from a Tkinter thread
    via root.after().
    """

    def __init__(self, o365_service, ad_service):
        self.o365     = o365_service
        self.ad       = ad_service
        self.status   = ConnectionStatus()
        self._cbs:    List[Callable] = []
        self._polling = False
        self._thread: Optional[threading.Thread] = None

    def add_callback(self, cb: Callable[[ConnectionStatus], None]) -> None:
        self._cbs.append(cb)

    def _notify(self) -> None:
        for cb in self._cbs:
            try:
                cb(self.status)
            except Exception:
                pass

    # ── Public API ────────────────────────────────────────────────────────────

    def check_all(self) -> ConnectionStatus:
        """Synchronous check. Blocks until both checks complete."""
        # O365
        ok, msg = self.o365.test_connection()
        self.status.o365_connected = ok
        self.status.o365_message   = msg
        if ok:
            info = self.o365.get_tenant_info()
            self.status.o365_tenant = info.get("displayName", "")

        # AD
        ok_ad, msg_ad = self.ad.test_connection()
        self.status.ad_connected = ok_ad
        self.status.ad_message   = msg_ad

        # AD Sync
        sync_ok, sync_msg = self.ad.check_ad_sync()
        self.status.ad_sync_running = sync_ok
        self.status.ad_sync_message = sync_msg

        self.status.last_checked = time.time()
        self._notify()
        return self.status

    def start_polling(self, interval: int = CONNECTION_POLL_INTERVAL) -> None:
        """Start background polling thread."""
        if self._thread and self._thread.is_alive():
            return
        self._polling = True
        self._thread  = threading.Thread(
            target=self._loop, args=(interval,), daemon=True
        )
        self._thread.start()

    def stop_polling(self) -> None:
        self._polling = False

    def _loop(self, interval: int) -> None:
        while self._polling:
            try:
                self.check_all()
            except Exception:
                pass
            time.sleep(interval)
