"""
core/dependency_checker.py
Checks and installs all required dependencies on startup.
"""

import subprocess
import sys
import importlib
import shutil
import json
from typing import Callable, List, Tuple

# (import_name, pip_install_spec)
PYTHON_DEPS: List[Tuple[str, str]] = [
    ("requests",    "requests>=2.31.0"),
    ("tkcalendar",  "tkcalendar>=1.6.1"),
    ("dotenv",      "python-dotenv>=1.0.0"),
    ("PIL",         "Pillow>=10.0.0"),
    ("keyring",     "keyring>=24.0.0"),
    ("msal",        "msal>=1.26.0"),
    ("ldap3",       "ldap3>=2.9.1"),
]


# ── Helpers ────────────────────────────────────────────────────────────────────

def _run(cmd_list: List[str], timeout: int = 60) -> Tuple[bool, str, str]:
    """Run a process without shell=True to avoid EDR blocks."""
    try:
        r = subprocess.run(
            cmd_list, capture_output=True, text=True,
            timeout=timeout
        )
        return r.returncode == 0, r.stdout.strip(), r.stderr.strip()
    except Exception as e:
        return False, "", str(e)


# ── Individual checks ──────────────────────────────────────────────────────────

def check_python_package(import_name: str) -> bool:
    try:
        importlib.import_module(import_name)
        return True
    except ImportError:
        return False


def install_python_package(pip_spec: str, log: Callable = print) -> bool:
    if getattr(sys, 'frozen', False):
        log(f"  [ERROR] Cannot install {pip_spec} in bundled EXE. Must be included in build.")
        return False

    log(f"  pip install {pip_spec} ...")
    cmd = [sys.executable, "-m", "pip", "install", pip_spec, "--quiet"]
    ok, out, err = _run(cmd, timeout=120)
    if not ok:
        log(f"  ERROR: {err or out}")
    return ok


# ── Dependency Check Orchestrator ──────────────────────────────────────────────

class DependencyCheck:
    """
    Runs all dependency checks, installs missing items.
    Uses callbacks so the GUI can display progress.
    """

    def __init__(
        self,
        progress_cb: Callable[[float, str], None] = None,
        log_cb: Callable[[str], None] = None,
    ):
        self.progress_cb = progress_cb or (lambda p, m: None)
        self.log_cb = log_cb or print
        self.issues:   List[str] = []
        self.warnings: List[str] = []

    def _p(self, pct: float, msg: str):
        self.progress_cb(pct, msg)
        self.log_cb(msg)

    def _check_python_packages(self, steps: int, current_step: int) -> int:
        for import_name, pip_spec in PYTHON_DEPS:
            current_step += 1
            pct = round(current_step / steps * 60)
            if check_python_package(import_name):
                self._p(pct, f"[OK] {pip_spec}")
            else:
                self._p(pct, f"[Installing] {pip_spec}")
                if install_python_package(pip_spec, self.log_cb):
                    self._p(pct, f"[OK] {pip_spec} installed")
                else:
                    self.issues.append(f"Failed to install {pip_spec}")
                    self._p(pct, f"[ERROR] Could not install {pip_spec}")
        return current_step

    def _check_o365_auth(self, steps: int, current_step: int) -> int:
        current_step += 1
        pct = round(current_step / steps * 80)
        self._p(pct, "Checking O365 authentication...")
        from core.credential_manager import cred_manager, SCOPES_GRAPH
        token = cred_manager.get_token(SCOPES_GRAPH)
        if token:
            self._p(pct, "[OK] O365 authenticated")
        else:
            self._p(pct, "[!] O365 login required")
        return current_step

    def run(self) -> Tuple[bool, List[str], List[str]]:
        """
        Returns (all_critical_ok, issues, warnings).
        """
        steps = len(PYTHON_DEPS) + 2
        step  = 0

        # ── Python packages ──────────────────────────────────────────
        step = self._check_python_packages(steps, step)

        # ── O365 Authentication (MSAL) ──────────────────────────────
        step = self._check_o365_auth(steps, step)

        self._p(100, "Dependency check complete")
        return len(self.issues) == 0, self.issues, self.warnings

        self._p(100, "Dependency check complete")
        return len(self.issues) == 0, self.issues, self.warnings
