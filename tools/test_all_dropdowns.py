from playwright.sync_api import sync_playwright
import time

def select_react_dropdown(page, input_id: str, desired_text: str):
    """Universal robust React-Select combobox solver."""
    inp = page.locator(f"input#{input_id}, input[id*='{input_id}']").first
    if inp.count() == 0:
        print(f"[-] Combobox #{input_id} not found.")
        return False

    # Scroll into view
    inp.scroll_into_view_if_needed()
    time.sleep(0.3)
    
    # Click input
    inp.click()
    time.sleep(0.3)
    
    # Type desired search text
    inp.type(desired_text, delay=60)
    time.sleep(0.8)
    
    # Look for options in popup
    options = page.locator("[id*='react-select'][id*='option'], div[class*='option'], div[role='option']").all()
    if not options:
        # Try keyboard enter as fallback
        inp.press("Enter")
        time.sleep(0.3)
        print(f"[!] Pressed Enter for #{input_id} -> '{desired_text}'")
        return True

    # Find best match
    matched = None
    desired_lower = desired_text.lower()
    for opt in options:
        opt_text = opt.inner_text().strip()
        if opt_text.lower() == desired_lower:
            matched = opt
            break
    if not matched:
        # Partial match
        for opt in options:
            opt_text = opt.inner_text().strip()
            if desired_lower in opt_text.lower():
                matched = opt
                break
    if not matched:
        matched = options[0]

    matched_text = matched.inner_text().strip()
    matched.click()
    time.sleep(0.5)
    print(f"[+] Selected #{input_id}: '{matched_text}'")
    return True


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1280, "height": 800})
    page.goto('https://job-boards.greenhouse.io/gitlab/jobs/8785285002', timeout=45000)
    page.wait_for_load_state("domcontentloaded")
    time.sleep(2)

    dropdowns_to_test = [
        ("question_38207493002", "India"), # Country of residence
        ("question_38207494002", "No"),    # Employment agreements
        ("question_38207497002", "No"),    # Sponsorship
        ("question_38207498002", "No"),    # Worked at GitLab
        ("gender", "Male"),                # Gender
        ("hispanic_ethnicity", "No"),      # Hispanic
        ("veteran_status", "not a protected veteran"), # Veteran
        ("disability_status", "No, I do not have a disability") # Disability
    ]

    print("\n" + "="*50)
    print("Testing Universal Dropdown Selection:")
    print("="*50)

    for field_id, value in dropdowns_to_test:
        select_react_dropdown(page, field_id, value)

    # Take screenshot of the filled dropdowns
    page.screenshot(path="storage/screenshots/dropdown_verification.png", full_page=True)
    print("\n[+] Full-page screenshot saved to storage/screenshots/dropdown_verification.png")
    browser.close()
