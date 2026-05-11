import sys
import importlib
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

def check_python_package(import_name: str) -> bool:
    try:
        importlib.import_module(import_name)
        return True
    except ImportError:
        return False


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
                self.issues.append(f"Missing {pip_spec}")
                self._p(pct, f"[ERROR] Missing {pip_spec}")
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
