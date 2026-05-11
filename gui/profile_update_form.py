"""
gui/profile_update_form.py
Profile Update form — search for an existing employee and update their
Reporting Manager, Phone Number, Department, and Designation.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
from typing import Optional, Dict, Any

from gui.styles import C, F
from core.ad_service import ADService
from core.o365_service import O365Service
from core.settings_manager import sm
from config import DEPARTMENTS


class ProfileUpdateForm(tk.Frame):
    """
    Form to search an employee and update:
      - Reporting Manager
      - Phone Number
      - Department
      - Designation (Job Title)
    Updates are written to both Active Directory and Office 365.
    """

    def __init__(self, parent, o365: O365Service, ad: ADService, on_back=None, **kwargs):
        super().__init__(parent, bg=C["bg"], **kwargs)
        self.o365    = o365
        self.ad      = ad
        self.on_back = on_back

        self._selected_user: Optional[Dict[str, Any]] = None   # currently loaded user
        self._manager_dn:    str = ""                           # DN of chosen manager

        self._build()

    # ──────────────────────────────────────────────────────────────────────────
    # UI Construction
    # ──────────────────────────────────────────────────────────────────────────

    def _build(self):
        # ── Top bar ──────────────────────────────────────────────────────────
        topbar = tk.Frame(self, bg=C["surface"], pady=8)
        topbar.pack(fill="x", side="top")

        ttk.Button(topbar, text="← Back to Home",
                   style="Secondary.TButton",
                   command=self._go_back).pack(side="left", padx=16)

        tk.Label(topbar, text="Update Employee Profile",
                 bg=C["surface"], fg=C["text"],
                 font=("Segoe UI", 14, "bold")).pack(side="left", padx=8)

        # ── Scrollable body ───────────────────────────────────────────────────
        canvas = tk.Canvas(self, bg=C["bg"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        self._scroll_frame = tk.Frame(canvas, bg=C["bg"])
        self._scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=self._scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        def _on_mw(e):
            try:
                if canvas.winfo_exists():
                    canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
            except Exception:
                pass
        
        canvas.bind_all("<MouseWheel>", _on_mw)
        self.bind("<Destroy>", lambda _: self.unbind_all("<MouseWheel>"))

        body = self._scroll_frame
        body.columnconfigure(0, weight=1)

        # ── Search card ───────────────────────────────────────────────────────
        self._build_search_card(body)

        # ── Edit card ────────────────────────────────────────────────────────
        self._edit_card = self._build_section(body, "✏️  Update Fields")
        self._edit_card.grid_remove()

        # ── Status bar ───────────────────────────────────────────────────────
        self._status_var = tk.StringVar()
        status_bar = tk.Frame(self, bg=C["surface2"], height=32)
        status_bar.pack(fill="x", side="bottom")
        tk.Label(status_bar, textvariable=self._status_var,
                 bg=C["surface2"], fg=C["text_muted"], font=F["body_sm"]
                 ).pack(side="left", padx=14, pady=6)

    def _build_section(self, parent: tk.Frame, title: str) -> tk.Frame:
        card = tk.Frame(parent, bg=C["surface"], padx=20, pady=16,
                        relief="flat", bd=0)
        card.grid(sticky="ew", padx=32, pady=(0, 16))
        parent.columnconfigure(0, weight=1)
        tk.Label(card, text=title,
                 bg=C["surface"], fg=C["accent"],
                 font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0, 12))
        return card

    def _build_search_card(self, parent: tk.Frame):
        card = tk.Frame(parent, bg=C["surface"], padx=20, pady=16)
        card.grid(sticky="ew", padx=32, pady=(24, 16))
        parent.columnconfigure(0, weight=1)

        tk.Label(card, text="🔍  Search Employee",
                 bg=C["surface"], fg=C["accent"],
                 font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0, 10))

        row = tk.Frame(card, bg=C["surface"])
        row.pack(fill="x")

        self._search_var = tk.StringVar()
        search_entry = ttk.Entry(row, textvariable=self._search_var,
                                  font=F["body"], width=40)
        search_entry.pack(side="left", ipady=5, padx=(0, 10))
        search_entry.bind("<Return>", lambda _: self._do_search())
        search_entry.insert(0, "Enter name, username or email…")
        search_entry.bind("<FocusIn>",  lambda e: self._clear_placeholder(search_entry))
        search_entry.bind("<FocusOut>", lambda e: self._restore_placeholder(search_entry))

        ttk.Button(row, text="Search", style="Primary.TButton",
                   command=self._do_search).pack(side="left")

        self._search_result_frame = tk.Frame(card, bg=C["surface"])
        self._search_result_frame.pack(fill="x", pady=(10, 0))

    def _clear_placeholder(self, entry):
        if entry.get() == "Enter name, username or email…":
            entry.delete(0, "end")

    def _restore_placeholder(self, entry):
        if not entry.get():
            entry.insert(0, "Enter name, username or email…")

    # ──────────────────────────────────────────────────────────────────────────
    # Search logic
    # ──────────────────────────────────────────────────────────────────────────

    def _do_search(self):
        query = self._search_var.get().strip()
        if not query or query == "Enter name, username or email…":
            return
        self._set_status("Searching…")
        for w in self._search_result_frame.winfo_children():
            w.destroy()
        threading.Thread(target=self._search_thread, args=(query,), daemon=True).start()

    def _search_thread(self, query: str):
        results = self.ad.search_user(query)
        self.after(0, lambda: self._show_search_results(results))

    def _show_search_results(self, results):
        for w in self._search_result_frame.winfo_children():
            w.destroy()

        if not results:
            tk.Label(self._search_result_frame,
                     text="No users found.", bg=C["surface"],
                     fg=C["error"], font=F["body_sm"]).pack(anchor="w")
            self._set_status("No results found.")
            return

        self._set_status(f"Found {len(results)} user(s). Click one to load.")

        listbox = tk.Listbox(self._search_result_frame, font=F["body"],
                             bg=C["surface2"], fg=C["text"],
                             selectbackground=C["accent"], selectforeground="#ffffff",
                             relief="flat", bd=0, height=min(len(results), 6),
                             activestyle="none")
        listbox.pack(fill="x", pady=(4, 0))

        for u in results:
            listbox.insert("end", f"  {u['displayName']}  —  {u['mail']}  ({u['sAMAccountName']})")

        listbox.bind("<<ListboxSelect>>",
                     lambda e: self._load_user(results[listbox.curselection()[0]])
                     if listbox.curselection() else None)

    # ──────────────────────────────────────────────────────────────────────────
    # Load selected user
    # ──────────────────────────────────────────────────────────────────────────

    def _load_user(self, user: Dict[str, Any]):
        self._selected_user = user
        self._manager_dn    = user.get("manager_dn", "")

        # Build / refresh the edit card
        self._build_edit_card(user)
        self._edit_card.grid()

        self._set_status(f"Loaded: {user['displayName']}")

    # ──────────────────────────────────────────────────────────────────────────
    # Edit card
    # ──────────────────────────────────────────────────────────────────────────

    def _build_edit_card(self, user: Dict[str, Any]):
        # Clear previous content (keep title label)
        for w in list(self._edit_card.winfo_children())[1:]:
            w.destroy()

        grid = tk.Frame(self._edit_card, bg=C["surface"])
        grid.pack(fill="x")
        grid.columnconfigure(1, weight=1)

        def lbl(text, row):
            tk.Label(grid, text=text, bg=C["surface"], fg=C["text_muted"],
                     font=F["body_sm"], anchor="e", width=18
                     ).grid(row=row, column=0, sticky="e", pady=6, padx=(0, 10))

        # ── Read-only Fields ─────────────────────────────────────────────────
        lbl("Name", 0)
        tk.Label(grid, text=user.get("displayName", ""), bg=C["surface"], fg=C["text"],
                 font=F["body"], anchor="w").grid(row=0, column=1, sticky="w", pady=6)

        lbl("Email ID", 1)
        tk.Label(grid, text=user.get("mail", ""), bg=C["surface"], fg=C["text"],
                 font=F["body"], anchor="w").grid(row=1, column=1, sticky="w", pady=6)

        lbl("Employee Number", 2)
        tk.Label(grid, text=user.get("employeeID", "(not set)"), bg=C["surface"], fg=C["text"],
                 font=F["body"], anchor="w").grid(row=2, column=1, sticky="w", pady=6)

        ttk.Separator(grid).grid(row=3, column=0, columnspan=2, sticky="ew", pady=(8, 12))

        # ── Editable Fields ──────────────────────────────────────────────────
        lbl("Designation / Title *", 4)
        self.v_title = tk.StringVar(value=user.get("title", ""))
        ttk.Entry(grid, textvariable=self.v_title, font=F["body"]
                  ).grid(row=4, column=1, sticky="ew", ipady=4)

        lbl("Department *", 5)
        self.v_dept = tk.StringVar(value=user.get("department", ""))
        ttk.Combobox(grid, textvariable=self.v_dept, values=sm.get("departments"), font=F["body"]
                  ).grid(row=5, column=1, sticky="ew")

        lbl("Mobile Number", 6)
        self.v_phone = tk.StringVar(value=user.get("mobile", ""))
        ttk.Entry(grid, textvariable=self.v_phone, font=F["body"]
                  ).grid(row=6, column=1, sticky="ew", ipady=4)

        lbl("Reporting Manager", 7)
        mgr_row = tk.Frame(grid, bg=C["surface"])
        mgr_row.grid(row=7, column=1, sticky="ew")
        mgr_row.columnconfigure(0, weight=1)

        self.v_manager_display = tk.StringVar(value=user.get("manager_name", ""))
        mgr_entry = ttk.Entry(mgr_row, textvariable=self.v_manager_display,
                               font=F["body"])
        mgr_entry.grid(row=0, column=0, sticky="ew", ipady=4)
        mgr_entry.bind("<Return>", lambda _: self._search_manager(self.v_manager_display.get()))

        ttk.Button(mgr_row, text="Find",
                   style="Secondary.TButton",
                   command=lambda: self._search_manager(self.v_manager_display.get())
                   ).grid(row=0, column=1, padx=(6, 0))

        # Manager result listbox (hidden by default)
        self._mgr_listbox_frame = tk.Frame(grid, bg=C["surface"])
        self._mgr_listbox_frame.grid(row=8, column=1, sticky="ew")

        # ── Divider ───────────────────────────────────────────────────────────
        ttk.Separator(self._edit_card).pack(fill="x", pady=12)

        # ── Action buttons ────────────────────────────────────────────────────
        btn_row = tk.Frame(self._edit_card, bg=C["surface"])
        btn_row.pack(anchor="e")

        self._progress_var = tk.DoubleVar()
        self._progress_bar = ttk.Progressbar(self._edit_card,
                                              variable=self._progress_var,
                                              maximum=100, length=400,
                                              mode="determinate")
        self._progress_bar.pack(fill="x", pady=(0, 8))
        self._progress_bar.pack_forget()   # hidden initially

        ttk.Button(btn_row, text="💾  Save Changes",
                   style="Primary.TButton",
                   command=self._save).pack(side="right", padx=(8, 0))
        ttk.Button(btn_row, text="↩  Reset",
                   style="Secondary.TButton",
                   command=lambda: self._load_user(self._selected_user)
                   ).pack(side="right")

    # ──────────────────────────────────────────────────────────────────────────
    # Manager search
    # ──────────────────────────────────────────────────────────────────────────

    def _search_manager(self, query: str):
        query = query.strip()
        if not query:
            return
        self._set_status("Searching for manager…")
        threading.Thread(target=self._manager_search_thread,
                         args=(query,), daemon=True).start()

    def _manager_search_thread(self, query: str):
        results = self.ad.search_user(query)
        self.after(0, lambda: self._show_manager_results(results))

    def _show_manager_results(self, results):
        for w in self._mgr_listbox_frame.winfo_children():
            w.destroy()

        if not results:
            self._set_status("No matching managers found.")
            return

        lb = tk.Listbox(self._mgr_listbox_frame, font=F["body_sm"],
                        bg=C["surface2"], fg=C["text"],
                        selectbackground=C["accent"], selectforeground="#ffffff",
                        relief="flat", bd=0,
                        height=min(len(results), 5), activestyle="none")
        lb.pack(fill="x")

        for u in results:
            lb.insert("end", f"  {u['displayName']}  ({u['sAMAccountName']})")

        def pick(event):
            idx = lb.curselection()
            if not idx:
                return
            chosen = results[idx[0]]
            self._manager_dn = chosen.get("distinguishedName", "")
            self.v_manager_display.set(chosen.get("displayName", ""))
            lb.destroy()
            self._set_status(f"Manager set to: {chosen['displayName']}")

        lb.bind("<<ListboxSelect>>", pick)
        self._set_status(f"Found {len(results)} potential manager(s). Click to select.")

    # ──────────────────────────────────────────────────────────────────────────
    # Save
    # ──────────────────────────────────────────────────────────────────────────

    def _save(self):
        if not self._selected_user:
            messagebox.showwarning("No User", "Please search and select a user first.")
            return

        changes = {
            "title":      self.v_title.get().strip(),
            "department": self.v_dept.get().strip(),
            "mobile":     self.v_phone.get().strip(),   # writes to AD 'mobile' (Telephones tab)
        }
        if self._manager_dn:
            changes["manager_dn"] = self._manager_dn

        self._progress_bar.pack(fill="x", pady=(0, 8))
        self._progress_var.set(10)
        self._set_status("Updating Active Directory…")

        threading.Thread(target=self._save_thread, args=(changes,), daemon=True).start()

    def _save_thread(self, changes: Dict):
        sam = self._selected_user["sAMAccountName"]
        upn = self._selected_user.get("userPrincipalName", "")

        # 1. Update AD (title, department, mobile, manager)
        ok_ad, msg_ad = self.ad.update_user_profile(sam, changes)
        self.after(0, lambda: self._progress_var.set(50))

        # 2. Update O365 via Graph API (title, department, mobilePhone)
        # Note: manager is NOT updated in O365 — it syncs automatically from AD via AD Connect.
        ok_o365, msg_o365 = False, "Skipped"
        try:
            if upn:
                patch = {}
                if changes.get("title"):      patch["jobTitle"]    = changes["title"]
                if changes.get("department"): patch["department"]  = changes["department"]
                if changes.get("mobile"):     patch["mobilePhone"] = changes["mobile"]
                if patch:
                    r = self.o365._patch(
                        f"https://graph.microsoft.com/v1.0/users/{upn}", patch)
                    ok_o365  = r.status_code in (200, 204)
                    msg_o365 = "Updated" if ok_o365 else r.text[:120]
                else:
                    ok_o365, msg_o365 = True, "Nothing to update in O365"
            else:
                msg_o365 = "No UPN — O365 update skipped"
        except Exception as e:
            msg_o365 = str(e)

        self.after(0, lambda: self._progress_var.set(100))
        self.after(0, lambda: self._on_save_done(ok_ad, msg_ad, ok_o365, msg_o365))

    def _on_save_done(self, ok_ad, msg_ad, ok_o365, msg_o365):
        self._progress_bar.pack_forget()

        ad_icon  = "✅" if ok_ad   else "❌"
        o365_icon = "✅" if ok_o365 else "⚠️"

        summary = (
            f"AD:   {ad_icon}  {msg_ad}\n"
            f"O365: {o365_icon}  {msg_o365}"
        )
        if ok_ad:
            messagebox.showinfo("Profile Updated", summary)
            # Refresh the display
            threading.Thread(
                target=lambda: self._reload_user(self._selected_user["sAMAccountName"]),
                daemon=True).start()
        else:
            messagebox.showerror("Update Failed", summary)

        self._set_status("Done.")

    def _reload_user(self, sam: str):
        results = self.ad.search_user(sam)
        if results:
            self.after(0, lambda: self._load_user(results[0]))

    # ──────────────────────────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────────────────────────

    def _set_status(self, text: str):
        try:
            self._status_var.set(text)
        except Exception:
            pass

    def _go_back(self):
        if self.on_back:
            self.on_back()
