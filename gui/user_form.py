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
    LICENSE_OPTIONS, EMPLOYEE_TYPES, DEPARTMENTS,
    LICENSE_SKU_MAP, MAILBOX_WAIT_SECONDS,
    DEFAULT_EMAIL_SENDER, DEFAULT_EMAIL_CC,
)
from core.mail_service import MailService
from core.credential_manager import save_password, get_password
from core.settings_manager import sm
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
        
        self._canvas = canvas
        def _on_mousewheel(event):
            try:
                if not canvas.winfo_exists(): return
                w = event.widget.winfo_containing(event.x_root, event.y_root)
            except Exception:
                w = event.widget
            
            widget_class = getattr(w, "winfo_class", lambda: "")() if w else ""
            if widget_class in ("TCombobox", "Listbox", "TSpinbox", "Spinbox"):
                return
                
            try:
                if canvas.winfo_exists():
                    canvas.yview_scroll(-1 * (event.delta // 120), "units")
            except tk.TclError: pass

        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        self.bind("<Destroy>", lambda _: self.unbind_all("<MouseWheel>"))

def _section(parent: tk.Widget, title: str, icon: str = "") -> tk.Frame:
    hdr = tk.Frame(parent, bg=C["surface2"])
    hdr.pack(fill="x", pady=(18, 0))
    tk.Frame(hdr, bg=C["accent"], width=4).pack(side="left", fill="y")
    lbl_text = f"  {icon}  {title}".strip() if icon else f"  {title}"
    tk.Label(hdr, text=lbl_text, bg=C["surface2"], fg=C["text"], font=F["subtitle"], pady=8).pack(side="left", padx=4)
    card = tk.Frame(parent, bg=C["surface"])
    card.pack(fill="x", pady=(0, 4))
    return card

def _grid_lbl(parent, text, row, col=0, span=1, required=False, padx=(12, 6)):
    suffix = "  *" if required else ""
    tk.Label(parent, text=f"{text}{suffix}", bg=C["surface"], fg=C["text_muted"], font=F["label"], anchor="w").grid(row=row, column=col, columnspan=span, sticky="w", padx=padx, pady=(8, 2))

class UserForm(tk.Frame):
    def __init__(self, parent, o365_service, ad_service, on_back=None):
        super().__init__(parent, bg=C["bg"])
        self.o365 = o365_service
        self.ad   = ad_service
        self.mail = MailService()
        self._on_back = on_back

        self._all_groups:     List[Tuple[str, str, str]] = [] 
        self._all_ad_ous:     List[Tuple[str, str]] = []   
        self._sub_ous:        List[Tuple[str, str]] = []   
        self._all_ad_groups:  List[Tuple[str, str]] = []   
        self._all_managers:   List[Tuple[str, str, str]] = []  
        self._license_skus:   dict = {}   
        self._license_counts: dict = {}   
        self._manager_id:     Optional[str] = None
        self._manager_upn:    Optional[str] = None
        self._email_job:      Optional[str] = None   
        self._check_job:      Optional[str] = None   

        self._build_ui()
        self._load_data()

    def _build_ui(self):
        header = tk.Frame(self, bg=C["bg"])
        header.pack(fill="x", padx=40, pady=(20, 0))
        if self._on_back:
            ttk.Button(header, text="←  Back", style="Secondary.TButton", command=self._on_back).pack(side="left")
        tk.Label(header, text="🚀  New Employee Onboarding", bg=C["bg"], fg=C["text"], font=F["title"]).pack(side="left", padx=20)

        scroll = _ScrollableFrame(self)
        scroll.pack(fill="both", expand=True, padx=40, pady=20)
        self._main = scroll.inner
        self._main.columnconfigure(0, weight=1)
        self._main.columnconfigure(1, weight=1)

        left_col = tk.Frame(self._main, bg=C["bg"])
        left_col.grid(row=0, column=0, sticky="nw", padx=(0, 10))
        right_col = tk.Frame(self._main, bg=C["bg"])
        right_col.grid(row=0, column=1, sticky="nw", padx=(10, 0))

        self._build_personal(left_col)
        self._build_profile(left_col)
        self._build_company(left_col)
        
        self._build_license(right_col)
        self._build_manager(right_col)
        self._build_groups(right_col)
        self._build_ad_config(right_col)
        self._build_mfa(right_col)
        self._build_actions(self._main)

    def _build_personal(self, parent):
        card = _section(parent, "Personal Information", "👤")
        card.columnconfigure(0, weight=1)
        card.columnconfigure(1, weight=1)

        def field(label, attr, row, col, required=False, padx_lbl=(12,6), padx_ent=(12,6)):
            _grid_lbl(card, label, row, col, required=required, padx=padx_lbl)
            var = tk.StringVar()
            setattr(self, attr, var)
            var.trace_add("write", self._on_name_change)
            ttk.Entry(card, textvariable=var, font=F["body"]).grid(row=row+1, column=col, sticky="ew", padx=padx_ent, pady=(0, 6))

        field("First Name", "v_first", 0, 0, True, padx_lbl=(12,6), padx_ent=(12,6))
        field("Last Name",  "v_last",  0, 1, True, padx_lbl=(6,12), padx_ent=(6,12))
        
        _grid_lbl(card, "Personal Email (for Welcome Email)", 2, 0, 2)
        self.v_personal_email = tk.StringVar()
        ttk.Entry(card, textvariable=self.v_personal_email, font=F["body"]).grid(row=3, column=0, columnspan=2, sticky="ew", padx=12, pady=(0,6))

    def _build_profile(self, parent):
        card = _section(parent, "Profile Information", "📋")
        card.columnconfigure(0, weight=1)
        card.columnconfigure(1, weight=1)

        def field(label, attr, row, col, default="", required=False, values=None, padx_lbl=(12,6), padx_ent=(12,6)):
            _grid_lbl(card, label, row, col, required=required, padx=padx_lbl)
            var = tk.StringVar(value=default)
            setattr(self, attr, var)
            if values:
                cb = ttk.Combobox(card, textvariable=var, values=values, font=F["body"])
                cb.grid(row=row+1, column=col, sticky="ew", padx=padx_ent, pady=(0, 6))
                if not default and values: var.set(values[0])
            else:
                ttk.Entry(card, textvariable=var, font=F["body"]).grid(row=row+1, column=col, sticky="ew", padx=padx_ent, pady=(0, 6))

        field("Job Title", "v_job_title", 0, 0)
        field("Department", "v_dept", 0, 1, values=sm.get("departments"))
        field("Office Location", "v_office", 2, 0, sm.get("default_office"))
        field("Mobile Phone", "v_mobile", 2, 1, required=True)

        _grid_lbl(card, "Street Address", 4, 0, 2)
        self.v_street = tk.StringVar(value=sm.get("default_street"))
        ttk.Entry(card, textvariable=self.v_street, font=F["body"]).grid(row=5, column=0, columnspan=2, sticky="ew", padx=12, pady=(0,6))

        field("City", "v_city", 6, 0, sm.get("default_city"))
        field("State", "v_state", 6, 1, sm.get("default_state"))
        field("ZIP", "v_zip", 8, 0, sm.get("default_zip"))
        field("Country", "v_country", 8, 1, sm.get("default_country"))

    def _build_company(self, parent):
        card = _section(parent, "Company Account", "🏢")
        card.columnconfigure(0, weight=1)
        card.columnconfigure(1, weight=1)

        _grid_lbl(card, "Employee ID", 0, 0, required=True)
        self.v_emp_id = tk.StringVar()
        self.v_emp_id.trace_add("write", self._on_id_change)
        ttk.Entry(card, textvariable=self.v_emp_id, font=F["body"]).grid(row=1, column=0, sticky="ew", padx=(12,6), pady=(0,6))

        _grid_lbl(card, "Employee Type", 0, 1)
        self.v_emp_type = tk.StringVar(value=EMPLOYEE_TYPES[0])
        ttk.Combobox(card, textvariable=self.v_emp_type, values=EMPLOYEE_TYPES, state="readonly", font=F["body"]).grid(row=1, column=1, sticky="ew", padx=(6,12), pady=(0,6))

        _grid_lbl(card, "Joining Date", 2, 0)
        self.v_date = _date_entry(card, 3, 0)

        _grid_lbl(card, "O365 Email (UPN)", 4, 0, 2, required=True)
        self.v_email = tk.StringVar()
        self.v_email.trace_add("write", self._on_email_manual_change)
        ttk.Entry(card, textvariable=self.v_email, font=F["body"]).grid(row=5, column=0, columnspan=2, sticky="ew", padx=12, pady=(0,6))

        self._dup_hint = tk.Label(card, text="", bg=C["surface"], fg=C["error"], font=F["body_sm"], anchor="w")
        self._dup_hint.grid(row=6, column=0, columnspan=2, sticky="ew", padx=12, pady=(0,6))

        _grid_lbl(card, "Account Password", 7, 0, 2, required=True)
        self.v_pwd = tk.StringVar(value=self._gen_pwd())
        pwd_frame = tk.Frame(card, bg=C["surface"])
        pwd_frame.grid(row=8, column=0, columnspan=2, sticky="ew", padx=12, pady=(0,12))
        ttk.Entry(pwd_frame, textvariable=self.v_pwd, font=F["mono"]).pack(side="left", fill="x", expand=True)
        ttk.Button(pwd_frame, text="🎲", width=3, command=lambda: self.v_pwd.set(self._gen_pwd())).pack(side="left", padx=(4,0))

    def _build_license(self, parent):
        card = _section(parent, "M365 License", "🔑")
        self.v_license = tk.StringVar(value=LICENSE_OPTIONS[0])
        self.v_license.trace_add("write", self._on_license_change)
        ttk.Combobox(card, textvariable=self.v_license, values=LICENSE_OPTIONS, state="readonly", font=F["body"]).pack(fill="x", padx=12, pady=(12,0))
        self._license_hint = tk.Label(card, text="Fetching SKU counts...", bg=C["surface"], fg=C["text_muted"], font=F["body_sm"], anchor="w")
        self._license_hint.pack(fill="x", padx=12, pady=(4,12))

    def _build_manager(self, parent):
        card = _section(parent, "Reporting Manager", "👤")
        tk.Label(card, text="Search manager by name or email:", bg=C["surface"], fg=C["text_muted"], font=F["label"]).pack(anchor="w", padx=12, pady=(10,0))
        self.v_mgr_search = tk.StringVar()
        self.v_mgr_search.trace_add("write", self._filter_managers)
        ttk.Entry(card, textvariable=self.v_mgr_search, font=F["body"]).pack(fill="x", padx=12, pady=4)
        self._mgr_combo = ttk.Combobox(card, state="readonly", font=F["body"])
        self._mgr_combo.pack(fill="x", padx=12, pady=(0,12))

    def _build_groups(self, parent):
        card = _section(parent, "O365 Groups & Distribution Lists", "👥")
        tk.Label(card, text="Filter groups:", bg=C["surface"], fg=C["text_muted"], font=F["label"]).pack(anchor="w", padx=12, pady=(10,0))
        self.v_grp_search = tk.StringVar()
        self.v_grp_search.trace_add("write", self._filter_groups)
        ttk.Entry(card, textvariable=self.v_grp_search, font=F["body"]).pack(fill="x", padx=12, pady=4)
        
        self._grp_lb = tk.Listbox(card, selectmode="multiple", font=F["body_sm"], bg=C["input_bg"], fg=C["text"], borderwidth=0, highlightthickness=1, highlightcolor=C["accent"], height=6)
        self._grp_lb.pack(fill="x", padx=12, pady=(0,12))

    def _build_ad_config(self, parent):
        card = _section(parent, "Active Directory Config", "🖥️")
        card.columnconfigure(0, weight=1)
        card.columnconfigure(1, weight=1)

        _grid_lbl(card, "Primary OU (Location)", 0, 0)
        self.v_location = tk.StringVar()
        self._ou_cb = ttk.Combobox(card, textvariable=self.v_location, state="readonly", font=F["body"])
        self._ou_cb.grid(row=1, column=0, sticky="ew", padx=(12,6), pady=(0,6))
        self._ou_cb.bind("<<ComboboxSelected>>", self._on_location_selected)

        _grid_lbl(card, "Sub-OU (Department)", 0, 1)
        self.v_sub_ou = tk.StringVar()
        self._sub_ou_cb = ttk.Combobox(card, textvariable=self.v_sub_ou, state="readonly", font=F["body"])
        self._sub_ou_cb.grid(row=1, column=1, sticky="ew", padx=(6,12), pady=(0,6))

        _grid_lbl(card, "AD Security Groups", 2, 0, 2)
        self._ad_grp_lb = tk.Listbox(card, selectmode="multiple", font=F["body_sm"], bg=C["input_bg"], fg=C["text"], height=4)
        self._ad_grp_lb.grid(row=3, column=0, columnspan=2, sticky="ew", padx=12, pady=(0,12))

    def _build_mfa(self, parent):
        card = _section(parent, "Security & MFA", "🛡️")
        self.v_mfa = tk.BooleanVar(value=True)
        ttk.Checkbutton(card, text="Enable Per-User MFA automatically", variable=self.v_mfa).pack(anchor="w", padx=12, pady=12)

    def _build_actions(self, parent):
        frame = tk.Frame(parent, bg=C["bg"])
        frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=40)
        self._btn_create = ttk.Button(frame, text="🚀  Create Employee Account", style="Primary.TButton", command=self._on_submit)
        self._btn_create.pack(side="right", padx=12)

    # ── Data Loading ──────────────────────────────────────────────────────────
    def _load_data(self):
        threading.Thread(target=self._fetch_managers, daemon=True).start()
        threading.Thread(target=self._fetch_groups, daemon=True).start()
        threading.Thread(target=self._fetch_licenses, daemon=True).start()
        threading.Thread(target=self._fetch_ad_ous, daemon=True).start()
        threading.Thread(target=self._reload_ad_groups, args=(None,), daemon=True).start()

    def _fetch_managers(self):
        users = self.o365.get_users()
        self._all_managers = [(u["id"], u.get("displayName", ""), u.get("userPrincipalName", "")) for u in users]
        self.after(0, self._populate_managers)

    def _populate_managers(self, data=None):
        if not self.winfo_exists(): return
        items = data if data is not None else self._all_managers
        vals = [f"{name} ({upn})" for _, name, upn in items]
        self._mgr_combo.configure(values=vals)

    def _filter_managers(self, *_):
        q = self.v_mgr_search.get().lower()
        filtered = [m for m in self._all_managers if q in m[1].lower() or q in m[2].lower()]
        self._populate_managers(filtered)

    def _fetch_groups(self):
        grps = self.o365.get_groups()
        self._all_groups = [(g["id"], g["displayName"], g.get("_type", "Group")) for g in grps]
        self.after(0, self._populate_groups)

    def _populate_groups(self, data=None):
        if not self.winfo_exists(): return
        items = data if data is not None else self._all_groups
        self._grp_lb.delete(0, "end")
        for _, name, gtype in items: self._grp_lb.insert("end", f"{name} ({gtype})")

    def _filter_groups(self, *_):
        q = self.v_grp_search.get().lower()
        filtered = [g for g in self._all_groups if q in g[1].lower()]
        self._populate_groups(filtered)

    def _fetch_licenses(self):
        skus = self.o365.get_license_skus()
        sku_map, counts = {}, {}
        for sku in skus:
            part, sid = sku.get("skuPartNumber", "").upper(), sku.get("skuId", "")
            avail = max(0, sku.get("prepaidUnits", {}).get("enabled", 0) - sku.get("consumedUnits", 0))
            name = None
            if part in ("O365_BUSINESS_ESSENTIALS", "M365_BUSINESS_BASIC"): name = "Microsoft 365 Business Basic"
            elif part in ("O365_BUSINESS_PREMIUM", "M365_BUSINESS_STANDARD"): name = "Microsoft 365 Business Standard"
            if name: sku_map[name], counts[name] = sid, (avail, sku.get("prepaidUnits", {}).get("enabled", 0))
        for k, v in LICENSE_SKU_MAP.items():
            if k not in sku_map: sku_map[k] = v
        self._license_skus, self._license_counts = sku_map, counts
        self.after(0, self._on_license_change)

    def _on_license_change(self, *_):
        name = self.v_license.get()
        if name in self._license_counts:
            avail, total = self._license_counts[name]
            self._license_hint.configure(text=f"Available: {avail} / Total: {total}", fg=C["success"] if avail > 0 else C["error"])
        else: self._license_hint.configure(text="License count unavailable", fg=C["warning"])

    def _fetch_ad_ous(self):
        ous = self.ad.get_ous()
        self._all_ad_ous = [(o["Name"], o["DistinguishedName"]) for o in ous]
        self.after(0, lambda: self._ou_cb.configure(values=[o[0] for o in self._all_ad_ous]))

    def _on_location_selected(self, *_):
        idx = self._ou_cb.current()
        if idx < 0: return
        dn = self._all_ad_ous[idx][1]
        threading.Thread(target=self._fetch_sub_ous, args=(dn,), daemon=True).start()
        self._reload_ad_groups(dn)

    def _fetch_sub_ous(self, parent_dn):
        sub = self.ad.get_ous(base=parent_dn, scope='OneLevel')
        self._sub_ous = [(o["Name"], o["DistinguishedName"]) for o in sub]
        names = ["(Use parent OU)"] + [o[0] for o in self._sub_ous]
        self.after(0, lambda: self._sub_ou_cb.configure(values=names))
        self.after(0, lambda: self._sub_ou_cb.current(0))

    def _reload_ad_groups(self, dn=None):
        def run():
            grps = self.ad.get_groups(search_base=dn)
            self._all_ad_groups = [(g["Name"], g["DistinguishedName"]) for g in grps]
            self.after(0, self._populate_ad_groups)
        threading.Thread(target=run, daemon=True).start()

    def _populate_ad_groups(self):
        if not self.winfo_exists(): return
        self._ad_grp_lb.delete(0, "end")
        for name, _ in self._all_ad_groups: self._ad_grp_lb.insert("end", name)

    # ── Logic ─────────────────────────────────────────────────────────────────
    def _gen_pwd(self):
        chars = string.ascii_letters + string.digits + "!@#$%^&*"
        return "".join(secrets.choice(chars) for _ in range(12))

    def _on_name_change(self, *_):
        f = re.sub(r"[^a-z0-9]", "", self.v_first.get().strip().lower())
        l = re.sub(r"[^a-z0-9]", "", self.v_last.get().strip().lower())
        if f and l: self.v_email.set(f"{f}.{l}@{EMAIL_DOMAIN}")

    def _on_email_manual_change(self, *_):
        if self._check_job: self.after_cancel(self._check_job)
        self._check_job = self.after(800, self._do_duplicate_check)

    def _on_id_change(self, *_):
        if self._check_job: self.after_cancel(self._check_job)
        self._check_job = self.after(800, self._do_duplicate_check)

    def _do_duplicate_check(self):
        email, eid = self.v_email.get().strip(), self.v_emp_id.get().strip()
        if not email: return
        def run():
            exists, msg = self.o365.check_duplicates(email, eid)
            self.after(0, lambda: self._dup_hint.configure(text=msg))
        threading.Thread(target=run, daemon=True).start()

    def _on_submit(self):
        if not self.v_first.get() or not self.v_last.get() or not self.v_email.get() or not self.v_emp_id.get():
            messagebox.showerror("Error", "Please fill in all required fields.")
            return
        
        data = {
            "first_name": self.v_first.get(), "last_name": self.v_last.get(),
            "email": self.v_email.get(), "password": self.v_pwd.get(),
            "job_title": self.v_job_title.get(), "department": self.v_dept.get(),
            "office": self.v_office.get(), "mobile": self.v_mobile.get(),
            "street": self.v_street.get(), "city": self.v_city.get(),
            "state": self.v_state.get(), "zip": self.v_zip.get(),
            "country": self.v_country.get(), "employee_id": self.v_emp_id.get(),
            "employee_type": self.v_emp_type.get(), "hire_date_iso": self.v_date.get_date().isoformat()
        }
        
        # Selected OU
        idx = self._ou_cb.current()
        if idx >= 0:
            dn = self._all_ad_ous[idx][1]
            sub_idx = self._sub_ou_cb.current()
            if sub_idx > 0: dn = self._sub_ous[sub_idx-1][1]
            data["ad_ou"] = dn
        
        # Selected Manager
        midx = self._mgr_combo.current()
        if midx >= 0:
            q = self.v_mgr_search.get().lower()
            filtered = [m for m in self._all_managers if q in m[1].lower() or q in m[2].lower()]
            if midx < len(filtered):
                data["o365_manager_id"] = filtered[midx][0]
                data["ad_manager_dn"] = self.ad.get_manager_dn(filtered[midx][2])

        # Selected O365 Groups
        data["o365_groups"] = [self._all_groups[i][0] for i in self._grp_lb.curselection()]
        # Selected AD Groups
        data["ad_groups"] = [self._all_ad_groups[i][1] for i in self._ad_grp_lb.curselection()]
        
        sku_id = self._license_skus.get(self.v_license.get())
        
        self._btn_create.configure(state="disabled", text="⌛  Processing...")
        threading.Thread(target=self._run_provisioning, args=(data, sku_id), daemon=True).start()

    def _run_provisioning(self, data, sku_id):
        log = []
        def _log(m): log.append(m); print(f"[Provisioning] {m}")

        # 1. AD Creation
        _log("Creating AD User...")
        ok, res = self.ad.create_user(data)
        if not ok:
            messagebox.showerror("AD Error", res)
            self.after(0, lambda: self._btn_create.configure(state="normal", text="🚀  Create Employee Account"))
            return
        sam = res
        _log(f"AD User created: {sam}")

        # 2. AD Groups
        for gdn in data.get("ad_groups", []):
            self.ad.add_user_to_group(sam, gdn)
        
        # 3. O365 Creation
        _log("Creating O365 User...")
        ok, uid, msg = self.o365.create_user(data)
        if not ok:
            messagebox.showerror("O365 Error", msg)
            self.after(0, lambda: self._btn_create.configure(state="normal", text="🚀  Create Employee Account"))
            return
        _log("O365 User created.")

        # 4. Wait for replication
        self.o365.wait_for_user_provisioned(uid)

        # 5. License
        if sku_id:
            _log("Assigning license...")
            self.o365.assign_license(uid, sku_id)

        # 6. Manager
        if data.get("o365_manager_id"):
            self.o365.set_manager(uid, data["o365_manager_id"])

        # 7. O365 Groups
        for gid in data.get("o365_groups", []):
            self.o365.add_to_group(uid, gid)

        # 8. MFA
        if self.v_mfa.get():
            _log("Enabling MFA...")
            self.o365.enable_mfa(uid)

        # 9. Email
        if self.v_personal_email.get().strip():
            _log("Sending welcome email...")
            from core.credential_manager import cred_manager
            pwd = cred_manager.get_password("it_email_pwd")
            if pwd:
                self.mail.send_welcome_email(DEFAULT_EMAIL_SENDER, pwd, self.v_personal_email.get().strip(), DEFAULT_EMAIL_CC, {**data, "sam_account_name": sam})

        # 10. Excel Log
        _log("Logging to SharePoint...")
        self.o365.log_to_excel("On-boarding", [
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            data["first_name"] + " " + data["last_name"],
            data["email"], sam, data["employee_id"], data["job_title"], data["department"]
        ])

        self.after(0, lambda: messagebox.showinfo("Success", f"Provisioning complete for {sam}"))
        self.after(0, self._on_back)
