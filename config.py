"""
config.py — Petrus Technologies Employee Onboarding Portal
Central configuration: constants, defaults, and environment settings.

Edit values below to match your organisation's AD / O365 tenant.
"""

# ── Application ───────────────────────────────────────────────────────────────
APP_TITLE   = "Petrus Technologies — Employee Onboarding"
APP_VERSION = "1.0.0"

# ── Company ───────────────────────────────────────────────────────────────────
COMPANY_NAME = "Petrus Technologies Pvt Ltd."
EMAIL_DOMAIN = "petrustechnologies.com"

# ── SharePoint Logging ────────────────────────────────────────────────────────
# Sharing URL for the Excel file containing on-boarding and off-boarding sheets.
SHAREPOINT_FILE_URL = "https://petrustechnologies-my.sharepoint.com/:x:/p/suriya_selvaraj/IQB1AofNsdKzQbWq6rSO163yAXjee8nf0mkKz2Y2VE9_Hto?e=FgmPAQ"

# Optional: Hardcoded IDs for fallback if URL resolution fails
# These can be found in the Graph API response of a successful resolution.
SHAREPOINT_DRIVE_ID = ""
SHAREPOINT_ITEM_ID  = ""

# ── Microsoft Graph API ───────────────────────────────────────────────────────
GRAPH_BASE     = "https://graph.microsoft.com/v1.0"
GRAPH_BETA     = "https://graph.microsoft.com/beta"
GRAPH_RESOURCE = "https://graph.microsoft.com"

# ── Active Directory ──────────────────────────────────────────────────────────
AD_DOMAIN          = "petrus.local"          # FQDN of the AD domain
AD_SERVER          = "10.20.30.101"                      # Optional: Manually specify DC IP or DNS if discovery fails
AD_BASE_DN         = "DC=petrus,DC=local"    # Base Distinguished Name
AD_PETRUS_USERS_OU = "OU=Petrus-Users,DC=petrus,DC=local"

# AD admin credentials (leave empty to use the current Windows session)
AD_ADMIN_USER     = ""
AD_ADMIN_PASSWORD = ""

# ── Default Field Values ──────────────────────────────────────────────────────
DEFAULT_CITY         = "Coimbatore"
DEFAULT_STATE        = "Tamil Nadu"
DEFAULT_ZIP          = "641006"
DEFAULT_COUNTRY      = "India"
DEFAULT_COUNTRY_CODE = 91          # ISO 3166-1 numeric for India
DEFAULT_STREET       = "511, Sathy Rd, Sivasakthi Colony, Ganapathy"
DEFAULT_OFFICE       = "Coimbatore"

# ── Dropdowns / Picklists ─────────────────────────────────────────────────────
LICENSE_OPTIONS = [
    "Microsoft 365 Business Basic",
    "Microsoft 365 Business Standard",
]

# Fallback SKU IDs — used when dynamic fetch cannot match by name.
# Obtained from: Get-MsolAccountSku  or  GET /subscribedSkus
LICENSE_SKU_MAP = {
    "Microsoft 365 Business Basic":    "3b555118-da6a-4418-894f-7df1e2096870",   # O365_BUSINESS_ESSENTIALS
    "Microsoft 365 Business Standard": "f245ecc8-75af-4f8e-b61f-27d8114de5f3",   # O365_BUSINESS_PREMIUM
}

DEPARTMENTS = [
    "Engineering Services",
    "IIOT",
    "Growth",
    "Human Resources",
    "MES Practice",
    "Finance",
    "IT",
    "SCM"
]

EMPLOYEE_TYPES = [
    "Full Time",
    "Part Time",
    "Contractor",
    "Intern",
]

# ── Enterprise Apps ───────────────────────────────────────────────────────────
ZOHO_APP_NAME      = "Zoho Accounts"
ZOHO_APP_OBJECT_ID = "62935978-85f5-4b19-af58-0101be6d8bcc"   # Azure Enterprise App Object ID

# ── Connection Polling ────────────────────────────────────────────────────────
CONNECTION_POLL_INTERVAL  = 120      # seconds between connection re-checks
MAILBOX_WAIT_SECONDS = 10    # Short wait for license to register; proceed immediately
GROUP_RETRY_COUNT = 3       # Number of attempts for group addition
MFA_RETRY_COUNT = 3         # Number of attempts for MFA enablement

# ── AD Group Search ──────────────────────────────────────────────────────────
# Base path for security groups shown in the AD selection
# We search recursively under Petrus-Users to ensure all groups are found
AD_GROUPS_BASE_OU = "OU=Petrus-Users,DC=petrus,DC=local"

# ── Email Notification ────────────────────────────────────────────────────────
DEFAULT_EMAIL_SENDER = "itsupport@petrustechnologies.com"
DEFAULT_EMAIL_CC     = "it@petrustechnologies.com"
WELCOME_EMAIL_SUBJECT = "Welcome to Petrus Technologies - Account Details"
WELCOME_EMAIL_TEMPLATE = """Hi {first_name},

Welcome to Petrus Technologies! We're excited to have you join our team and look forward to supporting you as you begin your journey with us.
To help you get started, please find your account details below:

Petrus Email Account (Microsoft 365):
• Username: {email}
• Temporary Password: {password}

You can log in at: https://www.office.com

Petrus System Login:
• Username: {sam_account_name}
• Password: Same as above

For security reasons, you will be prompted to change your password upon your first login.
If you encounter any issues or need assistance during setup, please don't hesitate to reach out to the IT team. We're here to help ensure a smooth onboarding experience.

Once again, welcome aboard—we're glad to have you with us!

Warm Regards
IT Team
638 4164 343
"""

OFFBOARDING_EMAIL_SUBJECT = "Action Required: Data Confirmation for Off-boarding - {name}"
OFFBOARDING_EMAIL_TEMPLATE = """Hi {manager_name},

As you are aware, one of your team members, Mr. {name}, has exited the organization.

Kindly confirm whether any mailbox data, emails, or files from the account need to be backed up.

If we do not receive any confirmation from your end within 5 days, the account and associated data will be permanently deleted and cannot be recovered thereafter.

Please let us know if any further assistance is required.

Best regards,
IT Team
6384164343
"""
