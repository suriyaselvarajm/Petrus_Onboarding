import tkinter as tk
from tkinter import ttk, messagebox
from gui.styles import C, F
from core.settings_manager import sm

class SettingsForm(tk.Frame):
    def __init__(self, parent, on_back=None):
        super().__init__(parent, bg=C["bg"])
        self._on_back = on_back
        self._build_ui()

    def _build_ui(self):
        # Header
        header = tk.Frame(self, bg=C["bg"])
        header.pack(fill="x", padx=40, pady=(20, 0))

        if self._on_back:
            ttk.Button(header, text="←  Back to Home",
                       style="Secondary.TButton",
                       command=self._on_back).pack(side="left")

        tk.Label(header, text="⚙️  Application Settings",
                 bg=C["bg"], fg=C["text"], font=F["title"]).pack(side="left", padx=20)

        # Tabs
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=40, pady=20)

        self._build_email_tab()
        self._build_defaults_tab()
        self._build_ad_tab()
        self._build_lookups_tab()

        # Footer Actions
        footer = tk.Frame(self, bg=C["bg"])
        footer.pack(fill="x", padx=40, pady=(0, 20))

        self._save_btn = ttk.Button(footer, text="💾  Save Settings",
                                   style="Primary.TButton",
                                   command=self._on_save)
        self._save_btn.pack(side="right")

    def _build_email_tab(self):
        tab = tk.Frame(self.notebook, bg=C["surface"], padx=20, pady=20)
        self.notebook.add(tab, text=" 📧 Email Templates ")

        def _labeled_text(parent, label, key, height=5):
            tk.Label(parent, text=label, bg=C["surface"], fg=C["text"], font=F["subtitle_sm"]).pack(anchor="w", pady=(10, 2))
            txt = tk.Text(parent, height=height, font=F["mono"], bg=C["input_bg"], fg=C["text"], borderwidth=1, relief="solid", padx=10, pady=10)
            txt.insert("1.0", sm.get(key))
            txt.pack(fill="x")
            return txt

        def _labeled_entry(parent, label, key):
            tk.Label(parent, text=label, bg=C["surface"], fg=C["text"], font=F["subtitle_sm"]).pack(anchor="w", pady=(10, 2))
            var = tk.StringVar(value=sm.get(key))
            ttk.Entry(parent, textvariable=var, font=F["body"]).pack(fill="x")
            return var

        self.v_welcome_subject = _labeled_entry(tab, "Onboarding Email Subject", "welcome_email_subject")
        self.t_welcome_template = _labeled_text(tab, "Onboarding Email Template", "welcome_email_template", 8)
        
        self.v_offboarding_subject = _labeled_entry(tab, "Offboarding Email Subject", "offboarding_email_subject")
        self.t_offboarding_template = _labeled_text(tab, "Offboarding Email Template", "offboarding_email_template", 8)

    def _build_defaults_tab(self):
        tab = tk.Frame(self.notebook, bg=C["surface"], padx=20, pady=20)
        self.notebook.add(tab, text=" 📍 Default Values ")

        def _grid_entry(parent, label, key, row, col):
            tk.Label(parent, text=label, bg=C["surface"], fg=C["text_muted"], font=F["label"]).grid(row=row*2, column=col, sticky="w", pady=(10, 0))
            var = tk.StringVar(value=sm.get(key))
            ttk.Entry(parent, textvariable=var, font=F["body"]).grid(row=row*2+1, column=col, sticky="ew", padx=(0, 20), pady=(2, 10))
            return var

        grid = tk.Frame(tab, bg=C["surface"])
        grid.pack(fill="x")
        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)

        self.v_def_office = _grid_entry(grid, "Default Office", "default_office", 0, 0)
        self.v_def_street = _grid_entry(grid, "Default Street", "default_street", 0, 1)
        self.v_def_city = _grid_entry(grid, "Default City", "default_city", 1, 0)
        self.v_def_state = _grid_entry(grid, "Default State", "default_state", 1, 1)
        self.v_def_zip = _grid_entry(grid, "Default Zip", "default_zip", 2, 0)
        self.v_def_country = _grid_entry(grid, "Default Country", "default_country", 2, 1)

    def _build_ad_tab(self):
        tab = tk.Frame(self.notebook, bg=C["surface"], padx=20, pady=20)
        self.notebook.add(tab, text=" 🖥️ Active Directory ")

        tk.Label(tab, text="AD Domain (FQDN)", bg=C["surface"], fg=C["text_muted"], font=F["label"]).pack(anchor="w", pady=(10, 0))
        self.v_ad_domain = tk.StringVar(value=sm.get("ad_domain"))
        ttk.Entry(tab, textvariable=self.v_ad_domain, font=F["body"]).pack(fill="x", pady=(2, 10))

        tk.Label(tab, text="AD Server IP / DNS (Optional)", bg=C["surface"], fg=C["text_muted"], font=F["label"]).pack(anchor="w", pady=(10, 0))
        self.v_ad_server = tk.StringVar(value=sm.get("ad_server"))
        ttk.Entry(tab, textvariable=self.v_ad_server, font=F["body"]).pack(fill="x", pady=(2, 10))

    def _build_lookups_tab(self):
        tab = tk.Frame(self.notebook, bg=C["surface"], padx=20, pady=20)
        self.notebook.add(tab, text=" 🔍 Lookup Lists ")

        tk.Label(tab, text="Departments (One per line)", bg=C["surface"], fg=C["text"], font=F["subtitle_sm"]).pack(anchor="w", pady=(10, 2))
        self.t_departments = tk.Text(tab, height=12, font=F["body"], bg=C["input_bg"], fg=C["text"], borderwidth=1, relief="solid", padx=10, pady=10)
        deps = sm.get("departments", [])
        self.t_departments.insert("1.0", "\n".join(deps))
        self.t_departments.pack(fill="both", expand=True)

    def _on_save(self):
        # Email
        sm.set("welcome_email_subject", self.v_welcome_subject.get())
        sm.set("welcome_email_template", self.t_welcome_template.get("1.0", "end-1c"))
        sm.set("offboarding_email_subject", self.v_offboarding_subject.get())
        sm.set("offboarding_email_template", self.t_offboarding_template.get("1.0", "end-1c"))

        # Defaults
        sm.set("default_office", self.v_def_office.get())
        sm.set("default_street", self.v_def_street.get())
        sm.set("default_city", self.v_def_city.get())
        sm.set("default_state", self.v_def_state.get())
        sm.set("default_zip", self.v_def_zip.get())
        sm.set("default_country", self.v_def_country.get())

        # AD
        sm.set("ad_domain", self.v_ad_domain.get())
        sm.set("ad_server", self.v_ad_server.get())

        # Lookups
        deps = self.t_departments.get("1.0", "end-1c").strip().split("\n")
        deps = [d.strip() for d in deps if d.strip()]
        sm.set("departments", deps)

        ok, msg = sm.save()
        if ok:
            messagebox.showinfo("Success", msg)
        else:
            messagebox.showerror("Error", msg)
