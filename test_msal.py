import msal
import webbrowser

# Well-known Client ID for Azure CLI
CLIENT_ID = "04b07795-8ddb-461a-bbee-02f9e1bf7b46"
AUTHORITY = "https://login.microsoftonline.com/common"
SCOPES = ["https://graph.microsoft.com/.default"]

app = msal.PublicClientApplication(CLIENT_ID, authority=AUTHORITY)

# Try to get token from cache first
accounts = app.get_accounts()
if accounts:
    result = app.acquire_token_silent(SCOPES, account=accounts[0])
    if result:
        print("Got token from cache!")
        exit(0)

# If not in cache, do interactive login
flow = app.initiate_device_flow(scopes=SCOPES)
if "user_code" in flow:
    print(f"Please login at: {flow['verification_uri']}")
    print(f"Code: {flow['user_code']}")
    # Try to open browser automatically
    webbrowser.open(flow['verification_uri'])
    
    result = app.acquire_token_by_device_flow(flow)
    if "access_token" in result:
        print("Success! Token acquired.")
    else:
        print("Error:", result.get("error_description"))
else:
    print("Could not initiate login flow.")
