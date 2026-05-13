/**
 * web/static/js/app.js
 * Comprehensive Single Page Application Logic for Petrus Onboarding
 */

const state = {
    user: null,
    currentView: 'dashboard',
    status: { ad: { connected: false }, o365: { connected: false } },
    lookups: { departments: [], ous: [], o365_groups: [], licenses: [] },
    settings: {},
    isLoginInProgress: false
};

// ── Views ───────────────────────────────────────────────────────────────────

const views = {
    dashboard: `
        <div class="card">
            <h3><i data-lucide="layout-grid" style="color: var(--primary)"></i> Command Center</h3>
            <p style="color: var(--text-secondary); margin-bottom: 32px;">System overview and service health status.</p>
            
            <div class="grid-2">
                <div class="stat-card card" style="padding: 24px; margin-bottom: 0;">
                    <div class="stat-icon"><i data-lucide="activity"></i></div>
                    <div style="font-size: 0.85rem; color: var(--text-dim); text-transform: uppercase; letter-spacing: 1px;">Service Health</div>
                    <div style="font-size: 1.2rem; font-weight: 700; margin-top: 8px;" id="dash-status">Checking...</div>
                    <button id="o365-reconnect-btn" class="primary-btn" style="margin-top: 20px; width: 100%; justify-content: center; display: none;">
                        <i data-lucide="key"></i> Connect M365
                    </button>
                </div>
                <div class="stat-card card" style="padding: 24px; margin-bottom: 0;">
                    <div class="stat-icon"><i data-lucide="user-check"></i></div>
                    <div style="font-size: 0.85rem; color: var(--text-dim); text-transform: uppercase; letter-spacing: 1px;">Authenticated Session</div>
                    <div style="font-size: 1.2rem; font-weight: 700; margin-top: 8px;" id="dash-user">...</div>
                </div>
            </div>
        </div>
        
        <div id="activity-log" style="display: none;">
            <div class="card">
                <h3><i data-lucide="clipboard-list" style="color: var(--primary)"></i> System Notifications</h3>
                <div id="activity-list" style="margin-top: 16px;"></div>
            </div>
        </div>

        <div class="card">
            <h3><i data-lucide="shield-check" style="color: var(--success)"></i> System Health Monitor</h3>
            <table style="width: 100%; border-collapse: collapse; margin-top: 16px;">
                <thead>
                    <tr style="text-align: left; color: var(--text-dim); font-size: 0.8rem; border-bottom: 1px solid var(--border-color);">
                        <th style="padding: 12px;">SERVICE</th>
                        <th style="padding: 12px;">STATUS</th>
                        <th style="padding: 12px;">LATENCY</th>
                    </tr>
                </thead>
                <tbody style="font-size: 0.9rem;">
                    <tr style="border-bottom: 1px solid var(--border-color);">
                        <td style="padding: 12px; display: flex; align-items: center; gap: 8px;">
                            <i data-lucide="server" style="width: 14px; color: var(--primary)"></i> AD Controller
                        </td>
                        <td style="padding: 12px;" id="health-ad-status">Active</td>
                        <td style="padding: 12px; color: var(--text-dim)">12ms</td>
                    </tr>
                    <tr style="border-bottom: 1px solid var(--border-color);">
                        <td style="padding: 12px; display: flex; align-items: center; gap: 8px;">
                            <i data-lucide="cloud" style="width: 14px; color: var(--primary)"></i> MS Graph API
                        </td>
                        <td style="padding: 12px;" id="health-o365-status">Operational</td>
                        <td style="padding: 12px; color: var(--text-dim)">145ms</td>
                    </tr>
                    <tr>
                        <td style="padding: 12px; display: flex; align-items: center; gap: 8px;">
                            <i data-lucide="mail" style="width: 14px; color: var(--primary)"></i> SMTP Relay
                        </td>
                        <td style="padding: 12px; color: var(--success)">Idle</td>
                        <td style="padding: 12px; color: var(--text-dim)">--</td>
                    </tr>
                </tbody>
            </table>
        </div>
    `,
    onboarding: `
        <form id="onboard-form" class="parity-form">
            <div class="onboard-layout">
                <div class="onboard-col">
                    <div class="card">
                        <h3>👤 Personal Information</h3>
                        <div class="grid-2">
                            <div class="form-group">
                                <label>First Name *</label>
                                <input type="text" id="onboard-fname" name="first_name" required placeholder="John">
                            </div>
                            <div class="form-group">
                                <label>Last Name *</label>
                                <input type="text" id="onboard-lname" name="last_name" required placeholder="Doe">
                            </div>
                        </div>
                        <div class="form-group">
                            <label>Primary Email * (firstname.lastname@petrustechnologies.com)</label>
                            <div style="display: flex; gap: 8px;">
                                <input type="email" id="onboard-email" name="personal_email" required readonly style="background: rgba(255,255,255,0.05); flex: 1;">
                                <div id="email-status" style="display: flex; align-items: center; font-size: 0.8rem;"></div>
                            </div>
                        </div>
                        <div class="grid-2">
                            <div class="form-group">
                                <label>Joining Date *</label>
                                <input type="date" id="onboard-joining" name="joining_date" required>
                            </div>
                            <div class="form-group">
                                <label>Password *</label>
                                <div style="display: flex; gap: 8px;">
                                    <input type="text" id="onboard-pwd" name="password" required style="flex: 1;">
                                    <button type="button" class="secondary-btn" onclick="generatePassword()" style="padding: 0 12px;"><i data-lucide="refresh-cw" style="width: 14px;"></i></button>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="card">
                        <h3>📍 Profile & Work Location</h3>
                        <div class="grid-2">
                            <div class="form-group">
                                <label>Office *</label>
                                <select id="onboard-office" name="office_location" required>
                                    <option value="Coimbatore">Coimbatore</option>
                                    <option value="Bangalore">Bangalore</option>
                                </select>
                            </div>
                            <div class="form-group">
                                <label>Employee Type *</label>
                                <select name="emp_type" required>
                                    <option value="Full Time">Full Time</option>
                                    <option value="Intern">Intern</option>
                                    <option value="Contractor">Contractor</option>
                                </select>
                            </div>
                        </div>
                        <div class="grid-2">
                            <div class="form-group">
                                <label>Job Title / Designation *</label>
                                <input type="text" name="job_title" required placeholder="Software Engineer">
                            </div>
                            <div class="form-group">
                                <label>Department *</label>
                                <select name="dept" class="dept-select-lookup" required></select>
                            </div>
                        </div>
                        <div class="grid-2">
                            <div class="form-group">
                                <label>Mobile Number (10 digits) *</label>
                                <input type="text" id="onboard-mobile" name="mobile" required maxlength="10" placeholder="9876543210">
                            </div>
                            <div class="form-group">
                                <label>Employee ID *</label>
                                <input type="text" id="onboard-emp-id" name="emp_id" required placeholder="PT001">
                            </div>
                        </div>
                        
                        <div id="office-address-card" style="padding: 16px; background: rgba(255,255,255,0.02); border-radius: 8px; font-size: 0.85rem; color: var(--text-dim);">
                            <div id="office-address-preview">
                                <strong>Coimbatore Office:</strong><br>
                                511, Sathy Rd, Sivasakthi Colony, Ganapathy, Coimbatore - 641006
                            </div>
                            <input type="hidden" name="street" id="addr-street" value="511, Sathy Rd, Sivasakthi Colony, Ganapathy">
                            <input type="hidden" name="city" id="addr-city" value="Coimbatore">
                            <input type="hidden" name="state" id="addr-state" value="Tamil Nadu">
                            <input type="hidden" name="zip" id="addr-zip" value="641006">
                        </div>
                    </div>
                </div>

                <div class="onboard-col">
                    <div class="card">
                        <h3>👥 Management & Access</h3>
                        <div class="form-group">
                            <label>Reporting Manager *</label>
                            <div style="position: relative;">
                                <input type="text" id="mgr-search" placeholder="Type name to search...">
                                <div id="mgr-results" class="multi-select-list" style="display: none; position: absolute; width: 100%; z-index: 100; max-height: 200px; overflow-y: auto;"></div>
                            </div>
                            <div id="mgr-selected" style="margin-top: 12px; padding: 10px; background: rgba(99,102,241,0.1); border-radius: 8px; display: none; align-items: center; justify-content: space-between;">
                                <span id="mgr-name-display" style="font-size: 0.9rem; font-weight: 600;"></span>
                                <input type="hidden" name="reporting_manager_upn" id="onboard-mgr-upn">
                                <button type="button" class="refresh-btn" onclick="clearManager()"><i data-lucide="x" style="width: 14px;"></i></button>
                            </div>
                        </div>

                        <div class="form-group">
                            <label>AD Creation Path (Parent OU) *</label>
                            <select name="parent_ou" class="ou-select-lookup" required></select>
                        </div>
                        
                        <div class="form-group">
                            <label>Microsoft 365 License *</label>
                            <select name="license_sku" class="license-select-lookup" required></select>
                        </div>
                    </div>

                    <div class="card">
                        <h3>🛡️ Group Access & Security</h3>
                        <div class="form-group">
                            <label>AD Security Groups</label>
                            <div class="ad-groups-lookup multi-select-list" style="max-height: 120px; overflow-y: auto;"></div>
                            <div id="ad-groups-confirmed" style="margin-top: 8px; font-size: 0.75rem; color: var(--primary);"></div>
                        </div>
                        <div class="form-group">
                            <label>O365 Distribution Lists (DL)</label>
                            <div class="o365-groups-lookup multi-select-list" style="max-height: 120px; overflow-y: auto;"></div>
                            <div id="o365-groups-confirmed" style="margin-top: 8px; font-size: 0.75rem; color: var(--primary);"></div>
                        </div>
                        <div class="checkbox-label">
                            <input type="checkbox" name="enable_mfa" checked>
                            <span>Enable Multi-Factor Authentication (MFA)</span>
                        </div>
                    </div>

                    <div class="card">
                        <h3>📧 Notification</h3>
                        <div class="grid-2">
                            <div class="form-group">
                                <label>Receiver Email</label>
                                <input type="email" name="receiver_email">
                            </div>
                            <div class="form-group">
                                <label>CC Email</label>
                                <input type="email" name="cc_email">
                            </div>
                        </div>
                        <div class="checkbox-label">
                            <input type="checkbox" name="send_welcome_email" checked>
                            <span>Send welcome email to manager/receiver</span>
                        </div>
                    </div>
                </div>
            </div>

            <div class="form-actions-bar">
                <button type="button" class="secondary-btn" onclick="resetForm()">Reset</button>
                <button type="submit" class="primary-btn" id="onboard-submit-btn">Complete Onboarding</button>
            </div>
        </form>
    `,
    offboarding: `
        <div class="offboard-layout grid-2">
            <div class="card">
                <h3>🔍 Search Employee</h3>
                <div class="form-group" style="display: flex; gap: 12px;">
                    <input type="text" id="offboard-search-input" placeholder="Search by name or email...">
                    <button class="primary-btn" id="offboard-search-btn">Search</button>
                </div>
                <div id="offboard-search-results" class="multi-select-list" style="display: none; border: none; padding: 0;"></div>
                
                <div id="offboard-user-preview" style="margin-top: 24px; display: none;">
                    <h4>User Details</h4>
                    <div id="user-preview-content" style="font-size: 0.9rem; color: var(--text-secondary); margin-top: 12px;"></div>
                </div>
            </div>

            <div class="card">
                <h3>🛠️ Select Actions to Perform</h3>
                <div class="actions-list">
                    <label class="checkbox-label"><input type="checkbox" id="act-block" checked> <span>Block O365 Sign-in</span></label>
                    <label class="checkbox-label"><input type="checkbox" id="act-lic" checked> <span>Remove O365 Licenses</span></label>
                    <label class="checkbox-label"><input type="checkbox" id="act-del-o365"> <span>Delete O365 User Account</span></label>
                    <label class="checkbox-label"><input type="checkbox" id="act-disable-ad" checked> <span>Disable AD Account</span></label>
                    <label class="checkbox-label"><input type="checkbox" id="act-del-ad"> <span>Delete AD Account</span></label>
                    <label class="checkbox-label"><input type="checkbox" id="act-notify" checked> <span>Send Manager Notification</span></label>
                </div>

                <div class="notification-sender-details" style="margin-top: 24px; padding-top: 24px; border-top: 1px solid rgba(255,255,255,0.05);">
                    <h4>Notification Sender Details</h4>
                    <div class="form-group" style="margin-top: 12px;">
                        <label>Sender Email</label>
                        <input type="text" id="off-sender-email">
                    </div>
                    <div class="grid-2">
                        <div class="form-group">
                            <label>Sender Password</label>
                            <input type="password" id="off-sender-pwd">
                        </div>
                        <div class="form-group">
                            <label>CC Email</label>
                            <input type="text" id="off-cc-email">
                        </div>
                    </div>
                </div>

                <div style="margin-top: 32px; display: flex; justify-content: flex-end;">
                    <button class="primary-btn" id="run-offboard-btn" style="background: var(--error);">Run Decommissioning</button>
                </div>
            </div>
        </div>
        <div id="offboard-log-card" class="card" style="margin-top: 24px; display: none;">
            <h3>Process Log</h3>
            <div id="offboard-log" class="process-log"></div>
        </div>
    `,
    'profile-update': `
        <div class="card">
            <h3>🔍 Search Employee</h3>
            <div class="form-group" style="display: flex; gap: 12px;">
                <input type="text" id="profile-search-input" placeholder="Search by name or email...">
                <button class="primary-btn" id="profile-search-btn">Search</button>
            </div>
            <div id="profile-search-results" class="multi-select-list" style="display: none; border: none; padding: 0;"></div>
        </div>

        <div id="profile-edit-card" class="card" style="display: none;">
            <h3>📝 Update Fields</h3>
            <div id="profile-user-summary" style="margin-bottom: 24px; padding: 16px; background: rgba(255,255,255,0.02); border-radius: 8px;"></div>
            
            <div class="grid-2">
                <div class="form-group">
                    <label>Designation / Title *</label>
                    <input type="text" id="upd-title">
                </div>
                <div class="form-group">
                    <label>Department *</label>
                    <select id="upd-dept" class="dept-select-lookup"></select>
                </div>
            </div>
            <div class="grid-2">
                <div class="form-group">
                    <label>Mobile Number</label>
                    <input type="text" id="upd-mobile">
                </div>
                <div class="form-group">
                    <label>Reporting Manager</label>
                    <div style="display: flex; gap: 8px;">
                        <input type="text" id="upd-manager-name" readonly>
                        <button class="secondary-btn" id="upd-manager-find">Find</button>
                    </div>
                    <input type="hidden" id="upd-manager-upn">
                </div>
            </div>
            <div style="display: flex; justify-content: flex-end; gap: 16px; margin-top: 24px;">
                <button class="secondary-btn" id="upd-reset">Reset</button>
                <button class="primary-btn" id="upd-save">Save Changes</button>
            </div>
        </div>
    `,
    settings: `
        <div class="card settings-card" style="padding: 0;">
            <div class="settings-tabs">
                <button class="tab-btn active" data-tab="tab-email">📧 Email Templates</button>
                <button class="tab-btn" data-tab="tab-defaults">📍 Default Values</button>
                <button class="tab-btn" data-tab="tab-ad">🖥️ Active Directory</button>
                <button class="tab-btn" data-tab="tab-integrations">🔗 Integrations</button>
                <button class="tab-btn" data-tab="tab-lookups">🔍 Lookup Lists</button>
                <button class="tab-btn" data-tab="tab-notifications">📧 Notification</button>
            </div>
            <div class="settings-content" style="padding: 24px;">
                <div id="tab-email" class="tab-pane active">
                    <h4>Welcome Email</h4>
                    <div class="form-group">
                        <label>Subject</label>
                        <input type="text" id="set-welcome-sub">
                    </div>
                    <div class="form-group">
                        <label>Template</label>
                        <textarea id="set-welcome-body" style="height: 150px; font-family: monospace;"></textarea>
                    </div>
                    <hr style="opacity: 0.1; margin: 24px 0;">
                    <h4>Offboarding Notification</h4>
                    <div class="form-group">
                        <label>Subject</label>
                        <input type="text" id="set-off-sub">
                    </div>
                    <div class="form-group">
                        <label>Template</label>
                        <textarea id="set-off-body" style="height: 100px; font-family: monospace;"></textarea>
                    </div>
                </div>

                <div id="tab-defaults" class="tab-pane">
                    <div class="form-group">
                        <label>Company Name</label>
                        <input type="text" id="set-company">
                    </div>
                    <div class="form-group">
                        <label>Primary Office Location</label>
                        <input type="text" id="set-office" value="Coimbatore">
                    </div>
                </div>

                <div id="tab-ad" class="tab-pane">
                    <div class="form-group">
                        <label>Users Base OU</label>
                        <input type="text" id="set-ad-users-base" placeholder="OU=Users,DC=petrus,DC=com">
                    </div>
                    <div class="form-group">
                        <label>Groups Base OU</label>
                        <input type="text" id="set-ad-groups-base">
                    </div>
                </div>

                <div id="tab-integrations" class="tab-pane">
                    <div class="grid-2">
                        <div class="form-group">
                            <label>AD Domain</label>
                            <input type="text" id="set-ad-domain" placeholder="example.local">
                        </div>
                        <div class="form-group">
                            <label>AD Server / DC IP</label>
                            <input type="text" id="set-ad-server" placeholder="10.0.0.1">
                        </div>
                    </div>
                    <div class="grid-2">
                        <div class="form-group">
                            <label>Admin Username (Optional)</label>
                            <input type="text" id="set-ad-admin-user">
                        </div>
                        <div class="form-group">
                            <label>Admin Password</label>
                            <input type="password" id="set-ad-admin-pass" placeholder="Leave empty to use session credentials">
                        </div>
                    </div>
                    <div style="margin-top: 12px; display: flex; gap: 12px;">
                        <button class="secondary-btn" id="test-ad-btn" style="flex: 1;">Test AD Connection</button>
                        <button class="secondary-btn" id="reconnect-o365-btn" style="flex: 1;">Reconnect M365</button>
                    </div>
                    <div id="test-results" style="margin-top: 12px; font-size: 0.85rem;"></div>
                </div>

                <div id="tab-lookups" class="tab-pane">
                    <div class="form-group">
                        <label>Departments (One per line)</label>
                        <textarea id="set-depts" style="height: 150px;"></textarea>
                    </div>
                </div>

                <div id="tab-notifications" class="tab-pane">
                    <div class="grid-2">
                        <div class="form-group">
                            <label>SMTP Sender Email</label>
                            <input type="email" id="set-smtp-sender" placeholder="it-support@petrustechnologies.com">
                        </div>
                        <div class="form-group">
                            <label>SMTP Sender Password</label>
                            <input type="password" id="set-smtp-pass">
                        </div>
                    </div>
                </div>
            </div>
            <div style="padding: 24px; border-top: 1px solid rgba(255,255,255,0.05); display: flex; justify-content: flex-end;">
                <button class="primary-btn" id="save-settings-btn">Save All Settings</button>
            </div>
        </div>
    `
};

