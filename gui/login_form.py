"""
gui/login_form.py
Provides the sign-in screen and permission validation logic.
"""

import tkinter as tk
from tkinter import ttk
import threading

from gui.styles import C, F
from core.ad_service import ADService
from core.o365_service import O365Service

class LoginForm(tk.Frame):
    def __init__(self, parent: tk.Widget, ad_service: ADService, o365_service: O365Service, on_success: callable):
        super().__init__(parent, bg=C["bg"])
        self.ad = ad_service
        self.o365 = o365_service
        self.on_success = on_success

        self._build_ui()

    def _build_ui(self):
        # Center container
        self.container = tk.Frame(self, bg=C["bg"])
        self.container.place(relx=0.5, rely=0.45, anchor="center")

        # Header
        tk.Label(self.container, text="Sign In", 
                 bg=C["bg"], fg=C["text"], font=F["title_lg"]).pack(pady=(0, 5))
        
        tk.Label(self.container, text="Please authenticate to access the portal", 
                 bg=C["bg"], fg=C["text_muted"], font=F["body"]).pack(pady=(0, 25))

        # Card
        card = tk.Frame(self.container, bg=C["surface"], padx=40, pady=35, relief="flat")
        card.pack(fill="x")

        # Username
        tk.Label(card, text="AD Username", bg=C["surface"], fg=C["text"], font=F["body_sm"]).pack(anchor="w")
        self.user_var = tk.StringVar()
        self.user_entry = tk.Entry(card, textvariable=self.user_var, font=F["body"],
                                   bg=C["input_bg"], fg=C["text"], insertbackground=C["text"],
                                   relief="flat", highlightthickness=1, 
                                   highlightbackground=C["border"], highlightcolor=C["accent"])
        self.user_entry.pack(fill="x", pady=(4, 16), ipady=6)

        # Password
        tk.Label(card, text="Password", bg=C["surface"], fg=C["text"], font=F["body_sm"]).pack(anchor="w")
        self.pwd_var = tk.StringVar()
        self.pwd_entry = tk.Entry(card, textvariable=self.pwd_var, show="●", font=F["body"],
                                  bg=C["input_bg"], fg=C["text"], insertbackground=C["text"],
                                  relief="flat", highlightthickness=1, 
                                  highlightbackground=C["border"], highlightcolor=C["accent"])
        self.pwd_entry.pack(fill="x", pady=(4, 24), ipady=6)
        
        # Bind enter key
        self.pwd_entry.bind("<Return>", lambda e: self._do_login())
        self.user_entry.bind("<Return>", lambda e: self.pwd_entry.focus_set())

        # Status Label
        self.status_lbl = tk.Label(card, text="", bg=C["surface"], fg=C["error"], font=F["body_sm"])
        self.status_lbl.pack(fill="x", pady=(0, 10))

        # Login Button
        self.login_btn = tk.Button(card, text="Sign In", font=F["body"],
                                   bg=C["accent"], fg="#FFFFFF", activebackground="#3B82F6", activeforeground="#FFFFFF",
                                   relief="flat", cursor="hand2", command=self._do_login)
        self.login_btn.pack(fill="x", ipady=6)

        self.user_entry.focus_set()

    def _set_status(self, msg: str, is_error: bool = True):
        color = C["error"] if is_error else C["success"]
        # truncate long msgs
        if len(msg) > 80:
            msg = msg[:77] + "..."
        self.status_lbl.configure(text=msg, fg=color)

    def _set_loading(self, is_loading: bool):
        if is_loading:
            self.login_btn.configure(text="Authenticating...", state="disabled", bg=C["border"])
            self.user_entry.configure(state="disabled")
            self.pwd_entry.configure(state="disabled")
        else:
            self.login_btn.configure(text="Sign In", state="normal", bg=C["accent"])
            self.user_entry.configure(state="normal")
            self.pwd_entry.configure(state="normal")

    def _do_login(self):
        username = self.user_var.get().strip()
        password = self.pwd_var.get()

        if not username or not password:
            self._set_status("Please enter both username and password")
            return

        self._set_status("", is_error=False)
        self._set_loading(True)

        threading.Thread(target=self._auth_worker, args=(username, password), daemon=True).start()

    def _auth_worker(self, username, password):
        # 1. Check AD Credentials & Domain Admin membership
        ad_ok, ad_msg = self.ad.authenticate_and_check_permission(username, password)
        
        if not ad_ok:
            self.after(0, lambda: self._set_status(ad_msg))
            self.after(0, lambda: self._set_loading(False))
            return

        # 2. Check O365 Roles via Azure CLI Session
        o365_ok, o365_msg = self.o365.check_admin_roles()
        
        if not o365_ok:
            self.after(0, lambda: self._set_status(o365_msg))
            self.after(0, lambda: self._set_loading(False))
            return

        # Success!
        import config
        config.AD_ADMIN_USER = username
        config.AD_ADMIN_PASSWORD = password

        self.after(0, self.on_success)
