"""
gui/app.py
Main application window — connection status bar + onboarding form.
"""

import tkinter as tk
from tkinter import ttk
import threading
import datetime

from config import APP_TITLE, APP_VERSION, COMPANY_NAME
from gui.styles import C, F, apply_theme
from gui.user_form import UserForm
from core.o365_service import O365Service
from core.ad_service import ADService
from core.connection_manager import ConnectionManager, ConnectionStatus

<<<<<<< Updated upstream
# Path to company logo — set this to your logo file (PNG/GIF).
# Place the logo in the project root or adjust the path.
=======
>>>>>>> Stashed changes
import os
LOGO_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logo.png")


class OnboardingApp:
    """
    Main application window.
    Shows a live connection status bar at the top; only renders
    the UserForm once BOTH O365 and AD connections are confirmed.
    """

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(f"{APP_TITLE}  v{APP_VERSION}")
        self.root.configure(bg=C["bg"])

        # Maximize on Windows; fallback geometry elsewhere
        try:
            self.root.state("zoomed")
        except tk.TclError:
            self.root.geometry("1400x900")

        apply_theme(self.root)

        # Services
        self.o365     = O365Service()
        self.ad       = ADService()
        self.conn_mgr = ConnectionManager(self.o365, self.ad)

        self._form: tk.Widget = None
        self._loading_lbl: tk.Label = None
        self._form_shown = False
<<<<<<< Updated upstream
        self._logo_img = None    # keep reference to prevent GC
=======
        self._logo_img = None    # prevent GC
>>>>>>> Stashed changes

        self._build_ui()
        self._start_checks()

    # ── UI Construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        self._build_topbar()
        self._build_statusbar()

        self._content = tk.Frame(self.root, bg=C["bg"])
        self._content.pack(fill="both", expand=True)

        # AD warning banner (shown when AD not yet connected)
        self._ad_warn = tk.Frame(self._content, bg=C["warning"])
        self._ad_warn_lbl = tk.Label(
            self._ad_warn,
            text="⚠  Active Directory not connected — AD user will not be created until connected.",
            bg=C["warning"], fg="#000000", font=F["body_sm"],
        )
        self._ad_warn_lbl.pack(side="left", padx=12, pady=6)
        ttk.Button(self._ad_warn, text="⟳ Retry AD",
                   style="Secondary.TButton",
                   command=self._refresh).pack(side="right", padx=8, pady=4)
        # Hidden by default; shown when AD fails

        # Loading placeholder (shown while O365 is still connecting)
        self._loading_lbl = tk.Label(
            self._content,
            text="⏳  Connecting to O365…\n\n"
                 "Please wait — this may take a few seconds.",
            bg=C["bg"], fg=C["text_muted"], font=F["title"],
            justify="center",
        )
        self._loading_lbl.pack(expand=True)

    def _build_topbar(self):
        bar = tk.Frame(self.root, bg=C["surface"], height=64)
        bar.pack(fill="x", side="top")
        bar.pack_propagate(False)

        # ── Company Logo ──────────────────────────────────────────────────
        if os.path.isfile(LOGO_PATH):
            try:
                from PIL import Image, ImageTk
                img = Image.open(LOGO_PATH).resize((44, 44), Image.LANCZOS)
                self._logo_img = ImageTk.PhotoImage(img)
                tk.Label(bar, image=self._logo_img, bg=C["surface"]
                         ).pack(side="left", padx=(18, 8), pady=8)
            except ImportError:
<<<<<<< Updated upstream
                # Pillow not installed — try native PhotoImage (GIF/PGM only)
                try:
                    self._logo_img = tk.PhotoImage(file=LOGO_PATH)
                    # Subsample if too large
                    w, h = self._logo_img.width(), self._logo_img.height()
=======
                try:
                    self._logo_img = tk.PhotoImage(file=LOGO_PATH)
                    w = self._logo_img.width()
