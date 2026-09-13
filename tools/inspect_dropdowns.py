from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    print("[*] Navigating to Greenhouse page...")
    page.goto('https://job-boards.greenhouse.io/gitlab/jobs/8785285002', timeout=45000)
    page.wait_for_load_state("domcontentloaded")
    
    # 1. Native <select> elements
    selects = page.locator('select').all()
    print(f"\n[+] Total native <select> elements: {len(selects)}")
    for s in selects:
        s_id = s.get_attribute('id') or ''
        s_name = s.get_attribute('name') or ''
        # find associated label
        label = ''
        if s_id:
            lbl = page.locator(f"label[for='{s_id}']").first
            if lbl.count() > 0:
                label = lbl.inner_text().strip()
        opts = [o.inner_text().strip() for o in s.locator('option').all()[:6]]
        print(f"  • ID: '{s_id}' | Name: '{s_name}' | Label: '{label}' | Options: {opts}")

    # 2. Custom ARIA / React / Combobox elements
    custom = page.locator("[role='combobox'], [aria-haspopup='listbox'], div[class*='select'], button[class*='dropdown']").all()
    print(f"\n[+] Custom comboboxes / dropdowns: {len(custom)}")
    for c in custom[:10]:
        tag = c.evaluate("el => el.tagName.toLowerCase()")
        c_id = c.get_attribute('id') or ''
        role = c.get_attribute('role') or ''
        txt = c.inner_text()[:40].replace('\n', ' ')
        print(f"  • Tag: <{tag}> | ID: '{c_id}' | Role: '{role}' | Text: '{txt}'")

    browser.close()
