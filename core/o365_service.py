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
    SHAREPOINT_FILE_URL, SHAREPOINT_DRIVE_ID, SHAREPOINT_ITEM_ID
)

SELECT_PARAM = "$select"
SP_SELECT_FIELDS = "id,displayName,appRoles"
ERROR_PREFIX = "ERROR:"
ODATA_NEXT_LINK = "@odata.nextLink"



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

def _fetch_exo_token() -> Optional[str]:
    """Get an Exchange Online token from Azure CLI."""
    try:
        r = subprocess.run(
            'az account get-access-token --resource https://outlook.office365.com/ --output json',
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
        self._last_auth_fail: float = 0.0
        self._drive_id: Optional[str] = None
        self._item_id:  Optional[str] = None

    # ── Auth ──────────────────────────────────────────────────────────────────

    def _token_valid(self) -> bool:
        # If last attempt failed recently, don't try again to avoid spamming prompts
        if self._last_auth_fail and time.time() - self._last_auth_fail < 30:
            return True # Pretend it's valid to skip the call
        return bool(self._token) and time.time() < self._token_expiry - 60

    def _refresh_token(self) -> None:
        self._token = _fetch_az_token()
        if self._token:
            self._token_expiry = time.time() + 3500
            self._last_auth_fail = 0
        else:
            self._last_auth_fail = time.time()
            self._token_expiry = 0

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

    def _post(self, url: str, body: Dict, params: Dict = None) -> requests.Response:
        r = requests.post(url, headers=self._headers(), json=body, params=params, timeout=20)
        self._check_sync_error(r)
        return r

    def _patch(self, url: str, body: Dict, params: Dict = None) -> requests.Response:
        r = requests.patch(url, headers=self._headers(), json=body, params=params, timeout=20)
        self._check_sync_error(r)
        return r

    def _check_sync_error(self, r: requests.Response):
        """Inject a hint if the error is due to AD sync read-only restrictions."""
        if r.status_code in (400, 403):
            try:
                err = r.json().get("error", {}).get("message", "")
                # Common sync error strings
                if "read-only" in err.lower() or "on-premises" in err.lower() or "mail-enabled" in err.lower():
                    # We prefix this so the GUI can detect it and try AD fallback
                    r.reason = f"SYNC_ERROR: {err}"
            except Exception:
                pass

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
                          params={SELECT_PARAM: "displayName,id"})
            if r.status_code == 200:
                orgs = r.json().get("value", [])
                return orgs[0] if orgs else {}
        except Exception:
            pass
        return {}

    def check_admin_roles(self) -> Tuple[bool, str]:
        """
        Check if the signed-in Azure CLI user has Global Admin or User Admin roles.
        """
        try:
            r = self._get(f"{GRAPH_BASE}/me/memberOf")
            if r.status_code == 200:
                data = r.json().get("value", [])
                for role in data:
                    if role.get("@odata.type") == "#microsoft.graph.directoryRole":
                        tid = role.get("roleTemplateId")
                        if tid in ("62e90394-69f5-4237-9190-012177145e10", "fe930be7-5e62-47db-91af-98c3a49a38b1"):
                            return True, f"Authorized as {role.get('displayName')}"
                return False, "User does not have User Administrator or Global Administrator roles in O365."
            elif r.status_code == 401:
                return False, "Azure CLI session expired or not authorized."
            else:
                return False, f"Failed to check O365 roles (HTTP {r.status_code})"
        except Exception as e:
            return False, f"Error checking O365 roles: {str(e)}"

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
                SELECT_PARAM: "id,displayName,userPrincipalName,jobTitle",
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
                    url = data.get(ODATA_NEXT_LINK)
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
                        self._tag_group_type(g)
                        groups.append(g)
                    url = data.get(ODATA_NEXT_LINK)
                else:
                    break
        except Exception:
            pass
        return groups

    def _tag_group_type(self, g: Dict):
        """Helper to tag group with its type for display."""
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
                    url = data.get(ODATA_NEXT_LINK)
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

    # ── Off-boarding & Search ─────────────────────────────────────────────────

    def check_duplicates(self, email: str, employee_id: str = "") -> Tuple[bool, str]:
        """Check if UPN or Employee ID already exists in O365."""
        try:
            # Check UPN
            r = self._get(f"{GRAPH_BASE}/users/{email}?$select=id,displayName")
            if r.status_code == 200:
                user = r.json()
                return True, f"UPN already exists: {user.get('displayName')} ({email})"
            
            # Check Employee ID
            if employee_id:
                params = {"$filter": f"employeeId eq '{employee_id}'", "$select": "id,displayName,userPrincipalName"}
                r_id = self._get(f"{GRAPH_BASE}/users", params=params)
                if r_id.status_code == 200:
                    val = r_id.json().get("value", [])
                    if val:
                        u = val[0]
                        return True, f"Employee ID '{employee_id}' already assigned to {u.get('displayName')} ({u.get('userPrincipalName')})"
        except Exception as e:
            return False, f"Duplicate check error: {str(e)}"
        return False, ""

    def search_users_broad(self, query: str) -> List[Dict]:
        """Search users by name, email, or job title."""
        users = []
        try:
            params = {
                "$search": f'"displayName:{query}" OR "userPrincipalName:{query}"',
                "$select": "id,displayName,userPrincipalName,jobTitle,department,employeeId,accountEnabled",
                "$top": 50
            }
            r = self._get(f"{GRAPH_BASE}/users", params=params, extra_headers={"ConsistencyLevel": "eventual"})
            if r.status_code == 200:
                users = r.json().get("value", [])
        except Exception:
            pass
        return users

    def get_user_details(self, user_id: str) -> Dict:
        """Fetch detailed info for off-boarding (licenses, manager)."""
        try:
            r = self._get(f"{GRAPH_BASE}/users/{user_id}",
                          params={"$select": "id,displayName,userPrincipalName,jobTitle,department,employeeId,accountEnabled,mobilePhone"})
            if r.status_code == 200:
                user = r.json()
                # Get licenses
                r_lic = self._get(f"{GRAPH_BASE}/users/{user_id}/licenseDetails")
                user["_licenses"] = r_lic.json().get("value", []) if r_lic.status_code == 200 else []
                # Get manager
                r_mgr = self._get(f"{GRAPH_BASE}/users/{user_id}/manager")
                user["_manager"] = r_mgr.json() if r_mgr.status_code == 200 else None
                return user
        except Exception:
            pass
        return {}

    def remove_license(self, user_id: str, sku_id: str) -> Tuple[bool, str]:
        """Remove a specific license from a user."""
        try:
            body = {"addLicenses": [], "removeLicenses": [sku_id]}
            r = self._post(f"{GRAPH_BASE}/users/{user_id}/assignLicense", body)
            if r.status_code == 200:
                return True, "License removed"
            err = r.json().get("error", {}).get("message", r.text[:200])
            return False, err
        except Exception as e:
            return False, str(e)

    def block_sign_in(self, user_id: str, block: bool = True) -> Tuple[bool, str]:
        """Block or unblock a user's sign-in."""
        try:
            r = self._patch(f"{GRAPH_BASE}/users/{user_id}", {"accountEnabled": not block})
            if r.status_code in (200, 204):
                return True, f"Sign-in {'blocked' if block else 'enabled'}"
            err = r.json().get("error", {}).get("message", r.text[:200])
            return False, err
        except Exception as e:
            return False, str(e)

    def delete_user(self, user_id: str) -> Tuple[bool, str]:
        """Delete a user account."""
        try:
            r = requests.delete(f"{GRAPH_BASE}/users/{user_id}", headers=self._headers(), timeout=20)
            if r.status_code in (200, 204):
                return True, "User deleted"
            err = r.json().get("error", {}).get("message", r.text[:200])
            return False, err
        except Exception as e:
            return False, str(e)

    # ── SharePoint Excel Logging ──────────────────────────────────────────────

    def _resolve_sharepoint_file(self) -> Tuple[bool, str]:
        """Resolve the SHAREPOINT_FILE_URL to a Drive ID and Item ID."""
        if self._drive_id and self._item_id:
            return True, "Already resolved"
        
        # Fallback to hardcoded IDs if provided in config
        if SHAREPOINT_DRIVE_ID and SHAREPOINT_ITEM_ID:
            self._drive_id = SHAREPOINT_DRIVE_ID
            self._item_id  = SHAREPOINT_ITEM_ID
            return True, "Using configured IDs"

        try:
            import base64
            sharing_url = SHAREPOINT_FILE_URL
            # Encode URL to base64, remove padding, and make URL-safe
            encoded = base64.b64encode(sharing_url.encode('utf-8')).decode('utf-8')
            encoded = "u!" + encoded.replace('/', '_').replace('+', '-').rstrip('=')
            
            r = self._get(f"{GRAPH_BASE}/shares/{encoded}/driveItem")
            if r.status_code == 200:
                data = r.json()
                self._drive_id = data.get("parentReference", {}).get("driveId")
                self._item_id  = data.get("id")
                return True, "Success"
            
            err = ""
            try:
                err = r.json().get("error", {}).get("message", r.text[:200])
            except Exception:
                err = r.text[:200]
            return False, f"Graph API Error ({r.status_code}): {err}"
        except Exception as e:
            return False, str(e)

    def log_to_excel(self, sheet_name: str, row_values: List[Any]) -> Tuple[bool, str]:
        """Append a row of data to a specific sheet in the SharePoint Excel file."""
        ok_res, msg_res = self._resolve_sharepoint_file()
        if not ok_res:
            return False, f"Could not resolve SharePoint file: {msg_res}"

        try:
            # We use the 'workbook/worksheets/{name}/tables/Table1/rows' or fallback to range
            # Let's try to find if there's a table first, or just append to the used range.
            # Easiest: POST .../range(address='A1')/insert with shift='Down'
            # But Graph Excel API is better with usedRange.
            
            url = f"{GRAPH_BASE}/drives/{self._drive_id}/items/{self._item_id}/workbook/worksheets/{sheet_name}/tables"
            r_tables = self._get(url)
            table_name = "Table1" # Default assumption
            if r_tables.status_code == 200:
                tables = r_tables.json().get("value", [])
                if tables:
                    table_name = tables[0].get("name", "Table1")
            
            # Add row to table
            url = f"{GRAPH_BASE}/drives/{self._drive_id}/items/{self._item_id}/workbook/worksheets/{sheet_name}/tables/{table_name}/rows"
            body = {"values": [row_values]}
            r = self._post(url, body)
            if r.status_code in (200, 201):
                return True, "Log entry added"
            
            # Fallback: Range insert (this is more complex, so we'll stop here if table fails)
            err = r.json().get("error", {}).get("message", r.text[:200])
            return False, f"Excel error: {err}"
        except Exception as e:
            return False, str(e)

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
        for _ in range(max_wait // 5):
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
        for _ in range(max_wait // 10):
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

    def _do_assign(self, identifier: str, body: dict, attempt: int, is_upn: bool) -> Tuple[bool, str, bool]:
        """Attempt to assign a license, returning (success, message, should_stop)."""
        try:
            r = self._post(f"{GRAPH_BASE}/users/{identifier}/assignLicense", body)
            if r.status_code == 200:
                if is_upn:
                    tag = f" via UPN (attempt {attempt+1})"
                elif attempt:
                    tag = f" (attempt {attempt+1})"
                else:
                    tag = ""
                return True, f"License assigned{tag}", True

            err_body = {}
            try:
                err_body = r.json()
            except Exception:
                pass
            last_err = err_body.get("error", {}).get("message", r.text[:200])

            # Stop retrying on unrecoverable errors
            stop = any(x in last_err.lower() for x in ("already", "authorization", "forbidden", "does not exist", "invalid"))
            return False, last_err, stop
        except Exception as e:
            return False, str(e), False

    def assign_license(self, user_id: str, sku_id: str) -> Tuple[bool, str]:
        """
        Assign a license robustly:
          1. PATCH usageLocation first (required by Graph before assignLicenses).
          2. Try using object-ID; if that keeps failing, fall back to UPN.
          3. Retry up to 4× with exponential back-off.
        """
        self._ensure_usage_location(user_id)
        time.sleep(3)   # brief pause for the PATCH to propagate

        body     = {"addLicenses": [{"skuId": sku_id}], "removeLicenses": []}
        delays   = [8, 20, 35, 50]   # seconds between retries
        last_err = ""
        upn      = None   # fetched lazily on first identifier fallback

        for i, delay in enumerate([0] + delays):
            if delay:
                time.sleep(delay)

            if i >= 2 and upn is None:
                upn = self._get_upn(user_id)
            identifier = upn if (i >= 2 and upn) else user_id

            ok, msg, stop = self._do_assign(identifier, body, i, identifier == upn)
            if ok:
                return True, msg
            last_err = msg
            if stop:
                break

        return False, f"License assignment failed after {len(delays)+1} attempts: {last_err}"

    def enable_mfa(self, user_id: str) -> Tuple[bool, str]:
        """
        Enable MFA for the user using progressive methods, retrying up to MFA_RETRY_COUNT times.
        """
        from config import MFA_RETRY_COUNT
        upn = self._get_upn(user_id) or user_id
        ps_err = ""
        
        for attempt in range(MFA_RETRY_COUNT):
            # ── Method 1: modern per-user MFA state ──────────────────────────────
            try:
                r = self._patch(
                    f"{GRAPH_BETA}/users/{user_id}/authentication/requirements",
                    {"perUserMfaState": "enabled"},
                )
                if r.status_code in (200, 204):
                    return True, f"Per-user MFA enabled (Graph API, attempt {attempt+1})"
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
                    return True, f"Per-user MFA enabled (legacy Graph, attempt {attempt+1})"
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
                    return True, f"Per-user MFA enabled (az rest, attempt {attempt+1})"
            except Exception:
                pass

            # If all Graph API methods fail, stop here to avoid interactive prompts.
            ps_err = "All Graph API methods failed. PowerShell fallback was removed to prevent interactive prompts."

            if attempt < MFA_RETRY_COUNT - 1:
                import time
                time.sleep(10)

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
                params={SELECT_PARAM: "isEnabled"},
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

        # PowerShell fallback removed to prevent interactive prompts.
        # Graph API errors or read-only properties (sync errors) will be handled downstream.

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
                          params={SELECT_PARAM: "proxyAddresses"})
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
                
                try:
                    msg = r2.json().get("error", {}).get("message", r2.text[:200])
                    if "proxyAddresses' is read-only" in msg:
                        return False, f"SYNC_ERROR: {msg}"
                except Exception:
                    pass
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
            if ERROR_PREFIX in r3.stdout:
                err_msg = r3.stdout.split(ERROR_PREFIX, 1)[-1].strip()
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

    def add_to_groups_multi(self, user_id: str, group_items: List[Tuple[str, str]], admin_upn: str = "") -> List[Tuple[str, bool, str]]:
        """
        Add a user to multiple groups in a single session to avoid multiple login prompts.
        group_items: List of (group_id, group_name)
        Returns: List of (group_name, success, message)
        """
        if not group_items: return []
        
        results = []
        upn = self._get_upn(user_id)
        if not upn:
            return [(name, False, "Could not resolve UPN") for _, name in group_items]

        # 1. Try Graph API for all first (fastest)
        remaining = []
        for gid, gname in group_items:
            ok, msg = self.add_to_group(user_id, gid, admin_upn=admin_upn, skip_ps=True)
            if ok:
                results.append((gname, True, msg))
            else:
                remaining.append((gid, gname))
        
        if not remaining:
            return results

        # 2. For those that failed Graph (likely DLs), use ONE PowerShell session
        group_data = [] # List of (email, name)
        for gid, gname in remaining:
            email = gid
            try:
                r = self._get(f"{GRAPH_BASE}/groups/{gid}?$select=mail")
                if r.status_code == 200:
                    email = r.json().get("mail") or gid
            except Exception: pass
            group_data.append((email, gname))

        # Build a script that iterates through groups
        ps_groups_array = ", ".join([f"'{e}'" for e, _ in group_data])
        ps_names_array  = ", ".join([f"'{n}'" for _, n in group_data])
        
        exo_token = _fetch_exo_token()
        if exo_token:
            auth_param = f"-AccessToken '{exo_token}' -Organization '{EMAIL_DOMAIN}'"
        else:
            upn_param = f"-UserPrincipalName '{admin_upn}'" if admin_upn else ""
            auth_param = upn_param
        
        ps_script = (
            "$ErrorActionPreference = 'Stop'\n"
            "try {\n"
            "    Import-Module ExchangeOnlineManagement\n"
            f"    Connect-ExchangeOnline {auth_param} -ErrorAction SilentlyContinue\n"
            f"    $emails = @({ps_groups_array})\n"
            f"    $names  = @({ps_names_array})\n"
            f"    for ($i=0; $i -lt $emails.Length; $i++) {{\n"
            "        try {\n"
            f"            Add-DistributionGroupMember -Identity $emails[$i] -Member '{upn}'\n"
            "            Write-Output \"SUCCESS:$($names[$i])\"\n"
            "        } catch {\n"
            "            Write-Output \"ERROR:$($names[$i]):$($_.Exception.Message)\"\n"
            "        }\n"
            "    }\n"
            "} catch {\n"
            "    Write-Output \"GLOBAL_ERROR:$($_.Exception.Message)\"\n"
            "}\n"
        )
        
        import subprocess as _sp
        try:
            r_ps = _sp.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
                capture_output=True, text=True, timeout=90
            )
            out = r_ps.stdout
            for _, gname in remaining:
                if f"SUCCESS:{gname}" in out:
                    results.append((gname, True, "Added via Exchange PS"))
                elif f"ERROR:{gname}:" in out:
                    msg = out.split(f"ERROR:{gname}:", 1)[1].split("\n")[0].strip()
                    results.append((gname, "already" in msg.lower(), f"PS Error: {msg[:100]}"))
                elif "GLOBAL_ERROR:" in out:
                    msg = out.split("GLOBAL_ERROR:", 1)[1].strip()
                    results.append((gname, False, f"PS Connection Error: {msg[:100]}"))
                else:
                    results.append((gname, False, "PS fallback failed"))
        except Exception as e:
            for _, gname in remaining:
                results.append((gname, False, f"Process Error: {str(e)}"))

        return results

    def add_to_group(self, user_id: str, group_id: str, admin_upn: str = "", skip_ps: bool = False) -> Tuple[bool, str]:
        """Add user to a group (Security or DL)."""
        body = {"@odata.id": f"{GRAPH_BASE}/directoryObjects/{user_id}"}
        last_err = "Unknown error"
        
        # 1. Try Graph API v1.0
        for _ in range(2):
            try:
                r = self._post(f"{GRAPH_BASE}/groups/{group_id}/members/$ref", body)
                if r.status_code in (204, 201): return True, "Added (Graph v1.0)"
                msg = r.json().get("error", {}).get("message", r.text[:200])
                if "already exists" in msg.lower(): return True, "Already a member"
                if "Cannot Update a mail-enabled" in msg:
                    last_err = f"GRAPH_DL_ERROR: {msg}"; break
                last_err = msg
            except Exception as e: last_err = str(e)

        if skip_ps: return False, last_err

        # 2. Try Graph BETA
        try:
            r_beta = self._post(f"{GRAPH_BETA}/groups/{group_id}/members/$ref", body)
            if r_beta.status_code in (200, 204): return True, "Added (Graph Beta)"
        except Exception: pass

        # 3. Fallback to PS (Singular)
        res = self.add_to_groups_multi(user_id, [(group_id, "Group")], admin_upn)
        if not res: return False, "PS fallback yielded no results"
        return res[0][1], res[0][2]

    def _find_sp_exact(self, display_name: str) -> Optional[Dict]:
        try:
            r = self._get(
                f"{GRAPH_BASE}/servicePrincipals",
                params={"$filter": f"displayName eq '{display_name}'", SELECT_PARAM: SP_SELECT_FIELDS},
            )
            if r.status_code == 200:
                vals = r.json().get("value", [])
                if vals:
                    return vals[0]
        except Exception:
            pass
        return None

    def _find_sp_search(self, display_name: str) -> Optional[Dict]:
        try:
            r = self._get(
                f"{GRAPH_BASE}/servicePrincipals",
                params={"$search": f'"displayName:{display_name}"', SELECT_PARAM: SP_SELECT_FIELDS, "$top": "20"},
                extra_headers={"ConsistencyLevel": "eventual"},
            )
            if r.status_code == 200:
                vals = r.json().get("value", [])
                needle = display_name.lower()
                for sp in vals:
                    if needle in sp.get("displayName", "").lower():
                        return sp
        except Exception:
            pass
        return None

    def _find_sp_broad(self, display_name: str) -> Optional[Dict]:
        try:
            url: Optional[str] = f"{GRAPH_BASE}/servicePrincipals?{SELECT_PARAM}={SP_SELECT_FIELDS}&$top=100"
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

    def _find_service_principal(self, display_name: str) -> Optional[Dict]:
        """Search for a service principal by exact then substring match."""
        return self._find_sp_exact(display_name) or self._find_sp_search(display_name) or self._find_sp_broad(display_name)

    def add_to_zoho_enterprise_app(self, user_id: str) -> Tuple[bool, str]:
        """Find Zoho Accounts enterprise app and assign the user to it."""
        try:
            # Try direct lookup by known Object ID first
            sp = None
            if ZOHO_APP_OBJECT_ID:
                try:
                    r = self._get(
                        f"{GRAPH_BASE}/servicePrincipals/{ZOHO_APP_OBJECT_ID}",
                        params={SELECT_PARAM: SP_SELECT_FIELDS},
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

    def wait_for_replication(self, user_id: str, max_wait: int = 60) -> Tuple[bool, str]:
        """Poll until the new user is visible in Graph."""
        import time as _t
        for _ in range(max_wait // 5):
            try:
                r = self._get(f"{GRAPH_BASE}/users/{user_id}?$select=id")
                if r.status_code == 200:
                    return True, "Azure AD replication confirmed ✔"
            except Exception:
                pass
            _t.sleep(5)
        return False, f"User not visible after {max_wait}s — proceeding anyway"

    def set_mail_address(self, user_id: str, email: str) -> Tuple[bool, str]:
        """PATCH mail property so it shows in Azure portal."""
        try:
            r = self._patch(f"{GRAPH_BASE}/users/{user_id}", {"mail": email})
            if r.status_code in (200, 204):
                return True, f"mail set to {email}"
            return False, r.text[:200]
        except Exception as e:
            return False, str(e)

    def wait_for_mailbox(self, user_id: str, max_wait: int = 120) -> Tuple[bool, str]:
        """Poll until Exchange mailbox is provisioned."""
        import time as _t
        for _ in range(max_wait // 10):
            try:
                r = self._get(f"{GRAPH_BASE}/users/{user_id}/mailboxSettings")
                if r.status_code == 200:
                    return True, ""
            except Exception:
                pass
            _t.sleep(10)
        return False, (
            f"Exchange mailbox not ready after {max_wait}s — "
            "aliases may need to be set manually in M365 admin."
        )

    def add_o365_alias(self, user_id: str, alias_email: str) -> Tuple[bool, str]:
        """
        Add an alias (smtp: address) to the user via Graph proxyAddresses.
        Requires Exchange mailbox to be provisioned.
        """
        if not alias_email or "@" not in alias_email:
            return False, "Invalid alias email"
        try:
            r = self._get(f"{GRAPH_BASE}/users/{user_id}",
                          params={SELECT_PARAM: "proxyAddresses,userPrincipalName"})
            if r.status_code != 200:
                return False, f"Cannot read user (HTTP {r.status_code})"
            
            data = r.json()
            current = data.get("proxyAddresses", [])
            upn = data.get("userPrincipalName", "")
            
            # Ensure primary SMTP is present
            has_primary = any(a.startswith("SMTP:") for a in current)
            if not has_primary and upn:
                current.append(f"SMTP:{upn}")
                
            alias_entry = f"smtp:{alias_email}"
            if any(a.lower() == alias_entry.lower() for a in current):
                return True, f"Alias already exists: {alias_email}"
            
            current.append(alias_entry)
            r2 = self._patch(f"{GRAPH_BASE}/users/{user_id}",
                             {"proxyAddresses": current})
            if r2.status_code in (200, 204):
                return True, f"Alias added: {alias_email}"
            err = ""
            try:
                err = r2.json().get("error", {}).get("message", r2.text[:200])
            except Exception:
                err = r2.text[:200]
            if "read-only" in err:
                return False, f"SYNC_ERROR: {err}"
            return False, f"Alias failed: {err}"
        except Exception as e:
            return False, str(e)

    def send_mail(self, sender_email: str, sender_password: str, to_email: str, subject: str, body_text: str, cc_email: str = "") -> Tuple[bool, str]:
        """
        Send an email using SMTP.
        """
        import smtplib
        from email.message import EmailMessage

        if not sender_email or not sender_password or not to_email:
            return False, "Sender email, password, or receiver email missing"
        
        msg = EmailMessage()
        msg.set_content(body_text)
        msg['Subject'] = subject
        msg['From'] = sender_email
        msg['To'] = to_email
        if cc_email:
            msg['Cc'] = cc_email

        try:
            # Connect to Office 365 SMTP server
            server = smtplib.SMTP('smtp.office365.com', 587)
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
            server.quit()
            return True, "Email sent successfully"
        except smtplib.SMTPAuthenticationError:
            return False, "Email sending failed: Authentication error (check password)"
        except Exception as e:
            return False, f"Email sending failed: {str(e)}"
