import os

file_path = r'c:\Petrus_Onboarding\core\o365_service.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

mfa_target = "            # ── Method 4: MSOnline PowerShell ─────────────────────────────────────"
mfa_end = "        return False, \"All attempts to enable MFA failed (including PowerShell fallback)\""
start_idx = content.find(mfa_target)
end_idx = content.find(mfa_end, start_idx) + len(mfa_end)

if start_idx != -1 and end_idx != -1:
    mfa_replacement = '''            # If all Graph API methods fail, stop here to avoid interactive prompts.
            time.sleep(2)
        return False, "All Graph API attempts to enable MFA failed. This property may be managed on-premises or requires manual setup."'''
    content = content[:start_idx] + mfa_replacement + content[end_idx:]

proxy_target = "        # Method 2: Use Exchange Online PowerShell"
proxy_end = "            return False, f\"Exception setting proxy addresses: {str(e)}\""
start_idx = content.find(proxy_target)
end_idx = content.find(proxy_end, start_idx) + len(proxy_end)

if start_idx != -1 and end_idx != -1:
    proxy_replacement = '''        
        # Check if it was a sync error (fallback to PowerShell will trigger login prompts, and it will fail anyway)
        return False, "Failed to set proxyAddresses via Graph API (Property is read-only for AD Synced users)."'''
    content = content[:start_idx] + proxy_replacement + content[end_idx:]

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Patch applied.")
