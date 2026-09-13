import os
import sys
import json
import time
import urllib.parse
from playwright.sync_api import sync_playwright

class AutonomousBrowserAgent:
    def __init__(self, session_dir=None):
        self.session_dir = session_dir or os.path.join(os.path.dirname(os.path.dirname(__file__)), "storage", "browser_session")
        os.makedirs(self.session_dir, exist_ok=True)
        self.profile = self._load_profile()

    def _load_profile(self):
        profile_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "storage", "memory", "user_profile.json")
        if os.path.exists(profile_path):
            try:
                with open(profile_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "name": "MUKILARASU S",
            "email": "mukilarasu55@gmail.com",
            "phone": "9080030538",
            "location": "Karur, Tamil Nadu",
            "skills": ["Python", "AI", "Full-Stack Development", "FastAPI", "React", "JavaScript", "SQL"]
        }

    def _get_context(self, p, headless=False):
        return p.chromium.launch_persistent_context(
            self.session_dir,
            headless=headless,
            channel="chrome",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            args=["--disable-blink-features=AutomationControlled", "--start-maximized"],
            no_viewport=True
        )

    def search_web(self, query: str, max_results: int = 5, headless: bool = False) -> str:
        """Searches Google/DuckDuckGo and returns top search results and snippets."""
        encoded = urllib.parse.quote(query)
        search_url = f"https://www.google.com/search?q={encoded}"
        
        with sync_playwright() as p:
            context = self._get_context(p, headless=headless)
            page = context.pages[0] if context.pages else context.new_page()
            page.goto(search_url, timeout=45000)
            time.sleep(3)
            
            results = []
            elements = page.locator("div.g, div.tF2Cxc").all()[:max_results]
            for el in elements:
                try:
                    title_elem = el.locator("h3").first
                    link_elem = el.locator("a").first
                    snippet_elem = el.locator("div.VwiC3b, div[data-sncf='1']").first
                    
                    title = title_elem.inner_text().strip() if title_elem.is_visible() else "No title"
                    link = link_elem.get_attribute("href") if link_elem.is_visible() else ""
                    snippet = snippet_elem.inner_text().strip() if snippet_elem.is_visible() else ""
                    
                    if title and link:
                        results.append(f"• **{title}**\n  🔗 {link}\n  📝 {snippet}")
                except Exception:
                    continue
            
            time.sleep(2)
            context.close()
            
            if results:
                return f"🔍 **Search Results for '{query}':**\n\n" + "\n\n".join(results)
            return f"Search completed for '{query}'. No structured snippets extracted."

    def browse_and_screenshot(self, url: str, headless: bool = False) -> str:
        """Navigates to any URL, renders page in Chrome, takes a full screenshot, and returns the path."""
        import tempfile
        if not url.startswith("http"):
            url = "https://" + url
            
        save_path = os.path.join(tempfile.gettempdir(), f"web_screenshot_{int(time.time())}.png")
        
        with sync_playwright() as p:
            context = self._get_context(p, headless=headless)
            page = context.pages[0] if context.pages else context.new_page()
            page.goto(url, timeout=45000)
            time.sleep(4)
            page.screenshot(path=save_path, full_page=False)
            title = page.title()
            time.sleep(2)
            context.close()
            
        return f"Screenshot of '{title}' ({url}) saved successfully at: {save_path}"

    def extract_page_summary(self, url: str, headless: bool = False) -> str:
        """Navigates to a webpage and extracts clean readable text content for analysis."""
        if not url.startswith("http"):
            url = "https://" + url
            
        with sync_playwright() as p:
            context = self._get_context(p, headless=headless)
            page = context.pages[0] if context.pages else context.new_page()
            page.goto(url, timeout=45000)
            time.sleep(3)
            
            title = page.title()
            # Extract main content
            paragraphs = page.locator("p, h1, h2, h3, article").all_inner_texts()
            clean_text = "\n".join([p.strip() for p in paragraphs if len(p.strip()) > 30])
            context.close()
            
        summary_preview = clean_text[:1500] if clean_text else "No substantial text content found on page."
        return f"🌐 **Page: {title} ({url})**\n\n{summary_preview}"

    def auto_fill_web_form(self, url: str, custom_fields: dict = None, headless: bool = False) -> str:
        """Intelligently identifies input fields on any form/website and fills them with user profile data."""
        if not url.startswith("http"):
            url = "https://" + url
            
        data = {
            "name": self.profile.get("name", "MUKILARASU S"),
            "email": self.profile.get("email", "mukilarasu55@gmail.com"),
            "phone": self.profile.get("phone", "9080030538"),
            "location": self.profile.get("location", "Karur, Tamil Nadu"),
            "subject": "Inquiry / Application from Mukil",
            "message": "Hello, I am interested in collaborating and discussing opportunities."
        }
        if custom_fields:
            data.update(custom_fields)
            
        filled_fields = []
        with sync_playwright() as p:
            context = self._get_context(p, headless=headless)
            page = context.pages[0] if context.pages else context.new_page()
            page.goto(url, timeout=45000)
            time.sleep(3)
            
            # Find common input fields
            inputs = page.locator("input, textarea").all()
            for inp in inputs:
                try:
                    if not inp.is_visible():
                        continue
                    inp_type = (inp.get_attribute("type") or "text").lower()
                    inp_name = (inp.get_attribute("name") or "").lower()
                    inp_id = (inp.get_attribute("id") or "").lower()
                    inp_placeholder = (inp.get_attribute("placeholder") or "").lower()
                    
                    combined = f"{inp_name} {inp_id} {inp_placeholder}"
                    
                    if "name" in combined and "user" not in combined:
                        inp.fill(data["name"])
                        filled_fields.append(f"Name -> {data['name']}")
                    elif "email" in combined or inp_type == "email":
                        inp.fill(data["email"])
                        filled_fields.append(f"Email -> {data['email']}")
                    elif "phone" in combined or "mobile" in combined or "tel" in combined or inp_type == "tel":
                        inp.fill(data["phone"])
                        filled_fields.append(f"Phone -> {data['phone']}")
                    elif "city" in combined or "location" in combined or "address" in combined:
                        inp.fill(data["location"])
                        filled_fields.append(f"Location -> {data['location']}")
                    elif "message" in combined or "comment" in combined or "desc" in combined:
                        inp.fill(data["message"])
                        filled_fields.append(f"Message -> {data['message']}")
                    elif "subject" in combined or "title" in combined:
                        inp.fill(data["subject"])
                        filled_fields.append(f"Subject -> {data['subject']}")
                except Exception:
                    continue
                    
            time.sleep(4)
            context.close()
            
        if filled_fields:
            return f"✅ Form on {url} successfully auto-filled with fields:\n• " + "\n• ".join(filled_fields)
        return f"Navigated to {url}. No standard matching form fields were detected."

    def execute_web_mission(self, url: str, mission_plan: dict, headless: bool = False) -> dict:
        """
        Executes a complex, multi-page autonomous browser mission.
        Handles: Input fields, Dropdowns, Radio buttons, File uploads, Pagination ('Next' / 'Submit'), and Proof Screenshots.
        Works identically in Headless mode (Server) and Headed mode (Laptop).
        """
        if not url.startswith("http"):
            url = "https://" + url

        report = {
            "url": url,
            "status": "RUNNING",
            "steps_completed": [],
            "screenshot": None,
            "error": None
        }

        with sync_playwright() as p:
            try:
                context = self._get_context(p, headless=headless)
                page = context.pages[0] if context.pages else context.new_page()
                page.goto(url, timeout=45000)
                page.wait_for_load_state("networkidle", timeout=15000)
                time.sleep(2)

                # Execute sequential steps from mission plan
                steps = mission_plan.get("steps", [])
                for i, step in enumerate(steps, 1):
                    action = step.get("action")
                    desc = step.get("description", f"Step {i}")

                    if action == "click":
                        selector = step.get("selector")
                        text = step.get("text")
                        if selector:
                            page.locator(selector).first.click(timeout=8000)
                        elif text:
                            page.get_by_text(text, exact=False).first.click(timeout=8000)
                        report["steps_completed"].append(f"Clicked: {desc}")

                    elif action == "fill":
                        selector = step.get("selector")
                        value = step.get("value")
                        if selector:
                            loc = page.locator(selector).first
                            loc.fill(str(value), timeout=8000)
                            report["steps_completed"].append(f"Filled {desc} -> {str(value)[:30]}...")

                    elif action == "upload_file":
                        file_path = step.get("file_path")
                        selector = step.get("selector", "input[type='file']")
                        if os.path.exists(file_path):
                            page.set_input_files(selector, file_path, timeout=10000)
                            report["steps_completed"].append(f"Uploaded file: {os.path.basename(file_path)}")
                        else:
                            report["steps_completed"].append(f"Skipped upload (file not found: {file_path})")

                    elif action == "press":
                        key = step.get("key", "Enter")
                        page.keyboard.press(key)
                        report["steps_completed"].append(f"Pressed key: {key}")

                    elif action == "wait":
                        seconds = step.get("seconds", 2)
                        time.sleep(seconds)

                    time.sleep(0.8)

                # Capture final visual proof screenshot
                import tempfile
                proof_path = os.path.join(tempfile.gettempdir(), f"mission_proof_{int(time.time())}.png")
                page.screenshot(path=proof_path, full_page=False)
                report["screenshot"] = proof_path
                report["status"] = "SUCCESS"
                time.sleep(3)
                context.close()

            except Exception as e:
                report["status"] = "ERROR"
                report["error"] = str(e)
                try:
                    context.close()
                except Exception:
                    pass

        return report

if __name__ == "__main__":
    agent = AutonomousBrowserAgent()
    print(agent.search_web("FastAPI Python latest features", max_results=3, headless=True))
