"""
gui/app.py
Main application window — connection status bar + onboarding form.
"""

import tkinter as tk
from tkinter import ttk
import threading
import datetime

<<<<<<< HEAD
from config import APP_TITLE, APP_VERSION
=======
from config import APP_TITLE, APP_VERSION, COMPANY_NAME
>>>>>>> 7ae16ae250dc44223ef24c615966296e203a90ad
from gui.styles import C, F, apply_theme
from gui.user_form import UserForm
from gui.offboarding_form import OffboardingForm
from gui.profile_update_form import ProfileUpdateForm
from gui.login_form import LoginForm
from gui.settings_form import SettingsForm
from core.o365_service import O365Service
from core.ad_service import ADService
from core.connection_manager import ConnectionManager, ConnectionStatus

<<<<<<< HEAD
<<<<<<< HEAD
=======
<<<<<<< Updated upstream
=======
>>>>>>> dev
# Path to company logo — set this to your logo file (PNG/GIF).
# Place the logo in the project root or adjust the path.
import os
import sys

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

LOGO_PATH = resource_path("logo.png")

>>>>>>> 7ae16ae250dc44223ef24c615966296e203a90ad

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
        self._login_form: tk.Widget = None
        self._loading_lbl: tk.Label = None
        self._form_shown = False
<<<<<<< HEAD
<<<<<<< HEAD
=======
<<<<<<< Updated upstream
        self._logo_img = None    # keep reference to prevent GC
=======
        self._logo_img = None    # prevent GC
>>>>>>> Stashed changes
>>>>>>> 7ae16ae250dc44223ef24c615966296e203a90ad
=======
        self._is_authenticated = False
        self._logo_img = None    # keep reference to prevent GC
        self._is_dark = False
        self._dep_status: Dict[str, bool] = {"az": True, "ad": True}
