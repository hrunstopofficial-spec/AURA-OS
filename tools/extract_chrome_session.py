"""
Direct Chrome Cookie Extractor for LinkedIn Session
Reads and decrypts LinkedIn cookies directly from Mukil's local Chrome profile,
generating storage/linkedin_session.json for Playwright headless server with ZERO manual clicks.
"""

import os
import sys
import json
import base64
import shutil
import sqlite3
from pathlib import Path
import win32crypt
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

BASE_DIR = Path(__file__).resolve().parent.parent
SESSION_FILE = BASE_DIR / "storage" / "linkedin_session.json"


def get_chrome_secret_key(local_state_path: str) -> bytes:
    with open(local_state_path, "r", encoding="utf-8") as f:
        local_state = json.load(f)
    encrypted_key = base64.b64decode(local_state["os_crypt"]["encrypted_key"])
    encrypted_key = encrypted_key[5:]  # Strip DPAPI prefix
    return win32crypt.CryptUnprotectData(encrypted_key, None, None, None, 0)[1]


def extract_cookies_from_db(cookie_db_path: str, secret_key: bytes):
    if not os.path.exists(cookie_db_path):
        return []

    temp_db = os.path.join(os.environ.get("TEMP", "."), "temp_jarvis_cookies.db")
    try:
        shutil.copy2(cookie_db_path, temp_db)
    except Exception as e:
        print(f"[!] Could not copy {cookie_db_path}: {e}")
        return []

    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    query = "SELECT host_key, name, path, encrypted_value, is_secure, is_httponly FROM cookies WHERE host_key LIKE '%linkedin.com%'"
    cursor.execute(query)

    cookies = []
    aes = AESGCM(secret_key)

    for host_key, name, path, enc_val, is_secure, is_httponly in cursor.fetchall():
        try:
            if enc_val[:3] in (b"v10", b"v11"):
                nonce = enc_val[3:15]
                ciphertext = enc_val[15:]
                decrypted = aes.decrypt(nonce, ciphertext, None).decode("utf-8")
                cookies.append({
                    "name": name,
                    "value": decrypted,
                    "domain": host_key,
                    "path": path,
                    "secure": bool(is_secure),
                    "httpOnly": bool(is_httponly),
                    "sameSite": "Lax"
                })
        except Exception:
            pass

    conn.close()
    try:
        os.remove(temp_db)
    except Exception:
        pass

    return cookies


def extract_linkedin_session() -> bool:
    local_app_data = os.environ.get("LOCALAPPDATA", r"C:\Users\mukil\AppData\Local")
    chrome_dir = os.path.join(local_app_data, r"Google\Chrome\User Data")
    local_state_path = os.path.join(chrome_dir, "Local State")

    if not os.path.exists(local_state_path):
        print("[-] Chrome Local State not found.")
        return False

    secret_key = get_chrome_secret_key(local_state_path)

    # Check Default and Profile 1..10
    profile_dirs = ["Default"] + [f"Profile {i}" for i in range(1, 10)]
    all_cookies = []

    for p in profile_dirs:
        cookie_path = os.path.join(chrome_dir, p, "Network", "Cookies")
        if os.path.exists(cookie_path):
            extracted = extract_cookies_from_db(cookie_path, secret_key)
            if any(c["name"] == "li_at" for c in extracted):
                print(f"[+] Found authenticated LinkedIn session in Chrome profile: '{p}'!")
                all_cookies = extracted
                break
            elif extracted and not all_cookies:
                all_cookies = extracted

    if not all_cookies:
        print("[-] No LinkedIn cookies found in any Chrome profile.")
        return False

    has_li_at = any(c["name"] == "li_at" for c in all_cookies)
    print(f"[*] Total LinkedIn cookies extracted: {len(all_cookies)} (li_at session present: {has_li_at})")

    storage_state = {
        "cookies": all_cookies,
        "origins": [
            {
                "origin": "https://www.linkedin.com",
                "localStorage": []
            }
        ]
    }

    SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
    SESSION_FILE.write_text(json.dumps(storage_state, indent=2), encoding="utf-8")
    print(f"[+] Successfully exported LinkedIn session state to: {SESSION_FILE}")
    print(f"[*] File size: {SESSION_FILE.stat().st_size} bytes")
    return True


if __name__ == "__main__":
    extract_linkedin_session()
