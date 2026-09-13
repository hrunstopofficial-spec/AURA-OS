"""
LinkedIn Persistent Session Exporter for Headless Server Automation
Launches a browser, allows one-time LinkedIn authentication, and exports
cookies/session storage state to storage/linkedin_session.json for cloud/headless workers.
"""

import os
import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent.parent
SESSION_FILE = BASE_DIR / "storage" / "linkedin_session.json"


def export_session():
    SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)

    print("\n" + "="*60)
    print("🔐 LINKEDIN PERSISTENT SESSION EXPORTER FOR CLOUD/SERVER")
    print("="*60)
    print("Opening browser for one-time login...")
    print("👉 If already logged in, wait for your LinkedIn feed to load.")
    print("👉 If not logged in, please enter credentials/OTP in the opened window.")
    print("Once feed loads, session will be automatically captured & saved.\n")

    with sync_playwright() as p:
        # Launch headed browser so user can see and complete any check if needed
        browser = p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled", "--start-maximized"]
        )
        # Launch browser with clean persistent or new context
        context_args = {"no_viewport": True}
        if SESSION_FILE.exists() and SESSION_FILE.stat().st_size > 50:
            try:
                context_args["storage_state"] = str(SESSION_FILE)
            except Exception:
                pass

        context = browser.new_context(**context_args)
        page = context.new_page()

        print("[*] Navigating to LinkedIn Feed / Login page...", flush=True)
        try:
            page.goto("https://www.linkedin.com/feed/", timeout=60000)
        except Exception as ex:
            print(f"[!] Navigation notice: {ex}. Navigating to login directly...", flush=True)
            page.goto("https://www.linkedin.com/login", timeout=60000)

        print("[*] Monitoring for authenticated feed session (timeout: 180s)...", flush=True)
        authenticated = False
        start_time = time.time()

        while time.time() - start_time < 180:
            current_url = page.url
            # Check if URL contains /feed or user nav element is visible
            if "/feed" in current_url or page.locator(".global-nav__me").is_visible() or page.locator(".feed-identity-module").is_visible():
                authenticated = True
                break
            time.sleep(2)

        if authenticated:
            time.sleep(2)
            context.storage_state(path=str(SESSION_FILE))
            print("\n" + "="*60)
            print(f"🎉 SUCCESS! LinkedIn session exported to:")
            print(f"   👉 {SESSION_FILE}")
            print("   Your cloud/headless servers can now execute authenticated operations!")
            print("="*60)
            browser.close()
            return True
        else:
            print("\n[-] Login not detected within 120s. Please retry.")
            browser.close()
            return False


if __name__ == "__main__":
    export_session()
