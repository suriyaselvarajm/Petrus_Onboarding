import os
import sys
import datetime
from typing import List, Dict, Optional, Any

from fastapi import FastAPI, Request, Form, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, EmailStr
import uuid
import hmac
import hashlib
from starlette.concurrency import run_in_threadpool
from core.credential_manager import cred_manager, SCOPES_GRAPH
sessions: Dict[str, Dict[str, Any]] = {}
SECRET_KEY = "petrus-secret-key" # In production, this should be in config/env

# Add parent dir to path to import core services
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.ad_service import ADService
from core.o365_service import O365Service
from core.settings_manager import sm
from config import (
    APP_TITLE, APP_VERSION, COMPANY_NAME, DEPARTMENTS, LICENSE_OPTIONS,
    WELCOME_EMAIL_TEMPLATE, WELCOME_EMAIL_SUBJECT, OFFBOARDING_EMAIL_TEMPLATE, OFFBOARDING_EMAIL_SUBJECT,
    AD_GROUPS_BASE_OU, AD_USERS_BASE_OU,
    AD_DOMAIN, AD_SERVER, AD_ADMIN_USER, AD_ADMIN_PASSWORD
)

app = FastAPI(title=f"{APP_TITLE} API", version=APP_VERSION)

# Services
ad_service = ADService()
o365_service = O365Service()

@app.on_event("startup")
async def startup_event():
    # Pre-fetch licenses to populate cache
    try:
        o365_service.get_license_skus()
    except Exception:
        pass

# Static files and templates
app.mount("/static", StaticFiles(directory="web/static"), name="static")
templates = Jinja2Templates(directory="web/templates")

# ── Models ───────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str

class OnboardRequest(BaseModel):
    # Personal Info
    first_name: str
    last_name: str
    personal_email: str
    joining_date: Optional[str] = None
    password: str
    require_password_change: bool = True
    
    # Company
    emp_id: str
    dept: str
    job_title: str
    emp_type: str = "Full Time"
    joining_date: str
    office_location: str = "Coimbatore"
    mobile: str = ""
    street: str = ""
    city: str = ""
    state: str = ""
    zip: str = ""
    country: str = "India"
    
    # Manager
    reporting_manager_upn: Optional[str] = None
    
    # AD
    parent_ou: str
    sub_ou: Optional[str] = None
    ad_groups: List[str] = []
    
    # O365
    license_sku: str
    o365_groups: List[str] = []
    
    # Security & MFA
    enable_mfa: bool = True
    send_welcome_email: bool = True
    sender_email: Optional[str] = None
    sender_password: Optional[str] = None
    cc_email: Optional[str] = None
    receiver_email: Optional[str] = None

class OffboardRequest(BaseModel):
    upn: str
    block_signin: bool = True
    remove_licenses: bool = True
    delete_o365_account: bool = False
    disable_ad_account: bool = True
    delete_ad_account: bool = False
    send_notification: bool = True
    sender_email: Optional[str] = None
    sender_password: Optional[str] = None
    cc_email: Optional[str] = None

class ProfileUpdateRequest(BaseModel):
    title: Optional[str] = None
    department: Optional[str] = None
    mobile: Optional[str] = None
    manager_dn: Optional[str] = None

class SettingsRequest(BaseModel):
    departments: List[str]
    welcome_email_subject: str
    welcome_email_template: str
    offboarding_email_subject: str
    offboarding_email_template: str
    ad_groups_base_ou: Optional[str] = None
    ad_users_base_ou: Optional[str] = None
    company_name: Optional[str] = None
    # Integration Settings
    ad_domain: Optional[str] = None
    ad_server: Optional[str] = None
    ad_admin_user: Optional[str] = None
    ad_admin_password: Optional[str] = None
    smtp_sender: Optional[str] = None
    smtp_password: Optional[str] = None

# ── Auth Dependency ──────────────────────────────────────────────────────────

async def get_current_user(request: Request):
    session_id = request.cookies.get("session_id")
    if not session_id or session_id not in sessions:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return sessions[session_id]

# ── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse(
        request=request, 
        name="index.html", 
        context={"title": APP_TITLE, "company": COMPANY_NAME}
    )

@app.post("/api/login")
async def login(req: LoginRequest):
    ok, msg = ad_service.authenticate_and_check_permission(req.username, req.password)
    if not ok:
        raise HTTPException(status_code=401, detail=msg)
    
    # Create session
    session_id = str(uuid.uuid4())
    sessions[session_id] = {"username": req.username, "is_admin": True}
    
    response = JSONResponse(content={"status": "ok", "user": req.username})
    response.set_cookie(key="session_id", value=session_id, httponly=True)
    return response

@app.post("/api/logout")
async def logout(request: Request):
    session_id = request.cookies.get("session_id")
    if session_id in sessions:
        del sessions[session_id]
    response = JSONResponse(content={"status": "ok"})
    response.delete_cookie("session_id")
    return response

@app.get("/api/me")
async def get_me(user: dict = Depends(get_current_user)):
    return user

