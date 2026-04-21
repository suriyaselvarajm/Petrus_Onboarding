# Petrus Technologies — Employee Onboarding Portal
## A GUI automation tool for creating new employees in O365 and Active Directory

---

## Requirements

| Component | Requirement |
|---|---|
| OS | **Windows** (domain-joined machine) |
| Python | 3.10 or higher |
| Azure CLI | Installed + logged in as **Global Admin** |
| RSAT | "RSAT: Active Directory Domain Services and Lightweight Directory Services Tools" |
| Network | Access to O365 tenant + AD domain controller |

---

## First-Time Setup (Run Once)

1. **Right-click `setup.bat`** → **Run as Administrator**
   - Installs Python packages
   - Installs Azure CLI (via winget if missing)
   - Installs RSAT AD PowerShell module

2. When setup completes, run:
   ```
   python main.py
   ```

3. A **browser window** will open automatically for Azure admin login.
   Sign in with your **Global Admin** account.

---

## How It Works

### Startup Flow
```
python main.py
  │
  ├─ Check Python packages  → install if missing
  ├─ Check Azure CLI        → install if missing
  ├─ Check RSAT AD module   → install if missing
  ├─ Check az login         → open browser if not authenticated
  │
  ├─ Test O365 connection  (Graph API /me)
  ├─ Test AD connection    (Get-ADDomain via PowerShell)
  │
  └─ Show onboarding form ONLY when both are connected
```

### User Creation Flow (in order)
1. ✅ Create O365 user (Microsoft Graph API)
2. ✅ Assign license (Business Basic or Standard)
3. ✅ Enable MFA (per-user, Graph beta API)
4. ✅ Set reporting manager
5. ✅ Add to selected O365 groups
6. ✅ Add to Zoho Accounts enterprise application
7. ✅ Create AD user (PowerShell `New-ADUser`)
8. ✅ Set proxy addresses (`SMTP:email` + `smtp:empid@domain`)
9. ✅ Add to selected AD groups

### Form Features
| Feature | How |
|---|---|
| Email auto-generation | Types in First/Last → auto-fills email |
| Duplicate email check | Real-time API check as you type |
| Groups dropdown | Fetched live from Azure / AD |
| AD OU selector | Fetched live from Active Directory |
| AD path preview | Updates as you type the name |
| Alias auto-generation | Filled when Employee ID is entered |
| Calendar date picker | Joining Date + Hire Date |
| Connection status bar | Live, refreshed every 60 seconds |

---

## File Structure

```
Petrus_Onboarding/
├── main.py                    Entry point
├── config.py                  Constants & defaults
├── requirements.txt           Python dependencies
├── setup.bat                  One-click setup (run as Admin)
├── core/
│   ├── dependency_checker.py  Checks & installs dependencies
│   ├── o365_service.py        Microsoft Graph API operations
│   ├── ad_service.py          PowerShell Active Directory operations
│   └── connection_manager.py  Connection monitoring & polling
└── gui/
    ├── styles.py              Dark theme styles
    ├── splash.py              Startup / install screen
    ├── user_form.py           Main onboarding form
    └── app.py                 Main window
```

---

## Authentication

This tool uses **Azure CLI** for authentication — no App Registration needed.
After `az login` with your admin account, all API calls use your delegated permissions.

The tool requires:
- `User.ReadWrite.All`
- `Group.ReadWrite.All`
- `Directory.ReadWrite.All`
- `AppRoleAssignment.ReadWrite.All`

All of these are available to a **Global Admin** via the CLI.

---

## Troubleshooting

| Problem | Solution |
|---|---|
| "O365: Not authenticated" | Run `az login` in a terminal, then refresh |
| "AD: Cannot connect" | Ensure you're on the domain / VPN |
| Groups not loading | Check O365 connection; click ↻ Refresh |
| OUs not loading | Ensure RSAT is installed and AD is reachable |
| MFA failed | Try manually or check tenant MFA policy |
| Zoho not found | Verify "Zoho Accounts" exists in Azure Enterprise Apps |