// ── App Core ────────────────────────────────────────────────────────────────

async function init() {
    // Navigation setup
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            const view = item.getAttribute('data-view');
            switchView(view);
        });
    });

    // Login logic
    document.getElementById('login-form').addEventListener('submit', handleLogin);
    document.getElementById('logout-btn').addEventListener('click', handleLogout);

    // Initial check
    const authed = await checkAuth();
    if (authed) {
        // Enforce O365
        await checkStatus();
        if (!state.status.o365.connected) {
            console.warn("M365 Disconnected. Enforcing authentication...");
            switchView('dashboard');
            return;
        }

        // Enforce Domain Admin
        if (!state.user || !state.user.is_admin) {
            alert("Unauthorized: Only Domain Admins are allowed to access this portal.");
            handleLogout();
            return;
        }

        fetchLookups();
        const path = window.location.hash.substring(1) || 'dashboard';
        switchView(path);
        
        // Make status dots clickable
        document.getElementById('o365-status').addEventListener('click', () => {
            triggerO365Login();
        });
    }
    
    // Auto-poll status
    setInterval(() => {
        if (state.user) checkStatus();
    }, 30000);

    // Global click listener for tab switching
    document.addEventListener('click', (e) => {
        const tabBtn = e.target.closest('.tab-btn');
        if (tabBtn) {
            const tabId = tabBtn.getAttribute('data-tab');
            const parent = tabBtn.closest('.settings-card');
            parent.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            parent.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
            tabBtn.classList.add('active');
            document.getElementById(tabId).classList.add('active');
        }
    });
}

