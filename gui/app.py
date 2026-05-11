"""
gui/app.py
Main application window — connection status bar + onboarding form.
"""

import tkinter as tk
from tkinter import ttk
import threading
import datetime
import os
import sys

from config import APP_TITLE, APP_VERSION, COMPANY_NAME
from gui.styles import C, F, apply_theme
from gui.user_form import UserForm
from gui.offboarding_form import OffboardingForm
from gui.profile_update_form import ProfileUpdateForm
from gui.login_form import LoginForm
from gui.settings_form import SettingsForm
from core.o365_service import O365Service
from core.ad_service import ADService
from core.connection_manager import ConnectionManager, ConnectionStatus

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

LOGO_PATH = resource_path("logo.png")

class OnboardingApp:
    """
    Main application window.
    Shows a live connection status bar at the top; only renders
    the selection screen once authenticated.
    """

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(f"{APP_TITLE}  v{APP_VERSION}")
        
        # Current theme state
        self._is_dark = True
        self._is_authenticated = False
        self._logo_img = None
        
        apply_theme(self.root, is_dark=self._is_dark)
        self.root.configure(bg=C["bg"])

        # Maximize on Windows; fallback geometry elsewhere
        try:
            self.root.state("zoomed")
        except tk.TclError:
            self.root.geometry("1400x900")

        # Services
        self.o365     = O365Service()
        self.ad       = ADService()
        self.conn_mgr = ConnectionManager(self.o365, self.ad)

        self._form: tk.Widget = None
        self._login_form: tk.Widget = None
        self._loading_lbl: tk.Label = None
        self._form_shown = False

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
            text="⚠  Active Directory not connected — AD user will not be created until reconnected.",
            bg=C["warning"], fg="#000000", font=F["body_sm"],
        )
        self._ad_warn_lbl.pack(side="left", padx=12, pady=6)
        ttk.Button(self._ad_warn, text="⟳ Retry AD",
                   style="Secondary.TButton",
                   command=self._refresh).pack(side="right", padx=8, pady=4)

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
        self._topbar = tk.Frame(self.root, bg=C["surface"], height=64)
        self._topbar.pack(fill="x", side="top")
        self._topbar.pack_propagate(False)
        bar = self._topbar

        # ── Company Logo ──────────────────────────────────────────────────
        logo_found = False
        if os.path.isfile(LOGO_PATH):
            try:
                from PIL import Image, ImageTk
                img = Image.open(LOGO_PATH).resize((44, 44), Image.LANCZOS)
                self._logo_img = ImageTk.PhotoImage(img)
                tk.Label(bar, image=self._logo_img, bg=C["surface"]
                         ).pack(side="left", padx=(18, 8), pady=8)
                logo_found = True
            except Exception:
                pass

        if not logo_found:
            tk.Label(bar, text="🏢",
                     bg=C["surface"], font=("Segoe UI Emoji", 22)
                     ).pack(side="left", padx=(18, 4), pady=10)

        # ── Company Name ────────────────────
        tk.Label(bar, text=COMPANY_NAME.upper(),
                 bg=C["surface"], fg=C["accent"],
                 font=("Segoe UI", 14, "bold")
                 ).pack(side="left", pady=10)
        
        tk.Label(bar, text="  —  Employee Onboarding Portal",
                 bg=C["surface"], fg=C["text_muted"], font=F["body"]
                 ).pack(side="left", pady=10)

        self._theme_btn = ttk.Button(bar, text="☀️  Light Mode" if self._is_dark else "🌙  Dark Mode",
                                    style="Secondary.TButton",
                                    command=self._toggle_theme)
        self._theme_btn.pack(side="right", padx=(4, 18), pady=12)

        ttk.Button(bar, text="🚪  Logout",
                   style="Secondary.TButton",
                   command=self._logout
                   ).pack(side="right", padx=4, pady=12)

        ttk.Button(bar, text="⟳  Refresh Connections",
                   style="Secondary.TButton",
                   command=self._refresh
                   ).pack(side="right", padx=4, pady=12)

        self._settings_btn = ttk.Button(bar, text="⚙️  Settings",
                   style="Secondary.TButton",
                   command=self._launch_settings
                   )

    def _logout(self):
        from tkinter import messagebox
        from core.credential_manager import cred_manager
        if messagebox.askyesno("Logout", "Are you sure you want to log out?", parent=self.root):
            cred_manager.logout()
            self.root.destroy()

    def _build_statusbar(self):
        self._statusbar = tk.Frame(self.root, bg=C["surface2"], height=28)
        self._statusbar.pack(fill="x", side="top")
        self._statusbar.pack_propagate(False)
        sb = self._statusbar

        def dot(var_attr):
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

        dot("o365");  tag("O365: Connecting…", "o365");  sep()
        dot("ad");    tag("AD: Connecting…",   "ad");    sep()
        
        self._sync_lbl = tk.Label(sb, text="AD Sync: Status Unknown",
                                   bg=C["surface2"], fg=C["text_muted"],
                                   font=F["status"])
        self._sync_lbl.pack(side="left", padx=12, pady=4)

        self._time_lbl = tk.Label(sb, text="",
                                   bg=C["surface2"], fg=C["text_dim"],
                                   font=F["status"])
        self._time_lbl.pack(side="right", padx=14, pady=4)

    def _toggle_theme(self):
        self._is_dark = not self._is_dark
        apply_theme(self.root, is_dark=self._is_dark)
        
        btn_text = "☀️  Light Mode" if self._is_dark else "🌙  Dark Mode"
        self._theme_btn.configure(text=btn_text)
        
        self._update_widget_themes(self.root)
        
        self._topbar.configure(bg=C["surface"])
        self._statusbar.configure(bg=C["surface2"])
        
        # Refresh current form if any
        if self._form:
            current_class = self._form.__class__
            self._form.destroy()
            if current_class == OffboardingForm: self._show_offboarding()
            elif current_class == ProfileUpdateForm: self._show_profile_update()
            elif current_class == SettingsForm: self._show_settings()
            else: self._show_form()
        elif hasattr(self, "_sel_frame") and self._sel_frame:
            self._sel_frame.destroy()
            self._show_selection()

    def _update_widget_themes(self, parent):
        for child in parent.winfo_children():
            wtype = child.winfo_class()
            if wtype.startswith("T"): 
                self._update_widget_themes(child)
                continue
            try:
                if wtype == "Frame":
                    child.configure(bg=C["bg"])
                elif wtype == "Label":
                    child.configure(bg=child.cget("bg"), fg=C["text"]) # Keep original bg if special
                    if child.cget("bg") == C["bg"] or child.cget("bg").lower() in ["#f0f4f8", "#0d1117"]:
                        child.configure(bg=C["bg"])
                self._update_widget_themes(child)
            except Exception: pass

    def _start_checks(self):
        self.conn_mgr.add_callback(self._on_status_update)
        threading.Thread(target=self._check_loop, daemon=True).start()

    def _check_loop(self):
        self.conn_mgr.check_all()
        self.conn_mgr.start_polling()

    def _refresh(self):
        threading.Thread(target=self.conn_mgr.check_all, daemon=True).start()

    def _on_status_update(self, status: ConnectionStatus):
        try:
            self.root.after(0, lambda s=status: self._apply_status(s))
        except RuntimeError: pass

    def _apply_status(self, status: ConnectionStatus):
        if status.o365_connected:
            tenant = f" ({status.o365_tenant})" if status.o365_tenant else ""
            self.o365_dot.configure(fg=C["success"])
            self.o365_lbl.configure(text=f"O365: Connected{tenant}", fg=C["success"])
        else:
            self.o365_dot.configure(fg=C["error"])
            self.o365_lbl.configure(text=f"O365: {status.o365_message}", fg=C["error"])

        if status.ad_connected:
            self.ad_dot.configure(fg=C["success"])
            self.ad_lbl.configure(text=f"AD: {status.ad_message}", fg=C["success"])
            try: self._ad_warn.pack_forget()
            except Exception: pass
        else:
            self.ad_dot.configure(fg=C["error"])
            self.ad_lbl.configure(text=f"AD: {status.ad_message}", fg=C["error"])
            if self._form_shown:
                try:
                    children = self._content.winfo_children()
                    if children:
                        self._ad_warn.pack(fill="x", side="top", before=children[0])
                    else:
                        self._ad_warn.pack(fill="x", side="top")
                except tk.TclError:
                    # Fallback if 'before' fails or widget state is invalid
                    try: self._ad_warn.pack(fill="x", side="top")
                    except Exception: pass

        sync_text  = "AD Sync: ✅ Running" if status.ad_sync_running else "AD Sync: ⚠ Not Running"
        sync_color = C["success"] if status.ad_sync_running else C["warning"]
        self._sync_lbl.configure(text=sync_text, fg=sync_color)

        if status.last_checked:
            t = datetime.datetime.fromtimestamp(status.last_checked).strftime("%H:%M:%S")
            self._time_lbl.configure(text=f"Last checked: {t}")

        if status.o365_connected and not self._form_shown:
            if not self._is_authenticated:
                self._show_login()
            else:
                self._show_selection()

    def _show_login(self):
        self._form_shown = True
        if self._loading_lbl: self._loading_lbl.destroy(); self._loading_lbl = None
        self._login_form = LoginForm(self._content, self.ad, self.o365, self._on_login_success)
        self._login_form.pack(fill="both", expand=True)
        
    def _on_login_success(self):
        self._is_authenticated = True
        if self._login_form: self._login_form.destroy(); self._login_form = None
        self._settings_btn.pack(side="right", padx=4, pady=12)
        self._form_shown = False
        self._show_selection()
        self._refresh()

    def _show_selection(self):
        self._form_shown = True
        if self._loading_lbl: self._loading_lbl.destroy(); self._loading_lbl = None
        
        self._sel_frame = tk.Frame(self._content, bg=C["bg"])
        self._sel_frame.pack(expand=True)

        tk.Label(self._sel_frame, text="What would you like to do today?",
                 bg=C["bg"], fg=C["text"], font=F["title"], pady=40).pack()

        btn_frame = tk.Frame(self._sel_frame, bg=C["bg"])
        btn_frame.pack()

        def _big_btn(text, color, cmd):
            return tk.Button(btn_frame, text=text, font=("Segoe UI", 16, "bold"),
                           bg=C["surface"], fg=color, relief="flat", bd=0, 
                           width=20, height=10, command=cmd)

        _big_btn("🚀\n\nEmployee\nOn-boarding", C["accent"], self._launch_onboarding).pack(side="left", padx=20)
        _big_btn("👋\n\nEmployee\nOff-boarding", C["error"], self._launch_offboarding).pack(side="left", padx=20)
        _big_btn("✏️\n\nUpdate\nEmployee Profile", C["text_muted"], self._launch_profile_update).pack(side="left", padx=20)
        _big_btn("⚙️\n\nApplication\nSettings", C["text_dim"], self._launch_settings).pack(side="left", padx=20)

    def _launch_onboarding(self): self._sel_frame.destroy(); self._show_form()
    def _launch_offboarding(self): self._sel_frame.destroy(); self._show_offboarding()
    def _launch_profile_update(self): self._sel_frame.destroy(); self._show_profile_update()
    
    def _launch_settings(self):
        if not self._is_authenticated: return
        if hasattr(self, "_sel_frame") and self._sel_frame: self._sel_frame.destroy()
        if self._form: self._form.destroy()
        self._show_settings()

    def _show_form(self):
        self._form = UserForm(self._content, self.o365, self.ad, on_back=self._reset_to_home)
        self._form.pack(fill="both", expand=True)

    def _show_offboarding(self):
        self._form = OffboardingForm(self._content, self.o365, self.ad, on_back=self._reset_to_home)
        self._form.pack(fill="both", expand=True)

    def _show_profile_update(self):
        self._form = ProfileUpdateForm(self._content, self.o365, self.ad, on_back=self._reset_to_home)
        self._form.pack(fill="both", expand=True)

    def _show_settings(self):
        self._form = SettingsForm(self._content, on_back=self._reset_to_home)
        self._form.pack(fill="both", expand=True)

    def _reset_to_home(self):
        if self._form: self._form.destroy(); self._form = None
        if hasattr(self, "_sel_frame") and self._sel_frame: self._sel_frame.destroy(); self._sel_frame = None
        self._form_shown = False
        if self._is_authenticated: self._show_selection()
        else: self._show_login()
        threading.Thread(target=self.conn_mgr.check_all, daemon=True).start()
