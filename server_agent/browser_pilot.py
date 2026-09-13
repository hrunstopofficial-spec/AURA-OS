"""
AURA-OS Server-Side Sandboxed Browser Pilot
server_agent/browser_pilot.py - Headless, Sandboxed Browser Automation & Web Research Primitive.

Security Guarantees:
1. Anti-SSRF Protection: Blocks private IPs (127.0.0.1, 10.0.0.0/8, 192.168.0.0/16, 169.254.169.254),
   localhost, and cloud metadata services.
2. Scheme Enforcement: Strictly allows http:// and https:// schemes. Blocks file://, ftp://, gopher://.
3. Hard Ceilings: Page navigation timeout enforced (default 15s, max 30s).
4. Content Clamping: Extracts clean DOM text capped to 10,000 chars to avoid memory explosion.
5. Ephemeral Execution: Launches isolated browser context per session with zero persisted state/cookies.
"""
import os
import re
import ipaddress
import logging
from urllib.parse import urlparse
from typing import Dict, Any, List, Optional, Tuple
from pydantic import BaseModel, Field

logger = logging.getLogger("browser_pilot")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCREENSHOTS_DIR = os.path.join(BASE_DIR, "storage", "screenshots")
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

DEFAULT_TIMEOUT_MS = 15000
MAX_CONTENT_CHARS = 10000


class BrowserNavigationResult(BaseModel):
    url: str
    success: bool
    status_code: Optional[int] = None
    title: str = ""
    text_content: str = ""
    links: List[str] = Field(default_factory=list)
    screenshot_path: Optional[str] = None
    error: Optional[str] = None
    duration_ms: float = 0.0


class BrowserSecurityGuard:
    """Anti-SSRF and URL Validation Engine."""

    FORBIDDEN_HOSTNAMES = {
        "localhost",
        "127.0.0.1",
        "0.0.0.0",
        "::1",
        "metadata.google.internal",
        "169.254.169.254"
    }

    @classmethod
    def validate_url(cls, url_str: str) -> Tuple[bool, str]:
        if not url_str or not isinstance(url_str, str):
            return False, "URL string must not be empty"

        parsed = urlparse(url_str.strip())
        scheme = parsed.scheme.lower()

        if scheme not in ("http", "https"):
            return False, f"Forbidden scheme '{scheme}'. Only http and https allowed."

        hostname = (parsed.hostname or "").lower()
        if not hostname:
            return False, "URL contains no valid host name."

        if hostname in cls.FORBIDDEN_HOSTNAMES:
            return False, f"Access to host '{hostname}' blocked by Anti-SSRF policy."

        # Check for private / link-local / loopback IP address ranges
        try:
            ip = ipaddress.ip_address(hostname)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                return False, f"Access to private IP range '{hostname}' blocked by Anti-SSRF policy."
        except ValueError:
            # Hostname is a domain name, not a raw IP
            pass

        return True, "URL validated"


class HeadlessBrowserPilot:
    """Headless Playwright-driven universal web extraction and automation engine."""

    def __init__(self):
        self._playwright = None

    def fetch_page(
        self,
        url: str,
        timeout_ms: int = DEFAULT_TIMEOUT_MS,
        max_chars: int = MAX_CONTENT_CHARS
    ) -> BrowserNavigationResult:
        """Navigates to URL, waits for network idle or DOM load, and extracts readable text."""
        import time
        from playwright.sync_api import sync_playwright

        start_time = time.time()
        is_safe, reason = BrowserSecurityGuard.validate_url(url)
        if not is_safe:
            logger.warning(f"[BLOCKED] Browser Pilot rejected URL '{url}': {reason}")
            return BrowserNavigationResult(
                url=url,
                success=False,
                error=f"SSRF Policy Violation: {reason}",
                duration_ms=round((time.time() - start_time) * 1000, 2)
            )

        timeout = min(max(timeout_ms, 5000), 30000)

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    viewport={"width": 1280, "height": 800}
                )
                page = context.new_page()

                response = page.goto(url, timeout=timeout, wait_until="domcontentloaded")
                status_code = response.status if response else None

                # Extract title and text
                title = page.title() or ""
                # Evaluate clean text without script and style tags
                raw_text = page.evaluate("""() => {
                    const scripts = document.querySelectorAll('script, style, noscript');
                    scripts.forEach(s => s.remove());
                    return document.body ? document.body.innerText : '';
                }""")

                clean_text = re.sub(r'\n{3,}', '\n\n', (raw_text or "").strip())
                if len(clean_text) > max_chars:
                    clean_text = clean_text[:max_chars] + f"\n\n... [TRUNCATED: Text exceeded {max_chars} chars]"

                # Extract visible links
                links = page.evaluate("""() => {
                    const anchors = Array.from(document.querySelectorAll('a[href]'));
                    return anchors.map(a => a.href).filter(h => h.startsWith('http')).slice(0, 20);
                }""")

                browser.close()

                elapsed_ms = round((time.time() - start_time) * 1000, 2)
                return BrowserNavigationResult(
                    url=url,
                    success=True,
                    status_code=status_code,
                    title=title,
                    text_content=clean_text,
                    links=links,
                    duration_ms=elapsed_ms
                )

        except Exception as err:
            elapsed_ms = round((time.time() - start_time) * 1000, 2)
            logger.error(f"[ERROR] Browser navigation error for '{url}': {err}")
            return BrowserNavigationResult(
                url=url,
                success=False,
                error=str(err),
                duration_ms=elapsed_ms
            )


# Global Singleton
browser_pilot = HeadlessBrowserPilot()
