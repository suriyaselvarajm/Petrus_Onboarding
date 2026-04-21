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
        groups: List[Dict] = []
        url: Optional[str] = (
            f"{GRAPH_BASE}/groups"
            "?$select=id,displayName,groupTypes,mailEnabled,onPremisesSyncEnabled&$top=999"
        )
        try:
            while url:
                r = self._get(url)
                if r.status_code == 200:
                    data = r.json()
                    for g in data.get("value", []):
                        # Skip groups synced from local AD (they cannot be modified in O365)
                        if g.get("onPremisesSyncEnabled"):
                            continue
                        # Skip Mail-Enabled Security Groups / Distribution Lists (Not supported by Graph API)
                        is_unified = "Unified" in g.get("groupTypes", [])
                        if g.get("mailEnabled") and not is_unified:
                            continue
                        groups.append(g)
                    url = data.get("@odata.nextLink")
                else:
                    break
        except Exception:
            pass
        return groups

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
        # Primary SMTP and secondary alias based on employee ID
        email_domain = email.split("@")[1] if "@" in email else ""
        proxy_addrs = [f"SMTP:{email}"]
        if emp_id and email_domain:
            proxy_addrs.append(f"smtp:{emp_id}@{email_domain}")

        body: Dict[str, Any] = {
            "accountEnabled":   True,
            "displayName":      f"{first} {last}",
            "givenName":        first,
            "surname":          last,
            "userPrincipalName": email,
            "mailNickname":     data.get("mail_nickname", sam[:48]),
            "proxyAddresses":   proxy_addrs,
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

    def assign_license(self, user_id: str, sku_id: str) -> Tuple[bool, str]:
        body = {"addLicenses": [{"skuId": sku_id}], "removeLicenses": []}
        try:
            r = self._post(f"{GRAPH_BASE}/users/{user_id}/assignLicenses", body)
            if r.status_code == 200:
                return True, "License assigned"
            err = r.json().get("error", {}).get("message", r.text[:200])
            return False, err
        except Exception as e:
            return False, str(e)

    def enable_mfa(self, user_id: str) -> Tuple[bool, str]:
        """Enable per-user MFA via Graph beta."""
        # Method 1: authentication/requirements (newer)
        try:
            r = self._patch(
                f"{GRAPH_BETA}/users/{user_id}/authentication/requirements",
                {"perUserMfaState": "enabled"},
            )
            if r.status_code in (200, 204):
                return True, "MFA enabled"
        except Exception:
            pass

        # Method 2: strongAuthenticationRequirements (fallback)
        try:
            r = self._patch(
                f"{GRAPH_BETA}/users/{user_id}",
                {"strongAuthenticationRequirements": [
                    {"rememberMultiFactorAuthenticationOnTrustedDevices": False,
                     "state": "enabled"}
                ]},
            )
            if r.status_code in (200, 204):
                return True, "MFA enabled (legacy method)"
            if r.status_code == 400 and "Request_BadRequest" in r.text:
                return False, "Tenant requires modern MFA enablement (via Entra ID Conditional Access or Security Defaults). Cannot be set locally."
            return False, f"MFA failed: {r.text[:200]}"
        except Exception as e:
            return False, str(e)

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
        body = {"@odata.id": f"{GRAPH_BASE}/directoryObjects/{user_id}"}
        try:
            r = self._post(f"{GRAPH_BASE}/groups/{group_id}/members/$ref", body)
            if r.status_code == 204:
                return True, "Added to group"
            # 400 with "already exists" is not a failure
            if r.status_code == 400 and "already exists" in r.text:
                return True, "Already a member"
            return False, r.text[:200]
        except Exception as e:
            return False, str(e)

    def add_to_zoho_enterprise_app(self, user_id: str) -> Tuple[bool, str]:
        """Find Zoho Accounts enterprise app and assign the user to it."""
        try:
            # Find service principal by display name
            r = self._get(
                f"{GRAPH_BASE}/servicePrincipals",
                params={
                    "$filter": f"displayName eq '{ZOHO_APP_NAME}'",
                    "$select": "id,appRoles",
                },
            )
            if r.status_code != 200:
                return False, f"Could not search enterprise apps (HTTP {r.status_code})"
            sps = r.json().get("value", [])
            if not sps:
                return False, f"Enterprise app '{ZOHO_APP_NAME}' not found in tenant"

            sp_id = sps[0]["id"]
            app_roles = sps[0].get("appRoles", [])
            # Use first role or the default "no role" GUID
            role_id = app_roles[0]["id"] if app_roles else "00000000-0000-0000-0000-000000000000"

            body = {
                "principalId": user_id,
                "resourceId":  sp_id,
                "appRoleId":   role_id,
            }
            r2 = self._post(f"{GRAPH_BASE}/users/{user_id}/appRoleAssignments", body)
            if r2.status_code in (200, 201):
                return True, "User added to Zoho Accounts enterprise app"
            if r2.status_code == 409:
                return True, "Already assigned to Zoho Accounts"
            return False, r2.text[:200]
        except Exception as e:
            return False, str(e)