>>>>>>> dev

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
<<<<<<< HEAD
<<<<<<< HEAD
        bar = tk.Frame(self.root, bg=C["surface"], height=60)
        bar.pack(fill="x", side="top")
        bar.pack_propagate(False)

        tk.Label(bar, text="🏢",
                 bg=C["surface"], font=("Segoe UI Emoji", 22)
                 ).pack(side="left", padx=(18, 4), pady=10)
        tk.Label(bar, text="PETRUS TECHNOLOGIES",
=======
        bar = tk.Frame(self.root, bg=C["surface"], height=64)
        bar.pack(fill="x", side="top")
        bar.pack_propagate(False)
=======
        self._topbar = tk.Frame(self.root, bg=C["surface"], height=64)
        self._topbar.pack(fill="x", side="top")
        self._topbar.pack_propagate(False)
        bar = self._topbar
>>>>>>> dev

        # ── Company Logo ──────────────────────────────────────────────────
        if os.path.isfile(LOGO_PATH):
            try:
                from PIL import Image, ImageTk
                img = Image.open(LOGO_PATH).resize((44, 44), Image.LANCZOS)
                self._logo_img = ImageTk.PhotoImage(img)
                tk.Label(bar, image=self._logo_img, bg=C["surface"]
                         ).pack(side="left", padx=(18, 8), pady=8)
            except ImportError:
                # Pillow not installed — try native PhotoImage (GIF/PGM only)
                try:
                    self._logo_img = tk.PhotoImage(file=LOGO_PATH)
                    # Subsample if too large
                    w, _ = self._logo_img.width(), self._logo_img.height()
                    if w > 48:
                        factor = max(1, w // 44)
                        self._logo_img = self._logo_img.subsample(factor, factor)
                    tk.Label(bar, image=self._logo_img, bg=C["surface"]
                             ).pack(side="left", padx=(18, 8), pady=8)
                except Exception:
                    tk.Label(bar, text="🏢",
                             bg=C["surface"], font=("Segoe UI Emoji", 22)
                             ).pack(side="left", padx=(18, 4), pady=10)
        else:
            tk.Label(bar, text="🏢",
                     bg=C["surface"], font=("Segoe UI Emoji", 22)
                     ).pack(side="left", padx=(18, 4), pady=10)

        # ── Company Name (from config.py COMPANY_NAME) ────────────────────
        tk.Label(bar, text=COMPANY_NAME.upper(),
>>>>>>> 7ae16ae250dc44223ef24c615966296e203a90ad
                 bg=C["surface"], fg=C["accent"],
                 font=("Segoe UI", 14, "bold")
                 ).pack(side="left", pady=10)
        tk.Label(bar, text="  —  Employee Onboarding Portal",
                 bg=C["surface"], fg=C["text_muted"], font=F["body"]
                 ).pack(side="left", pady=10)

        self._theme_btn = ttk.Button(bar, text="🌙  Dark Mode",
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
        # Hidden initially; shown after login in _on_login_success
        # self._settings_btn.pack(side="right", padx=4, pady=12)

    def _logout(self):
        from tkinter import messagebox
        from core.credential_manager import cred_manager
        if messagebox.askyesno("Logout", "Are you sure you want to log out of M365?\n\nThe application will close and you will need to restart to log in again.", parent=self.root):
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

    # ── Theme Toggle ──────────────────────────────────────────────────────────

    def _toggle_theme(self):
        self._is_dark = not self._is_dark
        apply_theme(self.root, is_dark=self._is_dark)
        
        # Update text of the button
        btn_text = "☀️  Light Mode" if self._is_dark else "🌙  Dark Mode"
        self._theme_btn.configure(text=btn_text)
        
        # Recursively update all non-ttk widgets (tk.Frame, tk.Label, etc.)
        self._update_widget_themes(self.root)
        
        # Special handling for elements that need specific colors from C
        self._topbar.configure(bg=C["surface"])
        self._statusbar.configure(bg=C["surface2"])
        
        # Refresh current form
        if self._form:
            if isinstance(self._form, OffboardingForm):
                self._form.destroy(); self._show_offboarding()
            elif isinstance(self._form, ProfileUpdateForm):
                self._form.destroy(); self._show_profile_update()
            elif isinstance(self._form, SettingsForm):
                self._form.destroy(); self._show_settings()
            else:
                self._form.destroy(); self._show_form()
        elif hasattr(self, "_sel_frame"):
            self._sel_frame.destroy()
            self._show_selection()

    def _update_widget_themes(self, parent):
        """Recursively update standard tk widgets with current theme colors."""
        for child in parent.winfo_children():
            wtype = child.winfo_class()
            
            # Skip ttk widgets as they are handled by apply_theme
            if wtype.startswith("T"): 
                self._update_widget_themes(child)
                continue
                
            try:
                # Update standard widgets
                if wtype == "Frame":
                    curr_bg = child.cget("bg").upper()
                    if curr_bg in ["#FFFFFF", "#1E293B"]: # Surface colors
                        child.configure(bg=C["surface"])
                    elif curr_bg in ["#E8EDF2", "#334155"]: # Surface2 colors
                        child.configure(bg=C["surface2"])
                    elif curr_bg not in ["#DC2626", "#EF4444", "#D97706", "#F59E0B"]:
                        child.configure(bg=C["bg"])
                        
                elif wtype == "Label":
                    curr_bg = child.cget("bg").upper()
                    if curr_bg in ["#FFFFFF", "#1E293B"]:
                        child.configure(bg=C["surface"], fg=C["text"])
                    elif curr_bg in ["#E8EDF2", "#334155"]:
                        child.configure(bg=C["surface2"], fg=C["text_muted"])
                    elif curr_bg not in ["#DC2626", "#EF4444", "#D97706", "#F59E0B"]:
                        child.configure(bg=C["bg"], fg=C["text"])
                
                elif wtype == "Text":
                    child.configure(bg="#1a1a1a" if self._is_dark else "#1a1a1a", # Keep log dark
                                    fg="#d1d1d1")
                
                elif wtype == "Button": # For the selection cards
                    child.configure(bg=C["surface"], activebackground=C["surface2"])

                self._update_widget_themes(child)
            except Exception:
                pass

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
            self._ad_warn.pack_forget()
        else:
            self.ad_dot.configure(fg=C["error"])
            self.ad_lbl.configure(text=f"AD: {status.ad_message}", fg=C["error"])
            if self._form_shown:
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
        if status.o365_connected and not self._form_shown:
            if not self._is_authenticated:
                self._show_login()
            else:
                self._show_selection()
        elif not status.o365_connected and not self._form_shown:
            self._loading_lbl.configure(
                text="⚠  Cannot connect to O365.\n\n"
                     "• Ensure Azure CLI is logged in (run: az login).\n"
                     "• Click  ⟳ Refresh Connections  to retry.\n\n"
                     f"O365:  {status.o365_message}",
                fg=C["warning"],
            )

    def _show_login(self):
        self._form_shown = True
        if self._loading_lbl:
            self._loading_lbl.destroy()
            self._loading_lbl = None
        
        self._login_form = LoginForm(self._content, self.ad, self.o365, self._on_login_success)
        self._login_form.pack(fill="both", expand=True)
        
    def _on_login_success(self):
        self._is_authenticated = True
        if self._login_form:
            self._login_form.destroy()
            self._login_form = None
        
        # Show settings button now that we are authenticated
        self._settings_btn.pack(side="right", padx=4, pady=12)
        
        self._form_shown = False
        self._show_selection()
        self._refresh()

    def _show_selection(self):
        self._form_shown = True
        if self._loading_lbl:
            self._loading_lbl.destroy()
            self._loading_lbl = None
        
        self._sel_frame = tk.Frame(self._content, bg=C["bg"])
        self._sel_frame.pack(expand=True)

        tk.Label(self._sel_frame, text="What would you like to do today?",
                 bg=C["bg"], fg=C["text"], font=F["title"],
                 pady=40).pack()

        btn_frame = tk.Frame(self._sel_frame, bg=C["bg"])
        btn_frame.pack()

        # Onboarding Button
        on_btn = tk.Button(btn_frame, text="🚀\n\nEmployee\nOn-boarding",
                           font=("Segoe UI", 16, "bold"),
                           bg=C["surface"], fg=C["accent"],
                           activebackground=C["surface2"], activeforeground=C["accent"],
                           relief="flat", bd=0, width=20, height=10,
                           command=self._launch_onboarding)
        on_btn.pack(side="left", padx=20)

        # Off-boarding Button
        off_btn = tk.Button(btn_frame, text="👋\n\nEmployee\nOff-boarding",
                            font=("Segoe UI", 16, "bold"),
                            bg=C["surface"], fg=C["error"],
                            activebackground=C["surface2"], activeforeground=C["error"],
                            relief="flat", bd=0, width=20, height=10,
                            command=self._launch_offboarding)
        off_btn.pack(side="left", padx=20)

        # Profile Update Button
        prof_btn = tk.Button(btn_frame, text="✏️\n\nUpdate\nEmployee Profile",
                             font=("Segoe UI", 16, "bold"),
                             bg=C["surface"], fg=C["text_muted"],
                             activebackground=C["surface2"], activeforeground=C["text"],
                             relief="flat", bd=0, width=20, height=10,
                             command=self._launch_profile_update)
        prof_btn.pack(side="left", padx=20)

        # Settings Button
        sett_btn = tk.Button(btn_frame, text="⚙️\n\nApplication\nSettings",
                             font=("Segoe UI", 16, "bold"),
                             bg=C["surface"], fg=C["text_dim"],
                             activebackground=C["surface2"], activeforeground=C["text"],
                             relief="flat", bd=0, width=20, height=10,
                             command=self._launch_settings)
        sett_btn.pack(side="left", padx=20)

    def _launch_onboarding(self):
        self._sel_frame.destroy()
        self._show_form()

    def _launch_offboarding(self):
        self._sel_frame.destroy()
        self._show_offboarding()

    def _launch_profile_update(self):
        self._sel_frame.destroy()
        self._show_profile_update()

    def _launch_settings(self):
        # Basic security check
        if not self._is_authenticated:
            from tkinter import messagebox
            messagebox.showwarning("Access Denied", "Please log in to access settings.")
            return

        if hasattr(self, "_sel_frame") and self._sel_frame:
            self._sel_frame.destroy()
        if self._form:
            self._form.destroy()
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
        if self._form:
            self._form.destroy()
            self._form = None
        
        if hasattr(self, "_sel_frame") and self._sel_frame:
            try:
                self._sel_frame.destroy()
            except Exception: pass
            self._sel_frame = None

        self._form_shown = False
        
        # Security check: only show selection if authenticated
        if self._is_authenticated:
            self._show_selection()
        else:
            self._show_login()
        
        threading.Thread(target=self.conn_mgr.check_all, daemon=True).start()
