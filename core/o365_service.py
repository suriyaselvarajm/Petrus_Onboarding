"""
core/o365_service.py
Microsoft 365 operations via Microsoft Graph REST API.
Authentication: Azure CLI token (az account get-access-token).
No App Registration needed — uses the logged-in admin's credentials.
"""

import subprocess
import json
import time
import requests
from typing import Optional, Dict, Any, List, Tuple

from config import (
    GRAPH_BASE, GRAPH_BETA, GRAPH_RESOURCE,
    ZOHO_APP_NAME, EMAIL_DOMAIN, COMPANY_NAME,
    LICENSE_SKU_MAP, ZOHO_APP_OBJECT_ID,
)


# ── Token acquisition ──────────────────────────────────────────────────────────

def _fetch_az_token() -> Optional[str]:
    """Get a Graph API access token from Azure CLI."""
    try:
        r = subprocess.run(
            f'az account get-access-token --resource "{GRAPH_RESOURCE}" --output json',
            capture_output=True, text=True, timeout=30, shell=True,
        )
        if r.returncode == 0:
            return json.loads(r.stdout).get("accessToken")
    except Exception:
        pass
    return None


# ── O365 Service ───────────────────────────────────────────────────────────────

class O365Service:

    def __init__(self):
        self._token: Optional[str] = None
        self._token_expiry: float = 0.0

    # ── Auth ──────────────────────────────────────────────────────────────────

    def _token_valid(self) -> bool:
        return bool(self._token) and time.time() < self._token_expiry - 60

    def _refresh_token(self) -> None:
        self._token = _fetch_az_token()
        self._token_expiry = time.time() + 3600

    def _headers(self) -> Dict[str, str]:
        if not self._token_valid():
            self._refresh_token()
        return {
            "Authorization": f"Bearer {self._token or ''}",
            "Content-Type": "application/json",
        }

    def _get(self, url: str, params: Dict = None, extra_headers: Dict = None) -> requests.Response:
        h = self._headers()
        if extra_headers:
            h.update(extra_headers)
        return requests.get(url, headers=h, params=params, timeout=15)

    def _post(self, url: str, body: Dict) -> requests.Response:
        return requests.post(url, headers=self._headers(), json=body, timeout=20)

    def _patch(self, url: str, body: Dict) -> requests.Response:
        return requests.patch(url, headers=self._headers(), json=body, timeout=20)

    def _put(self, url: str, body: Dict) -> requests.Response:
        return requests.put(url, headers=self._headers(), json=body, timeout=20)

    # ── Connection ────────────────────────────────────────────────────────────

    def test_connection(self) -> Tuple[bool, str]:
        try:
            r = self._get(f"{GRAPH_BASE}/me")
            if r.status_code == 200:
                return True, r.json().get("userPrincipalName", "Connected")
            if r.status_code == 401:
                return False, "Not authenticated — run 'az login'"
            return False, f"HTTP {r.status_code}"
        except Exception as e:
            return False, str(e)

    def get_tenant_info(self) -> Dict:
        try:
            r = self._get(f"{GRAPH_BASE}/organization",
                          params={"$select": "displayName,id"})
            if r.status_code == 200:
                orgs = r.json().get("value", [])
                return orgs[0] if orgs else {}
        except Exception:
            pass
        return {}

    # ── User Checks ───────────────────────────────────────────────────────────

    def email_exists(self, email: str) -> bool:
        try:
            r = self._get(f"{GRAPH_BASE}/users/{email}")
            return r.status_code == 200
        except Exception:
            return False

    # ── Fetch Data ────────────────────────────────────────────────────────────

    def get_users(self, search: str = "") -> List[Dict]:
        users = []
        try:
            params: Dict[str, Any] = {
                "$select": "id,displayName,userPrincipalName,jobTitle",
                "$top": 999,
            }
            extra = {}
            if search:
                params["$search"] = f'"displayName:{search}"'
                extra["ConsistencyLevel"] = "eventual"
            
            url = f"{GRAPH_BASE}/users"
            while url:
                r = self._get(url, params=params, extra_headers=extra)
                if r.status_code == 200:
                    data = r.json()
                    users.extend(data.get("value", []))
                    url = data.get("@odata.nextLink")
                    params = None  # query params are embedded in nextLink
                else:
                    break
        except Exception:
            pass
        return users

    def get_groups(self) -> List[Dict]:
        """Fetch ALL O365 groups AND Distribution Lists from the tenant."""
        groups: List[Dict] = []
        url: Optional[str] = (
            f"{GRAPH_BASE}/groups"
            "?$select=id,displayName,groupTypes,mailEnabled,securityEnabled,onPremisesSyncEnabled&$top=999"
        )
        try:
            while url:
                r = self._get(url)
                if r.status_code == 200:
                    data = r.json()
                    for g in data.get("value", []):
                        # Tag each group with its type for display
                        is_unified  = "Unified" in g.get("groupTypes", [])
                        is_mail     = g.get("mailEnabled", False)
                        is_security = g.get("securityEnabled", False)
                        is_synced   = g.get("onPremisesSyncEnabled", False)

                        if is_unified:
                            g["_type"] = "M365 Group"
                        elif is_mail and not is_security:
                            g["_type"] = "Distribution List"
                        elif is_mail and is_security:
                            g["_type"] = "Mail-Sec Group"
                        else:
                            g["_type"] = "Security Group"

                        if is_synced:
                            g["_type"] += " (AD Synced)"

                        groups.append(g)
                    url = data.get("@odata.nextLink")
                else:
                    break
        except Exception:
            pass
        return groups

    def get_distribution_lists(self) -> List[Dict]:
        """Fetch only Distribution Lists (mail-enabled, not security-enabled, not Unified)."""
        dls: List[Dict] = []
        url: Optional[str] = (
            f"{GRAPH_BASE}/groups"
            "?$select=id,displayName,groupTypes,mailEnabled,securityEnabled"
            "&$filter=mailEnabled eq true and securityEnabled eq false"
            "&$top=999"
        )
        try:
            while url:
                r = self._get(url)
                if r.status_code == 200:
                    data = r.json()
                    for g in data.get("value", []):
                        if "Unified" not in g.get("groupTypes", []):
                            g["_type"] = "Distribution List"
                            dls.append(g)
                    url = data.get("@odata.nextLink")
                else:
                    break
        except Exception:
            pass
        return dls

    def get_license_skus(self) -> List[Dict]:
        try:
            r = self._get(f"{GRAPH_BASE}/subscribedSkus")
            if r.status_code == 200:
                return r.json().get("value", [])
        except Exception:
            pass
        return []

    # ── User Creation ─────────────────────────────────────────────────────────

    def create_user(self, data: Dict[str, Any]) -> Tuple[bool, str, str]:
        """
        POST /users — returns (success, user_id, message).
        """
        first = data["first_name"]
        last  = data["last_name"]
        email = data["email"]
        sam   = f"{first.lower()}.{last.lower()}"

        emp_id = data.get("employee_id", "")

        body: Dict[str, Any] = {
            "accountEnabled":   True,
            "displayName":      f"{first} {last}",
            "givenName":        first,
            "surname":          last,
            "userPrincipalName": email,
            "mailNickname":     data.get("mail_nickname", sam[:48]),
            # NOTE: proxyAddresses is read-only via Graph API on user creation.
            # Proxy addresses (SMTP primary + smtp:empID alias) are set in AD only.
            "passwordProfile": {
                "forceChangePasswordNextSignIn": data.get("force_change_pwd", True),
                "password": data.get("password", "Welcome@123"),
            },
            "jobTitle":         data.get("job_title", ""),
            "department":       data.get("department", ""),
            "officeLocation":   data.get("office", "Coimbatore"),
            "mobilePhone":      data.get("mobile", ""),
            "streetAddress":    data.get("street", ""),
            "city":             data.get("city", "Coimbatore"),
            "state":            data.get("state", "Tamil Nadu"),
            "postalCode":       data.get("zip", "641006"),
            "country":          data.get("country", "India"),
            "companyName":      COMPANY_NAME,
            "employeeId":       emp_id,
            "employeeType":     data.get("employee_type", "Employee"),
            "usageLocation":    "IN",
        }

        # Hire date (ISO 8601) — only if provided
        if data.get("hire_date_iso"):
            body["employeeHireDate"] = data["hire_date_iso"]

        # Strip empty strings to avoid Graph validation errors
        body = {k: v for k, v in body.items() if v != "" and v is not None}

        try:
            r = self._post(f"{GRAPH_BASE}/users", body)
            if r.status_code == 201:
                user_id = r.json().get("id", "")
                return True, user_id, "User created successfully"
            err = r.json().get("error", {}).get("message", r.text[:300])
            return False, "", err
        except Exception as e:
            return False, "", str(e)

    # ── Post-Creation Steps ───────────────────────────────────────────────────

    def wait_for_user_provisioned(self, user_id: str,
                                  max_wait: int = 60) -> Tuple[bool, str]:
        """
        Poll GET /users/{id} until the new user is visible in Graph API.
        Azure AD replication can take 5-30 seconds.
        Returns (True, "") when ready, or (False, reason) on timeout.
        """
        url = f"{GRAPH_BASE}/users/{user_id}?$select=id,userPrincipalName"
        for attempt in range(max_wait // 5):
            try:
                r = self._get(url)
                if r.status_code == 200:
                    return True, ""
            except Exception:
                pass
            time.sleep(5)
        return False, f"User not visible in Graph after {max_wait}s — proceeding anyway"

    def wait_for_mailbox(self, user_id: str,
                         max_wait: int = 180) -> Tuple[bool, str]:
        """
        Poll until the Exchange Online mailbox is provisioned.
        The mailbox ONLY becomes available after the license (with Exchange) is
        applied and Azure's background provisioning completes — typically 1-3 min.
        Returns (True, "") when ready, or (False, reason) on timeout.
        """
        url = f"{GRAPH_BASE}/users/{user_id}/mailboxSettings"
        for attempt in range(max_wait // 10):
            try:
                r = self._get(url)
                # 200 = mailbox ready; 404/400 = not yet provisioned
                if r.status_code == 200:
                    return True, ""
                # MailboxNotEnabledForRESTAPI → still provisioning
            except Exception:
                pass
            time.sleep(10)
        return False, (
            f"Exchange mailbox not ready after {max_wait}s — "
            "groups & aliases may need to be set manually in M365 admin."
        )

    def _ensure_usage_location(self, user_id: str, location: str = "IN") -> None:
        """
        PATCH usageLocation on the user object.
        Graph's assignLicenses action silently requires usageLocation to be
        confirmed on the object even when it was set at creation time.
        This is the most common cause of 'HTTP method not allowed' on license calls.
        """
        try:
            self._patch(f"{GRAPH_BASE}/users/{user_id}",
                        {"usageLocation": location})
        except Exception:
            pass  # best-effort; we still attempt the license assignment

    def _get_upn(self, user_id: str) -> Optional[str]:
        """Resolve an object ID to its userPrincipalName."""
        try:
            r = self._get(f"{GRAPH_BASE}/users/{user_id}?$select=userPrincipalName")
            if r.status_code == 200:
                return r.json().get("userPrincipalName")
        except Exception:
            pass
        return None

    def assign_license(self, user_id: str, sku_id: str) -> Tuple[bool, str]:
        """
        Assign a license robustly:
          1. PATCH usageLocation first (required by Graph before assignLicenses).
          2. Try using object-ID; if that keeps failing, fall back to UPN.
          3. Retry up to 4× with exponential back-off.
        """
        # Step 1 — ensure usageLocation is confirmed on the object
        self._ensure_usage_location(user_id)
        time.sleep(3)   # brief pause for the PATCH to propagate

        body     = {"addLicenses": [{"skuId": sku_id}], "removeLicenses": []}
        delays   = [8, 20, 35, 50]   # seconds between retries
        last_err = ""
        upn      = None   # fetched lazily on first identifier fallback

        for i, delay in enumerate([0] + delays):
            if delay:
                time.sleep(delay)

            # Choose identifier: prefer object-ID; fall back to UPN after attempt 2
            if i >= 2 and upn is None:
                upn = self._get_upn(user_id)
            identifier = upn if (i >= 2 and upn) else user_id

            try:
                r = self._post(
                    f"{GRAPH_BASE}/users/{identifier}/assignLicense", body
                )
                if r.status_code == 200:
                    tag = f" via UPN (attempt {i+1})" if (identifier == upn) else (
                          f" (attempt {i+1})" if i else "")
                    return True, f"License assigned{tag}"

                err_body = {}
                try:
                    err_body = r.json()
                except Exception:
                    pass
                last_err = err_body.get("error", {}).get("message", r.text[:200])

                # Stop retrying on unrecoverable errors
                if any(x in last_err.lower() for x in
                       ("already", "authorization", "forbidden",
                        "does not exist", "invalid")):
                    break
            except Exception as e:
                last_err = str(e)

        return False, f"License assignment failed after {len(delays)+1} attempts: {last_err}"

    def enable_mfa(self, user_id: str) -> Tuple[bool, str]:
        """
        Enable MFA for the user using up to 4 progressive methods:

        1. PATCH /beta/users/{id}/authentication/requirements  (modern Graph)
        2. PATCH /beta/users/{id} strongAuthenticationRequirements  (legacy Graph)
        3. az rest — uses Azure CLI's native auth context (often more permissive)
        4. MSOnline PowerShell — Set-MsolUser (works on most tenants)

        Only returns "enforced via Security Defaults" if SD is explicitly confirmed ON.
        """
        upn = self._get_upn(user_id) or user_id

        # ── Method 1: modern per-user MFA state ──────────────────────────────
        try:
            r = self._patch(
                f"{GRAPH_BETA}/users/{user_id}/authentication/requirements",
                {"perUserMfaState": "enabled"},
            )
            if r.status_code in (200, 204):
                return True, "Per-user MFA enabled (Graph API)"
        except Exception:
            pass

        # ── Method 2: legacy strongAuthenticationRequirements ─────────────────
        try:
            r2 = self._patch(
                f"{GRAPH_BETA}/users/{user_id}",
                {"strongAuthenticationRequirements": [
                    {"rememberMultiFactorAuthenticationOnTrustedDevices": False,
                     "state": "enabled"}
                ]},
            )
            if r2.status_code in (200, 204):
                return True, "Per-user MFA enabled (legacy Graph)"
        except Exception:
            pass

        # ── Method 3: az rest (uses az CLI auth directly) ─────────────────────
        try:
            import subprocess as _sp
            body_json = '{"perUserMfaState":"enabled"}'
            r3 = _sp.run(
                ["az", "rest",
                 "--method", "patch",
                 "--url", f"{GRAPH_BETA}/users/{user_id}/authentication/requirements",
                 "--body", body_json,
                 "--headers", "Content-Type=application/json"],
                capture_output=True, text=True, timeout=30,
            )
            if r3.returncode == 0:
                return True, "Per-user MFA enabled (az rest)"
        except Exception:
            pass

        # ── Method 4: MSOnline PowerShell ─────────────────────────────────────
        try:
            import subprocess as _sp
            ps_script = f"""
            try {{
                Import-Module MSOnline -ErrorAction Stop
                # Use existing connection or connect with current credentials
                try {{ Get-MsolDomain -ErrorAction Stop | Out-Null }}
                catch {{ Connect-MsolService -ErrorAction Stop }}

                $mfa = New-Object -TypeName Microsoft.Online.Administration.StrongAuthenticationRequirement
                $mfa.RelyingParty = "*"
                $mfa.State = "Enabled"
                Set-MsolUser -UserPrincipalName '{upn}' -StrongAuthenticationRequirements @($mfa) -ErrorAction Stop
                Write-Output 'SUCCESS'
            }} catch {{
                Write-Output "ERROR:$($_.Exception.Message)"
            }}
            """
            r4 = _sp.run(
                ["powershell", "-NoProfile", "-NonInteractive",
                 "-ExecutionPolicy", "Bypass", "-Command", ps_script],
                capture_output=True, text=True, timeout=60,
            )
            if "SUCCESS" in r4.stdout:
                return True, "Per-user MFA enabled (MSOnline PowerShell)"
            if "ERROR:" in r4.stdout:
                ps_err = r4.stdout.split("ERROR:", 1)[-1].strip()[:150]
            else:
                ps_err = (r4.stderr or r4.stdout)[:150]
        except Exception as ex:
            ps_err = str(ex)[:100]

        # ── Check Security Defaults (only if confirmed ON via API) ────────────
        sd_on = self._security_defaults_enabled()
        if sd_on:
            return True, (
                "ℹ MFA enforced via Security Defaults — "
                "user will be prompted to register MFA on first login."
            )

        return False, (
            f"MFA could not be enabled via Graph API, az rest, or MSOnline PS. "
            f"Last PS error: {ps_err}. "
            "Please enable MFA manually in the Azure portal."
        )

    def _security_defaults_enabled(self) -> bool:
        """
        Check if Security Defaults is enabled for the tenant.
        Returns True ONLY when explicitly confirmed via API (isEnabled=true).
        Returns False on any error or permission issue — we no longer
        assume SD is on just because we can't read the policy.
        """
        try:
            r = self._get(
                f"{GRAPH_BETA}/policies/identitySecurityDefaultsEnforcementPolicy",
                params={"$select": "isEnabled"},
            )
            if r.status_code == 200:
                return bool(r.json().get("isEnabled", False))
        except Exception:
            pass
        return False

    def set_mail_address(self, user_id: str, email: str) -> Tuple[bool, str]:
        """
        Explicitly PATCH the 'mail' property on the Azure AD user object.
        Without this, the Email field in the Azure portal stays blank until
        Exchange Online provisioning completes (which can take minutes).
        """
        try:
            r = self._patch(f"{GRAPH_BASE}/users/{user_id}", {"mail": email})
            if r.status_code in (200, 204):
                return True, f"mail set to {email}"
            err = ""
            try:
                err = r.json().get("error", {}).get("message", r.text[:200])
            except Exception:
                err = r.text[:200]
            return False, f"mail PATCH failed: {err}"
        except Exception as e:
            return False, str(e)

    def set_proxy_addresses(self, user_id: str, email: str,
                             employee_id: str = "") -> Tuple[bool, str]:
        """
        Set proxyAddresses on the O365 user.
        proxyAddresses is read-only via Graph API for Exchange-managed users,
        so this method uses Exchange Online PowerShell as a fallback.
        """
        domain = email.split("@")[1] if "@" in email else ""
        addrs = [f"SMTP:{email}"]
        if employee_id and domain:
            addrs.append(f"smtp:{employee_id}@{domain}")

        # Method 1: Try Graph API first (works for some tenant configs)
        body = {"proxyAddresses": addrs}
        try:
            r = self._patch(f"{GRAPH_BASE}/users/{user_id}", body)
            if r.status_code in (200, 204):
                return True, f"proxyAddresses set via Graph: {', '.join(addrs)}"
        except Exception:
            pass

        # Method 2: Use Exchange Online PowerShell
        try:
            # Build PowerShell command to set proxy addresses
            alias_cmd = ""
            if employee_id and domain:
                alias_entry = f"{employee_id}@{domain}"
                alias_cmd = (
                    f"Set-Mailbox -Identity '{email}' "
                    f"-EmailAddresses @{{Add='smtp:{alias_entry}'}} "
                    f"-ErrorAction Stop\n"
                    f"Write-Output 'ALIAS_OK'"
                )
            ps_script = (
                "try {\n"
                "    Import-Module ExchangeOnlineManagement -ErrorAction SilentlyContinue\n"
                f"    Set-Mailbox -Identity '{email}' "
                f"-WindowsEmailAddress '{email}' -ErrorAction Stop\n"
                f"    {alias_cmd}\n"
                "    Write-Output 'SUCCESS'\n"
                "} catch {\n"
                "    Write-Output \"ERROR:$($_.Exception.Message)\"\n"
                "}\n"
            )
            import subprocess as _sp
            r2 = _sp.run(
                ["powershell", "-NoProfile", "-NonInteractive",
                 "-ExecutionPolicy", "Bypass", "-Command", ps_script],
                capture_output=True, text=True, timeout=60,
            )
            if "SUCCESS" in r2.stdout or "ALIAS_OK" in r2.stdout:
                return True, f"proxyAddresses set via Exchange PS: {', '.join(addrs)}"
            if "ERROR:" in r2.stdout:
                err_msg = r2.stdout.split("ERROR:", 1)[-1].strip()
                return False, f"Exchange PS: {err_msg[:200]}"
        except Exception as e:
            pass

        # Method 3: proxyAddresses will be synced from AD via AD Connect
        return False, (
            "proxyAddresses cannot be set via Graph API (read-only). "
            "Will be set via AD and synced by AD Connect."
        )

    def add_o365_alias(self, user_id: str, alias_email: str) -> Tuple[bool, str]:
        """
        Add an alias email to the user. Tries Graph API first,
        falls back to Exchange Online PowerShell.
        """
        if not alias_email or "@" not in alias_email:
            return False, "Invalid alias email"

        # Method 1: Try Graph API (append to proxyAddresses)
        try:
            r = self._get(f"{GRAPH_BASE}/users/{user_id}",
                          params={"$select": "proxyAddresses"})
            if r.status_code == 200:
                current = r.json().get("proxyAddresses", [])
                alias_entry = f"smtp:{alias_email}"
                if any(a.lower() == alias_entry.lower() for a in current):
                    return True, f"Alias already exists: {alias_email}"
                current.append(alias_entry)
                r2 = self._patch(f"{GRAPH_BASE}/users/{user_id}",
                                 {"proxyAddresses": current})
                if r2.status_code in (200, 204):
                    return True, f"Alias added via Graph: {alias_email}"
        except Exception:
            pass

        # Method 2: Exchange Online PowerShell
        try:
            upn = self._get_upn(user_id) or alias_email.split("@")[0]
            ps_script = (
                "try {\n"
                f"    Set-Mailbox -Identity '{upn}' "
                f"-EmailAddresses @{{Add='smtp:{alias_email}'}} -ErrorAction Stop\n"
                "    Write-Output 'SUCCESS'\n"
                "} catch {\n"
                "    Write-Output \"ERROR:$($_.Exception.Message)\"\n"
                "}\n"
            )
            import subprocess as _sp
            r3 = _sp.run(
                ["powershell", "-NoProfile", "-NonInteractive",
                 "-ExecutionPolicy", "Bypass", "-Command", ps_script],
                capture_output=True, text=True, timeout=60,
            )
            if "SUCCESS" in r3.stdout:
                return True, f"Alias added via Exchange PS: {alias_email}"
            if "ERROR:" in r3.stdout:
                err_msg = r3.stdout.split("ERROR:", 1)[-1].strip()
                return False, f"Exchange PS alias: {err_msg[:200]}"
        except Exception:
            pass

        return False, (
            f"Could not set alias '{alias_email}' via Graph or Exchange PS. "
            "Will be set via AD proxy addresses and synced by AD Connect."
        )

    def set_manager(self, user_id: str, manager_id: str) -> Tuple[bool, str]:
        body = {"@odata.id": f"{GRAPH_BASE}/users/{manager_id}"}
        try:
            r = self._put(f"{GRAPH_BASE}/users/{user_id}/manager/$ref", body)
            if r.status_code == 204:
                return True, "Manager set"
            return False, r.text[:200]
        except Exception as e:
            return False, str(e)

    def add_to_group(self, user_id: str, group_id: str) -> Tuple[bool, str]:
        """
        Add user to a group/DL, retrying twice with a 10-second pause.
        Mail-enabled groups (M365 Groups, DLs) require an Exchange mailbox
        which can take a moment to reflect after license assignment.
        """
        body = {"@odata.id": f"{GRAPH_BASE}/directoryObjects/{user_id}"}
        last_err = ""
        for attempt in range(3):   # 0, 1, 2
            if attempt:
                time.sleep(10)
            try:
                r = self._post(
                    f"{GRAPH_BASE}/groups/{group_id}/members/$ref", body
                )
                if r.status_code == 204:
                    tag = f" (attempt {attempt+1})" if attempt else ""
                    return True, f"Added to group{tag}"
                if r.status_code == 400 and "already exists" in r.text:
                    return True, "Already a member"
                last_err = r.text[:200]
                # Stop retrying on clear auth / not-found errors
                if r.status_code in (401, 403, 404):
                    break
            except Exception as e:
                last_err = str(e)
        return False, last_err

    def _find_service_principal(self, display_name: str) -> Optional[Dict]:
        """Search for a service principal by exact then substring match."""
        # 1. Exact match via $filter
        try:
            r = self._get(
                f"{GRAPH_BASE}/servicePrincipals",
                params={
                    "$filter": f"displayName eq '{display_name}'",
                    "$select": "id,displayName,appRoles",
                },
            )
            if r.status_code == 200:
                vals = r.json().get("value", [])
                if vals:
                    return vals[0]
        except Exception:
            pass

        # 2. $search fallback (ConsistencyLevel: eventual required)
        try:
            r = self._get(
                f"{GRAPH_BASE}/servicePrincipals",
                params={
                    "$search": f'"displayName:{display_name}"',
                    "$select": "id,displayName,appRoles",
                    "$top": "20",
                },
                extra_headers={"ConsistencyLevel": "eventual"},
            )
            if r.status_code == 200:
                vals = r.json().get("value", [])
                # Case-insensitive substring match
                needle = display_name.lower()
                for sp in vals:
                    if needle in sp.get("displayName", "").lower():
                        return sp
        except Exception:
            pass

        # 3. Broad list scan (paginate up to 3 pages)
        try:
            url: Optional[str] = (
                f"{GRAPH_BASE}/servicePrincipals"
                "?$select=id,displayName,appRoles&$top=100"
            )
            needle = display_name.lower()
            pages  = 0
            while url and pages < 3:
                r = self._get(url)
                if r.status_code == 200:
                    data = r.json()
                    for sp in data.get("value", []):
                        if needle in sp.get("displayName", "").lower():
                            return sp
                    url = data.get("@odata.nextLink")
                    pages += 1
                else:
                    break
        except Exception:
            pass

        return None

    def add_to_zoho_enterprise_app(self, user_id: str) -> Tuple[bool, str]:
        """Find Zoho Accounts enterprise app and assign the user to it."""
        try:
            # Try direct lookup by known Object ID first
            sp = None
            if ZOHO_APP_OBJECT_ID:
                try:
                    r = self._get(
                        f"{GRAPH_BASE}/servicePrincipals/{ZOHO_APP_OBJECT_ID}",
                        params={"$select": "id,displayName,appRoles"},
                    )
                    if r.status_code == 200:
                        sp = r.json()
                except Exception:
                    pass

            # Fall back to search by name
            if not sp:
                sp = self._find_service_principal(ZOHO_APP_NAME)
            if not sp:
                return False, (
                    f"Enterprise app '{ZOHO_APP_NAME}' not found in tenant. "
                    "Make sure it is added as an Enterprise Application in Entra ID."
                )

            sp_id     = sp["id"]
            app_roles = sp.get("appRoles", [])
            # Use first enabled role or the default "no role" GUID
            role_id   = next(
                (ar["id"] for ar in app_roles if ar.get("isEnabled", True)),
                "00000000-0000-0000-0000-000000000000"
            )

            body = {
                "principalId": user_id,
                "resourceId":  sp_id,
                "appRoleId":   role_id,
            }
            r2 = self._post(f"{GRAPH_BASE}/users/{user_id}/appRoleAssignments", body)
            if r2.status_code in (200, 201):
                return True, f"User added to '{sp.get('displayName','Zoho Accounts')}' enterprise app"
            if r2.status_code == 409:
                return True, "Already assigned to Zoho Accounts"
            return False, r2.text[:200]
        except Exception as e:
            return False, str(e)