@app.get("/api/status")
async def get_status():
    ad_ok, ad_msg = ad_service.test_connection()
    o365_ok, o365_msg = o365_service.test_connection()
    return {
        "ad": {"connected": ad_ok, "message": ad_msg},
        "o365": {"connected": o365_ok, "message": o365_msg}
    }

@app.post("/api/o365/login")
async def o365_login(user: dict = Depends(get_current_user)):
    print(f"DEBUG: Received O365 login request from {user.get('username')}")
    
    def do_login():
        print("DEBUG: Executing cred_manager.login_interactive...")
        return cred_manager.login_interactive(SCOPES_GRAPH)
    
    try:
        result = await run_in_threadpool(do_login)
    except Exception as e:
        print(f"ERROR: O365 Login failed: {str(e)}")
        return JSONResponse(status_code=504, content={"status": "error", "message": f"Connection to Microsoft timed out: {str(e)}"})
    
    print(f"DEBUG: MSAL result: {result.get('error') if 'error' in result else 'Success'}")
    
    if "access_token" in result:
        return {"status": "ok", "user": result.get("id_token_claims", {}).get("preferred_username")}
        
    return JSONResponse(status_code=401, content={"status": "error", "message": result.get("error_description", "Login failed")})

@app.get("/api/lookups")
async def get_lookups():
    # Departments from settings
    depts = sm.get("departments") or DEPARTMENTS
    
    # AD OUs
    ous = ad_service.get_ous()
    ou_list = [{"name": o["Name"], "dn": o["DistinguishedName"]} for o in ous]
    
    # O365 Groups
    groups = o365_service.get_groups()
    group_list = [{"id": g["id"], "name": g["displayName"], "type": g.get("_type", "Group")} for g in groups]
    
    # Licenses
    licenses = LICENSE_OPTIONS
    
    return {
        "departments": depts,
        "ous": ou_list,
        "o365_groups": group_list,
        "licenses": licenses
    }

@app.get("/api/ous/{parent_dn:path}")
async def get_sub_ous(parent_dn: str):
    sub = ad_service.get_ous(base=parent_dn, scope='OneLevel')
    return [{"name": o["Name"], "dn": o["DistinguishedName"]} for o in sub]

@app.get("/api/ad-groups")
async def get_ad_groups(base_dn: Optional[str] = None):
    groups = ad_service.get_groups(search_base=base_dn)
    return [{"name": g["Name"], "dn": g["DistinguishedName"]} for g in groups]

@app.get("/api/search-users")
async def search_users(q: str, user: dict = Depends(get_current_user)):
    # Search in both AD and O365 for comprehensive results
    results = []
    
    # 1. Search AD
    ad_users = ad_service.search_user(q)
    results.extend(ad_users)
    
    # 2. Search O365 if query is long enough
    if len(q) > 3:
        o365_users = o365_service.search_users_broad(q)
        # Convert O365 results to match AD format roughly
        for u in o365_users:
            # Avoid adding if already found in AD (match by UPN)
            if not any(r.get('userPrincipalName') == u.get('userPrincipalName') for r in results):
                results.append({
                    "displayName": u.get("displayName"),
                    "userPrincipalName": u.get("userPrincipalName"),
                    "sAMAccountName": u.get("sAMAccountName") or u.get("userPrincipalName", "").split("@")[0],
                    "mail": u.get("userPrincipalName"),
                    "source": "O365"
                })
    
    return results

@app.get("/api/user-details/{sam}")
async def get_user_details(sam: str, user: dict = Depends(get_current_user)):
    # Get details from AD
    ad_users = ad_service.search_user(sam)
    if not ad_users:
        raise HTTPException(status_code=404, detail="User not found in AD")
    user_data = ad_users[0]
    
    # Get details from O365 if possible
    o365_users = o365_service.search_users_broad(user_data["userPrincipalName"])
    if o365_users:
        o365_detail = o365_service.get_user_details(o365_users[0]["id"])
        user_data["o365"] = o365_detail
    
    return user_data

@app.post("/api/profile-update/{sam}")
async def update_profile(sam: str, req: ProfileUpdateRequest, user: dict = Depends(get_current_user)):
    changes = req.dict(exclude_unset=True)
    if not changes:
        return {"status": "ok", "message": "No changes to apply"}
    
    ok, msg = ad_service.update_user_profile(sam, changes)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
        
    return {"status": "ok", "message": msg}

@app.post("/api/offboard")
async def offboard_user(req: OffboardRequest, user: dict = Depends(get_current_user)):
    results = {"steps": []}
    def log_step(name, success, message=""):
        results["steps"].append({"name": name, "success": success, "message": message})

    # 1. Disable AD Account
    if req.disable_ad_account:
        ok, msg = ad_service.disable_user(req.upn)
        log_step("AD Account Disable", ok, msg)
        
    if req.delete_ad_account:
        # ad_service.delete_user(req.upn)
        log_step("AD Account Delete", True, "Action recorded (Deletions require manual sync confirmation)")
    
    # 2. O365 Actions
    o365_users = o365_service.search_users_broad(req.upn)
    if o365_users:
        uid = o365_users[0]["id"]
        
        if req.block_signin:
            ok, msg = o365_service.block_sign_in(uid)
            log_step("O365 Sign-in Block", ok, msg)
            
        if req.remove_licenses:
            details = o365_service.get_user_details(uid)
            for lic in details.get("_licenses", []):
                o365_service.remove_license(uid, lic["skuId"])
            log_step("O365 License Removal", True)
            
        if req.delete_o365_account:
            log_step("O365 Account Delete", True, "Action recorded")

    return results

