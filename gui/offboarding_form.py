"""
gui/offboarding_form.py
Form for decommission operations: user search, license removal, account blocking,
account disabling, and manager notification.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import datetime
from typing import Optional, List, Tuple, Dict, Any

from config import (
    COMPANY_NAME, DEFAULT_EMAIL_SENDER, DEFAULT_EMAIL_CC,
    OFFBOARDING_EMAIL_SUBJECT, OFFBOARDING_EMAIL_TEMPLATE
)
from core.mail_service import MailService
from core.credential_manager import save_password, get_password
from gui.styles import C, F

class OffboardingForm(tk.Frame):
    def __init__(self, parent, o365_service, ad_service, on_back=None):
        super().__init__(parent, bg=C["bg"])
        self.o365 = o365_service
        self.ad   = ad_service
        self.mail = MailService()
        self._on_back = on_back

        self._selected_user: Optional[Dict] = None
        self._build_ui()

    def _build_ui(self):
        # Header
        header = tk.Frame(self, bg=C["bg"])
        header.pack(fill="x", padx=40, pady=(20, 0))

        if self._on_back:
            ttk.Button(header, text="←  Back to Home",
                       style="Secondary.TButton",
                       command=self._on_back).pack(side="left")

        tk.Label(header, text="Employee Off-boarding",
                 bg=C["bg"], fg=C["text"], font=F["title"]).pack(side="left", padx=20)

        # Main container
        self._container = tk.Frame(self, bg=C["bg"])
        self._container.pack(fill="both", expand=True, padx=40, pady=20)

        # Left: Search & User Info
        self._left = tk.Frame(self._container, bg=C["bg"])
        self._left.pack(side="left", fill="both", expand=True, padx=(0, 20))

        self._build_search_section()
        self._build_info_section()

        # Right: Actions & Log
        self._right = tk.Frame(self._container, bg=C["bg"])
        self._right.pack(side="right", fill="both", expand=True)

        self._build_action_section()
        self._build_log_section()

    def _build_search_section(self):
        card = tk.Frame(self._left, bg=C["surface"], padx=20, pady=20)
        card.pack(fill="x", pady=(0, 20))

        tk.Label(card, text="Search User (Name or Email)",
                 bg=C["surface"], fg=C["text_muted"], font=F["label"]).pack(anchor="w")
        
        search_frame = tk.Frame(card, bg=C["surface"])
        search_frame.pack(fill="x", pady=(5, 0))

        self.v_search = tk.StringVar()
        self._search_entry = ttk.Entry(search_frame, textvariable=self.v_search, font=F["body"])
        self._search_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self._search_entry.bind("<Return>", lambda e: self._on_search())

        self._search_btn = ttk.Button(search_frame, text="Search", command=self._on_search)
        self._search_btn.pack(side="right")

        self._results_lb = tk.Listbox(card, font=F["body_sm"], height=5, 
                                      bg=C["surface2"], fg=C["text"], 
                                      highlightthickness=0, bd=0)
        self._results_lb.pack(fill="x", pady=(10, 0))
        self._results_lb.bind("<<ListboxSelect>>", self._on_user_select)
        self._results_lb.pack_forget() # Hide until results found

    def _build_info_section(self):
        self._info_card = tk.Frame(self._left, bg=C["surface"], padx=20, pady=20)
        self._info_card.pack(fill="both", expand=True)
        
        tk.Label(self._info_card, text="User Details",
                 bg=C["surface"], fg=C["text"], font=F["subtitle"]).pack(anchor="w", pady=(0, 10))

        self._info_lbl = tk.Label(self._info_card, text="Search and select a user to begin.",
                                  bg=C["surface"], fg=C["text_muted"], font=F["body"],
                                  justify="left", anchor="nw")
        self._info_lbl.pack(fill="both", expand=True)

    def _build_action_section(self):
        self._action_card = tk.Frame(self._right, bg=C["surface"], padx=20, pady=20)
        self._action_card.pack(fill="x", pady=(0, 20))


        # Action Checklist
        tk.Label(self._action_card, text="Select Actions to Perform",
                 bg=C["surface"], fg=C["text"], font=F["subtitle_sm"]).pack(anchor="w", pady=(0, 5))

        self.v_do_block   = tk.BooleanVar(value=True)
        self.v_do_license = tk.BooleanVar(value=True)
        self.v_do_delete  = tk.BooleanVar(value=False)
        self.v_do_ad      = tk.BooleanVar(value=True)
        self.v_do_ad_delete = tk.BooleanVar(value=False)
        self.v_do_mail    = tk.BooleanVar(value=True)

        def _cb(text, var):
            tk.Checkbutton(self._action_card, text=text, variable=var,
                           bg=C["surface"], fg=C["text"], activebackground=C["surface"],
                           selectcolor=C["accent_dim"], font=F["body_sm"]
                           ).pack(anchor="w", padx=5)

        _cb("Block O365 Sign-in", self.v_do_block)
        _cb("Remove O365 Licenses", self.v_do_license)
        _cb("Delete O365 User Account", self.v_do_delete)
        _cb("Disable AD Account", self.v_do_ad)
        _cb("Delete AD Account", self.v_do_ad_delete)
        _cb("Send Manager Notification", self.v_do_mail)

        tk.Frame(self._action_card, height=1, bg=C["border"]).pack(fill="x", pady=15)

        # Email section
        tk.Label(self._action_card, text="Notification Sender Details",
                 bg=C["surface"], fg=C["text"], font=F["subtitle_sm"]).pack(anchor="w", pady=(0, 5))

        self.v_mail_sender = tk.StringVar(value=DEFAULT_EMAIL_SENDER)
        tk.Label(self._action_card, text="Sender Email",
                 bg=C["surface"], fg=C["text_muted"], font=F["label"]).pack(anchor="w")
        ttk.Entry(self._action_card, textvariable=self.v_mail_sender, font=F["body_sm"]).pack(fill="x", pady=(2, 8))

        self.v_mail_pwd = tk.StringVar()
        pwd_sub = tk.Frame(self._action_card, bg=C["surface"])
        pwd_sub.pack(fill="x", pady=(2, 8))
        
        self._mail_pwd_entry = ttk.Entry(pwd_sub, textvariable=self.v_mail_pwd, font=F["body_sm"], show="●")
        self._mail_pwd_entry.pack(side="left", fill="x", expand=True)
        
        self._save_pwd_btn = ttk.Button(pwd_sub, text="💾", width=3,
                                        style="Secondary.TButton",
                                        command=self._save_mail_password)
        self._save_pwd_btn.pack(side="right", padx=(5, 0))

        self.v_cc = tk.StringVar(value=DEFAULT_EMAIL_CC)
        tk.Label(self._action_card, text="CC Email",
                 bg=C["surface"], fg=C["text_muted"], font=F["label"]).pack(anchor="w")
        ttk.Entry(self._action_card, textvariable=self.v_cc, font=F["body_sm"]).pack(fill="x", pady=(2, 10))

        self._btn_run = ttk.Button(self._action_card, text="🚀 Run Decommissioning", 
                                   state="disabled", command=self._on_run_actions)
        self._btn_run.pack(fill="x", pady=5)

    def _build_log_section(self):
        card = tk.Frame(self._right, bg=C["surface2"], padx=15, pady=15)
        card.pack(fill="both", expand=True)

        tk.Label(card, text="Process Log",
                 bg=C["surface2"], fg=C["text"], font=F["label"]).pack(anchor="w")

        self._log_txt = tk.Text(card, height=10, font=("Consolas", 9),
                                bg="#1a1a1a", fg="#d1d1d1", 
                                state="disabled", borderwidth=0, padx=10, pady=10)
        self._log_txt.pack(fill="both", expand=True, pady=(5, 0))

    # ── Logic ─────────────────────────────────────────────────────────────────

    def _log(self, message: str, success: bool = True):
        color = "#10b981" if success else "#ef4444"
        prefix = "✔" if success else "✘"
        self._log_txt.configure(state="normal")
        self._log_txt.insert("end", f"{prefix} {message}\n")
        self._log_txt.see("end")
        self._log_txt.configure(state="disabled")

    def _on_search(self):
        query = self.v_search.get().strip()
        if not query: return
        
        self._search_btn.configure(state="disabled")
        threading.Thread(target=self._run_search, args=(query,), daemon=True).start()

    def _run_search(self, query):
        users = self.o365.search_users_broad(query)
        self.after(0, lambda: self._show_results(users))

    def _show_results(self, users):
        self._search_btn.configure(state="normal")
        self._results_lb.delete(0, "end")
        self._found_users = users
        
        if not users:
            self._log("No users found.", False)
            self._results_lb.pack_forget()
            return

        for u in users:
            self._results_lb.insert("end", f"{u['displayName']} ({u['userPrincipalName']})")
        self._results_lb.pack(fill="x", pady=(10, 0))

    def _on_user_select(self, event):
        idx = self._results_lb.curselection()
        if not idx: return
        user = self._found_users[idx[0]]
        self._load_user_details(user["id"])

    def _load_user_details(self, user_id):
        threading.Thread(target=self._run_load_details, args=(user_id,), daemon=True).start()

    def _run_load_details(self, user_id):
        details = self.o365.get_user_details(user_id)
        self.after(0, lambda: self._apply_user_details(details))

    def _apply_user_details(self, details):
        self._selected_user = details
        info = (
            f"Name: {details.get('displayName')}\n"
            f"Email: {details.get('userPrincipalName')}\n"
            f"Emp ID: {details.get('employeeId', 'N/A')}\n"
            f"Title: {details.get('jobTitle', 'N/A')}\n"
            f"Dept: {details.get('department', 'N/A')}\n"
            f"Status: {'Active' if details.get('accountEnabled') else 'Blocked'}\n\n"
            f"Licenses: {len(details.get('_licenses', []))}\n"
            f"Manager: {details.get('_manager', {}).get('displayName', 'None')}"
        )
        self._info_lbl.configure(text=info, fg=C["text"])
        
        # Enable Run button
        self._btn_run.configure(state="normal")
        self._log(f"Selected user: {details.get('displayName')}")
        
        # Load saved password
        saved = get_password(self.v_mail_sender.get())
        if saved:
            self.v_mail_pwd.set(saved)

    def _save_mail_password(self):
        email = self.v_mail_sender.get().strip()
        pwd   = self.v_mail_pwd.get()
        if not email or not pwd:
            messagebox.showwarning("Warning", "Enter both email and password to save.")
            return
        save_password(email, pwd)
        messagebox.showinfo("Saved", "Password saved securely in Windows Vault.")

    def _on_run_actions(self):
        if not self._selected_user: return
        
        needs_confirm = self.v_do_delete.get() or self.v_do_ad_delete.get()
        
        if needs_confirm:
            # Special "Type DELETE" dialog
            confirm_win = tk.Toplevel(self)
            confirm_win.title("Confirm Deletion")
            confirm_win.geometry("400x260")
            confirm_win.configure(bg=C["surface"])
            confirm_win.transient(self.master)
            confirm_win.grab_set()
            
            tk.Label(confirm_win, text="❗ PERMANENT DELETION",
                     bg=C["surface"], fg=C["error"], font=F["subtitle"]).pack(pady=(20, 10))
            tk.Label(confirm_win, text=f"Type 'DELETE' to confirm removing\n{self._selected_user['displayName']}",
                     bg=C["surface"], fg=C["text"], font=F["body"]).pack(pady=5)
            
            v_conf = tk.StringVar()
            ent = ttk.Entry(confirm_win, textvariable=v_conf, font=F["body"])
            ent.pack(pady=10, padx=40, fill="x")
            ent.focus_set()
            
            def do_confirm():
                if v_conf.get().strip().upper() == "DELETE":
                    confirm_win.destroy()
                    self._start_execution()
                else:
                    messagebox.showerror("Error", "Confirmation text mismatch.")
            
            ttk.Button(confirm_win, text="Confirm Deletion", command=do_confirm).pack(pady=10)
        else:
            if messagebox.askyesno("Confirm Off-boarding", "Are you sure you want to perform the selected actions?"):
                self._start_execution()

    def _start_execution(self):
        self._btn_run.configure(state="disabled")
        threading.Thread(target=self._run_all_actions, daemon=True).start()

    def _run_all_actions(self):
        details = self._selected_user
        user_id = details["id"]
        upn     = details["userPrincipalName"]
        sam     = upn.split("@")[0]
        
        # 1. Block Sign-in
        if self.v_do_block.get():
            self.after(0, lambda: self._log("Blocking O365 sign-in..."))
            ok, msg = self.o365.block_sign_in(user_id, block=True)
            self.after(0, lambda: self._log(f"O365 Sign-in: {msg}", ok))

        # 2. Remove Licenses
        if self.v_do_license.get():
            licenses = details.get("_licenses", [])
            if licenses:
                self.after(0, lambda: self._log(f"Removing {len(licenses)} licenses..."))
                for lic in licenses:
                    sku_id = lic.get("skuId")
                    sku_name = lic.get("skuPartNumber", sku_id)
                    ok, msg = self.o365.remove_license(user_id, sku_id)
                    self.after(0, lambda: self._log(f"License {sku_name}: {msg}", ok))
            else:
                self.after(0, lambda: self._log("No licenses to remove."))

        # 3. Disable AD Account
        if self.v_do_ad.get() and not self.v_do_ad_delete.get():
            self.after(0, lambda: self._log("Disabling AD account..."))
            if self.ad.user_exists(sam):
                ok, msg = self.ad.disable_user(sam)
                self.after(0, lambda: self._log(f"AD Account: {msg}", ok))
            else:
                self.after(0, lambda: self._log(f"AD User '{sam}' not found.", False))

        # 3b. Delete AD Account
        if self.v_do_ad_delete.get():
            self.after(0, lambda: self._log("Deleting AD account..."))
            if self.ad.user_exists(sam):
                ok, msg = self.ad.delete_user(sam)
                self.after(0, lambda: self._log(f"AD Deletion: {msg}", ok))
            else:
                self.after(0, lambda: self._log(f"AD User '{sam}' not found.", False))

        # 4. Delete O365 Account (Do this LAST or before mail?)
        # Better do it after mail if mail is needed, but mail template uses the account info.
        # Actually, let's do mail first, then delete.
        
        # 5. Send Notification
        if self.v_do_mail.get():
            self._run_send_mail_internal()

        # 6. Delete O365 Account
        if self.v_do_delete.get():
            self.after(0, lambda: self._log("Deleting O365 account..."))
            ok, msg = self.o365.delete_user(user_id)
            self.after(0, lambda: self._log(f"O365 Deletion: {msg}", ok))

        self.after(0, lambda: self._btn_run.configure(state="normal"))

    def _run_send_mail_internal(self):
        details = self._selected_user
        mgr = details.get("_manager")
        if not mgr:
            self.after(0, lambda: self._log("Mail failed: No manager found.", False))
            return
        
        mgr_email = mgr.get("userPrincipalName") or mgr.get("mail")
        subject = OFFBOARDING_EMAIL_SUBJECT.format(name=details["displayName"])
        cc = self.v_cc.get().strip()
        sender = self.v_mail_sender.get().strip()
        pwd = self.v_mail_pwd.get().strip()
        
        if not pwd:
            self.after(0, lambda: self._log("Mail failed: Sender password missing.", False))
            return

        body = OFFBOARDING_EMAIL_TEMPLATE.format(
            manager_name=mgr.get("displayName", "Manager"),
            name=details["displayName"],
            email=details["userPrincipalName"],
            license_removed="Completed" if self.v_do_license.get() else "N/A",
            sign_in_blocked="Yes" if self.v_do_block.get() else "N/A",
            ad_disabled="Completed" if self.v_do_ad.get() else "N/A"
        )

        self.after(0, lambda: self._log("Sending manager notification..."))
        ok, msg = self.o365.send_mail(sender, pwd, mgr_email, subject, body, cc_email=cc)
        self.after(0, lambda: self._log(f"Notification: {msg}", ok))


