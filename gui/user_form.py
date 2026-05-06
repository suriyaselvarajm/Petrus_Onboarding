"""
gui/user_form.py
Main onboarding form — all fields, validation, and user creation logic.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import re
import datetime
import secrets
import string
from typing import Optional, List, Tuple, Dict, Any

from tkcalendar import DateEntry

from config import (
    COMPANY_NAME, EMAIL_DOMAIN, AD_PETRUS_USERS_OU,
    DEFAULT_CITY, DEFAULT_STATE, DEFAULT_ZIP,
    DEFAULT_COUNTRY, DEFAULT_STREET, DEFAULT_OFFICE,
    LICENSE_OPTIONS, EMPLOYEE_TYPES,
    LICENSE_SKU_MAP, MAILBOX_WAIT_SECONDS,
    DEFAULT_EMAIL_SENDER, DEFAULT_EMAIL_CC,
)
from core.mail_service import MailService
from core.credential_manager import save_password, get_password
from gui.styles import C, F


# ═══════════════════════════════════════════════════════════════════════════════
#  Helpers
# ═══════════════════════════════════════════════════════════════════════════════

class _ScrollableFrame(tk.Frame):
    """Canvas-backed scrollable container."""
    def __init__(self, parent: tk.Widget, **kw):
        super().__init__(parent, bg=C["bg"], **kw)
        canvas = tk.Canvas(self, bg=C["bg"], highlightthickness=0)
        vsb    = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        self.inner = tk.Frame(canvas, bg=C["bg"])
        self.inner.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.create_window((0, 0), window=self.inner, anchor="nw")
        canvas.configure(yscrollcommand=vsb.set)
        canvas.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        # Mouse-wheel scrolling — only scroll the canvas when the
        # cursor is actually over the canvas, NOT over a Combobox,
        # Listbox, or other scrollable widget.  This prevents the
        # bug where scrolling the page changes Combobox / OU values.
        self._canvas = canvas
        def _on_mousewheel(event):
            # Get the widget directly under the cursor
            try:
                if not canvas.winfo_exists(): return
                w = event.widget.winfo_containing(event.x_root, event.y_root)
            except Exception:
                w = event.widget
            
            # Skip scrolling if cursor is over a Combobox, Listbox, or Spinbox
            widget_class = getattr(w, "winfo_class", lambda: "")() if w else ""
            if widget_class in ("TCombobox", "Listbox", "TSpinbox", "Spinbox"):
                return   # let the widget handle its own scroll
                
            try:
                if canvas.winfo_exists():
                    canvas.yview_scroll(-1 * (event.delta // 120), "units")
            except tk.TclError:
                pass # Widget was destroyed during event processing

        canvas.bind_all("<MouseWheel>", _on_mousewheel)


def _section(parent: tk.Widget, title: str, icon: str = "") -> tk.Frame:
    """Render a section header bar and return a card Frame beneath it."""
    hdr = tk.Frame(parent, bg=C["surface2"])
    hdr.pack(fill="x", pady=(18, 0))
    # Accent side-bar
    tk.Frame(hdr, bg=C["accent"], width=4).pack(side="left", fill="y")
    lbl_text = f"  {icon}  {title}".strip() if icon else f"  {title}"
    tk.Label(hdr, text=lbl_text,
             bg=C["surface2"], fg=C["text"],
             font=F["subtitle"], pady=8).pack(side="left", padx=4)

    card = tk.Frame(parent, bg=C["surface"])
    card.pack(fill="x", pady=(0, 4))
    return card


def _lbl(parent, text, required=False, bg=None):
    bg = bg or C["surface"]
    suffix = "  *" if required else ""
    tk.Label(parent, text=f"{text}{suffix}",
             bg=bg, fg=C["text_muted"], font=F["label"], anchor="w").grid(
        **_lbl.kw)               # caller sets _lbl.kw before calling


def _entry(parent, var, row, col=0, span=1, readonly=False, show="",
           padx=(12, 6)):
    state = "readonly" if readonly else "normal"
    e = ttk.Entry(parent, textvariable=var, font=F["body"], show=show, state=state)
    e.grid(row=row, column=col, columnspan=span, sticky="ew",
           padx=padx, pady=(0, 6))
    return e


def _combo(parent, var, values, row, col=0, span=1, padx=(12, 6)):
    cb = ttk.Combobox(parent, textvariable=var, values=values,
                      state="readonly", font=F["body"])
    cb.grid(row=row, column=col, columnspan=span, sticky="ew",
            padx=padx, pady=(0, 6))
    return cb


def _date_entry(parent, row, col=0, padx=(12, 6)):
    de = DateEntry(parent, font=F["body"], date_pattern="dd/mm/yyyy",
                   background=C["accent"], foreground="white",
                   headersbackground=C["accent_dim"],
                   normalbackground=C["surface2"], normalforeground=C["text"],
                   weekendbackground=C["surface2"], weekendforeground=C["text"],
                   othermonthforeground=C["text_dim"],
                   borderwidth=1)
    de.grid(row=row, column=col, sticky="w", padx=padx, pady=(0, 6))
    return de


def _grid_lbl(parent, text, row, col=0, span=1, required=False, padx=(12, 6)):
    suffix = "  *" if required else ""
    tk.Label(parent, text=f"{text}{suffix}",
             bg=C["surface"], fg=C["text_muted"],
             font=F["label"], anchor="w").grid(
        row=row, column=col, columnspan=span, sticky="w",
        padx=padx, pady=(8, 2))


# ═══════════════════════════════════════════════════════════════════════════════
#  Main Form
# ═══════════════════════════════════════════════════════════════════════════════

class UserForm(tk.Frame):
    """
    Full onboarding form.
    Left column  → Personal, Profile, Azure/Company info.
    Right column → License, Manager, O365 Groups, AD config, MFA.
    """

    def __init__(self, parent, o365_service, ad_service, on_back=None):
        super().__init__(parent, bg=C["bg"])
        self.o365 = o365_service
        self.ad   = ad_service
        self.mail = MailService()
        self._on_back = on_back

        # Remote data caches
        self._all_groups:     List[Tuple[str, str, str]] = []  # (id, name, type)
        self._all_ad_ous:     List[Tuple[str, str]] = []   # (name, dn)
        self._sub_ous:        List[Tuple[str, str]] = []   # (name, dn) child OUs of selected OU
        self._all_ad_groups:  List[Tuple[str, str]] = []   # (name, dn)
        self._all_managers:   List[Tuple[str, str, str]] = []  # (id, name, upn)
        self._license_skus:   dict = {}   # display_name -> sku_id
        self._license_counts: dict = {}   # display_name -> (available, total)
        self._manager_id:     Optional[str] = None
        self._manager_upn:    Optional[str] = None
        self._email_job:      Optional[str] = None   # after() job id
        self._check_job:      Optional[str] = None   # for debouncing duplicate checks

        self._build_ui()
        self.after(400, self._load_remote_data)

    # ────────────────────────────────────────────────────────────────────────────────
    #  Layout
    # ────────────────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        # ── Header / Back Button ──────────────────────────────────────────
        header = tk.Frame(self, bg=C["bg"])
        header.pack(fill="x", padx=20, pady=(20, 0))

        if self._on_back:
            ttk.Button(header, text="←  Back to Home",
                       style="Secondary.TButton",
                       command=self._on_back).pack(side="left")

        tk.Label(header, text="New Employee On-boarding",
                 bg=C["bg"], fg=C["text"], font=F["title"]).pack(side="left", padx=20)

        # ── Scrollable Content ──────────────────────────────────────────
        scroll = _ScrollableFrame(self)
        scroll.pack(fill="both", expand=True, padx=20, pady=20)
        inner = scroll.inner

        # Two equal columns
        left  = tk.Frame(inner, bg=C["bg"])
        right = tk.Frame(inner, bg=C["bg"])
        left.grid (row=0, column=0, sticky="nsew", padx=(12, 6),  pady=8)
        right.grid(row=0, column=1, sticky="nsew", padx=(6,  12), pady=8)
        inner.columnconfigure(0, weight=1, uniform="half")
        inner.columnconfigure(1, weight=1, uniform="half")

        # Build sections
        self._build_personal(left)
        self._build_profile(left)
        self._build_azure(left)

        self._build_license(right)
        self._build_manager(right)
        self._build_o365_groups(right)
        self._build_ad_config(right)
        self._build_security(right)

        # Bottom action bar spans both columns
        self._build_action_bar(inner)

    # ──────────────────────────────────────────────────────────────────────────
    #  Section: Personal Information
    # ──────────────────────────────────────────────────────────────────────────

    def _build_personal(self, parent):
        card = _section(parent, "Personal Information", "👤")
        card.columnconfigure(0, weight=1)
        card.columnconfigure(1, weight=1)

        # First / Last name
        _grid_lbl(card, "First Name", 0, 0, required=True)
        _grid_lbl(card, "Last Name",  0, 1, required=True, padx=(6, 12))
        self.v_first = tk.StringVar()
        self.v_last  = tk.StringVar()
        self._e_first = _entry(card, self.v_first, 1, 0, padx=(12, 6))
        self._e_last  = _entry(card, self.v_last,  1, 1, padx=(6, 12))
        self.v_first.trace_add("write", self._on_name_change)
        self.v_last.trace_add ("write", self._on_name_change)

        # Email
        _grid_lbl(card, "Email Address", 2, 0, 2, required=True)
        self.v_email = tk.StringVar()
        self.v_email.trace_add("write", self._on_name_change)
        self.v_email.trace_add("write", self._trigger_duplicate_check)
        self.v_email.trace_add("write", self._on_email_change)
        _entry(card, self.v_email, 3, 0, span=2, padx=(12, 12))

        self._email_hint = tk.Label(card, text="",
                                    bg=C["surface"], fg=C["text_muted"],
                                    font=F["body_sm"], anchor="w")
        self._email_hint.grid(row=4, column=0, columnspan=2,
                              sticky="w", padx=14, pady=(0, 6))

        # Password + force change
        _grid_lbl(card, "Password", 5, 0, required=True)
        pwd_f = tk.Frame(card, bg=C["surface"])
        pwd_f.grid(row=6, column=0, sticky="ew", padx=(12, 6))
        
        self.v_pwd = tk.StringVar(value=self._generate_password())
        self._e_pwd = ttk.Entry(pwd_f, textvariable=self.v_pwd, font=F["body"])
        self._e_pwd.pack(side="left", fill="x", expand=True)
        
        ttk.Button(pwd_f, text="🎲", width=3,
                   style="Secondary.TButton",
                   command=lambda: self.v_pwd.set(self._generate_password())).pack(side="right", padx=(5, 0))

        self.v_force_pwd = tk.BooleanVar(value=True)
        tk.Checkbutton(card, text=" Require password change on 1st sign-in",
                       variable=self.v_force_pwd,
                       bg=C["surface"], fg=C["text"],
                       activebackground=C["surface"],
                       selectcolor=C["accent_dim"],
                       font=F["body_sm"]
                       ).grid(row=6, column=1, sticky="w",
                                padx=(6, 12), pady=(0, 6))

        # Joining date
        _grid_lbl(card, "Joining Date", 8, 0, required=True)
        self._joining_date = _date_entry(card, 9, 0)

    # ──────────────────────────────────────────────────────────────────────────
    #  Section: Profile Information
    # ──────────────────────────────────────────────────────────────────────────

    def _build_profile(self, parent):
        card = _section(parent, "Profile Information", "📋")
        card.columnconfigure(0, weight=1)
        card.columnconfigure(1, weight=1)

        # Helper to add a label+entry pair
        def field(label, attr, row, col, default="", required=False,
                  padx_lbl=(12,6), padx_ent=(12,6), span=1):
            _grid_lbl(card, label, row, col, span, required=required, padx=padx_lbl)
            var = tk.StringVar(value=default)
            setattr(self, attr, var)
            ttk.Entry(card, textvariable=var, font=F["body"]).grid(
                row=row+1, column=col, columnspan=span, sticky="ew",
                padx=padx_ent, pady=(0, 6))

        field("Job Title",        "v_job_title", 0, 0, padx_lbl=(12,6), padx_ent=(12,6))
        field("Department",       "v_dept",      0, 1, padx_lbl=(6,12), padx_ent=(6,12))
        field("Office Location",  "v_office",    2, 0, DEFAULT_OFFICE,
              padx_lbl=(12,6), padx_ent=(12,6))
        field("Mobile Phone",     "v_mobile",    2, 1, required=True,
              padx_lbl=(6,12), padx_ent=(6,12))

        # Street address spans both columns
        _grid_lbl(card, "Street Address", 4, 0, span=2, padx=(12,12))
        self.v_street = tk.StringVar(value=DEFAULT_STREET)
        ttk.Entry(card, textvariable=self.v_street, font=F["body"]).grid(
            row=5, column=0, columnspan=2, sticky="ew", padx=(12,12), pady=(0,6))

        field("City",             "v_city",   6, 0, DEFAULT_CITY,
              padx_lbl=(12,6), padx_ent=(12,6))
        field("State / Province", "v_state",  6, 1, DEFAULT_STATE,
              padx_lbl=(6,12), padx_ent=(6,12))
        field("ZIP / Postal Code","v_zip",    8, 0, DEFAULT_ZIP,
              padx_lbl=(12,6), padx_ent=(12,6))
        field("Country",          "v_country",8, 1, DEFAULT_COUNTRY,
              padx_lbl=(6,12), padx_ent=(6,12))

        tk.Frame(card, bg=C["surface"], height=8).grid(row=10, column=0, columnspan=2)

    # ────────────────────────────────────────────────────────────────────────────────
    #  Section: Azure & Company Properties
    # ────────────────────────────────────────────────────────────────────────────────

    def _build_azure(self, parent):
        card = _section(parent, "Azure & Company Properties", "☁")
        card.columnconfigure(0, weight=1)
        card.columnconfigure(1, weight=1)

        # Company name (readonly)
        _grid_lbl(card, "Company Name", 0, 0, 2)
        self.v_company = tk.StringVar(value=COMPANY_NAME)
        _entry(card, self.v_company, 1, 0, 2, readonly=True, padx=(12, 12))

        # Employee ID + Type
        _grid_lbl(card, "Employee ID", 2, 0)
        _grid_lbl(card, "Employee Type", 2, 1, padx=(6, 12))
        self.v_emp_id   = tk.StringVar()
        self.v_emp_id.trace_add("write", self._trigger_duplicate_check)
        self.v_emp_type = tk.StringVar(value=EMPLOYEE_TYPES[0])
        _entry (card, self.v_emp_id,   3, 0, padx=(12, 6))
        _combo (card, self.v_emp_type, EMPLOYEE_TYPES, 3, 1, padx=(6, 12))
        self.v_emp_id.trace_add("write", self._on_emp_id_change)

        # Hire date
        _grid_lbl(card, "Employee Hire Date", 4, 0)
        self._hire_date = _date_entry(card, 5, 0)

        # ── Alias / Proxy Addresses ──────────────────────────────────────────
        tk.Label(card, text="  ─── Alias & Proxy Addresses ───",
                 bg=C["surface"], fg=C["text_dim"],
                 font=F["body_sm"]).grid(row=6, column=0, columnspan=2,
                                         sticky="w", padx=12, pady=(14, 4))

        _grid_lbl(card, "Primary SMTP  (auto-generated)", 7, 0, 2)
        self.v_primary_smtp = tk.StringVar(value=f"SMTP:@{EMAIL_DOMAIN}")
        _entry(card, self.v_primary_smtp, 8, 0, 2, readonly=True, padx=(12, 12))

        _grid_lbl(card, "AD Proxy — Employee ID Alias  (auto from Employee ID)", 9, 0, 2)
        self.v_alias = tk.StringVar(value=f"smtp:@{EMAIL_DOMAIN}")
        _entry(card, self.v_alias, 10, 0, 2, readonly=True, padx=(12, 12))

        _grid_lbl(card, "O365 Alias  (EmployeeID@petrustechnologies.com)", 11, 0, 2)
        self.v_o365_alias = tk.StringVar(value=f"@{EMAIL_DOMAIN}")
        _entry(card, self.v_o365_alias, 12, 0, 2, readonly=True, padx=(12, 12))

        tk.Frame(card, bg=C["surface"], height=8).grid(row=13, column=0, columnspan=2)

    # ────────────────────────────────────────────────────────────────────────────────
    #  Section: License
    # ────────────────────────────────────────────────────────────────────────────────

    def _build_license(self, parent):
        card = _section(parent, "License Assignment", "🗝")
        card.columnconfigure(0, weight=1)

        _grid_lbl(card, "License Type", 0, required=True)
        self.v_license = tk.StringVar(value=LICENSE_OPTIONS[0])
        _combo(card, self.v_license, LICENSE_OPTIONS, 1, padx=(12, 12))
        self.v_license.trace_add("write", self._on_license_change)

        self._license_hint = tk.Label(card, text="Fetching available SKUs…",
                                      bg=C["surface"], fg=C["text_muted"],
                                      font=F["body_sm"], anchor="w")
        self._license_hint.grid(row=2, column=0, sticky="w", padx=14, pady=(0, 10))

    # ────────────────────────────────────────────────────────────────────────────────
    #  Section: Reporting Manager
    # ────────────────────────────────────────────────────────────────────────────────

    def _build_manager(self, parent):
        card = _section(parent, "Reporting Manager", "👔")
        card.columnconfigure(0, weight=1)

        _grid_lbl(card, "Search Manager (type to filter)", 0)
        self.v_mgr_search = tk.StringVar()
        mgr_search = ttk.Entry(card, textvariable=self.v_mgr_search, font=F["body"])
        mgr_search.grid(row=1, column=0, sticky="ew", padx=(12, 12), pady=(0, 4))
        mgr_search.bind("<KeyRelease>", self._filter_managers)

        self._mgr_combo = ttk.Combobox(card, state="readonly", font=F["body"])
        self._mgr_combo.grid(row=2, column=0, sticky="ew", padx=(12, 12), pady=(0, 4))
        self._mgr_combo.bind("<<ComboboxSelected>>", self._on_manager_select)

        self._mgr_lbl = tk.Label(card, text="No manager selected",
                                  bg=C["surface"], fg=C["text_dim"], font=F["body_sm"])
        self._mgr_lbl.grid(row=3, column=0, sticky="w", padx=14, pady=(0, 10))

    # ────────────────────────────────────────────────────────────────────────────────
    #  Section: O365 Groups
    # ────────────────────────────────────────────────────────────────────────────────

    def _build_o365_groups(self, parent):
        card = _section(parent, "O365 Groups", "👥")
        card.columnconfigure(0, weight=1)

        # ── Filter bar (search + type filter) ──────────────────────────────
        ctrl = tk.Frame(card, bg=C["surface"])
        ctrl.grid(row=0, column=0, sticky="ew", padx=12, pady=(8, 4))
        ctrl.columnconfigure(0, weight=1)

        self.v_grp_search = tk.StringVar()
        ttk.Entry(ctrl, textvariable=self.v_grp_search, font=F["body"]
                  ).grid(row=0, column=0, sticky="ew")
        self.v_grp_search.trace_add("write", self._filter_groups)

        self.v_grp_type = tk.StringVar(value="All")
        ttk.Combobox(ctrl, textvariable=self.v_grp_type,
                     values=["All", "M365 Group", "Distribution List",
                             "Security Group", "Mail-Sec Group"],
                     state="readonly", width=18, font=F["body"]
                     ).grid(row=0, column=1, padx=(4, 0))
        self.v_grp_type.trace_add("write", self._filter_groups)

        ttk.Button(ctrl, text="↻ Refresh", style="Secondary.TButton",
                   command=lambda: threading.Thread(
                       target=self._fetch_groups, daemon=True).start()
                   ).grid(row=0, column=2, padx=(6, 0))

        # Listbox
        lb_frame = tk.Frame(card, bg=C["surface"])
        lb_frame.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 4))
        lb_frame.columnconfigure(0, weight=1)

        self._grp_lb = tk.Listbox(lb_frame, selectmode="multiple", height=8,
                                   bg=C["input_bg"], fg=C["text"],
                                   selectbackground=C["accent"],
                                   selectforeground="white",
                                   font=F["body"], relief="flat",
                                   activestyle="none", bd=0, exportselection=False)
        grp_vsb = ttk.Scrollbar(lb_frame, command=self._grp_lb.yview)
        self._grp_lb.configure(yscrollcommand=grp_vsb.set)
        self._grp_lb.grid(row=0, column=0, sticky="ew")
        # Selected groups display
        self._o365_sel_frame = tk.Frame(card, bg=C["surface"])
        self._o365_sel_frame.grid(row=3, column=0, sticky="ew", padx=12, pady=(0, 10))
        self._grp_lb.bind("<<ListboxSelect>>", self._update_o365_sel_display)

        self._grp_hint = tk.Label(card, text="Loading groups…",
                                   bg=C["surface"], fg=C["text_muted"],
                                   font=F["body_sm"], anchor="w")
        self._grp_hint.grid(row=2, column=0, sticky="w", padx=14, pady=(0, 10))

    # ────────────────────────────────────────────────────────────────────────────────
    #  Section: Active Directory Configuration
    # ────────────────────────────────────────────────────────────────────────────────

    def _build_ad_config(self, parent):
        card = _section(parent, "Active Directory Configuration", "🖥")
        card.columnconfigure(0, weight=1)

        # ── Hierarchical OU Selection ──────────────────────────────────────────
        _grid_lbl(card, "AD Location (Parent OU)  *", 0)
        self.v_location = tk.StringVar(value="Loading Locations…")
        self._ou_cb = ttk.Combobox(card, textvariable=self.v_location,
                                    state="readonly", font=F["body"])
        self._ou_cb.grid(row=1, column=0, sticky="ew", padx=(12, 12), pady=(0, 6))
        self._ou_cb.bind("<<ComboboxSelected>>", self._on_location_selected)

        _grid_lbl(card, "AD Department / Sub-OU  *", 2)
        self.v_sub_ou = tk.StringVar(value="Select location first")
        self._sub_ou_cb = ttk.Combobox(card, textvariable=self.v_sub_ou,
                                        state="readonly", font=F["body"])
        self._sub_ou_cb.grid(row=3, column=0, sticky="ew", padx=(12, 12), pady=(0, 6))
        self._sub_ou_cb.bind("<<ComboboxSelected>>", self._on_sub_ou_selected)

        # AD Groups
        _grid_lbl(card, "AD Groups  (Ctrl+click to multi-select)", 6)
        lb_frame = tk.Frame(card, bg=C["surface"])
        lb_frame.grid(row=7, column=0, sticky="ew", padx=12, pady=(0, 4))
        lb_frame.columnconfigure(0, weight=1)

        self._ad_grp_lb = tk.Listbox(lb_frame, selectmode="multiple", height=5,
                                      bg=C["input_bg"], fg=C["text"],
                                      selectbackground=C["accent"],
                                      selectforeground="white",
                                      font=F["body"], relief="flat",
                                      activestyle="none", bd=0, exportselection=False)
        ad_vsb = ttk.Scrollbar(lb_frame, command=self._ad_grp_lb.yview)
        self._ad_grp_lb.configure(yscrollcommand=ad_vsb.set)
        self._ad_grp_lb.grid(row=0, column=0, sticky="ew")
        ad_vsb.grid(row=0, column=1, sticky="ns")
        
        # Selected AD groups display
        self._ad_sel_frame = tk.Frame(card, bg=C["surface"])
        self._ad_sel_frame.grid(row=8, column=0, sticky="ew", padx=12, pady=(0, 10))
        self._ad_grp_lb.bind("<<ListboxSelect>>", self._update_ad_sel_display)

        tk.Frame(card, bg=C["surface"], height=8).grid(row=9, column=0)

    # ────────────────────────────────────────────────────────────────────────────────
    #  Section: Security / MFA
    # ────────────────────────────────────────────────────────────────────────────────

    def _build_security(self, parent):
        card = _section(parent, "Security & MFA", "🔐")

        self.v_mfa = tk.BooleanVar(value=True)
        tk.Checkbutton(card, text=" Enable Multi-Factor Authentication (MFA)",
                       variable=self.v_mfa,
                       bg=C["surface"], fg=C["text"],
                       activebackground=C["surface"],
                       selectcolor=C["accent_dim"],
                       font=F["body"]).pack(anchor="w", padx=16, pady=(12, 4))
        
        # Welcome Email Section
        tk.Frame(card, bg=C["surface2"], height=1).pack(fill="x", pady=10)
        self.v_send_email = tk.BooleanVar(value=True)
        tk.Checkbutton(card, text=" Send Welcome Email to User",
                       variable=self.v_send_email,
                       bg=C["surface"], fg=C["text"],
                       activebackground=C["accent"],
                       font=F["subtitle_sm"]).pack(anchor="w", padx=16, pady=5)
        
        mail_frame = tk.Frame(card, bg=C["surface"])
        mail_frame.pack(fill="x", padx=16, pady=5)
        
        _grid_lbl(mail_frame, "Sender Email", 0, 0)
        self.v_mail_sender = tk.StringVar(value=DEFAULT_EMAIL_SENDER)
        _entry(mail_frame, self.v_mail_sender, 1, 0, padx=(0, 6))
        
        _grid_lbl(mail_frame, "Sender Password", 0, 1)
        self.v_mail_pwd = tk.StringVar()
        
        pwd_sub = tk.Frame(mail_frame, bg=C["surface"])
        pwd_sub.grid(row=1, column=1, sticky="ew", padx=(6, 0))
        
        self._mail_pwd_entry = ttk.Entry(pwd_sub, textvariable=self.v_mail_pwd, font=F["body"], show="●")
        self._mail_pwd_entry.pack(side="left", fill="x", expand=True)
        
        self._save_pwd_btn = ttk.Button(pwd_sub, text="💾", width=3,
                                        style="Secondary.TButton",
                                        command=self._save_mail_password)
        self._save_pwd_btn.pack(side="right", padx=(5, 0))
        
        _grid_lbl(mail_frame, "Receiver Email (Personal) *", 2, 0)
        self.v_mail_receiver = tk.StringVar()
        _entry(mail_frame, self.v_mail_receiver, 3, 0, padx=(0, 6))

        _grid_lbl(mail_frame, "CC Email", 2, 1)
        self.v_mail_cc = tk.StringVar(value=DEFAULT_EMAIL_CC)
        _entry(mail_frame, self.v_mail_cc, 3, 1, padx=(6, 0))
        
        tk.Label(card,
                 text="MFA will be retried up to 3 times if it fails.",
                 bg=C["surface"], fg=C["text_muted"],
                 font=F["body_sm"], wraplength=300, justify="left"
                 ).pack(anchor="w", padx=20, pady=(10, 12))

    # ────────────────────────────────────────────────────────────────────────────────
    #  Action Bar
    # ────────────────────────────────────────────────────────────────────────────────

    def _build_action_bar(self, parent):
        bar = tk.Frame(parent, bg=C["surface2"])
        bar.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 0))

        self._status_lbl = tk.Label(bar, text="",
                                    bg=C["surface2"], fg=C["text_muted"],
                                    font=F["body"])
        self._status_lbl.pack(side="left", padx=16, pady=12)

        self._progress = ttk.Progressbar(bar, mode="indeterminate",
                                          length=180, style="TProgressbar")

        ttk.Button(bar, text="🗑  Clear Form",
                   style="Secondary.TButton",
                   command=self._clear_form
                   ).pack(side="right", padx=(4, 16), pady=12)

        self._submit_btn = ttk.Button(
            bar, text="  🚀  Create User in O365 & AD  ",
            command=self._on_submit)
        self._submit_btn.pack(side="right", padx=4, pady=12)

    # ────────────────────────────────────────────────────────────────────────────────
    #  Remote data loading
    # ────────────────────────────────────────────────────────────────────────────────

    def _load_remote_data(self):
        # Load saved password
        saved = get_password(self.v_mail_sender.get())
        if saved:
            self.v_mail_pwd.set(saved)
            
        for fn in (self._fetch_groups, self._fetch_ous_and_ad_groups,
                   self._fetch_managers, self._fetch_licenses):
            threading.Thread(target=fn, daemon=True).start()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _generate_password(self):
        """Helper to generate a strong password and update the UI."""
        import secrets
        import string
        length = 12
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        pwd_list = [
            secrets.choice(string.ascii_lowercase),
            secrets.choice(string.ascii_uppercase),
            secrets.choice(string.digits),
            secrets.choice("!@#$%^&*")
        ]
        pwd_list += [secrets.choice(alphabet) for _ in range(length - 4)]
        secrets.SystemRandom().shuffle(pwd_list)
        pwd = "".join(pwd_list)
        
        # Update the UI variable
        if hasattr(self, "v_pwd"):
            self.v_pwd.set(pwd)
        return pwd

    def _generate_password(self):
        """Helper to generate a strong password and update the UI."""
        import secrets
        import string
        length = 12
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        pwd_list = [
            secrets.choice(string.ascii_lowercase),
            secrets.choice(string.ascii_uppercase),
            secrets.choice(string.digits),
            secrets.choice("!@#$%^&*")
        ]
        pwd_list += [secrets.choice(alphabet) for _ in range(length - 4)]
        secrets.SystemRandom().shuffle(pwd_list)
        pwd = "".join(pwd_list)
        
        # Update the UI variable
        if hasattr(self, "v_pwd"):
            self.v_pwd.set(pwd)
        return pwd

    def _save_mail_password(self):
        email = self.v_mail_sender.get().strip()
        pwd   = self.v_mail_pwd.get()
        if not email or not pwd:
            messagebox.showwarning("Warning", "Enter both email and password to save.")
            return
        save_password(email, pwd)
        messagebox.showinfo("Saved", "Password saved securely in Windows Vault.")

    def _trigger_duplicate_check(self, *_):
        """Debounced check for duplicates."""
        if self._check_job:
            self.after_cancel(self._check_job)
        self._check_job = self.after(1000, self._run_duplicate_check)

    def _run_duplicate_check(self):
        email = self.v_email.get().strip()
        emp_id = self.v_emp_id.get().strip()
        if not email and not emp_id: return
        
        def run():
            ok, msg = self.o365.check_duplicates(email, emp_id)
            if ok:
                self.after(0, lambda: self.winfo_exists() and messagebox.showwarning("Duplicate Detected", msg))
        
        threading.Thread(target=run, daemon=True).start()

    def _fetch_groups(self):
        # The user requested to see ONLY Distribution Lists here
        groups = self.o365.get_distribution_lists()
        # Store (id, name, type)
        self._all_groups = [
            (g["id"], g["displayName"], g.get("_type", "Distribution List"))
            for g in groups
        ]
        self.after(0, self._populate_groups)

    def _populate_groups(self, data: List[Tuple] = None):
        if not self.winfo_exists(): return
        items = data if data is not None else self._all_groups
        try:
            self._grp_lb.delete(0, "end")
            for _, name, gtype in items:
                self._grp_lb.insert("end", f"[{gtype}]  {name}")
            n = len(items)
            self._grp_hint.configure(
                text=f"{n} DLs found — Hold 'Ctrl' key to select multiple",
                fg=C["success"] if n else C["warning"])
        except tk.TclError: pass

    def _filter_groups(self, *_):
        q    = self.v_grp_search.get().lower()
        gtyp = self.v_grp_type.get()   # "All" or specific type prefix
        filtered = [
            (gid, name, gtype)
            for gid, name, gtype in self._all_groups
            if (q in name.lower() or q in gtype.lower())
            and (gtyp == "All" or gtype.startswith(gtyp))
        ]
        self._populate_groups(filtered)

    def _fetch_ous_and_ad_groups(self):
        # Fetch ONLY top-level OUs under Petrus Users
        ous = self.ad.get_ous(scope="OneLevel")
        self._all_ad_ous = [
            (o.get("Name", ""), o.get("DistinguishedName", "")) for o in ous
        ]
        self.after(0, self._populate_ous)
        
        # Load AD groups from the specific DL/AD Use path defined in config
        self._reload_ad_groups(None) # None uses default from config

    def _populate_ous(self):
        if not self.winfo_exists(): return
        names = [o[0] for o in self._all_ad_ous]
        if not names:
            names = ["No locations found"]
        try:
            self._ou_cb.configure(values=names)
            self.v_location.set("Select location...")
            self.v_sub_ou.set("Select location first")
        except tk.TclError: pass

    def _reload_ad_groups(self, ou_dn: Optional[str]):
        """Fetch AD groups under a given OU DN (in background thread)."""
        def run():
            groups = self.ad.get_groups(search_base=ou_dn) if ou_dn else self.ad.get_groups()
            self._all_ad_groups = [
                (g.get("Name", ""), g.get("DistinguishedName", "")) for g in groups
            ]
            self.after(0, self._populate_ad_groups)
        threading.Thread(target=run, daemon=True).start()

    def _on_location_selected(self, *_):
        idx = self._ou_cb.current()
        if idx < 0: return
        name, dn = self._all_ad_ous[idx]
        self.v_location.set(name)
        # Fetch sub-OUs
        threading.Thread(target=self._fetch_sub_ous, args=(dn,), daemon=True).start()

    def _fetch_sub_ous(self, parent_dn):
        sub_ous = self.ad.get_ous(base=parent_dn, scope='OneLevel')
        self._sub_ous = [(o.get('Name', ''), o.get('DistinguishedName', '')) for o in sub_ous]
        names = [o[0] for o in self._sub_ous]
        if not names:
            self.after(0, lambda: self.v_sub_ou.set('No sub-OUs found'))
            self.after(0, lambda: self._sub_ou_cb.configure(values=[]))
        else:
            self.after(0, lambda: self._sub_ou_cb.configure(values=names))
            self.after(0, lambda: self.v_sub_ou.set('Select department...'))

    def _on_sub_ou_selected(self, *_):
        pass # Value is in v_sub_ou

    def _populate_ad_groups(self):
        if not self.winfo_exists(): return
        try:
            self._ad_grp_lb.delete(0, "end")
            for name, _ in self._all_ad_groups:
                self._ad_grp_lb.insert("end", name)
        except tk.TclError: pass

    def _fetch_managers(self):
        users = self.o365.get_users()
        self._all_managers = [
            (u["id"], u.get("displayName", ""), u.get("userPrincipalName", ""))
            for u in users
        ]
        self.after(0, self._populate_managers)

    def _populate_managers(self, data=None):
        if not self.winfo_exists(): return
        items = data if data is not None else self._all_managers
        vals = [f"{name}  ({upn})" for _, name, upn in items]
        try:
            self._mgr_combo.configure(values=vals)
        except tk.TclError: pass

    def _filter_managers(self, e=None):
        q = self.v_mgr_search.get().lower()
        filtered = [
            (mid, name, upn) for mid, name, upn in self._all_managers
            if q in name.lower() or q in upn.lower()
        ]
        self._populate_managers(filtered)
        if filtered:
            self._mgr_combo.current(0)

    def _fetch_licenses(self):
        from config import LICENSE_SKU_MAP
        skus = self.o365.get_license_skus()
        sku_map = {}
        counts  = {}
        
        for sku in skus:
            part   = sku.get("skuPartNumber", "").upper()
            sku_id = sku.get("skuId", "")
            
            # Calculate counts
            consumed = sku.get("consumedUnits", 0)
            enabled  = sku.get("prepaidUnits", {}).get("enabled", 0)
            available = max(0, enabled - consumed)
            
            # Match ONLY O365/M365 Business SKUs — be very specific
            # to avoid matching POWER_BI_STANDARD or other unrelated SKUs
            name = None
            if part in ("O365_BUSINESS_ESSENTIALS", "SMB_BUSINESS_ESSENTIALS",
                        "M365_BUSINESS_BASIC"):
                name = "Microsoft 365 Business Basic"
            elif part in ("O365_BUSINESS_PREMIUM", "SMB_BUSINESS_PREMIUM",
                          "M365_BUSINESS_STANDARD", "SPB"):
                name = "Microsoft 365 Business Standard"
            
            if name:
                sku_map[name] = sku_id
                counts[name]  = (available, enabled)

        # Fall back to hardcoded SKU IDs for any that weren't matched
        for name, fallback_id in LICENSE_SKU_MAP.items():
            if name not in sku_map:
                sku_map[name] = fallback_id
                # counts[name] remains missing -> "Count unavailable"
        
        self._license_skus   = sku_map
        self._license_counts = counts
        
        def update_ui():
            if not self.winfo_exists(): return
            n = len(skus)
            try:
                self._license_hint.configure(
                    text=f"{n} SKU(s) loaded from tenant",
                    fg=C["success"] if n else C["warning"])
                self._on_license_change() # Trigger initial update of the count hint
            except tk.TclError: pass

        self.after(0, update_ui)

    def _on_license_change(self, *_):
        if not self.winfo_exists(): return
        name = self.v_license.get()
        try:
            if name in self._license_counts:
                avail, total = self._license_counts[name]
                color = C["success"] if avail > 0 else C["error"]
                self._license_hint.configure(
                    text=f"Available: {avail} / Total: {total}", fg=color)
            else:
                # Only show "Loading..." if we haven't loaded anything yet
                if not self._license_skus:
                    self._license_hint.configure(text="Fetching available SKUs…", fg=C["text_muted"])
                else:
                    self._license_hint.configure(text="License count unavailable", fg=C["warning"])
        except tk.TclError: pass

    # ────────────────────────────────────────────────────────────────────────────────
    #  Event handlers
    # ────────────────────────────────────────────────────────────────────────────────

    def _on_name_change(self, *_):
        first = re.sub(r"[^a-z0-9]", "", self.v_first.get().strip().lower())
        last  = re.sub(r"[^a-z0-9]", "", self.v_last.get().strip().lower())
        if first and last:
            self.v_email.set(f"{first}.{last}@{EMAIL_DOMAIN}")

    def _on_email_change(self, *_):
        email = self.v_email.get().strip()
        self.v_primary_smtp.set(f"SMTP:{email}" if email else f"SMTP:@{EMAIL_DOMAIN}")
        # Debounce duplicate check
        if self._email_job:
            self.after_cancel(self._email_job)
        self._email_job = self.after(900, lambda: self._check_email_dupe(email))

    def _check_email_dupe(self, email: str):
        if not email or "@" not in email:
            self._email_hint.configure(text="Enter a valid email address",
                                        fg=C["warning"])
            return
        self._email_hint.configure(text="⏳ Checking availability…",
                                    fg=C["text_muted"])

        def run():
            exists = self.o365.email_exists(email)
            def upd():
                if exists:
                    self._email_hint.configure(
                        text="⚠  Email already exists — please change it",
                        fg=C["error"])
                else:
                    self._email_hint.configure(
                        text="✅  Email available",
                        fg=C["success"])
            self.after(0, upd)
        threading.Thread(target=run, daemon=True).start()

    def _on_emp_id_change(self, *_):
        emp_id = self.v_emp_id.get().strip()
        if emp_id:
            # AD Proxy: smtp:employeeID@domain (lowercase smtp = secondary)
            self.v_alias.set(f"smtp:{emp_id}@{EMAIL_DOMAIN}")
            # O365 Alias: EmployeeID@domain (no smtp: prefix)
            self.v_o365_alias.set(f"{emp_id}@{EMAIL_DOMAIN}")
        else:
            self.v_alias.set(f"smtp:@{EMAIL_DOMAIN}")
            self.v_o365_alias.set(f"@{EMAIL_DOMAIN}")

    def _on_manager_select(self, e=None):
        sel = self._mgr_combo.get()
        for mid, name, upn in self._all_managers:
            if upn in sel:
                self._manager_id  = mid
                self._manager_upn = upn
                self._mgr_lbl.configure(
                    text=f"✅  {name}  ({upn})", fg=C["success"])
                break

    # (Removed _update_ad_path as path preview was removed from UI)

    # ────────────────────────────────────────────────────────────────────────────────
    #  Clear
    # ────────────────────────────────────────────────────────────────────────────────

    def _clear_form(self):
        if not messagebox.askyesno("Clear", "Clear all form fields?"):
            return
        for var, default in [
            (self.v_first, ""), (self.v_last, ""),
            (self.v_email, ""), (self.v_pwd, self._generate_password()),
            (self.v_job_title, ""), (self.v_dept, ""),
            (self.v_office, DEFAULT_OFFICE), (self.v_mobile, ""),
            (self.v_street, DEFAULT_STREET), (self.v_city, DEFAULT_CITY),
            (self.v_state, DEFAULT_STATE), (self.v_zip, DEFAULT_ZIP),
            (self.v_country, DEFAULT_COUNTRY), (self.v_emp_id, ""),
            (self.v_o365_alias, f"@{EMAIL_DOMAIN}"),
            (self.v_mail_pwd, ""), (self.v_mail_receiver, ""),
        ]:
            var.set(default)
        self._manager_id = self._manager_upn = None
        self._mgr_lbl.configure(text="No manager selected", fg=C["text_dim"])
        self._grp_lb.selection_clear(0, "end")
        self._ad_grp_lb.selection_clear(0, "end")
        self._update_o365_sel_display()
        self._update_ad_sel_display()
        self.v_location.set("Select location...")
        self.v_sub_ou.set("Select location first")
        self._status_lbl.configure(text="")

    # ────────────────────────────────────────────────────────────────────────────────
    #  Validation & data collection
    # ────────────────────────────────────────────────────────────────────────────────

    def _validate(self) -> Tuple[bool, str]:
        if not self.v_first.get().strip():
            return False, "First Name is required"
        if not self.v_last.get().strip():
            return False, "Last Name is required"
        
        email = self.v_email.get().strip()
        if not email or "@" not in email:
            return False, "A valid Email Address is required"
        
        if not self.v_pwd.get().strip():
            return False, "Password is required"
        
        # Mobile number validation (exactly 10 digits)
        mobile = self.v_mobile.get().strip()
        if not mobile:
            return False, "Mobile Phone is required"
        # Remove common separators if any (though user asked for "only number")
        clean_mobile = "".join(c for c in mobile if c.isdigit())
        if len(clean_mobile) != 10:
            return False, "Mobile Phone must be exactly 10 digits"
        if len(mobile) != 10 or not mobile.isdigit():
             return False, "Mobile Phone must contain only 10 digits (no spaces or special characters)"

        # Receiver Email validation
        # Receiver Email validation
        if self.v_send_email.get():
            receiver = self.v_mail_receiver.get().strip()
            if not receiver:
                return False, "Receiver Email (Personal) is required to send the Welcome Email"
            if "@" not in receiver:
                return False, "A valid Receiver Email (Personal) is required"

        # Joining Date validation
        if not self._joining_date.get_date():
            return False, "Joining Date is required"

        # AD Location validation
        if self.v_location.get() in ("", "Loading Locations...", "Select location..."):
            return False, "AD Location (Parent OU) is required"
        
        sub_ou = self.v_sub_ou.get()
        if sub_ou in ("", "Select location first", "No sub-OUs found"):
            # We allow it if there truly are no sub-OUs, but usually it's required
            pass

        return True, ""

    def _collect(self) -> Dict[str, Any]:
        first  = self.v_first.get().strip()
        last   = self.v_last.get().strip()
        email  = self.v_email.get().strip()
        emp_id = self.v_emp_id.get().strip()

        # Hire date ISO
        hire_dt  = self._hire_date.get_date()
        hire_iso = hire_dt.isoformat() + "T00:00:00Z" if hire_dt else None

        # O365 groups selected  — strip the "[Type]  " prefix to get the real name
        lb_items = list(self._grp_lb.get(0, "end"))
        o365_groups = []
        for idx in self._grp_lb.curselection():
            row_text = lb_items[idx]  # e.g. "[Distribution List]  All Staff"
            # Strip the tag prefix to recover the real display name
            real_name = row_text.split("]  ", 1)[-1] if "]  " in row_text else row_text
            for gid, gname, gtype in self._all_groups:
                if gname == real_name:
                    o365_groups.append((gid, gname))
                    break

        # AD groups selected
        ad_items = list(self._ad_grp_lb.get(0, "end"))
        ad_groups = []
        for idx in self._ad_grp_lb.curselection():
            name = ad_items[idx]
            for gname, gdn in self._all_ad_groups:
                if gname == name:
                    ad_groups.append((gname, gdn))
                    break

        # OU DN — sub-OU overrides parent if selected
        ou_dn = AD_PETRUS_USERS_OU
        sub_idx = self._sub_ou_cb.current()
        if sub_idx >= 0 and sub_idx < len(self._sub_ous):
            ou_dn = self._sub_ous[sub_idx][1]
        else:
            loc_idx = self._ou_cb.current()
            if loc_idx >= 0 and loc_idx < len(self._all_ad_ous):
                ou_dn = self._all_ad_ous[loc_idx][1]

        # License SKU
        lic_name = self.v_license.get()
        sku_id   = self._license_skus.get(lic_name)

        # O365 alias (employeeID@domain)
        o365_alias = self.v_o365_alias.get().strip()
        if o365_alias.startswith("@"):
            o365_alias = ""   # no employee ID entered

        return {
            "first_name":       first,
            "last_name":        last,
            "email":            email,
            "password":         self.v_pwd.get().strip(),
            "force_change_pwd": self.v_force_pwd.get(),
            "mail_nickname":    f"{first.lower()}.{last.lower()}"[:48],
            "job_title":        self.v_job_title.get().strip(),
            "department":       self.v_dept.get().strip(),
            "office":           self.v_office.get().strip(),
            "mobile":           self.v_mobile.get().strip(),
            "street":           self.v_street.get().strip(),
            "city":             self.v_city.get().strip(),
            "state":            self.v_state.get().strip(),
            "zip":              self.v_zip.get().strip(),
            "country":          self.v_country.get().strip(),
            "employee_id":      emp_id,
            "employee_type":    self.v_emp_type.get(),
            "hire_date_iso":    hire_iso,
            "license_name":     lic_name,
            "license_sku_id":   sku_id,
            "enable_mfa":       self.v_mfa.get(),
            "manager_id":       self._manager_id,
            "manager_upn":      self._manager_upn,
            "o365_groups":      o365_groups,
            "o365_alias":       o365_alias,
            "ad_ou":            ou_dn,
            "ad_groups":        ad_groups,
            "receiver_email":   self.v_mail_receiver.get().strip(),
        }

    # ────────────────────────────────────────────────────────────────────────────────
    #  Submission
    # ────────────────────────────────────────────────────────────────────────────────

    def _on_submit(self):
        ok, msg = self._validate()
        if not ok:
            messagebox.showerror("Validation Error", msg)
            return

        email = self.v_email.get().strip()
        if self.o365.email_exists(email):
            choice = messagebox.askyesno(
                "Email Already Exists",
                f"The email  '{email}'  already exists in O365.\n\n"
                "Do you want to change the email and continue?\n"
                "(Click 'No' to cancel creation)",
                icon="warning",
            )
            if choice:
                self._e_email.focus_set()
            return

        self._submit_btn.configure(state="disabled")
        self._progress.pack(side="left", padx=8, pady=12)
        self._progress.start(10)
        self._status_lbl.configure(text="⏳ Creating user…", fg=C["text_muted"])

        data = self._collect()
        threading.Thread(target=self._run_creation, args=(data,), daemon=True).start()

    def _run_creation(self, data: Dict[str, Any]):
        from config import LICENSE_SKU_MAP, MAILBOX_WAIT_SECONDS
        log: List[Tuple[bool, str]] = []

        def step(ok: bool, msg: str):
            log.append((ok, msg))
            icon = "✅" if ok else "⚠"
            self.after(0, lambda m=f"{icon} {msg}":
                self._status_lbl.configure(
                    text=m, fg=C["text"] if ok else C["warning"]))

        # ── 1. Create O365 user ───────────────────────────────────────────────
        step(True, "Creating O365 user…")
        ok, user_id, msg = self.o365.create_user(data)
        if not ok:
            self.after(0, lambda: self._done(False, f"O365 user creation failed:\n{msg}", log))
            return
        step(ok, f"O365 user created ({user_id[:8]}…)")

        # ── 1b. Wait for Azure AD replication ────────────────────────────────
        step(True, "⏳ Waiting for Azure AD replication (up to 60 s)…")
        prov_ok, prov_msg = self.o365.wait_for_user_provisioned(user_id, max_wait=60)
        if not prov_ok:
            step(False, prov_msg)   # warn but continue
        else:
            step(True, "Azure AD replication confirmed ✔")

        # ── 1c. Set mail address (shows email in Azure portal immediately) ────
        mail_ok, mail_msg = self.o365.set_mail_address(user_id, data["email"])
        step(mail_ok, f"Azure AD mail address: {mail_msg}")

        # ── 2. Assign license ─────────────────────────────────────────────────
        sku_id = data.get("license_sku_id")
        # Fallback to hardcoded SKU IDs if dynamic fetch didn't find one
        if not sku_id:
            sku_id = LICENSE_SKU_MAP.get(data.get("license_name", ""))
        lic_ok = False
        if sku_id:
            step(True, "Assigning license (retrying if needed)…")
            lic_ok, m2 = self.o365.assign_license(user_id, sku_id)
            step(lic_ok, f"License: {m2}")
        else:
            step(False, f"License SKU for '{data['license_name']}' not found — assign manually")

        # ── 2b. Wait for Exchange mailbox provisioning ────────────────────────
        # Groups and aliases in O365 require an active Exchange mailbox.
        # The mailbox only becomes live AFTER the license is applied.
        step(True, f"⏳ Waiting for Exchange Online mailbox (up to {MAILBOX_WAIT_SECONDS}s)…")
        mbx_ok, mbx_msg = self.o365.wait_for_mailbox(user_id, max_wait=MAILBOX_WAIT_SECONDS)
        if mbx_ok:
            step(True, "Exchange mailbox ready ✔")
        else:
            step(False, f"{mbx_msg}  — will retry after AD creation")

        # ── 3. Manager ────────────────────────────────────────────────────────
        if data.get("manager_id"):
            ok4, m4 = self.o365.set_manager(user_id, data["manager_id"])
            step(ok4, f"Manager: {m4}")

        # ── 4. First attempt: Alias, Groups ──────────────────────────────────
        # Track failures for retry after AD creation
        retry_alias   = False
        retry_groups  = []    # list of (gid, gname) that failed

        emp_id     = data.get("employee_id", "")
        # Generate alias if not already provided
        o365_alias = data.get("o365_alias", "")
        if not o365_alias and emp_id and "@" in data["email"]:
            o365_alias = f"{emp_id}@{data['email'].split('@')[1]}"

        # 4a. MFA
        if data.get("enable_mfa"):
            step(True, "ℹ MFA: Please enable MFA manually in Azure portal → Users → Per-user MFA")

        # 4b. O365 Alias (employeeID@domain)
        if o365_alias:
            al_ok, al_msg = self.o365.add_o365_alias(user_id, o365_alias)
            step(al_ok, f"O365 alias: {al_msg}")
            if not al_ok: retry_alias = True

        # 4c. O365 Groups (Cloud-only) - Batch processed to avoid multiple logins
        admin_upn = self.v_mail_sender.get()
        o365_groups = data.get("o365_groups", [])
        if o365_groups:
            results = self.o365.add_to_groups_multi(user_id, o365_groups, admin_upn=admin_upn)
            for gname, ok, msg in results:
                step(ok, f"O365 group '{gname}': {msg}")
                if not ok:
                    # Find the gid for this group name to retry
                    gid = next((g[0] for g in o365_groups if g[1] == gname), None)
                    if gid: retry_groups.append((True, gid, gname))

        # 4d. Zoho Enterprise App
        zoho_ok, m6 = self.o365.add_to_zoho_enterprise_app(user_id)
        step(zoho_ok, f"Zoho Accounts: {m6}")

        # ── 5. Create AD user ─────────────────────────────────────────────────
        step(True, "Creating Active Directory user…")
        if data.get("manager_upn"):
            data["ad_manager_dn"] = self.ad.get_manager_dn(data["manager_upn"]) or ""
        ok7, result7 = self.ad.create_user(data)
        if not ok7:
            step(False, f"AD creation error: {result7}")
            # Don't return — continue with retries even if AD fails
            sam = None
        else:
            sam = result7
            data["sam_account_name"] = sam
            step(ok7, f"AD user created: {sam}")

        # ── 6. AD Proxy addresses ────────────────────────────────────────────
        if sam and (emp_id or retry_alias == "AD_FALLBACK"):
            # Set primary and alias in AD
            addrs = [f"SMTP:{data['email']}"]
            if o365_alias:
                addrs.append(f"smtp:{o365_alias}")
            ok8, m8 = self.ad.set_proxy_addresses(sam, addrs)
            step(ok8, f"AD Proxy addresses: {m8}")

        # ── 7. AD groups & O365 Fallback ──────────────────────────────────────
        if sam:
            # Standard AD groups
            for gname, gdn in data.get("ad_groups", []):
                ok9, m9 = self.ad.add_user_to_group(sam, gdn)
                step(ok9, f"AD group '{gname}': {m9}")
            
            # No fallback to AD for O365 groups (per user clarification they are different)
            pass

        # ══════════════════════════════════════════════════════════════════════
        # ── 8. RETRY failed O365 operations ──────────────────────────────────
        # By now, more time has passed since license assignment (AD creation
        # took 10-30s), so the Exchange mailbox is more likely to be ready.
        # ══════════════════════════════════════════════════════════════════════
        # ── 8. RETRY failed O365 operations ──────────────────────────────────
        needs_retry = retry_alias or retry_groups
        if needs_retry:
            step(True, "")
            step(True, "═══ Retrying failed O365 operations after AD creation ═══")

            # Re-check mailbox if it wasn't ready before
            if not mbx_ok:
                step(True, "⏳ Re-checking Exchange mailbox…")
                mbx_ok, mbx_msg = self.o365.wait_for_mailbox(user_id, max_wait=60)
                step(mbx_ok, f"Mailbox re-check: {'ready ✔' if mbx_ok else mbx_msg}")

            # Retry alias
            if retry_alias is True and o365_alias:
                step(True, "🔄 Retrying O365 alias…")
                al_ok2, al_msg2 = self.o365.add_o365_alias(user_id, o365_alias)
                step(al_ok2, f"O365 alias retry: {al_msg2}")

            # Retry groups - Batch processed
            if retry_groups:
                step(True, f"🔄 Retrying {len(retry_groups)} failed group(s)…")
                o365_retries = [(gid, gname) for is_o365, gid, gname in retry_groups if is_o365]
                if o365_retries:
                    results = self.o365.add_to_groups_multi(user_id, o365_retries, admin_upn=admin_upn)
                    for gname, ok, msg in results:
                        step(ok, f"Group retry '{gname}': {msg}")

        # ── 9. MFA — skipped (per user request) ─────────────────────────────────────────
        # if data.get("enable_mfa"):
        #     ...
        pass

        # ── 10. Welcome Email ─────────────────────────────────────────────────
        if self.v_send_email.get():
            data["sam_account_name"] = sam if sam else "Unknown"
            self._send_welcome_email(data, step)

        self.after(0, lambda: self._done(
            True, f"User '{data['email']}' created in O365 & AD!", log))

    def _done(self, success: bool, message: str, log: list):
        self._progress.stop()
        self._progress.pack_forget()
        self._submit_btn.configure(state="normal")
        color = C["success"] if success else C["error"]
        icon  = "✅" if success else "❌"
        self._status_lbl.configure(text=f"{icon} {message}", fg=color)
        self._show_result(success, message, log)

    def _show_result(self, success: bool, message: str, log: list):
        win = tk.Toplevel(self)
        win.title("Onboarding " + ("Successful" if success else "Failed"))
        win.configure(bg=C["bg"])
        win.geometry("600x520")
        win.grab_set()
        win.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width()  - 600) // 2
        y = self.winfo_rooty() + (self.winfo_height() - 520) // 2
        win.geometry(f"600x520+{x}+{y}")

        color = C["success"] if success else C["error"]
        tk.Label(win, text=("✅  Success" if success else "❌  Failed"),
                 bg=C["bg"], fg=color, font=F["title_lg"]
                 ).pack(padx=20, pady=(20, 4), anchor="w")
        tk.Label(win, text=message,
                 bg=C["bg"], fg=C["text"], font=F["body"],
                 wraplength=560, justify="left"
                 ).pack(padx=20, pady=(0, 12), anchor="w")

        log_frame = tk.Frame(win, bg=C["surface"])
        log_frame.pack(fill="both", expand=True, padx=20, pady=(0, 8))
        txt = tk.Text(log_frame, bg=C["input_bg"], fg=C["text"],
                      font=("Consolas", 9), relief="flat", bd=0, wrap="word")
        vsb = ttk.Scrollbar(log_frame, command=txt.yview)
        txt.configure(yscrollcommand=vsb.set)
        txt.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        vsb.pack(side="right", fill="y", pady=6)

        txt.tag_configure("ok",   foreground=C["success"])
        txt.tag_configure("warn", foreground=C["warning"])
        txt.tag_configure("err",  foreground=C["error"])
        for ok, msg in log:
            tag = "ok" if ok else "warn"
            txt.insert("end", msg + "\n", tag)
        txt.configure(state="disabled")

        ttk.Button(win, text="Close", command=win.destroy
                   ).pack(pady=(4, 16))

    # ────────────────────────────────────────────────────────────────────────────────
    #  Hierarchical OU & Group Selection Logic
    # ────────────────────────────────────────────────────────────────────────────────

    def _on_location_selected(self, *_):
        idx = self._ou_cb.current()
        if idx < 0: return
        name, dn = self._all_ad_ous[idx]
        self.v_location.set(name)
        # Fetch sub-OUs
        threading.Thread(target=self._fetch_sub_ous, args=(dn,), daemon=True).start()

    def _fetch_sub_ous(self, parent_dn):
        sub_ous = self.ad.get_ous(base=parent_dn, scope='OneLevel')
        self._sub_ous = [(o.get('Name', ''), o.get('DistinguishedName', '')) for o in sub_ous]
        names = [o[0] for o in self._sub_ous]
        if not names:
            self.after(0, lambda: self.v_sub_ou.set('No sub-OUs found'))
            self.after(0, lambda: self._sub_ou_cb.configure(values=[]))
        else:
            self.after(0, lambda: self._sub_ou_cb.configure(values=names))
            self.after(0, lambda: self.v_sub_ou.set('Select department...'))

    def _on_sub_ou_selected(self, *_):
        pass # The value is already in v_sub_ou

    def _update_o365_sel_display(self, *_):
        self._update_sel_list(self._grp_lb, self._all_groups, self._o365_sel_frame)

    def _update_ad_sel_display(self, *_):
        self._update_sel_list(self._ad_grp_lb, self._all_ad_groups, self._ad_sel_frame)

    def _update_sel_list(self, lb, all_items, frame):
        # Clear frame
        for w in frame.winfo_children(): w.destroy()
        indices = lb.curselection()
        if not indices:
            tk.Label(frame, text='(None selected)', bg=C['surface'], fg=C['text_dim'], font=F['body_sm']).pack(side='left')
            return
        
        for idx in indices:
            # We need to map the listbox index back to the filtered items if filtered
            # but for now let's assume we use the display text
            text = lb.get(idx)
            lbl = tk.Label(frame, text=text, bg=C['accent_dim'], fg=C['text'], 
                           padx=6, pady=2, font=F['body_sm'])
            lbl.pack(side='left', padx=2, pady=2)

    # ────────────────────────────────────────────────────────────────────────────────
    #  Email Sending
    # ────────────────────────────────────────────────────────────────────────────────

    def _send_welcome_email(self, user_data, step):
        if not self.v_send_email.get(): return
        
        step(True, '📧 Sending welcome email...')
        sender = self.v_mail_sender.get()
        pwd = self.v_mail_pwd.get()
        cc = self.v_mail_cc.get()
        
        if not pwd:
            step(False, 'Email skipped: Sender password not provided')
            return

        ok, msg = self.mail.send_welcome_email(sender, pwd, 
                                              user_data.get('receiver_email') or user_data['email'], 
                                              cc, user_data)
        step(ok, msg)