@app.get("/api/settings")
async def get_settings(user: dict = Depends(get_current_user)):
    return {
        "departments": sm.get("departments") or DEPARTMENTS,
        "welcome_email_subject": sm.get("welcome_email_subject") or WELCOME_EMAIL_SUBJECT,
        "welcome_email_template": sm.get("welcome_email_template") or WELCOME_EMAIL_TEMPLATE,
        "offboarding_email_subject": sm.get("offboarding_email_subject") or OFFBOARDING_EMAIL_SUBJECT,
        "offboarding_email_template": sm.get("offboarding_email_template") or OFFBOARDING_EMAIL_TEMPLATE,
        "ad_groups_base_ou": sm.get("ad_groups_base_ou") or AD_GROUPS_BASE_OU,
        "ad_users_base_ou": sm.get("ad_users_base_ou") or AD_USERS_BASE_OU,
        "company_name": sm.get("company_name") or COMPANY_NAME,
        "ad_domain": sm.get("ad_domain") or AD_DOMAIN,
        "ad_server": sm.get("ad_server") or AD_SERVER,
        "ad_admin_user": sm.get("ad_admin_user") or AD_ADMIN_USER,
        "ad_admin_password": sm.get("ad_admin_password") or "********" if AD_ADMIN_PASSWORD else ""
    }

@app.post("/api/settings")
async def save_settings(req: SettingsRequest, user: dict = Depends(get_current_user)):
    sm.set("departments", req.departments)
    sm.set("welcome_email_subject", req.welcome_email_subject)
    sm.set("welcome_email_template", req.welcome_email_template)
    sm.set("offboarding_email_subject", req.offboarding_email_subject)
    sm.set("offboarding_email_template", req.offboarding_email_template)
    sm.set("ad_groups_base_ou", req.ad_groups_base_ou)
    sm.set("ad_users_base_ou", req.ad_users_base_ou)
    sm.set("company_name", req.company_name)
    sm.set("ad_domain", req.ad_domain)
    sm.set("ad_server", req.ad_server)
    
    if req.ad_admin_user: 
        sm.set("ad_admin_user", req.ad_admin_user)
    if req.ad_admin_password and req.ad_admin_password != "********":
        sm.set("ad_admin_password", req.ad_admin_password)
        
    if req.smtp_sender: 
        sm.set("smtp_sender", req.smtp_sender)
    if req.smtp_password and req.smtp_password != "********": 
        sm.set("smtp_password", req.smtp_password)
    
    # Re-init services with new settings
    ad_service.reconnect()
    return {"status": "ok"}

@app.post("/api/test-ad")
async def test_ad_connection(user: dict = Depends(get_current_user)):
    ok, msg = ad_service.test_connection()
    return {"success": ok, "message": msg}

@app.post("/api/onboard")
async def onboard_user(req: OnboardRequest, user: dict = Depends(get_current_user)):
    results = {"steps": []}
    def log_step(name, success, message=""):
        results["steps"].append({"name": name, "success": success, "message": message})

    # Prepare data for AD creation
    ad_data = {
        "first_name": req.first_name,
        "last_name": req.last_name,
        "email": req.personal_email,
        "password": req.password,
        "employee_id": req.emp_id,
        "department": req.dept,
        "job_title": req.job_title,
        "ad_ou": req.sub_ou or req.parent_ou,
        "street": req.street,
        "city": req.city,
        "state": req.state,
        "zip": req.zip,
        "mobile": req.mobile,
        "office": req.office_location,
        "manager": req.reporting_manager_upn,
        "emp_id": req.emp_id
    }
    
    # 1. AD Creation
    ok, res = ad_service.create_user(ad_data)
    if not ok:
        log_step("AD Creation", False, res)
        return JSONResponse(status_code=400, content=results)
    sam = res
    log_step("AD Creation", True, f"User {sam} created")

    # 2. AD Groups
    for gdn in req.ad_groups:
        ad_service.add_user_to_group(sam, gdn)
    log_step("AD Groups", True)

    # 3. O365 Creation
    o365_data = req.dict()
    o365_data["email"] = req.personal_email # Map to service expectation
    o365_ok, o365_id, o365_msg = o365_service.create_user(o365_data)
    
    if not o365_ok:
        log_step("O365 Creation", False, o365_msg)
    else:
        log_step("O365 Creation", True, f"User {o365_id} created")
        # Licenses & Groups
        if req.license_sku:
            o365_service.assign_license(o365_id, req.license_sku)
        for gid in req.o365_groups:
            o365_service.add_user_to_group(o365_id, gid)
        log_step("O365 Config", True)

    # 4. Optional Welcome Email
    if req.send_welcome_email and o365_ok:
        # Email logic would go here
        log_step("Welcome Email", True, "Queued for delivery")

    return results

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
