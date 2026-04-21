"""
config.py — Petrus Technologies Onboarding Tool
Central configuration and default values.
"""

# ── Application ────────────────────────────────────────────────────────────────
APP_TITLE   = "Petrus Technologies | Employee Onboarding Portal"
APP_VERSION = "1.0.0"

# ── Company Defaults ───────────────────────────────────────────────────────────
COMPANY_NAME   = "Petrus Technologies Pvt. Ltd."
EMAIL_DOMAIN   = "petrustechnologies.com"
AD_DOMAIN      = "10.20.30.101"          # DC IP — use IP if DNS resolution fails

# ── Default Credentials ────────────────────────────────────────────────────────
DEFAULT_PASSWORD = "Welcome@123"

# ── Default Address ────────────────────────────────────────────────────────────
DEFAULT_OFFICE         = "Coimbatore"
DEFAULT_STREET         = "511, Sathy Rd, Sivasakthi Colony, Ganapathy"
DEFAULT_CITY           = "Coimbatore"
DEFAULT_STATE          = "Tamil Nadu"
DEFAULT_ZIP            = "641006"
DEFAULT_COUNTRY        = "India"
DEFAULT_COUNTRY_CODE   = "91"          # ADSI country code for India

# ── Active Directory ───────────────────────────────────────────────────────────
AD_ADMIN_USER       = ""    # e.g. "petrustechnologies\\admin" (leave empty for current session)
AD_ADMIN_PASSWORD   = ""    # e.g. "Secret@123"
AD_BASE_DN          = "DC=petrus,DC=local"
AD_PETRUS_USERS_OU  = "OU=Petrus-Users,DC=petrus,DC=local"

# ── License Options (display names) ───────────────────────────────────────────
LICENSE_OPTIONS = [
    "Microsoft 365 Business Basic",
    "Microsoft 365 Business Standard",
]

# ── Employee Types ─────────────────────────────────────────────────────────────
EMPLOYEE_TYPES = ["Full Time", "Part Time", "Contract", "Intern"]

# ── Microsoft Graph API ────────────────────────────────────────────────────────
GRAPH_BASE      = "https://graph.microsoft.com/v1.0"
GRAPH_BETA      = "https://graph.microsoft.com/beta"
GRAPH_RESOURCE  = "https://graph.microsoft.com"

# ── Zoho Enterprise Application ───────────────────────────────────────────────
ZOHO_APP_NAME = "Zoho Accounts"

# ── Connection Polling ─────────────────────────────────────────────────────────
CONNECTION_POLL_INTERVAL = 60   # seconds