async function checkAuth() {
    try {
        const resp = await fetch('/api/me');
        if (resp.ok) {
            const data = await resp.json();
            state.user = data;
            document.getElementById('login-overlay').style.display = 'none';
            
            // Dynamic User Display
            const displayName = data.username || "User";
            const initial = displayName.charAt(0).toUpperCase();
            
            document.getElementById('user-name').innerText = displayName; 
            document.getElementById('user-avatar').innerText = initial;
            
            // Header updates
            const headerName = document.getElementById('header-user-name');
            const headerAvatar = document.getElementById('header-user-avatar');
            if (headerName) headerName.innerText = displayName;
            if (headerAvatar) headerAvatar.src = `https://ui-avatars.com/api/?name=${encodeURIComponent(displayName)}&background=0D8ABC&color=fff`;
            
            return true;
        }
    } catch (err) {}
    
    document.getElementById('login-overlay').style.display = 'flex';
    return false;
}

async function handleLogin(e) {
    e.preventDefault();
    const formData = new FormData(e.target);
    const data = Object.fromEntries(formData.entries());
    const errorDiv = document.getElementById('login-error');
    errorDiv.innerText = '';
    
    try {
        const resp = await fetch('/api/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        if (resp.ok) {
            const result = await resp.json();
            state.user = { username: result.user };
            location.reload();
        } else {
            const err = await resp.json();
            errorDiv.innerText = err.detail || 'Login failed';
        }
    } catch (err) {
        errorDiv.innerText = 'Server error';
    }
}

