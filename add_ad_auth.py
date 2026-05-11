import sys

with open('c:\\Petrus_Onboarding\\core\\ad_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

new_method = '''        return False, _clean_ps_err(err or out)

    def authenticate_and_check_permission(self, username: str, password: str) -> Tuple[bool, str]:
        """
        Authenticate an AD user and verify they are a member of 'Domain Admins'.
        Returns (success, message).
        """
        script = f"""
        try {{
            Import-Module ActiveDirectory -ErrorAction Stop
            $sec_auth = ConvertTo-SecureString '{_esc(password)}' -AsPlainText -Force
            $cred_auth = New-Object System.Management.Automation.PSCredential ('{_esc(username)}', $sec_auth)

            try {{
                $u = Get-ADUser -Identity '{_esc(username)}' -Credential $cred_auth -Server '{AD_DOMAIN}' -ErrorAction Stop
            }} catch {{
                Write-Output "AUTH_FAIL:$($_.Exception.Message)"
                exit
            }}

            try {{
                $groups = Get-ADPrincipalGroupMembership -Identity '{_esc(username)}' -Credential $cred_auth -Server '{AD_DOMAIN}' -ErrorAction Stop | Select-Object -ExpandProperty Name
                if ($groups -contains 'Domain Admins') {{
                    Write-Output "SUCCESS:IS_ADMIN"
                }} else {{
                    Write-Output "AUTH_OK:NOT_ADMIN"
                }}
            }} catch {{
                Write-Output "ERR:$($_.Exception.Message)"
            }}
        }} catch {{
            Write-Output "ERR:$($_.Exception.Message)"
        }}
        """
        
        # Override the configured AD credentials for this specific call
        import config
        old_user = config.AD_ADMIN_USER
        old_pwd = config.AD_ADMIN_PASSWORD
        config.AD_ADMIN_USER = ""
        config.AD_ADMIN_PASSWORD = ""
        
        try:
            _, out, err = _ps(script, timeout=60)
        finally:
            config.AD_ADMIN_USER = old_user
            config.AD_ADMIN_PASSWORD = old_pwd

        if "SUCCESS:IS_ADMIN" in out:
            return True, "Authenticated and verified as Domain Admin"
        elif "AUTH_OK:NOT_ADMIN" in out:
            return False, "User authenticated but is not a member of 'Domain Admins'"
        elif "AUTH_FAIL:" in out:
            msg = out.split("AUTH_FAIL:", 1)[1].strip()
            return False, f"Authentication Failed: {msg}"
        elif "ERR:" in out:
            msg = out.split("ERR:", 1)[1].strip()
            return False, f"Error checking permissions: {msg}"
        
        return False, _clean_ps_err(err or out)

    def check_ad_sync'''

content = content.replace('''        return False, _clean_ps_err(err or out)

    def check_ad_sync''', new_method)

with open('c:\\Petrus_Onboarding\\core\\ad_service.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Done")
