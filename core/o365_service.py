"""
core/o365_service.py
Microsoft 365 operations via Microsoft Graph REST API.
"""

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
from core.credential_manager import cred_manager, SCOPES_GRAPH

SELECT_PARAM = "$select"
SP_SELECT_FIELDS = "id,displayName,appRoles"
ODATA_NEXT_LINK = "@odata.nextLink"

class O365Service:
    def __init__(self):
        self._token: Optional[str] = None
        self._token_expiry: float = 0.0
        self._last_auth_fail: float = 0.0
        self._drive_id: Optional[str] = None
        self._item_id:  Optional[str] = None

    def _token_valid(self) -> bool:
        if self._last_auth_fail and time.time() - self._last_auth_fail < 30:
            return True
        return bool(self._token) and time.time() < self._token_expiry - 60

    def _refresh_token(self) -> None:
        self._token = cred_manager.get_token(SCOPES_GRAPH)
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
        if extra_headers: h.update(extra_headers)
        return requests.get(url, headers=h, params=params, timeout=15)

    def _post(self, url: str, body: Dict, params: Dict = None) -> requests.Response:
        r = requests.post(url, headers=self._headers(), json=body, params=params, timeout=20)
        self._check_sync_error(r)
        return r

    def _patch(self, url: str, body: Dict, params: Dict = None) -> requests.Response:
        r = requests.patch(url, headers=self._headers(), json=body, params=params, timeout=20)
        self._check_sync_error(r)
        return r

    def _put(self, url: str, body: Dict) -> requests.Response:
        return requests.put(url, headers=self._headers(), json=body, timeout=20)

    def _check_sync_error(self, r: requests.Response):
        if r.status_code in (400, 403):
            try:
                err = r.json().get("error", {}).get("message", "")
                if any(x in err.lower() for x in ("read-only", "on-premises", "mail-enabled")):
                    r.reason = f"SYNC_ERROR: {err}"
            except Exception: pass

    def test_connection(self) -> Tuple[bool, str]:
        try:
            r = self._get(f"{GRAPH_BASE}/me")
            if r.status_code == 200: return True, r.json().get("userPrincipalName", "Connected")
            return False, f"HTTP {r.status_code}"
        except Exception as e: return False, str(e)

    def get_tenant_info(self) -> Dict:
        try:
            r = self._get(f"{GRAPH_BASE}/organization", params={SELECT_PARAM: "displayName,id"})
            if r.status_code == 200:
                orgs = r.json().get("value", [])
                return orgs[0] if orgs else {}
        except Exception: pass
        return {}

    def check_admin_roles(self) -> Tuple[bool, str]:
        try:
            r = self._get(f"{GRAPH_BASE}/me/memberOf")
            if r.status_code == 200:
                data = r.json().get("value", [])
                for role in data:
                    if role.get("@odata.type") == "#microsoft.graph.directoryRole":
                        tid = role.get("roleTemplateId")
                        if tid in ("62e90394-69f5-4237-9190-012177145e10", "fe930be7-5e62-47db-91af-98c3a49a38b1"):
                            return True, f"Authorized as {role.get('displayName')}"
                return False, "User does not have User/Global Admin roles."
            return False, f"HTTP {r.status_code}"
        except Exception as e: return False, str(e)

    def email_exists(self, email: str) -> bool:
        try: return self._get(f"{GRAPH_BASE}/users/{email}").status_code == 200
        except Exception: return False

    def get_users(self, search: str = "") -> List[Dict]:
        users = []
        try:
            params = {SELECT_PARAM: "id,displayName,userPrincipalName,jobTitle", "$top": 999}
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
                    url = data.get(ODATA_NEXT_LINK); params = None
                else: break
        except Exception: pass
        return users

    def get_groups(self) -> List[Dict]:
        groups = []
        url = f"{GRAPH_BASE}/groups?$select=id,displayName,groupTypes,mailEnabled,securityEnabled,onPremisesSyncEnabled&$top=999"
        try:
            while url:
                r = self._get(url)
                if r.status_code == 200:
                    data = r.json()
                    for g in data.get("value", []):
                        self._tag_group_type(g)
                        groups.append(g)
                    url = data.get(ODATA_NEXT_LINK)
                else: break
        except Exception: pass
        return groups

    def _tag_group_type(self, g: Dict):
        is_unified  = "Unified" in g.get("groupTypes", [])
        is_mail     = g.get("mailEnabled", False)
        is_security = g.get("securityEnabled", False)
        is_synced   = g.get("onPremisesSyncEnabled", False)
        if is_unified: g["_type"] = "M365 Group"
        elif is_mail and not is_security: g["_type"] = "Distribution List"
        elif is_mail and is_security: g["_type"] = "Mail-Sec Group"
        else: g["_type"] = "Security Group"
        if is_synced: g["_type"] += " (AD Synced)"

    def get_license_skus(self) -> List[Dict]:
        try:
            r = self._get(f"{GRAPH_BASE}/subscribedSkus")
            if r.status_code == 200: return r.json().get("value", [])
        except Exception: pass
        return []

    def check_duplicates(self, email: str, employee_id: str = "") -> Tuple[bool, str]:
        try:
            r = self._get(f"{GRAPH_BASE}/users/{email}?$select=id,displayName")
            if r.status_code == 200: return True, f"UPN exists: {r.json().get('displayName')} ({email})"
            if employee_id:
                r_id = self._get(f"{GRAPH_BASE}/users", params={"$filter": f"employeeId eq '{employee_id}'", "$select": "id,displayName,userPrincipalName"})
                if r_id.status_code == 200:
                    val = r_id.json().get("value", [])
                    if val: return True, f"ID '{employee_id}' assigned to {val[0].get('displayName')} ({val[0].get('userPrincipalName')})"
        except Exception as e: return False, f"Error: {e}"
        return False, ""

    def search_users_broad(self, query: str) -> List[Dict]:
        try:
            r = self._get(f"{GRAPH_BASE}/users", params={"$search": f'"displayName:{query}" OR "userPrincipalName:{query}"', "$select": "id,displayName,userPrincipalName,jobTitle,department,employeeId,accountEnabled", "$top": 50}, extra_headers={"ConsistencyLevel": "eventual"})
            return r.json().get("value", []) if r.status_code == 200 else []
        except Exception: return []

    def get_user_details(self, user_id: str) -> Dict:
        try:
            r = self._get(f"{GRAPH_BASE}/users/{user_id}", params={"$select": "id,displayName,userPrincipalName,jobTitle,department,employeeId,accountEnabled,mobilePhone"})
            if r.status_code == 200:
                user = r.json()
                user["_licenses"] = self._get(f"{GRAPH_BASE}/users/{user_id}/licenseDetails").json().get("value", [])
                user["_manager"]  = self._get(f"{GRAPH_BASE}/users/{user_id}/manager").json()
                return user
        except Exception: pass
        return {}

    def remove_license(self, user_id: str, sku_id: str) -> Tuple[bool, str]:
        try:
            r = self._post(f"{GRAPH_BASE}/users/{user_id}/assignLicense", {"addLicenses": [], "removeLicenses": [sku_id]})
            return (True, "Removed") if r.status_code == 200 else (False, r.text[:200])
        except Exception as e: return False, str(e)

    def block_sign_in(self, user_id: str, block: bool = True) -> Tuple[bool, str]:
        try:
            r = self._patch(f"{GRAPH_BASE}/users/{user_id}", {"accountEnabled": not block})
            return (True, "Success") if r.status_code in (200, 204) else (False, r.text[:200])
        except Exception as e: return False, str(e)

    def delete_user(self, user_id: str) -> Tuple[bool, str]:
        try:
            r = requests.delete(f"{GRAPH_BASE}/users/{user_id}", headers=self._headers(), timeout=20)
            return (True, "Deleted") if r.status_code in (200, 204) else (False, r.text[:200])
        except Exception as e: return False, str(e)

    def _resolve_sharepoint_file(self) -> Tuple[bool, str]:
        if self._drive_id and self._item_id: return True, "OK"
        if SHAREPOINT_DRIVE_ID and SHAREPOINT_ITEM_ID:
            self._drive_id, self._item_id = SHAREPOINT_DRIVE_ID, SHAREPOINT_ITEM_ID
            return True, "OK"
        try:
            import base64
            encoded = "u!" + base64.b64encode(SHAREPOINT_FILE_URL.encode('utf-8')).decode('utf-8').replace('/', '_').replace('+', '-').rstrip('=')
            r = self._get(f"{GRAPH_BASE}/shares/{encoded}/driveItem")
            if r.status_code == 200:
                data = r.json()
                self._drive_id, self._item_id = data.get("parentReference", {}).get("driveId"), data.get("id")
                return True, "OK"
            return False, r.text[:200]
        except Exception as e: return False, str(e)

    def log_to_excel(self, sheet_name: str, row_values: List[Any]) -> Tuple[bool, str]:
        ok, msg = self._resolve_sharepoint_file()
        if not ok: return False, msg
        try:
            url = f"{GRAPH_BASE}/drives/{self._drive_id}/items/{self._item_id}/workbook/worksheets/{sheet_name}/tables/Table1/rows"
            r = self._post(url, {"values": [row_values]})
            return (True, "Logged") if r.status_code in (200, 201) else (False, r.text[:200])
        except Exception as e: return False, str(e)

    def create_user(self, data: Dict[str, Any]) -> Tuple[bool, str, str]:
        body = {
            "accountEnabled": True, "displayName": f"{data['first_name']} {data['last_name']}",
            "givenName": data['first_name'], "surname": data['last_name'],
            "userPrincipalName": data['email'], "mailNickname": data.get("mail_nickname", data['email'].split('@')[0]),
            "passwordProfile": {"forceChangePasswordNextSignIn": True, "password": data.get("password", "Welcome@123")},
            "jobTitle": data.get("job_title", ""), "department": data.get("department", ""),
            "officeLocation": data.get("office", "Coimbatore"), "mobilePhone": data.get("mobile", ""),
            "streetAddress": data.get("street", ""), "city": data.get("city", "Coimbatore"),
            "state": data.get("state", "Tamil Nadu"), "postalCode": data.get("zip", "641006"),
            "country": data.get("country", "India"), "companyName": COMPANY_NAME,
            "employeeId": data.get("employee_id", ""), "employeeType": data.get("employee_type", "Employee"),
            "usageLocation": "IN"
        }
        if data.get("hire_date_iso"): body["employeeHireDate"] = data["hire_date_iso"]
        body = {k: v for k, v in body.items() if v != "" and v is not None}
        try:
            r = self._post(f"{GRAPH_BASE}/users", body)
            if r.status_code == 201: return True, r.json().get("id", ""), "Success"
            return False, "", r.json().get("error", {}).get("message", r.text[:200])
        except Exception as e: return False, "", str(e)

    def wait_for_user_provisioned(self, user_id: str, max_wait: int = 60) -> Tuple[bool, str]:
        for _ in range(max_wait // 5):
            try:
                if self._get(f"{GRAPH_BASE}/users/{user_id}").status_code == 200: return True, ""
            except Exception: pass
            time.sleep(5)
        return False, "Timeout"

    def wait_for_mailbox(self, user_id: str, max_wait: int = 180) -> Tuple[bool, str]:
        for _ in range(max_wait // 10):
            try:
                if self._get(f"{GRAPH_BASE}/users/{user_id}/mailboxSettings").status_code == 200: return True, ""
            except Exception: pass
            time.sleep(10)
        return False, "Timeout"

    def assign_license(self, user_id: str, sku_id: str) -> Tuple[bool, str]:
        self._patch(f"{GRAPH_BASE}/users/{user_id}", {"usageLocation": "IN"})
        time.sleep(3)
        body = {"addLicenses": [{"skuId": sku_id}], "removeLicenses": []}
        delays = [8, 20, 35, 50]; last_err = ""
        for i, delay in enumerate([0] + delays):
            if delay: time.sleep(delay)
            r = self._post(f"{GRAPH_BASE}/users/{user_id}/assignLicense", body)
            if r.status_code == 200: return True, "Assigned"
            last_err = r.text[:200]
            if any(x in last_err.lower() for x in ("already", "forbidden", "invalid")): break
        return False, last_err

    def enable_mfa(self, user_id: str) -> Tuple[bool, str]:
        try:
            r = self._patch(f"{GRAPH_BETA}/users/{user_id}/authentication/requirements", {"perUserMfaState": "enabled"})
            if r.status_code in (200, 204): return True, "MFA enabled"
            r2 = self._patch(f"{GRAPH_BETA}/users/{user_id}", {"strongAuthenticationRequirements": [{"rememberMultiFactorAuthenticationOnTrustedDevices": False, "state": "enabled"}]})
            if r2.status_code in (200, 204): return True, "MFA enabled (legacy)"
        except Exception: pass
        return False, "Failed to enable MFA via Graph"

    def add_to_group(self, user_id: str, group_id: str) -> Tuple[bool, str]:
        body_ref = {"@odata.id": f"{GRAPH_BASE}/directoryObjects/{user_id}"}
        try:
            r = self._post(f"{GRAPH_BASE}/groups/{group_id}/members/$ref", body_ref)
            if r.status_code in (204, 201): return True, "Added"
            if "already exists" in r.text.lower(): return True, "Already a member"
            r2 = self._post(f"{GRAPH_BASE}/groups/{group_id}/members", {"id": user_id})
            if r2.status_code in (204, 201): return True, "Added (Direct)"
            return False, r.text[:200]
        except Exception as e: return False, str(e)

    def add_to_zoho_enterprise_app(self, user_id: str) -> Tuple[bool, str]:
        try:
            sp = None
            if ZOHO_APP_OBJECT_ID:
                r = self._get(f"{GRAPH_BASE}/servicePrincipals/{ZOHO_APP_OBJECT_ID}")
                if r.status_code == 200: sp = r.json()
            if not sp:
                r = self._get(f"{GRAPH_BASE}/servicePrincipals", params={"$filter": f"displayName eq '{ZOHO_APP_NAME}'"})
                if r.status_code == 200 and r.json().get("value"): sp = r.json()["value"][0]
            if not sp: return False, "App not found"
            role_id = next((ar["id"] for ar in sp.get("appRoles", []) if ar.get("isEnabled", True)), "00000000-0000-0000-0000-000000000000")
            r2 = self._post(f"{GRAPH_BASE}/users/{user_id}/appRoleAssignments", {"principalId": user_id, "resourceId": sp["id"], "appRoleId": role_id})
            return (True, "Success") if r2.status_code in (200, 201, 409) else (False, r2.text[:200])
        except Exception as e: return False, str(e)

    def add_o365_alias(self, user_id: str, alias_email: str) -> Tuple[bool, str]:
        try:
            r = self._get(f"{GRAPH_BASE}/users/{user_id}", params={SELECT_PARAM: "proxyAddresses,userPrincipalName"})
            if r.status_code != 200: return False, "Failed to read user"
            data = r.json(); current = data.get("proxyAddresses", []); upn = data.get("userPrincipalName", "")
            if not any(a.startswith("SMTP:") for a in current) and upn: current.append(f"SMTP:{upn}")
            alias_entry = f"smtp:{alias_email}"
            if any(a.lower() == alias_entry.lower() for a in current): return True, "Exists"
            current.append(alias_entry)
            r2 = self._patch(f"{GRAPH_BASE}/users/{user_id}", {"proxyAddresses": current})
            if r2.status_code in (200, 204): return True, "Added"
            if "read-only" in r2.text: return False, f"SYNC_ERROR: {r2.text[:200]}"
            return False, r2.text[:200]
        except Exception as e: return False, str(e)

    def set_manager(self, user_id: str, manager_id: str) -> Tuple[bool, str]:
        try:
            r = self._put(f"{GRAPH_BASE}/users/{user_id}/manager/$ref", {"@odata.id": f"{GRAPH_BASE}/users/{manager_id}"})
            return (True, "Set") if r.status_code == 204 else (False, r.text[:200])
        except Exception as e: return False, str(e)
