"""
gui/splash.py
Startup / dependency check screen.
Uses a thread-safe queue — background thread puts messages in queue,
main thread drains it via after(50, ...) polling. No direct widget
calls from background threads (fixes RuntimeError in Python 3.14+).
"""

import tkinter as tk
from tkinter import ttk
import threading
import queue

from gui.styles import C, F, apply_theme
from core.dependency_checker import (
    DependencyCheck, check_az_logged_in, do_az_login,
)


class SplashScreen(tk.Toplevel):
    """Frameless startup window for dependency checks."""

    def __init__(self, parent: tk.Tk):
        super().__init__(parent)
        self.success   = False
        self._done     = False
        self._q: queue.Queue = queue.Queue()

        self.overrideredirect(True)          # no title bar
        self.configure(bg=C["bg"])
        apply_theme(self)

        W, H = 680, 480
        self.geometry(f"{W}x{H}")
        self._center(W, H)

        self._build()

        # Start queue polling (main thread)
        self._poll()
        # Start dependency check (background thread)
        self.after(300, self._start_check)

    def _center(self, w: int, h: int) -> None:
        self.update_idletasks()
        x = (self.winfo_screenwidth()  - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    # ── Build UI ──────────────────────────────────────────────────────────────

    def _build(self) -> None:
        # Header band
        hdr = tk.Frame(self, bg=C["surface"], height=70)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        tk.Label(hdr, text="PETRUS TECHNOLOGIES",
                 bg=C["surface"], fg=C["accent"],
                 font=("Segoe UI", 16, "bold")).pack(side="left", padx=24, pady=18)
        tk.Label(hdr, text="Employee Onboarding Portal",
                 bg=C["surface"], fg=C["text_muted"],
                 font=F["body"]).pack(side="right", padx=24, pady=18)

        body = tk.Frame(self, bg=C["bg"])
        body.pack(fill="both", expand=True, padx=40, pady=20)

        tk.Label(body, text="Initializing System…",
                 bg=C["bg"], fg=C["text"],
                 font=F["title_lg"]).pack(pady=(0, 6))

        self._subtitle = tk.Label(
            body, text="Checking dependencies — please wait",
            bg=C["bg"], fg=C["text_muted"], font=F["body"])
        self._subtitle.pack(pady=(0, 18))

        # Progress bar
        self._pvar = tk.DoubleVar()
        self._pbar = ttk.Progressbar(body, variable=self._pvar,
                                      maximum=100, mode="determinate", length=580)
        self._pbar.pack(fill="x")

        self._plabel = tk.Label(body, text="Starting…",
                                 bg=C["bg"], fg=C["text_muted"], font=F["body_sm"])
        self._plabel.pack(anchor="w", pady=(4, 12))

        # Log panel
        log_outer = tk.Frame(body, bg=C["surface"], bd=0)
        log_outer.pack(fill="both", expand=True)

        self._log = tk.Text(log_outer, bg=C["input_bg"], fg=C["text_muted"],
                             font=("Consolas", 8), relief="flat", state="disabled",
                             wrap="word", bd=0, height=10)
        log_scroll = ttk.Scrollbar(log_outer, command=self._log.yview)
        self._log.configure(yscrollcommand=log_scroll.set)
        self._log.pack(side="left", fill="both", expand=True, padx=8, pady=8)
        log_scroll.pack(side="right", fill="y", pady=8)

        # Status label
        self._status_lbl = tk.Label(body, text="",
                                     bg=C["bg"], fg=C["success"], font=F["body"])
        self._status_lbl.pack(pady=(10, 0))

        # Action buttons area
        self._action_frame = tk.Frame(body, bg=C["bg"])
        self._action_frame.pack(pady=4)

    # ── Thread-safe queue pump ────────────────────────────────────────────────

    def _poll(self) -> None:
        """Drain the message queue from the main thread (called every 50 ms)."""
        try:
            while True:
                msg = self._q.get_nowait()
                kind = msg[0]

                if kind == "log":
                    self._do_log(msg[1])
                elif kind == "progress":
                    self._do_progress(msg[1], msg[2])
                elif kind == "status":
                    self._do_status(msg[1], msg[2])
                elif kind == "az_login":
                    self._prompt_az_login()
                elif kind == "az_ok":
                    self._do_log("[OK] Azure CLI authenticated successfully")
                    self._complete(True)
                elif kind == "az_timeout":
                    self._do_status("❌ Azure login timed out. Close and retry.", C["error"])
                elif kind == "complete":
                    self._complete(msg[1])
                    return          # stop polling — splash will close
                elif kind == "critical":
                    self._on_critical_error(msg[1])
                    return
        except queue.Empty:
            pass

        if not self._done:
            self.after(50, self._poll)

    # Actual widget-update methods (always on main thread)

    def _do_log(self, text: str) -> None:
        self._log.configure(state="normal")
        self._log.insert("end", text + "\n")
        self._log.see("end")
        self._log.configure(state="disabled")

    def _do_progress(self, pct: float, msg: str) -> None:
        self._pvar.set(pct)
        self._plabel.configure(text=msg)

    def _do_status(self, text: str, color: str) -> None:
        self._status_lbl.configure(text=text, fg=color)

    # ── Thread-safe callbacks (called from background thread) ─────────────────

    def _q_log(self, msg: str) -> None:
        self._q.put(("log", msg))

    def _q_progress(self, pct: float, msg: str) -> None:
        self._q.put(("progress", pct, msg))

    # ── Dependency check flow ─────────────────────────────────────────────────

    def _start_check(self) -> None:
        def run():
            checker = DependencyCheck(
                progress_cb=self._q_progress,
                log_cb=self._q_log,
            )
            all_ok, issues, warnings = checker.run()

            if not all_ok:
                self._q.put(("critical", issues))
                return

            for w in warnings:
                self._q.put(("log", f"[WARN] {w}"))

            # Check Azure CLI login
            if not check_az_logged_in():
                self._q.put(("az_login",))
            else:
                self._q.put(("complete", True))

        threading.Thread(target=run, daemon=True).start()

    def _on_critical_error(self, issues: list) -> None:
        self._do_status("❌ Critical dependency check failed", C["error"])
        for issue in issues:
            self._do_log(f"[CRITICAL] {issue}")
        ttk.Button(self._action_frame, text="Close",
                   style="Danger.TButton",
                   command=self.destroy).pack(padx=4, pady=4)

    def _prompt_az_login(self) -> None:
        self._do_progress(95, "Azure CLI login required")
        self._do_log("\n[INFO] Not authenticated — opening browser for Azure login…")
        self._do_status(
            "⏳ Waiting for Azure login… (sign in with your admin account)",
            C["warning"])
        do_az_login()
        # Poll login in background, push result to queue
        threading.Thread(target=self._wait_for_az_login, daemon=True).start()

    def _wait_for_az_login(self, attempt: int = 0) -> None:
        """Background thread: poll every 3 s until az login completes."""
        import time
        for i in range(41):          # max ~2 minutes
            time.sleep(3)
            if check_az_logged_in():
                self._q.put(("az_ok",))
                return
        self._q.put(("az_timeout",))

    def _complete(self, success: bool) -> None:
        self._done = True
        self.success = success
        if success:
            self._do_progress(100, "All systems ready!")
            self._do_status("✅ All dependencies verified — launching portal…", C["success"])
            self.after(1500, self.destroy)
        else:
            self._do_status("❌ Setup incomplete.", C["error"])
            ttk.Button(self._action_frame, text="Continue Anyway",
                       command=self.destroy).pack(side="left", padx=4)
            ttk.Button(self._action_frame, text="Exit",
                       style="Danger.TButton",
                       command=lambda: self.master.destroy()).pack(side="left", padx=4)
