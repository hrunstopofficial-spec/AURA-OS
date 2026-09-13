import os
import time
from playwright.sync_api import sync_playwright

post_url = "https://www.linkedin.com/feed/update/urn:li:share:7504757899731333120/"
shot_path = r"C:\Users\mukil\jarvis-core\storage\reports\linkedin_post_screenshot_clean.png"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(
        viewport={"width": 1366, "height": 950},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
    page.goto(post_url, timeout=30000, wait_until="domcontentloaded")
    time.sleep(3)
    
    # Dismiss or remove login modal and backdrop
    page.evaluate("""() => {
        const modal = document.querySelector('.modal__outlet, .contextual-sign-in-modal, [data-test-id*="authwall"], div[id*="artdeco-modal"]');
        if (modal) modal.remove();
        const backdrop = document.querySelector('.modal-wormhole, .artdeco-modal-overlay, div[class*="backdrop"]');
        if (backdrop) backdrop.remove();
        const banner = document.querySelector('.banner-container, div[class*="bottom-banner"]');
        if (banner) banner.remove();
        // also click modal close button if present
        const closeBtn = document.querySelector('button[aria-label="Dismiss"], button[data-test-id*="close"]');
        if (closeBtn) closeBtn.click();
    }""")
    time.sleep(1)
    
    page.screenshot(path=shot_path, full_page=False)
    print(f"Clean screenshot saved to: {shot_path} ({os.path.getsize(shot_path)} bytes)")
    browser.close()
