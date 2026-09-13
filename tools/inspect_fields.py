import json
from playwright.sync_api import sync_playwright

url = "https://job-boards.greenhouse.io/gitlab/jobs/8785285002"
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1280, "height": 1200})
    page.goto(url, timeout=30000, wait_until="domcontentloaded")
    
    elements = page.evaluate("""() => {
        const results = [];
        const inputs = document.querySelectorAll('input, select, textarea');
        inputs.forEach(el => {
            const label = el.closest('div') ? el.closest('div').innerText.trim() : '';
            results.push({
                tag: el.tagName,
                type: el.type || '',
                name: el.name || '',
                id: el.id || '',
                placeholder: el.placeholder || '',
                label: label.substring(0, 100)
            });
        });
        return results;
    }""")
    
    print(f"Found {len(elements)} input elements:")
    for el in elements:
        print(f"[{el['tag']} - {el['type']}] name='{el['name']}' id='{el['id']}' | label='{el['label'].replace(chr(10), ' ')}'")
        
    browser.close()
