"""
core/credential_manager.py
Handles MSAL-based authentication and token caching using keyring.
Eliminates dependency on Azure CLI.
"""

import os
import json
import time
import msal
import keyring
from typing import Optional, List, Dict

# Well-known Client ID for Azure CLI - allows login without custom App Registration
CLIENT_ID = "04b07795-8ddb-461a-bbee-02f9e1bf7b46"
AUTHORITY = "https://login.microsoftonline.com/common"

# Resource-specific scopes
SCOPES_GRAPH = ["https://graph.microsoft.com/.default"]
SCOPES_EXO   = ["https://outlook.office365.com/.default"]

SERVICE_NAME = "PetrusOnboarding"
CACHE_KEY    = "msal_cache"

class CredentialManager:
    def __init__(self):
        # Enable broker (WAM) for native Windows authentication
        self._app = msal.PublicClientApplication(
            CLIENT_ID, 
            authority=AUTHORITY,
            token_cache=self._load_cache(),
            enable_broker_on_windows=False # Disable broker for more reliable browser-based login
        )

    def _load_cache(self) -> msal.SerializableTokenCache:
        cache = msal.SerializableTokenCache()
        try:
            encrypted_data = keyring.get_password(SERVICE_NAME, CACHE_KEY)
            if encrypted_data:
                cache.deserialize(encrypted_data)
        except Exception:
            pass
        return cache

    def _save_cache(self, cache: msal.SerializableTokenCache):
        try:
            if cache.has_state_changed:
                keyring.set_password(SERVICE_NAME, CACHE_KEY, cache.serialize())
        except Exception:
            pass

    def get_token(self, scopes: List[str]) -> Optional[str]:
        """Try to get token from cache, or return None if login required."""
        accounts = self._app.get_accounts()
        if not accounts:
            return None

        # Try silent acquisition
        result = self._app.acquire_token_silent(scopes, account=accounts[0])
        self._save_cache(self._app.token_cache)
        
        if result and "access_token" in result:
            return result["access_token"]
        return None

    def login_interactive(self, scopes: List[str], parent_window_handle: Any = None) -> Dict:
        """
        Open native Windows dialog for interactive login (WAM).
        This eliminates the need for a browser tab and closes automatically.
        """
        if parent_window_handle is None:
            # For console applications/servers started from terminal, use the console handle
            parent_window_handle = msal.PublicClientApplication.CONSOLE_WINDOW_HANDLE
            
        # Custom success page that tries to close the tab or redirect back
        # Removed indentation to prevent potential issues with some browser interpretations
        success_tpl = "<html><body style=\"font-family:sans-serif;background:#0f172a;color:white;display:flex;flex-direction:column;align-items:center;justify-content:center;height:100vh;margin:0;\"><div style=\"background:#1e293b;padding:32px;border-radius:12px;border:1px solid rgba(255,255,255,0.1);text-align:center;\"><div style=\"font-size:40px;margin-bottom:16px;\">✅</div><h2 style=\"margin:0 0 8px 0;\">Signed In</h2><p style=\"color:#94a3b8;font-size:0.9rem;\">This window will close automatically.</p></div><script>setTimeout(function(){ window.location.href='http://localhost:8000'; setTimeout(function(){ window.close(); }, 300); }, 500);</script></body></html>"

        result = self._app.acquire_token_interactive(
            scopes=scopes,
            parent_window_handle=parent_window_handle,
            prompt="select_account",
            success_template=success_tpl
        )
        self._save_cache(self._app.token_cache)
        return result

    def logout(self):
        accounts = self._app.get_accounts()
        for account in accounts:
            self._app.remove_account(account)
        self._save_cache(self._app.token_cache)

def save_password(account_name: str, password: str):
    """Store a password securely in the Windows Vault/Keyring."""
    keyring.set_password(SERVICE_NAME, account_name, password)


def get_password(account_name: str) -> Optional[str]:
    """Retrieve a saved password from the Windows Vault/Keyring."""
    return keyring.get_password(SERVICE_NAME, account_name)


# Global instance
cred_manager = CredentialManager()
