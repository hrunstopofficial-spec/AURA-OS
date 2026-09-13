from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto('https://job-boards.greenhouse.io/gitlab/jobs/8785285002', timeout=45000)
    page.wait_for_load_state("domcontentloaded")
    time.sleep(2)

    # Find all inputs with role='combobox'
    comboboxes = page.locator("input[role='combobox']").all()
    print(f"[+] Found {len(comboboxes)} React-Select combobox inputs:")
    for cb in comboboxes:
        cb_id = cb.get_attribute('id') or ''
        cb_aria = cb.get_attribute('aria-labelledby') or cb.get_attribute('aria-label') or ''
        # Find parent container or label
        parent_text = cb.locator("xpath=ancestor::div[contains(@class, 'field') or contains(@class, 'form-group') or contains(@class, 'question')][1]").inner_text() if cb.count() > 0 else ""
        title = parent_text.split('\n')[0] if parent_text else cb_id
        print(f"  • ID: '{cb_id}' | Label/Title: '{title}'")

    # Test selecting 'India' in the country dropdown:
    print("\n[*] Testing React-Select on 'country'...")
    country_input = page.locator("input#country, input[id*='country']").first
    if country_input.count() > 0:
        print("[*] Clicking country input container...")
        country_input.click()
        time.sleep(0.5)
        country_input.type("India", delay=50)
        time.sleep(1)
        # Check if dropdown options appeared
        options = page.locator("[id*='react-select'][id*='option'], div[class*='option']").all()
        print(f"[+] Found {len(options)} options after typing 'India':")
        for opt in options[:5]:
            print(f"    - Option: '{opt.inner_text().strip()}'")
        if options:
            options[0].click()
            print("[+] Successfully clicked first option!")
            time.sleep(1)
            # Verify selected value
            container = country_input.locator("xpath=ancestor::div[contains(@class, 'control') or contains(@class, 'container')][1]")
            print(f"[+] Selected text in container: '{container.inner_text().strip()}'")

    browser.close()
