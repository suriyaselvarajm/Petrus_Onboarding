"""
core/ad_service.py
Active Directory operations via PowerShell subprocess.
Designed for Windows domain-joined machines with RSAT tools installed.
"""

import subprocess
import json
from typing import Optional, List, Dict, Any, Tuple

from config import (
    AD_DOMAIN, AD_BASE_DN, AD_PETRUS_USERS_OU,
    COMPANY_NAME, DEFAULT_COUNTRY_CODE,
    AD_ADMIN_USER, AD_ADMIN_PASSWORD,
)


import os
import tempfile


ERROR_PREFIX = "ERROR:"

# ── PowerShell runner ──────────────────────────────────────────────────────────

def _ps(script: str, timeout: int = 45) -> Tuple[bool, str, str]:
    """
    Write script to a temp .ps1 file and run it with powershell -File.
    Using -File is far more reliable on Windows than passing multiline
    scripts via -Command (which has quoting/newline issues).
    """
    tmp_path = None
    
    # ── Inject explicit credentials if provided ──
    script_header = ""
    if AD_ADMIN_USER and AD_ADMIN_PASSWORD:
        script_header = f"""
        $sec_auth = ConvertTo-SecureString '{_esc(AD_ADMIN_PASSWORD)}' -AsPlainText -Force
        $cred_auth = New-Object System.Management.Automation.PSCredential ('{_esc(AD_ADMIN_USER)}', $sec_auth)
        $PSDefaultParameterValues = @{{ "*-AD*:Credential" = $cred_auth }}
        """

    full_script = script_header + script

    try:
        # Write script to a temp file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".ps1",
            delete=False, encoding="utf-8"
        ) as f:
            f.write(full_script)
            tmp_path = f.name

        r = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive",
             "-ExecutionPolicy", "Bypass", "-File", tmp_path],
            capture_output=True, text=True, timeout=timeout,
        )
        return r.returncode == 0, r.stdout.strip(), r.stderr.strip()

    except subprocess.TimeoutExpired:
        return False, "", f"PowerShell timed out after {timeout}s"
    except FileNotFoundError:
        return False, "", "powershell.exe not found — is this Windows?"
    except Exception as e:
        return False, "", str(e)
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass



def _esc(value: str) -> str:
    """Escape a value for use inside a PowerShell single-quoted string."""
    if not value:
        return ""
    return str(value).replace("'", "''")


def _clean_ps_err(raw: str) -> str:
    """
    Strips PowerShell noise from error output:
    temp file paths, CategoryInfo, FullyQualifiedErrorId, '+' lines.
    Returns just the human-readable first line of the exception.
    """
    if not raw:
        return "Unknown error"
    lines = []
    for line in raw.splitlines():
        stripped = line.strip()
        # Skip PS noise lines
        if any(stripped.startswith(x) for x in (
            "+ ", "At ", "CategoryInfo", "FullyQualifiedErrorId",
            "tmp", "C:\\Users",
        )):
            continue
        if stripped:
            lines.append(stripped)
    # Return first meaningful line
    clean = lines[0] if lines else raw.splitlines()[0]
    # Remove temp file name prefix like "tmpXXX.ps1 : "
    import re as _re
    clean = _re.sub(r'^tmp\w+\.ps1\s*:\s*', '', clean)
    clean = _re.sub(r'^.*\.ps1\s*:\s*', '', clean)
    return clean.strip() or "Cannot connect to AD domain"


# ── AD Service ─────────────────────────────────────────────────────────────────

