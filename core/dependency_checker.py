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
]


# ── Helpers ────────────────────────────────────────────────────────────────────

def _run(cmd: str, timeout: int = 60) -> Tuple[bool, str, str]:
    """Run a shell command; returns (ok, stdout, stderr)."""
    try:
        r = subprocess.run(
            cmd, capture_output=True, text=True,
            timeout=timeout, shell=True
        )
        return r.returncode == 0, r.stdout.strip(), r.stderr.strip()
    except subprocess.TimeoutExpired:
        return False, "", "Timed out"
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
    log(f"  pip install {pip_spec} ...")
    ok, out, err = _run(
        f'"{sys.executable}" -m pip install "{pip_spec}" --quiet',
        timeout=120
    )
    if not ok:
        log(f"  ERROR: {err or out}")
    return ok


def check_azure_cli() -> bool:
    return shutil.which("az") is not None


def check_az_logged_in() -> bool:
    ok, out, _ = _run("az account show --output json", timeout=15)
    try:
        return ok and bool(json.loads(out).get("id"))
    except Exception:
        return False


def do_az_login() -> None:
    """Open a new console window for az login."""
    try:
        # Disable WAM to force standard browser login (allows picking account)
        subprocess.run("az config set core.authenticate_using_wam=false", shell=True, capture_output=True)
        subprocess.Popen(
            "az login",
            shell=True,
            creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0),
        )
    except Exception:
        pass


def check_ps_ad_module() -> bool:
    script = (
        'if (Get-Module -ListAvailable -Name ActiveDirectory) '
        '{ exit 0 } else { exit 1 }'
    )
    ok, _, _ = _run(f'powershell -NoProfile -Command "{script}"', timeout=20)
    return ok


def install_rsat(log: Callable = print) -> bool:
    log("  Installing RSAT: Active Directory tools (requires admin)...")
    cmd = (
        'powershell -NoProfile -Command '
        '"Add-WindowsCapability -Online -Name Rsat.ActiveDirectory.DS-LDS.Tools~~~~0.0.1.0"'
    )
    ok, out, err = _run(cmd, timeout=180)
    if not ok:
        log(f"  WARNING: {err or out}")
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

    def _check_azure_cli(self, steps: int, current_step: int) -> int:
        current_step += 1
        pct = round(current_step / steps * 80)
        self._p(pct, "Checking Azure CLI...")
        if check_azure_cli():
            self._p(pct, "[OK] Azure CLI found")
        else:
            self._p(pct, "[ERROR] Azure CLI not installed")
            self.issues.append(
                "Azure CLI not installed. Run setup.bat or download from "
                "https://aka.ms/installazurecliwindows"
            )
        return current_step

    def _check_ps_ad_module(self) -> None:
        self._p(85, "Checking PowerShell ActiveDirectory module...")
        if check_ps_ad_module():
            self._p(87, "[OK] PowerShell ActiveDirectory module present")
        else:
            self._p(87, "[!] AD module missing — attempting RSAT install...")
            if install_rsat(self.log_cb):
                self._p(90, "[OK] RSAT installed")
            else:
                self.warnings.append(
                    "RSAT AD tools not installed. AD operations will fail.\n"
                    "Enable via: Settings › Optional Features › RSAT: Active Directory"
                )

    def _check_azure_login(self) -> None:
        self._p(95, "Checking Azure CLI authentication...")
        if check_az_logged_in():
            self._p(97, "[OK] Azure CLI authenticated")
        else:
            self._p(97, "[!] Not logged in — browser will open for Azure login")
            self.warnings.append(
                "Azure CLI login required — secure browser will open automatically."
            )

    def run(self) -> Tuple[bool, List[str], List[str]]:
        """
        Returns (all_critical_ok, issues, warnings).
        """
        steps = len(PYTHON_DEPS) + 3
        step  = 0

        # ── Python packages ──────────────────────────────────────────
        step = self._check_python_packages(steps, step)

        # ── Azure CLI ────────────────────────────────────────────────
        step = self._check_azure_cli(steps, step)

        # ── PowerShell AD module ─────────────────────────────────────
        self._check_ps_ad_module()

        # ── Azure CLI login ──────────────────────────────────────────
        self._check_azure_login()

        self._p(100, "Dependency check complete")
        return len(self.issues) == 0, self.issues, self.warnings
