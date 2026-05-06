"""
core/credential_manager.py
Handles secure storage of passwords using the Windows Credential Manager (keyring).
"""

import keyring
from typing import Optional

SERVICE_NAME = "PetrusOnboardingTool"

def save_password(email: str, password: str):
    """Save a password securely for the given email."""
    if not email or not password:
        return
    try:
        keyring.set_password(SERVICE_NAME, email, password)
    except Exception:
        pass

def get_password(email: str) -> Optional[str]:
    """Retrieve the password for the given email."""
    if not email:
        return None
    try:
        return keyring.get_password(SERVICE_NAME, email)
    except Exception:
        return None

def delete_password(email: str):
    """Remove the password for the given email."""
    if not email:
        return
    try:
        keyring.delete_password(SERVICE_NAME, email)
    except Exception:
        pass
