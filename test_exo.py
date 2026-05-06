import subprocess
import json

r = subprocess.run(
    'az account get-access-token --resource https://outlook.office365.com/ --output json',
    shell=True, capture_output=True, text=True
)
if r.returncode == 0:
    token = json.loads(r.stdout).get("accessToken")
    print(f"Got token! Length: {len(token)}")
    
    ps_script = f"""
    try {{
        Import-Module ExchangeOnlineManagement -ErrorAction Stop
        Connect-ExchangeOnline -AccessToken '{token}' -Organization petrustechnologies.com -ErrorAction Stop
        Write-Output "CONNECTED!"
    }} catch {{
        Write-Output "ERROR: $($_.Exception.Message)"
    }}
    """
    
    r_ps = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
        capture_output=True, text=True
    )
    print("PS Output:")
    print(r_ps.stdout)
    print(r_ps.stderr)
else:
    print("Failed to get az token:", r.stderr)
