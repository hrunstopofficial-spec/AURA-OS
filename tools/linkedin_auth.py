"""
LinkedIn 1-Click OAuth Authenticator for JARVIS
Generates LinkedIn OAuth2 Access Token and Person URN, then saves to .env
"""

import http.server
import socketserver
import urllib.parse
import webbrowser
import requests
import os
import sys
from pathlib import Path

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import config

PORT = 8000
REDIRECT_URI = f"http://localhost:{PORT}/callback"

auth_code = None

class OAuthCallbackHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Suppress standard logging to keep terminal clean
        pass

    def do_GET(self):
        global auth_code
        parsed_url = urllib.parse.urlparse(self.path)
        
        if parsed_url.path == "/callback":
            params = urllib.parse.parse_qs(parsed_url.query)
            if "code" in params:
                auth_code = params["code"][0]
                self.send_response(200)
                self.send_header("Content-type", "text/html; charset=utf-8")
                self.end_headers()
                success_html = """
                <!DOCTYPE html>
                <html>
                <head>
                    <title>JARVIS LinkedIn OAuth</title>
                    <style>
                        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0b0f19; color: #fff; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }
                        .card { background: #161e2e; padding: 40px; border-radius: 16px; border: 1px solid #2d3748; text-align: center; max-width: 480px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }
                        h1 { color: #0a66c2; margin-bottom: 10px; font-size: 28px; }
                        p { color: #a0aec0; line-height: 1.6; }
                        .badge { display: inline-block; background: #0a66c2; color: white; padding: 8px 18px; border-radius: 20px; font-weight: 600; margin-top: 15px; }
                    </style>
                </head>
                <body>
                    <div class="card">
                        <h1>🔗 LinkedIn Connected!</h1>
                        <p>JARVIS has successfully captured your LinkedIn authorization code.</p>
                        <p>You can close this tab now and return to your terminal.</p>
                        <div class="badge">Active & Ready</div>
                    </div>
                </body>
                </html>
                """
                self.wfile.write(success_html.encode("utf-8"))
            elif "error" in params:
                error_desc = params.get("error_description", ["Unknown error"])[0]
                self.send_response(400)
                self.send_header("Content-type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(f"<h3>OAuth Error: {error_desc}</h3>".encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()


def update_env_file(access_token: str, person_urn: str):
    env_path = BASE_DIR / ".env"
    if not env_path.exists():
        print(f"[-] .env file not found at {env_path}")
        return

    content = env_path.read_text(encoding="utf-8")
    lines = content.splitlines()
    new_lines = []
    
    has_token = False
    has_urn = False

    for line in lines:
        if line.startswith("LINKEDIN_ACCESS_TOKEN="):
            new_lines.append(f"LINKEDIN_ACCESS_TOKEN={access_token}")
            has_token = True
        elif line.startswith("LINKEDIN_PERSON_URN="):
            new_lines.append(f"LINKEDIN_PERSON_URN={person_urn}")
            has_urn = True
        else:
            new_lines.append(line)

    if not has_token:
        new_lines.append(f"LINKEDIN_ACCESS_TOKEN={access_token}")
    if not has_urn:
        new_lines.append(f"LINKEDIN_PERSON_URN={person_urn}")

    env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    print(f"[+] Successfully updated {env_path} with new Access Token and Person URN!")


def authenticate():
    client_id = config.LINKEDIN_CLIENT_ID
    client_secret = config.LINKEDIN_CLIENT_SECRET

    if not client_id or not client_secret:
        print("[-] Error: LINKEDIN_CLIENT_ID or LINKEDIN_CLIENT_SECRET is missing in .env")
        return False

    scopes = "openid profile w_member_social email"
    encoded_scopes = urllib.parse.quote(scopes)
    encoded_redirect = urllib.parse.quote(REDIRECT_URI)
    
    auth_url = (
        f"https://www.linkedin.com/oauth/v2/authorization?"
        f"response_type=code&"
        f"client_id={client_id}&"
        f"redirect_uri={encoded_redirect}&"
        f"state=jarvis_secure_state_123&"
        f"scope={encoded_scopes}"
    )

    print("\n" + "="*60)
    print("🚀 JARVIS LINKEDIN 1-CLICK AUTHENTICATION")
    print("="*60)
    print(f"1. Make sure your LinkedIn App has Authorized Redirect URL:")
    print(f"   👉 {REDIRECT_URI}")
    print(f"2. Opening LinkedIn Login in your browser...")
    print(f"   If browser doesn't open, copy & paste this URL:")
    print(f"   {auth_url}\n")

    webbrowser.open(auth_url)

    socketserver.TCPServer.allow_reuse_address = True
    server = socketserver.TCPServer(("localhost", PORT), OAuthCallbackHandler)
    server.timeout = 180  # 3 minutes timeout

    print(f"[*] Waiting for callback on port {PORT}... (Press Ctrl+C to cancel)")

    try:
        while auth_code is None:
            server.handle_request()
    except KeyboardInterrupt:
        print("\n[-] Cancelled by user.")
        server.server_close()
        return False

    server.server_close()

    if not auth_code:
        print("[-] Did not receive authorization code.")
        return False

    print("\n[+] Authorization code received! Exchanging for Access Token...")

    # Step 2: Exchange code for Access Token
    token_url = "https://www.linkedin.com/oauth/v2/accessToken"
    token_payload = {
        "grant_type": "authorization_code",
        "code": auth_code,
        "redirect_uri": REDIRECT_URI,
        "client_id": client_id,
        "client_secret": client_secret
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    res = requests.post(token_url, data=token_payload, headers=headers)
    if res.status_code != 200:
        print(f"[-] Token exchange failed: {res.status_code} -> {res.text}")
        return False

    token_data = res.json()
    access_token = token_data.get("access_token")
    expires_in = token_data.get("expires_in")
    print(f"[+] Access Token acquired! (Expires in ~{int(expires_in)//86400} days)")

    # Step 3: Fetch Person URN (User Info)
    person_urn = None
    user_headers = {"Authorization": f"Bearer {access_token}"}

    # Try OpenID /userinfo first
    userinfo_res = requests.get("https://api.linkedin.com/v2/userinfo", headers=user_headers)
    if userinfo_res.status_code == 200:
        user_info = userinfo_res.json()
        sub = user_info.get("sub")
        name = user_info.get("name", "LinkedIn Member")
        person_urn = f"urn:li:person:{sub}"
        print(f"[+] Logged in as: {name} ({person_urn})")
    else:
        # Fallback to /v2/me
        me_res = requests.get("https://api.linkedin.com/v2/me", headers=user_headers)
        if me_res.status_code == 200:
            me_info = me_res.json()
            sub = me_info.get("id")
            first_name = me_info.get("localizedFirstName", "")
            last_name = me_info.get("localizedLastName", "")
            person_urn = f"urn:li:person:{sub}"
            print(f"[+] Logged in as: {first_name} {last_name} ({person_urn})")
        else:
            print(f"[!] Warning: Could not auto-fetch user URN ({userinfo_res.status_code}, {me_res.status_code})")

    if access_token:
        update_env_file(access_token, person_urn or "")
        print("\n" + "="*60)
        print("🎉 SUCCESS! LinkedIn credentials are saved in .env")
        print("="*60)
        return True

    return False


if __name__ == "__main__":
    authenticate()
