"""
AURA-OS Browser Pilot Test Suite
tests/test_browser_pilot.py - Verifies Anti-SSRF protection, scheme enforcement,
and live DOM extraction capabilities.
"""
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server_agent.browser_pilot import (
    browser_pilot,
    BrowserSecurityGuard,
    BrowserNavigationResult
)


def test_1_ssrf_protection_blocks_localhost():
    """Anti-SSRF guard must immediately block localhost and 127.0.0.1."""
    urls = [
        "http://localhost:8000/admin",
        "http://127.0.0.1:3000/api",
        "http://169.254.169.254/latest/meta-data",
        "http://0.0.0.0:80"
    ]
    for u in urls:
        is_safe, reason = BrowserSecurityGuard.validate_url(u)
        assert is_safe is False
        assert "SSRF" in reason or "blocked" in reason

        res = browser_pilot.fetch_page(u)
        assert res.success is False
        assert "SSRF" in res.error
    print("\n[Test 1 Passed] Anti-SSRF guard successfully blocked private IPs & localhost.")


def test_2_scheme_enforcement():
    """Non-HTTP(S) schemes (file, gopher, ftp) must be strictly rejected."""
    bad_schemes = [
        "file:///C:/Users/mukil/.env",
        "ftp://example.com/file",
        "javascript:alert(1)"
    ]
    for u in bad_schemes:
        is_safe, reason = BrowserSecurityGuard.validate_url(u)
        assert is_safe is False
        assert "Forbidden scheme" in reason

        res = browser_pilot.fetch_page(u)
        assert res.success is False
    print("\n[Test 2 Passed] Scheme enforcement verified: non-HTTP(S) strictly blocked.")


def test_3_live_page_dom_extraction():
    """Browser Pilot navigates to public domain (example.com) and extracts clean DOM text."""
    res = browser_pilot.fetch_page("https://example.com", timeout_ms=15000)

    assert res.success is True
    assert res.status_code == 200
    assert "Example Domain" in res.title
    assert "documentation examples" in res.text_content.lower()
    assert len(res.links) > 0
    print(f"\n[Test 3 Passed] Live DOM extracted in {res.duration_ms}ms. Title: '{res.title}'")


if __name__ == "__main__":
    pytest.main(["-v", "-s", __file__])