async function handleLogout() {
    await fetch('/api/logout', { method: 'POST' });
    location.reload();
}

function switchView(viewName) {
    if (!state.user) return;
    state.currentView = viewName;
    
    // Update nav UI
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.toggle('active', item.getAttribute('data-view') === viewName);
    });

    // Update title
    const titles = {
        dashboard: 'Dashboard',
        onboarding: 'New Employee Onboarding',
        offboarding: 'Employee Off-boarding',
        'profile-update': 'Update Employee Profile',
        settings: 'Settings'
    };
    document.getElementById('view-title').innerText = titles[viewName] || 'Petrus Onboarding';

    // Render content
    try {
        const container = document.getElementById('view-container');
        if (!container) throw new Error("view-container not found");
        
        const content = views[viewName];
        if (!content) {
            container.innerHTML = `<div class="card"><h3>View Not Found: ${viewName}</h3></div>`;
            return;
        }
        
        container.innerHTML = content;
        
        // Initialize components
        if (viewName === 'dashboard') renderDashboard();
        if (viewName === 'onboarding') renderOnboardingForm();
        if (viewName === 'offboarding') renderOffboarding();
        if (viewName === 'profile-update') renderProfileUpdate();
        if (viewName === 'settings') renderSettings();
        
        // Dynamic dashboard health update
        if (viewName === 'dashboard') updateHealthMonitor();
        
        lucide.createIcons();
        container.scrollTop = 0;
    } catch (err) {
        console.error("View render error:", err);
        document.getElementById('view-container').innerHTML = `
            <div class="card" style="border: 1px solid var(--error);">
                <h3 style="color: var(--error);">Failed to render view</h3>
                <p style="margin-top: 12px; font-family: monospace;">${err.message}</p>
                <button class="primary-btn" style="margin-top: 20px;" onclick="location.reload()">Reload App</button>
            </div>
        `;
    }
}

// ── View Renderers ───────────────────────────────────────────────────────────

function renderDashboard() {
    const isOnline = state.status.ad.connected && state.status.o365.connected;
    const statusText = isOnline ? 'System Fully Operational' : 'Partial Service Connectivity';
    const statusIcon = isOnline ? 'shield-check' : 'zap-off';
    const statusColor = isOnline ? 'var(--success)' : 'var(--warning)';

    document.getElementById('dash-status').innerText = statusText;
    document.getElementById('dash-status').style.color = statusColor;
    document.getElementById('dash-user').innerText = state.user ? state.user.username : "Guest Session";
    
    const reconnectBtn = document.getElementById('o365-reconnect-btn');
    if (reconnectBtn) {
        reconnectBtn.style.display = state.status.o365.connected ? 'none' : 'flex';
        reconnectBtn.onclick = () => triggerO365Login();
    }
    
    updateHealthMonitor();

    const activityLog = document.getElementById('activity-log');
    const activityList = document.getElementById('activity-list');
    
    if (!state.status.o365.connected) {
        activityLog.style.display = 'block';
        activityList.innerHTML = `
            <div class="step-item error">
                <i data-lucide="shield-alert" style="color: var(--error)"></i>
                <div>
                    <strong>Microsoft 365 Authentication Required</strong>
                    <p>M365 services are currently disconnected. This usually happens after a session timeout or server restart.</p>
                    <button class="primary-btn" style="margin-top: 12px; padding: 8px 16px; font-size: 0.8rem;" onclick="triggerO365Login()">
                        <i data-lucide="key"></i> Re-authenticate Now
                    </button>
                </div>
            </div>
        `;
    } else {
        activityLog.style.display = 'block';
        activityList.innerHTML = `
            <div class="step-item success">
                <i data-lucide="check-circle" style="color: var(--success)"></i>
                <div>
                    <strong>All Systems Connected</strong>
                    <p>Azure Active Directory and Microsoft 365 services are synchronized and ready.</p>
                </div>
            </div>
        `;
    }
    lucide.createIcons();
}

