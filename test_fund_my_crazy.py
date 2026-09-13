import sys
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from playwright.sync_api import sync_playwright
import time
import os

def main():
    print("[*] Launching Playwright for Fund My Crazy 2.0...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://enter.fundmycrazy.com/", timeout=45000)
        page.wait_for_load_state("networkidle", timeout=15000)
        print(f"[*] Page loaded: {page.title()}")

        # 1. Select Individual
        print("[*] Selecting Individual option...")
        page.locator("input#choice_781e9bf9-c118-4ca3-8b57-060796c3b687").check(force=True)
        time.sleep(0.5)

        # 2. Fill Personal Details
        print("[*] Filling Applicant Info...")
        page.locator("input[id='1240b1f2-3f31-4fa4-b5f9-d8aa766222ef']").fill("MUKILARASU S")
        page.locator("input[type='email']").fill("mukilarasu55@gmail.com")
        page.locator("input[id='704a50cc-8005-46a3-bec3-969570d243ff']").fill("+91-9080030538")
        page.locator("input[id='54e3a8a6-2f01-4c3b-96d2-49e6bb2df540']").fill("VSB Engineering College, Karur")
        time.sleep(0.5)

        # 3. Click Next
        print("[*] Submitting Page 1 (Clicking Next)...")
        page.get_by_role("button", name="Next").click()
        time.sleep(3.5)

        # 4. Save Page 2 Proof
        proof_path = r"C:\Users\mukil\Desktop\FundMyCrazy_Page2_Proof.png"
        page.screenshot(path=proof_path, full_page=True)
        print(f"[*] Page 2 loaded successfully! Proof saved to: {proof_path}")

        # Let's inspect Page 2 elements
        page2_text = page.inner_text("body")
        print("[*] Page 2 Preview Snippet:")
        for line in page2_text.splitlines()[:15]:
            if line.strip():
                print(f"    > {line.strip()}")

        browser.close()

if __name__ == '__main__':
    main()