>>>>>>> Stashed changes
                    if w > 48:
                        factor = max(1, w // 44)
                        self._logo_img = self._logo_img.subsample(factor, factor)
                    tk.Label(bar, image=self._logo_img, bg=C["surface"]
                             ).pack(side="left", padx=(18, 8), pady=8)
                except Exception:
<<<<<<< Updated upstream
                    tk.Label(bar, text="🏢",
                             bg=C["surface"], font=("Segoe UI Emoji", 22)
                             ).pack(side="left", padx=(18, 4), pady=10)
        else:
            tk.Label(bar, text="🏢",
                     bg=C["surface"], font=("Segoe UI Emoji", 22)
                     ).pack(side="left", padx=(18, 4), pady=10)

        # ── Company Name ──────────────────────────────────────────────────
=======
                    tk.Label(bar, text="🏢", bg=C["surface"],
                             font=("Segoe UI Emoji", 22)
                             ).pack(side="left", padx=(18, 4), pady=10)
        else:
            tk.Label(bar, text="🏢", bg=C["surface"],
                     font=("Segoe UI Emoji", 22)
                     ).pack(side="left", padx=(18, 4), pady=10)

        # ── Company Name (from config.py COMPANY_NAME) ────────────────────
>>>>>>> Stashed changes
        tk.Label(bar, text=COMPANY_NAME.upper(),
                 bg=C["surface"], fg=C["accent"],
                 font=("Segoe UI", 14, "bold")
                 ).pack(side="left", pady=10)
        tk.Label(bar, text="  —  Employee Onboarding Portal",
                 bg=C["surface"], fg=C["text_muted"], font=F["body"]
                 ).pack(side="left", pady=10)

        ttk.Button(bar, text="⟳  Refresh Connections",
                   style="Secondary.TButton",
                   command=self._refresh
                   ).pack(side="right", padx=18, pady=12)

    def _build_statusbar(self):
        sb = tk.Frame(self.root, bg=C["surface2"], height=28)
        sb.pack(fill="x", side="top")
        sb.pack_propagate(False)

        def dot(text, var_attr):
            lbl = tk.Label(sb, text="●", bg=C["surface2"],
                           fg=C["text_dim"], font=F["status"])
            lbl.pack(side="left", padx=(14, 2), pady=4)
            setattr(self, var_attr + "_dot", lbl)

        def tag(text, var_attr):
            lbl = tk.Label(sb, text=text, bg=C["surface2"],
                           fg=C["text_muted"], font=F["status"])
            lbl.pack(side="left", padx=(0, 12), pady=4)
            setattr(self, var_attr + "_lbl", lbl)

        def sep():
            tk.Label(sb, text="|", bg=C["surface2"],
                     fg=C["border"], font=F["status"]).pack(side="left")

        dot("", "o365");  tag("O365: Connecting…", "o365");  sep()
        dot("", "ad");    tag("AD: Connecting…",   "ad");    sep()
        self._sync_lbl = tk.Label(sb, text="AD Sync: Checking…",
                                   bg=C["surface2"], fg=C["text_muted"],
                                   font=F["status"])
        self._sync_lbl.pack(side="left", padx=12, pady=4)

        self._time_lbl = tk.Label(sb, text="",
                                   bg=C["surface2"], fg=C["text_dim"],
                                   font=F["status"])
        self._time_lbl.pack(side="right", padx=14, pady=4)

    # ── Connection check ──────────────────────────────────────────────────────

    def _start_checks(self):
        self.conn_mgr.add_callback(self._on_status_update)
        threading.Thread(target=self._check_loop, daemon=True).start()

    def _check_loop(self):
        self.conn_mgr.check_all()
        self.conn_mgr.start_polling()

    def _refresh(self):
        threading.Thread(target=self.conn_mgr.check_all, daemon=True).start()

    # ── Status update (called from background thread via conn_mgr) ────────────

    def _on_status_update(self, status: ConnectionStatus):
        # Schedule on main thread — this method is called from a background thread.
        # root.after() is safe to call cross-thread (it posts to the event queue).
        try:
            self.root.after(0, lambda s=status: self._apply_status(s))
        except RuntimeError:
            pass   # window already destroyed

    def _apply_status(self, status: ConnectionStatus):
        # O365 status bar
        if status.o365_connected:
            tenant = f" ({status.o365_tenant})" if status.o365_tenant else ""
            self.o365_dot.configure(fg=C["success"])
            self.o365_lbl.configure(text=f"O365: Connected{tenant}", fg=C["success"])
        else:
            self.o365_dot.configure(fg=C["error"])
            self.o365_lbl.configure(text=f"O365: {status.o365_message}", fg=C["error"])

        # AD status bar
        if status.ad_connected:
            self.ad_dot.configure(fg=C["success"])
            self.ad_lbl.configure(text=f"AD: {status.ad_message}", fg=C["success"])
            # Hide the AD warning banner if it was showing
            self._ad_warn.pack_forget()
        else:
            self.ad_dot.configure(fg=C["error"])
            self.ad_lbl.configure(text=f"AD: {status.ad_message}", fg=C["error"])
            # Show AD warning banner in content area (if form is already visible)
            if self._form_shown:
                # Truncate long PS error to keep the banner tidy
                short_err = status.ad_message.split("\n")[0][:120]
                self._ad_warn_lbl.configure(
                    text=f"⚠  AD: {short_err}  —  AD user creation disabled until reconnected.")
                self._ad_warn.pack(fill="x", before=self._form)

        # AD Sync
        sync_text  = "AD Sync: ✅ Running" if status.ad_sync_running else "AD Sync: ⚠ Not Running"
        sync_color = C["success"] if status.ad_sync_running else C["warning"]
        self._sync_lbl.configure(text=sync_text, fg=sync_color)

        # Timestamp
        if status.last_checked:
            t = datetime.datetime.fromtimestamp(status.last_checked).strftime("%H:%M:%S")
            self._time_lbl.configure(text=f"Last checked: {t}")

        # ── Form display logic ────────────────────────────────────────────────
        # Show form as soon as O365 is connected.
        # AD being disconnected just shows a warning banner — doesn't block the form.
        if status.o365_connected and not self._form_shown:
            self._show_form()
        elif not status.o365_connected and not self._form_shown:
            self._loading_lbl.configure(
                text="⚠  Cannot connect to O365.\n\n"
                     "• Ensure Azure CLI is logged in (run: az login).\n"
                     "• Click  ⟳ Refresh Connections  to retry.\n\n"
                     f"O365:  {status.o365_message}",
                fg=C["warning"],
            )

    def _show_form(self):
        self._form_shown = True
        if self._loading_lbl:
            self._loading_lbl.destroy()
            self._loading_lbl = None
        self._form = UserForm(self._content, self.o365, self.ad)
        self._form.pack(fill="both", expand=True)
        # Expose form ref so _apply_status can position the banner before it