function updateHealthMonitor() {
    const adStatus = document.getElementById('health-ad-status');
    const o365Status = document.getElementById('health-o365-status');
    
    if (adStatus) {
        adStatus.innerText = state.status.ad.connected ? 'Active' : 'Offline';
        adStatus.style.color = state.status.ad.connected ? 'var(--success)' : 'var(--error)';
    }
    if (o365Status) {
        o365Status.innerText = state.status.o365.connected ? 'Operational' : 'Disconnected';
        o365Status.style.color = state.status.o365.connected ? 'var(--success)' : 'var(--error)';
    }
}

async function renderOnboardingForm() {
    const deptSelects = document.querySelectorAll('.dept-select-lookup');
    const ouSelects = document.querySelectorAll('.ou-select-lookup');
    const licenseSelects = document.querySelectorAll('.license-select-lookup');
    const adLists = document.querySelectorAll('.ad-groups-lookup');
    const o365Lists = document.querySelectorAll('.o365-groups-lookup');

    // Fill lookups
    deptSelects.forEach(s => s.innerHTML = state.lookups.departments.map(d => `<option value="${d}">${d}</option>`).join(''));
    ouSelects.forEach(s => s.innerHTML = state.lookups.ous.map(o => `<option value="${o.dn}">${o.name}</option>`).join(''));
    
    // License Filter: Only Basic and Standard
    licenseSelects.forEach(s => {
        const filtered = state.lookups.licenses.filter(l => 
            l.skuPartNumber.toLowerCase().includes('basic') || 
            l.skuPartNumber.toLowerCase().includes('standard')
        );
        s.innerHTML = filtered.map(l => `<option value="${l.skuId}">${l.skuPartNumber} (${l.available} avail)</option>`).join('');
    });

    // Event: Email Generation
    const fname = document.getElementById('onboard-fname');
    const lname = document.getElementById('onboard-lname');
    const emailInput = document.getElementById('onboard-email');
    const emailStatus = document.getElementById('email-status');

    const updateEmail = async () => {
        const fn = fname.value.trim().toLowerCase().replace(/[^a-z0-9]/g, '');
        const ln = lname.value.trim().toLowerCase().replace(/[^a-z0-9]/g, '');
        
        if (fn && ln) {
            const email = `${fn}.${ln}@petrustechnologies.com`;
            emailInput.value = email;
            
            // Check availability
            emailStatus.innerHTML = '<span style="color: var(--text-dim)">Checking...</span>';
            try {
                const resp = await fetch(`/api/search-users?q=${encodeURIComponent(email)}`);
                if (!resp.ok) {
                    emailStatus.innerHTML = '<span style="color: var(--error)">Error checking</span>';
                    return;
                }
                const users = await resp.json();
                if (Array.isArray(users) && users.length > 0) {
                    emailStatus.innerHTML = '<span style="color: var(--error)">Already Exists!</span>';
                } else {
                    emailStatus.innerHTML = '<span style="color: var(--success)">Available</span>';
                }
            } catch (err) {
                emailStatus.innerHTML = '<span style="color: var(--error)">Check failed</span>';
            }
        } else {
            emailInput.value = '';
            emailStatus.innerHTML = '';
        }
    };
    
    fname.addEventListener('input', updateEmail);
    lname.addEventListener('input', updateEmail);
    
    // Trigger initially if fields are pre-filled
    if (fname.value || lname.value) updateEmail();

    // Event: Office Selection & Address
    const officeSelect = document.getElementById('onboard-office');
    const addrPreview = document.getElementById('office-address-preview');
    const offices = {
        "Coimbatore": {
            display: "<strong>Coimbatore Office:</strong><br>511, Sathy Rd, Sivasakthi Colony, Ganapathy, Coimbatore - 641006",
            street: "511, Sathy Rd, Sivasakthi Colony, Ganapathy",
            city: "Coimbatore",
            state: "Tamil Nadu",
            zip: "641006"
        },
        "Bangalore": {
            display: "<strong>Bangalore Office:</strong><br>E-101 & 102 1st Floor, No 22, Sunrise Chamber, Ulsoor Road, Bengaluru - 560042",
            street: "E-101 & 102 1st Floor, No 22, Sunrise Chamber, Ulsoor Road",
            city: "Bengaluru",
            state: "Karnataka",
            zip: "560042"
        }
    };

    officeSelect.addEventListener('change', (e) => {
        const off = offices[e.target.value];
        addrPreview.innerHTML = off.display;
        document.getElementById('addr-street').value = off.street;
        document.getElementById('addr-city').value = off.city;
        document.getElementById('addr-state').value = off.state;
        document.getElementById('addr-zip').value = off.zip;
    });

    // Numeric Mobile Only
    const mobileInput = document.getElementById('onboard-mobile');
    mobileInput.addEventListener('keypress', (e) => {
        if (!/[0-9]/.test(e.key)) e.preventDefault();
    });

    // Manager Autocomplete
    const mgrSearch = document.getElementById('mgr-search');
    const mgrResults = document.getElementById('mgr-results');
    const mgrSelected = document.getElementById('mgr-selected');
    const mgrNameDisplay = document.getElementById('mgr-name-display');
    const mgrUpnHidden = document.getElementById('onboard-mgr-upn');

    mgrSearch.addEventListener('input', debounce(async (e) => {
        const q = e.target.value.trim();
        if (q.length < 2) { mgrResults.style.display = 'none'; return; }
        
        const resp = await fetch(`/api/search-users?q=${encodeURIComponent(q)}`);
        if (!resp.ok) {
            mgrResults.innerHTML = '<div style="padding: 12px; color: var(--error)">Search failed. Please login again.</div>';
            return;
        }
        const users = await resp.json();
        if (!Array.isArray(users)) {
             mgrResults.innerHTML = '<div style="padding: 12px; color: var(--error)">Unexpected response from server.</div>';
             return;
        }
        mgrResults.innerHTML = users.map(u => `
            <div class="select-item mgr-opt" data-upn="${u.userPrincipalName}" data-name="${u.displayName}">
                ${u.displayName} (${u.userPrincipalName})
            </div>
        `).join('');
        mgrResults.style.display = 'block';
    }, 300));

    mgrResults.addEventListener('click', (e) => {
        const opt = e.target.closest('.mgr-opt');
        if (opt) {
            const name = opt.getAttribute('data-name');
            const upn = opt.getAttribute('data-upn');
            mgrNameDisplay.innerText = name;
            mgrUpnHidden.value = upn;
            mgrSearch.value = '';
            mgrResults.style.display = 'none';
            mgrSearch.style.display = 'none';
            mgrSelected.style.display = 'flex';
            lucide.createIcons();
        }
    });

    window.clearManager = () => {
        mgrSelected.style.display = 'none';
        mgrSearch.style.display = 'block';
        mgrUpnHidden.value = '';
    };

    // AD & O365 Groups Initialization
    ouSelects.forEach(s => {
        s.addEventListener('change', async (e) => {
            const dn = e.target.value;
            const gResp = await fetch(`/api/ad-groups?base_dn=${encodeURIComponent(dn)}`);
            const groups = await gResp.json();
            // Filter: Security Groups only
            const securityGroups = groups.filter(g => g.type === 'Security');
            adLists.forEach(list => {
                list.innerHTML = securityGroups.map(g => `
                    <label class="select-item">
                        <input type="checkbox" name="ad_groups" value="${g.dn}" onchange="confirmSelection('ad')">
                        <span>${g.name}</span>
                    </label>
                `).join('');
            });
        });
    });

    o365Lists.forEach(list => {
        // Filter: Distribution Groups only
        const dls = state.lookups.o365_groups.filter(g => g.type === 'Unified' || g.type === 'Distribution' || g.type === 'MailEnabledSecurity');
        list.innerHTML = dls.map(g => `
            <label class="select-item">
                <input type="checkbox" name="o365_groups" value="${g.id}" onchange="confirmSelection('o365')">
                <span>${g.name}</span>
            </label>
        `).join('');
    });

    window.confirmSelection = (type) => {
        const list = type === 'ad' ? 'ad_groups' : 'o365_groups';
        const target = type === 'ad' ? 'ad-groups-confirmed' : 'o365-groups-confirmed';
        const checked = Array.from(document.querySelectorAll(`input[name="${list}"]:checked`));
        const names = checked.map(c => c.nextElementSibling.innerText);
        document.getElementById(target).innerText = names.length ? "Selected: " + names.join(', ') : "";
    };

    // Date default to today
    document.getElementById('onboard-joining').valueAsDate = new Date();

    document.getElementById('onboard-form').addEventListener('submit', handleOnboardSubmit);
    lucide.createIcons();
}

