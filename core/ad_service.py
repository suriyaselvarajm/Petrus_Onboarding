import ldap3
from ldap3 import Server, Connection, ALL, NTLM, SUBTREE, MODIFY_REPLACE
import subprocess
import json
from typing import Optional, List, Dict, Any, Tuple

from config import (
    AD_DOMAIN, AD_SERVER, AD_BASE_DN, AD_PETRUS_USERS_OU,
    COMPANY_NAME, DEFAULT_COUNTRY_CODE,
    AD_ADMIN_USER, AD_ADMIN_PASSWORD,
)

import os


ERROR_PREFIX = "ERROR:"

# ── AD Service (LDAP3 Implementation) ──────────────────────────────────────────

class ADService:

    def __init__(self):
        self._connected = False
        self._server_address = AD_SERVER or AD_DOMAIN
        self._session_user = None
        self._session_password = None

    def _get_connection(self) -> Connection:
        """Create and bind an LDAP connection using config or session credentials."""
        server = Server(self._server_address, get_info=ALL)
        
        user = self._session_user or AD_ADMIN_USER
        password = self._session_password or AD_ADMIN_PASSWORD

        if not user:
            raise ValueError("Authentication required. Please sign in.")

        if user and "\\" not in user and "@" not in user:
            user = f"{user}@{AD_DOMAIN}"

        # Use SIMPLE authentication
        conn = Connection(
            server, 
            user=user, 
            password=password, 
            authentication=ldap3.SIMPLE,
            auto_bind=True
        )
        return conn

    # ── Connection ────────────────────────────────────────────────────────────

    def test_connection(self) -> Tuple[bool, str]:
        if not (self._session_user or AD_ADMIN_USER):
            return False, "Authentication required"
        try:
            with self._get_connection() as conn:
                self._connected = True
                return True, f"Connected to {self._server_address}"
        except Exception as e:
            return False, str(e)

    def authenticate_and_check_permission(self, username: str, password: str) -> Tuple[bool, str]:
        """Verify credentials and check 'Domain Admins' membership via LDAP."""
        try:
            server = Server(self._server_address, get_info=ALL)
            
            # Format user for SIMPLE bind (UPN format: user@domain)
            auth_user = username
            if "\\" not in username and "@" not in username:
                auth_user = f"{username}@{AD_DOMAIN}"
            
            # Use SIMPLE authentication
            with Connection(server, user=auth_user, password=password, authentication=ldap3.SIMPLE) as conn:
                if not conn.bind():
                    return False, "Authentication Failed: Invalid credentials"
                
                # Check group membership
                conn.search(
                    search_base=AD_BASE_DN,
                    search_filter=f'(&(objectClass=user)(sAMAccountName={username}))',
                    attributes=['memberOf', 'distinguishedName']
                )
                if not conn.entries:
                    return False, "User not found in directory"
                
                user_entry = conn.entries[0]
                groups = user_entry.memberOf.value if 'memberOf' in user_entry else []
                is_admin = any('CN=Domain Admins' in g for g in groups)
                
                if is_admin:
                    # Save these credentials for the current session
                    self._session_user = username
                    self._session_password = password
                    self._connected = True
                    return True, "Authenticated and verified as Domain Admin"
                return False, "User authenticated but is not a member of 'Domain Admins'"
        except Exception as e:
            return False, f"Error checking permissions: {str(e)}"

    def check_ad_sync(self) -> Tuple[bool, str]:
        """
        Passive check for AD Sync status.
        Removed PowerShell call to bypass SentinelOne security blocks.
        """
        return False, "Status Unknown (Security Hardened)"

    # ── Query helpers ─────────────────────────────────────────────────────────

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
        
        # We try a multi-stage search for maximum reliability
        bases_to_try = []
        if base: bases_to_try.append(base)
        if AD_PETRUS_USERS_OU and AD_PETRUS_USERS_OU not in bases_to_try:
            bases_to_try.append(AD_PETRUS_USERS_OU)
            
        search_filter = '(|(objectClass=group)(objectCategory=group))'
        
        for current_base in bases_to_try:
            print(f"[DEBUG] AD get_groups: Attempting search in '{current_base}'...")
            try:
                with self._get_connection() as conn:
                    conn.search(
                        search_base=current_base,
                        search_filter=search_filter,
                        search_scope=SUBTREE,
                        attributes=['cn', 'name', 'sAMAccountName', 'distinguishedName', 'displayName']
                    )
                    
                    if not conn.entries:
                        print(f"[DEBUG] AD get_groups: No groups found in '{current_base}'.")
                        continue
                        
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
                                "GroupCategory": "Security" # Default to Security as fallback
                            })
                    
                    if results:
                        print(f"[DEBUG] AD get_groups: Successfully found {len(results)} groups in '{current_base}'.")
                        return results
            except Exception as e:
                print(f"[DEBUG] AD get_groups: Search failed in '{current_base}': {str(e)}")
                
        return []

    def get_manager_dn(self, upn: str) -> Optional[str]:
        try:
            with self._get_connection() as conn:
                conn.search(AD_BASE_DN, f'(userPrincipalName={upn})', attributes=['distinguishedName'])
                return conn.entries[0].distinguishedName.value if conn.entries else None
        except Exception:
            return None

    def get_user_dn(self, sam: str) -> Optional[str]:
        try:
            with self._get_connection() as conn:
                conn.search(AD_BASE_DN, f'(sAMAccountName={sam})', attributes=['distinguishedName'])
                return conn.entries[0].distinguishedName.value if conn.entries else None
        except Exception:
            return None

    # ── Create User ───────────────────────────────────────────────────────────

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
            'physicalDeliveryOfficeName': data.get("office", "Coimbatore"),
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
            'description': f'Created by Petrus Onboarding Tool on {os.name}'
        }
        
        if manager_dn:
            attrs['manager'] = manager_dn

        # Proxy addresses (SMTP primary + smtp:alias)
        emp_id = data.get("employee_id", "")
        proxy_addrs = [f"SMTP:{email}"]
        if emp_id:
            domain = email.split("@")[1] if "@" in email else ""
            if domain:
                proxy_addrs.append(f"smtp:{emp_id}@{domain}")
        attrs['proxyAddresses'] = proxy_addrs

        try:
            with self._get_connection() as conn:
                # 1. Add user
                if not conn.add(user_dn, attributes=attrs):
                    return False, f"Failed to create user object: {conn.result['description']}"
                
                # 2. Set password (requires LDAPS or special bind)
                # Note: In some environments, this may fail if not using SSL/TLS
                encoded_pwd = f'"{password}"'.encode('utf-16-le')
                conn.modify(user_dn, {'unicodePwd': [(MODIFY_REPLACE, [encoded_pwd])]})
                
                # 3. Enable account and set 'Change Password At Logon' via pwdLastSet=0
                conn.modify(user_dn, {
                    'userAccountControl': [(MODIFY_REPLACE, [512])],
                    'pwdLastSet': [(MODIFY_REPLACE, [0])]
                })
                
                return True, sam
        except Exception as e:
            return False, str(e)

    def disable_user(self, sam: str) -> Tuple[bool, str]:
        try:
            dn = self.get_user_dn(sam)
            if not dn: return False, "User not found"
            with self._get_connection() as conn:
                # 514 = Normal Account + Disabled
                conn.modify(dn, {'userAccountControl': [(MODIFY_REPLACE, [514])]})
                return True, "AD account disabled"
        except Exception as e:
            return False, str(e)

    def set_proxy_addresses(self, sam: str, addresses: List[str]) -> Tuple[bool, str]:
        try:
            dn = self.get_user_dn(sam)
            if not dn: return False, "User not found"
            with self._get_connection() as conn:
                conn.modify(dn, {'proxyAddresses': [(MODIFY_REPLACE, addresses)]})
                return True, "Proxy addresses updated in AD"
        except Exception as e:
            return False, str(e)

    def add_user_to_group(self, sam: str, group_dn: str) -> Tuple[bool, str]:
        try:
            user_dn = self.get_user_dn(sam)
            if not user_dn: return False, "User not found"
            with self._get_connection() as conn:
                conn.modify(group_dn, {'member': [(ldap3.MODIFY_ADD, [user_dn])]})
                return True, "Added to AD group"
        except Exception as e:
            return False, str(e)

    def delete_user(self, sam: str) -> Tuple[bool, str]:
        try:
            dn = self.get_user_dn(sam)
            if not dn: return False, "User not found"
            with self._get_connection() as conn:
                conn.delete(dn)
                return True, "AD account deleted"
        except Exception as e:
            return False, str(e)


