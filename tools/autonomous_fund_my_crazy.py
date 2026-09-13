import os
import sys
import time
from playwright.sync_api import sync_playwright

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

PROOF_PATH = r"C:\Users\mukil\Desktop\FundMyCrazy_Verify_State.png"

def test_verify_step():
    print("[*] Launching headless Playwright on server/background mode...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://enter.fundmycrazy.com/", timeout=45000)
        page.wait_for_load_state("networkidle", timeout=15000)
        print(f"[*] Loaded: {page.title()}")

        # 1. Fill Page 1
        page.locator("input#choice_781e9bf9-c118-4ca3-8b57-060796c3b687").check(force=True)
        page.locator("input[id='1240b1f2-3f31-4fa4-b5f9-d8aa766222ef']").fill("MUKILARASU S")
        page.locator("input[type='email']").fill("mukilarasu55@gmail.com")
        page.locator("input[type='tel']").fill("+919080030538")
        page.locator("input[id='54e3a8a6-2f01-4c3b-96d2-49e6bb2df540']").fill("VSB Engineering College, Karur")
        time.sleep(1)

        # 2. Check Verify button
        verify_btn = page.get_by_role("button", name="Verify")
        if verify_btn.is_visible():
            print("[*] Clicking 'Verify' button for mukilarasu55@gmail.com...")
            verify_btn.click()
            time.sleep(4)

        # 3. Save proof screenshot
        page.screenshot(path=PROOF_PATH, full_page=True)
        print(f"[*] Saved verification state proof to: {PROOF_PATH}")

        # Check page text for OTP instruction
        snippet = page.inner_text("body")
        print("[*] Page Text Snippet:")
        for l in snippet.splitlines()[:20]:
            if l.strip():
                print(f"    {l.strip()}")

        browser.close()

if __name__ == '__main__':
    test_verify_step()