async function handleOnboardSubmit(e) {
    e.preventDefault();
    const btn = document.getElementById('onboard-submit-btn');
    const originalText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<span>Processing...</span>';

    const formData = new FormData(e.target);
    const data = Object.fromEntries(formData.entries());
    
    // Handle multi-checkboxes
    data.ad_groups = formData.getAll('ad_groups');
    data.o365_groups = formData.getAll('o365_groups');
    data.enable_mfa = formData.get('enable_mfa') === 'on';
    data.send_welcome_email = formData.get('send_welcome_email') === 'on';

    try {
        const resp = await fetch('/api/onboard', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        const result = await resp.json();
        if (resp.ok) {
            alert('Provisioning process started! Redirecting to dashboard.');
            switchView('dashboard');
        } else {
            alert('Error: ' + (result.message || 'Provisioning failed'));
        }
    } catch (err) {
        alert('Server error: ' + err.message);
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalText;
    }
}

function renderOffboarding() {
    const btn = document.getElementById('offboard-search-btn');
    const input = document.getElementById('offboard-search-input');
    const resultsDiv = document.getElementById('offboard-search-results');
    const preview = document.getElementById('offboard-user-preview');
    const logCard = document.getElementById('offboard-log-card');
    const log = document.getElementById('offboard-log');

    btn.addEventListener('click', async () => {
        const q = input.value.trim();
        if (!q) return;
        
        btn.disabled = true;
        resultsDiv.innerHTML = '<div style="padding: 12px">Searching...</div>';
        resultsDiv.style.display = 'block';
        
        const resp = await fetch(`/api/search-users?q=${encodeURIComponent(q)}`);
        btn.disabled = false;
        
        if (!resp.ok) {
            resultsDiv.innerHTML = '<div style="padding: 12px; color: var(--error)">Search failed. Please login again.</div>';
            return;
        }
        
        const users = await resp.json();
        if (!Array.isArray(users)) {
            resultsDiv.innerHTML = '<div style="padding: 12px; color: var(--error)">Invalid response.</div>';
            return;
        }
        
        if (users.length === 0) {
            resultsDiv.innerHTML = '<div style="padding: 12px">No users found.</div>';
        } else {
            resultsDiv.innerHTML = users.map(u => `
                <div class="select-item user-option" data-sam="${u.sAMAccountName}" data-upn="${u.userPrincipalName}" data-name="${u.displayName}">
                    <strong>${u.displayName}</strong> (${u.userPrincipalName || u.sAMAccountName})
                </div>
            `).join('');
        }
    });

    resultsDiv.addEventListener('click', async (e) => {
        const opt = e.target.closest('.user-option');
        if (opt) {
            const sam = opt.getAttribute('data-sam');
            const upn = opt.getAttribute('data-upn');
            const name = opt.getAttribute('data-name');
            resultsDiv.style.display = 'none';
            preview.style.display = 'block';
            document.getElementById('user-preview-content').innerHTML = `
                <p><strong>Name:</strong> ${name}</p>
                <p><strong>UPN:</strong> ${upn}</p>
                <p><strong>SAM:</strong> ${sam}</p>
            `;
            preview.setAttribute('data-upn', upn);
        }
    });

    document.getElementById('run-offboard-btn').addEventListener('click', async () => {
        const upn = preview.getAttribute('data-upn');
        if (!upn) { alert('Please select a user first'); return; }
        
        if (!confirm(`Confirm decommissioning for ${upn}?`)) return;
        
        logCard.style.display = 'block';
        log.innerHTML = `<div class="log-entry info">> Initializing process for ${upn}...</div>`;
        
        const data = {
            upn: upn,
            block_signin: document.getElementById('act-block').checked,
            remove_licenses: document.getElementById('act-lic').checked,
            delete_o365_account: document.getElementById('act-del-o365').checked,
            disable_ad_account: document.getElementById('act-disable-ad').checked,
            delete_ad_account: document.getElementById('act-del-ad').checked,
            notify_manager: document.getElementById('act-notify').checked,
            sender_email: document.getElementById('off-sender-email').value,
            sender_password: document.getElementById('off-sender-pwd').value,
            cc_email: document.getElementById('off-cc-email').value
        };
        
        try {
            const resp = await fetch('/api/offboard', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            const result = await resp.json();
            
            result.steps.forEach(s => {
                const entry = document.createElement('div');
                entry.className = `log-entry ${s.success ? 'success' : 'error'}`;
                entry.innerHTML = `> ${s.name}: ${s.message || (s.success ? 'Done' : 'Failed')}`;
                log.appendChild(entry);
            });
            
            const final = document.createElement('div');
            final.className = 'log-entry info';
            final.innerHTML = '> Process finished.';
            log.appendChild(final);
            
        } catch (err) {
            const entry = document.createElement('div');
            entry.className = 'log-entry error';
            entry.innerHTML = `> ERROR: ${err.message}`;
            log.appendChild(entry);
        }
    });
}

async function loadOffboardDetails(sam) {
    const card = document.getElementById('offboard-details-card');
    const resp = await fetch(`/api/user-details/${sam}`);
    if (!resp.ok) { alert('Failed to fetch user details'); return; }
    
    const user = await resp.json();
    document.getElementById('offboard-user-name').innerText = user.displayName;
    document.getElementById('offboard-user-name').setAttribute('data-sam', sam);
    document.getElementById('offboard-dept').innerText = user.department || '-';
    document.getElementById('offboard-email').innerText = user.userPrincipalName || '-';
    
    card.style.display = 'block';
}

function renderProfileUpdate() {
    const searchBtn = document.getElementById('profile-search-btn');
    const input = document.getElementById('profile-search-input');
    const resultsDiv = document.getElementById('profile-search-results');
    
    if (!searchBtn || !input || !resultsDiv) {
        console.error("Profile update search elements not found");
        return;
    }

    searchBtn.addEventListener('click', async () => {
        const q = input.value.trim();
        if (!q) return;
        
        searchBtn.disabled = true;
        resultsDiv.innerHTML = '<div style="padding: 12px">Searching...</div>';
        resultsDiv.style.display = 'block';
        
        const resp = await fetch(`/api/search-users?q=${encodeURIComponent(q)}`);
        searchBtn.disabled = false;
        
        if (!resp.ok) {
            resultsDiv.innerHTML = '<div style="padding: 12px; color: var(--error)">Search failed. Please login again.</div>';
            return;
        }
        
        const users = await resp.json();
        if (!Array.isArray(users)) {
            resultsDiv.innerHTML = '<div style="padding: 12px; color: var(--error)">Invalid response.</div>';
            return;
        }
        
        if (users.length === 0) {
            resultsDiv.innerHTML = '<div style="padding: 12px">No users found.</div>';
        } else {
            resultsDiv.innerHTML = users.map(u => `
                <div class="select-item update-user-option" data-sam="${u.sAMAccountName}" data-name="${u.displayName}" data-title="${u.title}" data-dept="${u.department}">
                    <strong>${u.displayName}</strong> (${u.sAMAccountName})
                </div>
            `).join('');
        }
    });

    resultsDiv.addEventListener('click', (e) => {
        const opt = e.target.closest('.update-user-option');
        if (opt) {
            const sam = opt.getAttribute('data-sam');
            const name = opt.getAttribute('data-name');
            const title = opt.getAttribute('data-title');
            const dept = opt.getAttribute('data-dept');
            resultsDiv.style.display = 'none';
            
            const summary = document.getElementById('profile-user-summary');
            if (summary) summary.innerHTML = `<strong>Selected User:</strong> ${name} (${sam})`;
            
            const titleInput = document.getElementById('upd-title');
            if (titleInput) titleInput.value = (title && title !== 'null') ? title : '';
            
            const deptSelect = document.getElementById('upd-dept');
            if (deptSelect) {
                deptSelect.innerHTML = state.lookups.departments.map(d => `<option value="${d}" ${d === dept ? 'selected' : ''}>${d}</option>`).join('');
            }
            
            const editCard = document.getElementById('profile-edit-card');
            if (editCard) {
                editCard.style.display = 'block';
                editCard.setAttribute('data-sam', sam);
            }
        }
    });

    // Save Logic
    document.getElementById('upd-save').onclick = async () => {
        const sam = document.getElementById('profile-edit-card').getAttribute('data-sam');
        const data = {
            title: document.getElementById('upd-title').value,
            department: document.getElementById('upd-dept').value,
            mobile: document.getElementById('upd-mobile').value,
            manager_dn: document.getElementById('upd-manager-upn').value
        };
        
        const saveBtn = document.getElementById('upd-save');
        saveBtn.disabled = true;
        saveBtn.innerText = 'Saving...';
        
        try {
            const resp = await fetch(`/api/profile-update/${sam}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            const res = await resp.json();
            if (resp.ok) {
                alert('Profile updated successfully!');
                switchView('dashboard');
            } else {
                alert('Update failed: ' + (res.detail || 'Unknown error'));
            }
        } catch (err) {
            alert('Server error: ' + err.message);
        } finally {
            saveBtn.disabled = false;
            saveBtn.innerText = 'Save Changes';
        }
    };

    // Reset Logic
    document.getElementById('upd-reset').onclick = () => {
        document.getElementById('profile-edit-card').style.display = 'none';
        document.getElementById('profile-search-results').style.display = 'none';
        document.getElementById('profile-search-input').value = '';
    };

    // Manager Find Logic
    document.getElementById('upd-manager-find').onclick = async () => {
        const name = prompt("Enter manager name to search:");
        if (!name) return;
        
        const resp = await fetch(`/api/search-users?q=${encodeURIComponent(name)}`);
        if (!resp.ok) { alert("Search failed"); return; }
        const users = await resp.json();
        
        if (users.length === 0) {
            alert("No managers found.");
        } else {
            const u = users[0]; // Take first for simplicity in prompt
            if (confirm(`Set ${u.displayName} as manager?`)) {
                document.getElementById('upd-manager-name').value = u.displayName;
                document.getElementById('upd-manager-upn').value = u.distinguishedName || u.userPrincipalName;
            }
        }
    };
}

async function renderSettings() {
    const resp = await fetch('/api/settings');
    const s = await resp.json();
    state.settings = s;

    document.getElementById('set-welcome-sub').value = s.welcome_email_subject || '';
    document.getElementById('set-welcome-body').value = s.welcome_email_template || '';
    document.getElementById('set-off-sub').value = s.offboarding_email_subject || '';
    document.getElementById('set-off-body').value = s.offboarding_email_template || '';
    document.getElementById('set-company').value = s.company_name || '';
    document.getElementById('set-ad-users-base').value = s.ad_users_base_ou || '';
    document.getElementById('set-ad-groups-base').value = s.ad_groups_base_ou || '';
    document.getElementById('set-ad-domain').value = s.ad_domain || '';
    document.getElementById('set-ad-server').value = s.ad_server || '';
    document.getElementById('set-ad-admin-user').value = s.ad_admin_user || '';
    document.getElementById('set-ad-admin-pass').value = s.ad_admin_password || '';
    document.getElementById('set-depts').value = s.departments ? s.departments.join('\n') : '';
    document.getElementById('set-smtp-sender').value = s.smtp_sender || '';
    document.getElementById('set-smtp-pass').value = s.smtp_password || '';

    // Button Listeners for Integrations
    document.getElementById('test-ad-btn').onclick = testADConnection;
    document.getElementById('reconnect-o365-btn').onclick = () => triggerO365Login();
    
    document.getElementById('save-settings-btn').addEventListener('click', async () => {
        const data = {
            departments: document.getElementById('set-depts').value.split('\n').map(d => d.trim()).filter(d => d),
            welcome_email_subject: document.getElementById('set-welcome-sub').value,
            welcome_email_template: document.getElementById('set-welcome-body').value,
            offboarding_email_subject: document.getElementById('set-off-sub').value,
            offboarding_email_template: document.getElementById('set-off-body').value,
            company_name: document.getElementById('set-company').value,
            ad_users_base_ou: document.getElementById('set-ad-users-base').value,
            ad_groups_base_ou: document.getElementById('set-ad-groups-base').value,
            ad_domain: document.getElementById('set-ad-domain').value,
            ad_server: document.getElementById('set-ad-server').value,
            ad_admin_user: document.getElementById('set-ad-admin-user').value,
            ad_admin_password: document.getElementById('set-ad-admin-pass').value,
            smtp_sender: document.getElementById('set-smtp-sender').value,
            smtp_password: document.getElementById('set-smtp-pass').value
        };
        
        const saveResp = await fetch('/api/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        if (saveResp.ok) {
            alert('Settings saved successfully!');
            fetchLookups();
        } else {
            alert('Failed to save settings');
        }
    });
}

window.resetForm = () => {
    const form = document.querySelector('.parity-form');
    if (form) form.reset();
};

// ── Helpers ──────────────────────────────────────────────────────────────────

async function checkStatus(autoLogin = false) {
    try {
        const resp = await fetch('/api/status');
        const data = await resp.json();
        state.status = data;
        updateStatusUI();
        if (state.currentView === 'dashboard') renderDashboard();
        
        // Auto-trigger login if disconnected and requested (e.g. on app load)
        if (autoLogin && !data.o365.connected) {
            console.log("O365 disconnected, triggering auto-login...");
            triggerO365Login();
        }
    } catch (err) {}
}

async function triggerO365Login() {
    if (state.isLoginInProgress) {
        console.log("Login already in progress, skipping...");
        return;
    }
    
    state.isLoginInProgress = true;
    try {
        const resp = await fetch('/api/o365/login', { method: 'POST' });
        if (resp.ok) {
            console.log("O365 login successful");
            const log = document.getElementById('activity-log');
            if (log) log.style.display = 'none';
            
            await checkStatus(); 
            fetchLookups(); 
        } else {
            const err = await resp.json();
            alert("Login Failed: " + (err.message || "Unknown error"));
        }
    } catch (err) {
        console.error("O365 login error:", err);
    } finally {
        state.isLoginInProgress = false;
    }
}

function updateStatusUI() {
    const adDot = document.querySelector('#ad-status .dot');
    const o365Dot = document.querySelector('#o365-status .dot');
    const adSub = document.querySelector('#ad-status .status-sub');
    const o365Sub = document.querySelector('#o365-status .status-sub');
    
    if (adDot) adDot.className = `dot ${state.status.ad.connected ? 'green' : 'red'}`;
    if (o365Dot) o365Dot.className = `dot ${state.status.o365.connected ? 'green' : 'red'}`;
    
    if (adSub) adSub.innerText = state.status.ad.connected ? 'Connected' : 'Offline';
    if (o365Sub) o365Sub.innerText = state.status.o365.connected ? 'Connected' : 'Disconnected';
}

async function fetchLookups() {
    try {
        const resp = await fetch('/api/lookups');
        state.lookups = await resp.json();
    } catch (err) {}
}

function debounce(func, wait) {
    let timeout;
    return function(...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(this, args), wait);
    };
}

window.generatePassword = () => {
    const upper = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
    const lower = "abcdefghijklmnopqrstuvwxyz";
    const nums = "0123456789";
    const syms = "!@#$%^&*";
    const all = upper + lower + nums + syms;
    
    let pass = "";
    pass += upper[Math.floor(Math.random() * upper.length)];
    pass += lower[Math.floor(Math.random() * lower.length)];
    pass += nums[Math.floor(Math.random() * nums.length)];
    pass += syms[Math.floor(Math.random() * syms.length)];
    
    for (let i = 0; i < 8; i++) pass += all.charAt(Math.floor(Math.random() * all.length));
    
    // Shuffle
    pass = pass.split('').sort(() => Math.random() - 0.5).join('');
    document.getElementById('onboard-pwd').value = pass;
};

// Start the app
init();

async function testADConnection() {
    const btn = document.getElementById('test-ad-btn');
    const resDiv = document.getElementById('test-results');
    if (!btn || !resDiv) return;

    btn.disabled = true;
    resDiv.innerText = "Testing...";
    resDiv.style.color = "var(--text-dim)";

    try {
        const resp = await fetch('/api/test-ad', { method: 'POST' });
        const data = await resp.json();
        resDiv.innerText = data.message;
        resDiv.style.color = data.success ? "var(--success)" : "var(--error)";
    } catch (err) {
        resDiv.innerText = "Error testing connection";
        resDiv.style.color = "var(--error)";
    } finally {
        btn.disabled = false;
    }
}
