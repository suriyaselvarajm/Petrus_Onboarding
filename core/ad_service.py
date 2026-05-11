import ldap3
from ldap3 import Server, Connection, ALL, NTLM, SUBTREE, MODIFY_REPLACE, Tls
import ssl
import json
from typing import Optional, List, Dict, Any, Tuple

from config import (
    AD_DOMAIN, AD_SERVER, AD_BASE_DN, AD_PETRUS_USERS_OU,
    COMPANY_NAME, DEFAULT_COUNTRY_CODE,
    AD_ADMIN_USER, AD_ADMIN_PASSWORD,
)

from core.settings_manager import sm
import os

ERROR_PREFIX = "ERROR:"

class ADService:
    def __init__(self):
        self._connected = False
        self._server_address = sm.get("ad_server") or sm.get("ad_domain") or AD_DOMAIN
        self._session_user = None
        self._session_password = None

    def _get_connection(self) -> Connection:
        """Create and bind an LDAP connection using config or session credentials over LDAPS."""
        tls_config = Tls(validate=ssl.CERT_NONE, version=ssl.PROTOCOL_TLSv1_2)
        server = Server(self._server_address, port=636, use_ssl=True, tls=tls_config, get_info=ALL)
        
        user = self._session_user or AD_ADMIN_USER
        password = self._session_password or AD_ADMIN_PASSWORD

        if not user:
            raise ValueError("Authentication required. Please sign in.")

        if user and "\\" not in user and "@" not in user:
            domain = sm.get("ad_domain") or AD_DOMAIN
            user = f"{user}@{domain}"

        # Use SIMPLE authentication
        conn = Connection(
            server, 
            user=user, 
            password=password, 
            authentication=ldap3.SIMPLE,
            auto_bind=True
        )
        return conn

    def test_connection(self) -> Tuple[bool, str]:
        if not (self._session_user or AD_ADMIN_USER):
            return False, "Authentication required"
        try:
            with self._get_connection() as conn:
                self._connected = True
                return True, "Connected"
        except Exception as e:
            return False, str(e)

    def authenticate_and_check_permission(self, username: str, password: str) -> Tuple[bool, str]:
        """Verify credentials and check 'Domain Admins' membership via LDAPS."""
        try:
            tls_config = Tls(validate=ssl.CERT_NONE, version=ssl.PROTOCOL_TLSv1_2)
            server = Server(self._server_address, port=636, use_ssl=True, tls=tls_config, get_info=ALL)
            
            auth_user = username
            if "\\" not in username and "@" not in username:
                domain = sm.get("ad_domain") or AD_DOMAIN
                auth_user = f"{username}@{domain}"
            
            with Connection(server, user=auth_user, password=password, authentication=ldap3.SIMPLE) as conn:
                if not conn.bind():
                    return False, "Authentication Failed: Invalid credentials"
                
                conn.search(
                    search_base=AD_BASE_DN,
                    search_filter=f'(&(objectClass=user)(sAMAccountName={username}))',
                    attributes=['memberOf']
                )
                if not conn.entries:
                    return False, "User not found in directory"
                
                user_entry = conn.entries[0]
                groups = user_entry.memberOf.value if 'memberOf' in user_entry else []
                is_admin = any('CN=Domain Admins' in g for g in groups)
                
                if is_admin:
                    self._session_user = username
                    self._session_password = password
                    self._connected = True
                    return True, "Authenticated and verified as Domain Admin"
                return False, "User authenticated but is not a member of 'Domain Admins'"
        except Exception as e:
            return False, f"Error checking permissions: {str(e)}"

    def check_ad_sync(self) -> Tuple[bool, str]:
        return False, "Status Unknown (Security Hardened)"

    def user_exists(self, sam: str) -> bool:
        try:
            with self._get_connection() as conn:
                conn.search(AD_BASE_DN, f'(sAMAccountName={sam})', attributes=['sAMAccountName'])
                return len(conn.entries) > 0
        except Exception:
            return False

    def get_ous(self, base: str = None, scope: str = "LEVEL") -> List[Dict]:
        search_base = base or AD_PETRUS_USERS_OU
        ldap_scope = ldap3.LEVEL if scope == "OneLevel" else ldap3.SUBTREE
        try:
            with self._get_connection() as conn:
                conn.search(
                    search_base=search_base,
                    search_filter='(objectClass=organizationalUnit)',
                    search_scope=ldap_scope,
                    attributes=['name', 'distinguishedName']
                )
                return [{"Name": e.name.value, "DistinguishedName": e.distinguishedName.value} for e in conn.entries]
        except Exception:
            return []

    def get_groups(self, search_base: str = None) -> List[Dict]:
        from config import AD_GROUPS_BASE_OU, AD_PETRUS_USERS_OU
        base = search_base or AD_GROUPS_BASE_OU
        
        bases_to_try = []
        if base: bases_to_try.append(base)
        if AD_PETRUS_USERS_OU and AD_PETRUS_USERS_OU not in bases_to_try:
            bases_to_try.append(AD_PETRUS_USERS_OU)
            
        search_filter = '(|(objectClass=group)(objectCategory=group))'
        
        for current_base in bases_to_try:
            try:
                with self._get_connection() as conn:
                    conn.search(
                        search_base=current_base,
                        search_filter=search_filter,
                        search_scope=SUBTREE,
                        attributes=['cn', 'name', 'sAMAccountName', 'distinguishedName', 'displayName']
                    )
                    
                    if not conn.entries: continue
                        
                    results = []
                    for e in conn.entries:
                        name = ""
                        for attr in ['cn', 'name', 'sAMAccountName', 'displayName']:
                            if hasattr(e, attr) and getattr(e, attr):
                                val = getattr(e, attr).value
                                if val:
                                    name = str(val)
                                    break
                        if name:
                            results.append({
                                "Name": name, 
                                "DistinguishedName": e.distinguishedName.value,
                                "GroupCategory": "Security"
                            })
                    if results: return results
            except Exception: pass
        return []

    def get_manager_dn(self, upn: str) -> Optional[str]:
        try:
            with self._get_connection() as conn:
                conn.search(AD_BASE_DN, f'(userPrincipalName={upn})', attributes=['distinguishedName'])
                return conn.entries[0].distinguishedName.value if conn.entries else None
        except Exception: return None

    def get_user_dn(self, sam: str) -> Optional[str]:
        try:
            with self._get_connection() as conn:
                conn.search(AD_BASE_DN, f'(sAMAccountName={sam})', attributes=['distinguishedName'])
                return conn.entries[0].distinguishedName.value if conn.entries else None
        except Exception: return None

    def create_user(self, data: Dict[str, Any]) -> Tuple[bool, str]:
        first    = data["first_name"]
        last     = data["last_name"]
        email    = data["email"]
        display  = f"{first} {last}"
        sam      = f"{first.lower()}.{last.lower()}"[:20]
        ou       = data.get("ad_ou", AD_PETRUS_USERS_OU)
        password = data.get("password", "Welcome@123")
        manager_dn = data.get("ad_manager_dn", "")

        user_dn = f"CN={display},{ou}"
        
        attrs = {
            'objectClass': ['top', 'person', 'organizationalPerson', 'user'],
            'cn': display,
            'sn': last,
            'givenName': first,
            'displayName': display,
            'sAMAccountName': sam,
            'userPrincipalName': email,
            'mail': email,
            'title': data.get("job_title", ""),
            'department': data.get("department", ""),
            'mobile': data.get("mobile", ""),
            'streetAddress': data.get("street", ""),
            'l': data.get("city", "Coimbatore"),
            'st': data.get("state", "Tamil Nadu"),
            'postalCode': data.get("zip", "641006"),
            'c': 'IN',
            'co': 'India',
            'countryCode': int(DEFAULT_COUNTRY_CODE),
            'company': COMPANY_NAME,
            'employeeID': data.get("employee_id", ""),
            'employeeNumber': data.get("employee_id", ""),
            'userAccountControl': '514' 
        }
        
        if manager_dn: attrs['manager'] = manager_dn

        emp_id = data.get("employee_id", "")
        proxy_addrs = [f"SMTP:{email}"]
        if emp_id:
            domain = email.split("@")[1] if "@" in email else ""
            if domain: proxy_addrs.append(f"smtp:{emp_id}@{domain}")
        attrs['proxyAddresses'] = proxy_addrs

        try:
            with self._get_connection() as conn:
                if not conn.add(user_dn, attributes=attrs):
                    return False, f"Failed to create user object: {conn.result['description']}"
                
                encoded_pwd = f'"{password}"'.encode('utf-16-le')
                pwd_ok = conn.modify(user_dn, {'unicodePwd': [(MODIFY_REPLACE, [encoded_pwd])]})
                
                enable_ok = conn.modify(user_dn, {
                    'userAccountControl': [(MODIFY_REPLACE, [512])],
                    'pwdLastSet': [(MODIFY_REPLACE, [0])]
                })
                
                if not pwd_ok or not enable_ok:
                    return True, f"{sam} (Warning: Account created but remains DISABLED. Please enable manually.)"
                return True, sam
        except Exception as e:
            return False, str(e)

    def disable_user(self, sam: str) -> Tuple[bool, str]:
        try:
            dn = self.get_user_dn(sam)
            if not dn: return False, "User not found"
            with self._get_connection() as conn:
                conn.modify(dn, {'userAccountControl': [(MODIFY_REPLACE, [514])]})
                return True, "AD account disabled"
        except Exception as e: return False, str(e)

    def set_proxy_addresses(self, sam: str, addresses: List[str]) -> Tuple[bool, str]:
        try:
            dn = self.get_user_dn(sam)
            if not dn: return False, "User not found"
            with self._get_connection() as conn:
                conn.modify(dn, {'proxyAddresses': [(MODIFY_REPLACE, addresses)]})
                return True, "Proxy addresses updated in AD"
        except Exception as e: return False, str(e)

    def add_user_to_group(self, sam: str, group_dn: str) -> Tuple[bool, str]:
        try:
            user_dn = self.get_user_dn(sam)
            if not user_dn: return False, "User not found"
            with self._get_connection() as conn:
                conn.modify(group_dn, {'member': [(ldap3.MODIFY_ADD, [user_dn])]})
                return True, "Added to AD group"
        except Exception as e: return False, str(e)

    def delete_user(self, sam: str) -> Tuple[bool, str]:
        try:
            dn = self.get_user_dn(sam)
            if not dn: return False, "User not found"
            with self._get_connection() as conn:
                conn.delete(dn)
                return True, "AD account deleted"
        except Exception as e: return False, str(e)

    def search_user(self, query: str) -> List[Dict]:
        try:
            with self._get_connection() as conn:
                conn.search(
                    search_base=AD_BASE_DN,
                    search_filter=(
                        f'(&(objectClass=user)(objectCategory=person)'
                        f'(|(displayName=*{query}*)(sAMAccountName=*{query}*)(mail=*{query}*)))'
                    ),
                    search_scope=SUBTREE,
                    attributes=['displayName', 'sAMAccountName', 'mail', 'title',
                                'department', 'telephoneNumber', 'mobile',
                                'manager', 'distinguishedName', 'userPrincipalName', 'employeeID']
                )
                results = []
                for e in conn.entries:
                    def _v(attr, _e=e):
                        try: return getattr(_e, attr).value or ""
                        except Exception: return ""
                    manager_dn = _v("manager")
                    manager_name = ""
                    if manager_dn:
                        try:
                            conn.search(AD_BASE_DN, f'(distinguishedName={manager_dn})', attributes=['displayName'])
                            if conn.entries: manager_name = conn.entries[0].displayName.value or ""
                        except Exception: pass
                    results.append({
                        "displayName":       _v("displayName"),
                        "sAMAccountName":    _v("sAMAccountName"),
                        "mail":              _v("mail"),
                        "title":             _v("title"),
                        "department":        _v("department"),
                        "mobile":            _v("mobile") or _v("telephoneNumber"),
                        "manager_dn":        manager_dn,
                        "manager_name":      manager_name,
                        "distinguishedName": _v("distinguishedName"),
                        "userPrincipalName": _v("userPrincipalName"),
                        "employeeID":        _v("employeeID"),
                    })
                return results
        except Exception as e:
            print(f"[AD] search_user error: {e}")
            return []

    def update_user_profile(self, sam: str, changes: Dict[str, Any]) -> Tuple[bool, str]:
        try:
            dn = self.get_user_dn(sam)
            if not dn: return False, "User not found in AD"
            field_map = {"title":"title", "department":"department", "mobile":"mobile", "manager_dn":"manager"}
            mods = {}
            for key, attr in field_map.items():
                if key in changes:
                    val = changes[key]
                    mods[attr] = [(MODIFY_REPLACE, [val])] if val else [(MODIFY_REPLACE, [])]
            if not mods: return True, "No changes"
            with self._get_connection() as conn:
                conn.modify(dn, mods)
                if conn.result["result"] == 0: return True, "AD profile updated"
                return False, conn.result.get("description", "LDAP error")
        except Exception as e: return False, str(e)
