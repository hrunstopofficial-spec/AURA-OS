"""
Combined LinkedIn & Naukri Persistent Session Exporter for JARVIS
Launches a real Chrome window on Mukil's PC so he can log in once to LinkedIn and Naukri.
Automatically detects when login succeeds, captures full session states (cookies + storage),
and saves them to storage/linkedin_session.json and storage/naukri_session.json.
"""
import os
import sys
import time
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent.parent
STORAGE_DIR = BASE_DIR / "storage"
LINKEDIN_SESSION_FILE = STORAGE_DIR / "linkedin_session.json"
NAUKRI_SESSION_FILE = STORAGE_DIR / "naukri_session.json"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

def run_session_login():
    print("\n" + "="*65, flush=True)
    print("👑 MUKIL JARVIS: LINKEDIN & NAUKRI 1-TIME LOGIN PORTAL", flush=True)
    print("="*65, flush=True)
    print("Opening Chrome browser for one-time login...", flush=True)
    print("👉 Tab 1: LinkedIn Login (Enter email/password or Google Login)")
    print("👉 Tab 2: Naukri.com Login (Enter email/password or OTP)")
    print("As soon as you log in, JARVIS will automatically detect and save the session!\n", flush=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            channel="chrome",
            args=[
                "--disable-blink-features=AutomationControlled",
                "--start-maximized"
            ]
        )
        context = browser.new_context(
            no_viewport=True,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )

        # Tab 1: LinkedIn
        page_li = context.new_page()
        page_li.add_init_script("delete Object.getPrototypeOf(navigator).webdriver")
        print("[*] Opening LinkedIn Login Tab...", flush=True)
        try:
            page_li.goto("https://www.linkedin.com/login", timeout=45000)
        except Exception as e:
            print(f"[!] LinkedIn navigation: {e}", flush=True)

        # Tab 2: Naukri
        page_nk = context.new_page()
        page_nk.add_init_script("delete Object.getPrototypeOf(navigator).webdriver")
        print("[*] Opening Naukri Login Tab...", flush=True)
        try:
            page_nk.goto("https://www.naukri.com/nlogin/login", timeout=45000)
        except Exception as e:
            print(f"[!] Naukri navigation: {e}", flush=True)

        print("\n⏳ Monitoring for login completion (Timeout: 300 seconds / 5 minutes)...", flush=True)
        
        li_logged_in = False
        nk_logged_in = False
        start_time = time.time()

        while time.time() - start_time < 300:
            # Check LinkedIn
            if not li_logged_in:
                try:
                    url_li = page_li.url
                    if "/feed" in url_li or "/in/" in url_li or page_li.locator(".global-nav__me, .feed-identity-module").count() > 0:
                        li_logged_in = True
                        context.storage_state(path=str(LINKEDIN_SESSION_FILE))
                        print(f"\n🎉 [1/2] LINKEDIN LOGIN DETECTED & SAVED TO: {LINKEDIN_SESSION_FILE}", flush=True)
                except Exception:
                    pass

            # Check Naukri
            if not nk_logged_in:
                try:
                    url_nk = page_nk.url
                    if "my-naukri" in url_nk or "homepage" in url_nk or page_nk.locator(".nI-gNb-drawer__bars, .view-profile-wrapper, a[href*='mnjuser']").count() > 0:
                        nk_logged_in = True
                        context.storage_state(path=str(NAUKRI_SESSION_FILE))
                        print(f"\n🎉 [2/2] NAUKRI LOGIN DETECTED & SAVED TO: {NAUKRI_SESSION_FILE}", flush=True)
                except Exception:
                    pass

            if li_logged_in and nk_logged_in:
                print("\n🔥 BOTH LINKEDIN AND NAUKRI SESSIONS SAVED SUCCESSFULLY!", flush=True)
                time.sleep(3)
                break

            time.sleep(2)

        # Final capture if browser was manually closed or timeout
        if not li_logged_in:
            try:
                if "/feed" in page_li.url:
                    context.storage_state(path=str(LINKEDIN_SESSION_FILE))
                    li_logged_in = True
                    print(f"[+] Saved LinkedIn session: {LINKEDIN_SESSION_FILE}", flush=True)
            except Exception:
                pass

        if not nk_logged_in:
            try:
                if "my-naukri" in page_nk.url or page_nk.locator(".view-profile-wrapper").count() > 0:
                    context.storage_state(path=str(NAUKRI_SESSION_FILE))
                    nk_logged_in = True
                    print(f"[+] Saved Naukri session: {NAUKRI_SESSION_FILE}", flush=True)
            except Exception:
                pass

        try:
            browser.close()
        except Exception:
            pass

    print("\n" + "="*65, flush=True)
    print("SUMMARY OF SESSION EXPORT:")
    print(f" • LinkedIn: {'✅ LOGGED IN & SAVED' if li_logged_in else '❌ NOT LOGGED IN'}")
    print(f" • Naukri:   {'✅ LOGGED IN & SAVED' if nk_logged_in else '❌ NOT LOGGED IN'}")
    print("="*65 + "\n", flush=True)
    return li_logged_in or nk_logged_in

if __name__ == "__main__":
    run_session_login()
