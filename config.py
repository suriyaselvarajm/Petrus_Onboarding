"""
<<<<<<< HEAD
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
=======
config.py — Petrus Technologies Employee Onboarding Portal
Central configuration: constants, defaults, and environment settings.

Edit values below to match your organisation's AD / O365 tenant.
"""

# ── Application ───────────────────────────────────────────────────────────────
APP_TITLE   = "Petrus Technologies — Employee Onboarding"
APP_VERSION = "1.0.0"

# ── Company ───────────────────────────────────────────────────────────────────
COMPANY_NAME = "Petrus Technologies Pvt. Ltd."
EMAIL_DOMAIN = "petrustechnologies.com"

# ── Microsoft Graph API ───────────────────────────────────────────────────────
GRAPH_BASE     = "https://graph.microsoft.com/v1.0"
GRAPH_BETA     = "https://graph.microsoft.com/beta"
GRAPH_RESOURCE = "https://graph.microsoft.com"

# ── Active Directory ──────────────────────────────────────────────────────────
AD_DOMAIN          = "petrus.local"          # FQDN of the AD domain
AD_BASE_DN         = "DC=petrus,DC=local"    # Base Distinguished Name
AD_PETRUS_USERS_OU = "OU=Petrus-Users,DC=petrus,DC=local"

# AD admin credentials (leave empty to use the current Windows session)
AD_ADMIN_USER     = ""
AD_ADMIN_PASSWORD = ""

# ── Default Field Values ──────────────────────────────────────────────────────
DEFAULT_PASSWORD     = "Welcome@123"
DEFAULT_CITY         = "Coimbatore"
DEFAULT_STATE        = "Tamil Nadu"
DEFAULT_ZIP          = "641006"
DEFAULT_COUNTRY      = "India"
DEFAULT_COUNTRY_CODE = 91          # ISO 3166-1 numeric for India
DEFAULT_STREET       = "511, Sathy Rd, Sivasakthi Colony, Ganapathy"
DEFAULT_OFFICE       = "Coimbatore"

# ── Dropdowns / Picklists ─────────────────────────────────────────────────────
>>>>>>> 7ae16ae250dc44223ef24c615966296e203a90ad
LICENSE_OPTIONS = [
    "Microsoft 365 Business Basic",
    "Microsoft 365 Business Standard",
]

<<<<<<< HEAD
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
=======
# Fallback SKU IDs — used when dynamic fetch cannot match by name.
# Obtained from: Get-MsolAccountSku  or  GET /subscribedSkus
LICENSE_SKU_MAP = {
    "Microsoft 365 Business Basic":    "3b555118-da6a-4418-894f-7df1e2096870",   # O365_BUSINESS_ESSENTIALS
    "Microsoft 365 Business Standard": "f245ecc8-75af-4f8e-b61f-27d8114de5f3",   # O365_BUSINESS_PREMIUM
}

EMPLOYEE_TYPES = [
    "Full Time",
    "Part Time",
    "Contractor",
    "Intern",
]

<<<<<<< Updated upstream
# ── Enterprise Apps ───────────────────────────────────────────────────────────
ZOHO_APP_NAME      = "Zoho Accounts"
ZOHO_APP_OBJECT_ID = "62935978-85f5-4b19-af58-0101be6d8bcc"   # Azure Enterprise App Object ID

# ── Connection Polling ────────────────────────────────────────────────────────
CONNECTION_POLL_INTERVAL  = 60      # seconds between connection re-checks
MAILBOX_WAIT_SECONDS     = 120     # seconds to wait for Exchange mailbox provisioning
=======
# ── Zoho Enterprise Application ───────────────────────────────────────────────
ZOHO_APP_NAME      = "Zoho Accounts"
ZOHO_APP_OBJECT_ID = "62935978-85f5-4b19-af58-0101be6d8bcc"   # Azure Enterprise App Object ID

# ── License SKU Mapping (fallback) ────────────────────────────────────────────
# Used when dynamic fetch from tenant doesn't match by partNumber.
# Get these from: GET /subscribedSkus  or  Get-MsolAccountSku
LICENSE_SKU_MAP = {
    "Microsoft 365 Business Basic":    "3b555118-da6a-4418-894f-7df1e2096870",   # O365_BUSINESS_ESSENTIALS
    "Microsoft 365 Business Standard": "f245ecc8-75af-4f8e-b61f-27d8114de5f3",   # O365_BUSINESS_PREMIUM
}

# ── Connection Polling ─────────────────────────────────────────────────────────
CONNECTION_POLL_INTERVAL = 60    # seconds
MAILBOX_WAIT_SECONDS    = 120   # seconds to wait for Exchange mailbox provisioning
>>>>>>> Stashed changes
>>>>>>> 7ae16ae250dc44223ef24c615966296e203a90ad