class ADService:

    def __init__(self):
        self._connected = False

    # ── Connection ────────────────────────────────────────────────────────────

    def test_connection(self) -> Tuple[bool, str]:
        # Write-Output the error so it comes through stdout (clean, no stack trace)
        script = f"""
        try {{
            Import-Module ActiveDirectory -ErrorAction Stop
            $d = Get-ADDomain -Server '{AD_DOMAIN}' -ErrorAction Stop
            Write-Output "OK:$($d.DNSRoot)"
        }} catch {{
            Write-Output "ERR:$($_.Exception.Message)"
        }}
        """
        _, out, err = _ps(script, timeout=80)   # generous — first PS run is slow
        if out.startswith("OK:"):
            self._connected = True
            return True, out[3:]
        # Extract error from stdout ERR: prefix, fall back to stderr
        if out.startswith("ERR:"):
            return False, out[4:].strip()
        return False, _clean_ps_err(err or out)

    def check_ad_sync(self) -> Tuple[bool, str]:
        """Check if Azure AD Connect (ADSync) service is running."""
        script = """
        try {
            $s = Get-Service -Name ADSync -ErrorAction Stop
            Write-Output $s.Status
        } catch {
            Write-Output "NOT_INSTALLED"
        }
        """
        _, out, _ = _ps(script, timeout=20)
        running = "Running" in out
        return running, out

    # ── Query helpers ─────────────────────────────────────────────────────────

    def user_exists(self, sam: str) -> bool:
        script = f"""
        try {{
            Import-Module ActiveDirectory -ErrorAction Stop
            $u = Get-ADUser -Filter {{SamAccountName -eq '{_esc(sam)}'}} `
                 -Server '{AD_DOMAIN}' -ErrorAction Stop
            if ($u) {{ Write-Output 'EXISTS' }} else {{ Write-Output 'NO' }}
        }} catch {{ Write-Output 'NO' }}
        """
        _, out, _ = _ps(script)
        return "EXISTS" in out

    def get_ous(self, base: str = None) -> List[Dict]:
        """List OUs directly under Petrus Users OU."""
        search_base = base or AD_PETRUS_USERS_OU
        script = f"""
        try {{
            Import-Module ActiveDirectory -ErrorAction Stop
            $ous = Get-ADOrganizationalUnit -Filter * `
                       -SearchBase '{_esc(search_base)}' `
                       -Server '{AD_DOMAIN}' `
                       -SearchScope Subtree `
                       -Properties Name,DistinguishedName |
                   Select-Object Name,DistinguishedName |
                   ConvertTo-Json -Compress
            if ($ous) {{ Write-Output $ous }} else {{ Write-Output '[]' }}
        }} catch {{
            Write-Output '[]'
        }}
        """
        _, out, _ = _ps(script, timeout=40)
        try:
            data = json.loads(out)
            # Single object comes back as dict, not list
            if isinstance(data, dict):
                data = [data]
            return data
        except Exception:
            return []

    def get_groups(self, search_base: str = None) -> List[Dict]:
        """List AD groups under the Petrus Users OU subtree."""
        base = search_base or AD_PETRUS_USERS_OU
        script = f"""
        try {{
            Import-Module ActiveDirectory -ErrorAction Stop
            $grps = Get-ADGroup -Filter * `
                        -SearchBase '{_esc(base)}' `
                        -Server '{AD_DOMAIN}' `
                        -SearchScope Subtree `
                        -Properties Name,DistinguishedName,GroupCategory |
                    Select-Object Name,DistinguishedName,GroupCategory |
                    ConvertTo-Json -Compress
            if ($grps) {{ Write-Output $grps }} else {{ Write-Output '[]' }}
        }} catch {{ Write-Output '[]' }}
        """
        _, out, _ = _ps(script, timeout=40)
        try:
            data = json.loads(out)
            if isinstance(data, dict):
                data = [data]
            return data
        except Exception:
            return []

    def get_manager_dn(self, upn: str) -> Optional[str]:
        """Resolve a manager's UPN to their DistinguishedName."""
        script = f"""
        try {{
            Import-Module ActiveDirectory -ErrorAction Stop
            $u = Get-ADUser -Filter {{UserPrincipalName -eq '{_esc(upn)}'}} `
                 -Server '{AD_DOMAIN}'
            Write-Output $u.DistinguishedName
        }} catch {{ Write-Output '' }}
        """
        _, out, _ = _ps(script)
        return out if out else None

    def get_user_dn(self, sam: str) -> Optional[str]:
        script = f"""
        try {{
            Import-Module ActiveDirectory -ErrorAction Stop
            $u = Get-ADUser -Identity '{_esc(sam)}' -Server '{AD_DOMAIN}'
            Write-Output $u.DistinguishedName
        }} catch {{ Write-Output '' }}
        """
        _, out, _ = _ps(script)
        return out if out else None

    # ── Create User ───────────────────────────────────────────────────────────

    def create_user(self, data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Create a new AD user. Returns (success, sam_or_error_message).
        """
        first    = data["first_name"]
        last     = data["last_name"]
        email    = data["email"]
        display  = f"{first} {last}"
        sam      = f"{first.lower()}.{last.lower()}"[:20]
        ou       = data.get("ad_ou", AD_PETRUS_USERS_OU)
        password = data.get("password", "Welcome@123")
        manager_dn = data.get("ad_manager_dn", "")

        e = _esc   # alias for brevity

        manager_line = (
            f"-Manager '{e(manager_dn)}' `" if manager_dn else ""
        )

        script = f"""
        try {{
            Import-Module ActiveDirectory -ErrorAction Stop
            $pwd = ConvertTo-SecureString '{e(password)}' -AsPlainText -Force

            New-ADUser `
                -Name            '{e(display)}' `
                -GivenName       '{e(first)}' `
                -Surname         '{e(last)}' `
                -SamAccountName  '{e(sam)}' `
                -UserPrincipalName '{e(email)}' `
                -EmailAddress    '{e(email)}' `
                -DisplayName     '{e(display)}' `
                -Path            '{e(ou)}' `
                -AccountPassword $pwd `
                -ChangePasswordAtLogon $true `
                -Enabled         $true `
                -Title           '{e(data.get("job_title",""))}' `
                -Department      '{e(data.get("department",""))}' `
                -Office          '{e(data.get("office","Coimbatore"))}' `
                -MobilePhone     '{e(data.get("mobile",""))}' `
                -StreetAddress   '{e(data.get("street",""))}' `
                -City            '{e(data.get("city","Coimbatore"))}' `
                -State           '{e(data.get("state","Tamil Nadu"))}' `
                -PostalCode      '{e(data.get("zip","641006"))}' `
                -Country         'IN' `
                -Company         '{e(COMPANY_NAME)}' `
                -EmployeeID      '{e(data.get("employee_id",""))}' `
                -EmployeeNumber  '{e(data.get("employee_id",""))}' `
                {manager_line}
                -Server          '{AD_DOMAIN}' `
                -ErrorAction Stop

            # ── Set extended attributes ──────────────────────────────
            $user = Get-ADUser -Filter {{SamAccountName -eq '{e(sam)}'}} `
                        -Server '{AD_DOMAIN}' -ErrorAction Stop

            $attrs = @{{
                countryCode  = [int]{DEFAULT_COUNTRY_CODE};
                c            = 'IN';
                co           = 'India';
                employeeType = '{e(data.get("employee_type","Full Time"))}';
            }}
            Set-ADUser $user -Replace $attrs -Server '{AD_DOMAIN}'

            Write-Output 'SUCCESS:{e(sam)}'
        }} catch {{
            Write-Output "{ERROR_PREFIX}$($_.Exception.Message)"
        }}
        """
        _, out, err = _ps(script, timeout=90)
        if "SUCCESS:" in out:
            return True, sam
        msg = (err or out or "Unknown error").replace(ERROR_PREFIX, "").strip()
        return False, msg

    # ── Post-Creation ─────────────────────────────────────────────────────────

    def set_proxy_addresses(self, sam: str, email: str, employee_id: str) -> Tuple[bool, str]:
        domain = email.split("@")[1] if "@" in email else ""
        primary   = f"SMTP:{email}"
        secondary = f"smtp:{employee_id}@{domain}" if domain else ""
        addrs = f"'{primary}'" + (f",'{secondary}'" if secondary else "")

        script = f"""
        try {{
            Import-Module ActiveDirectory -ErrorAction Stop
            $user = Get-ADUser -Identity '{_esc(sam)}' -Server '{AD_DOMAIN}'
            Set-ADUser $user `
                -Replace @{{proxyAddresses=@({addrs})}} `
                -Server '{AD_DOMAIN}' `
                -ErrorAction Stop
            Write-Output 'SUCCESS'
        }} catch {{
            Write-Output "{ERROR_PREFIX}$($_.Exception.Message)"
        }}
        """
        _, out, err = _ps(script)
        ok = "SUCCESS" in out
        return ok, (err or out).replace(ERROR_PREFIX, "").strip()

    def add_to_group(self, sam: str, group_dn: str) -> Tuple[bool, str]:
        script = f"""
        try {{
            Import-Module ActiveDirectory -ErrorAction Stop
            Add-ADGroupMember `
                -Identity '{_esc(group_dn)}' `
                -Members  '{_esc(sam)}' `
                -Server   '{AD_DOMAIN}' `
                -ErrorAction Stop
            Write-Output 'SUCCESS'
        }} catch {{
            Write-Output "{ERROR_PREFIX}$($_.Exception.Message)"
        }}
        """
        _, out, err = _ps(script)
        ok = "SUCCESS" in out
        return ok, (err or out).replace(ERROR_PREFIX, "").strip()
