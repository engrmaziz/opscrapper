"""
Unit and integration tests for WebNavigatorTool, anti-bot block detection, and HTML-to-Markdown cleaning.
"""

import asyncio
from pathlib import Path
import sys

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.web_navigator import (
    clean_html_to_markdown,
    check_for_anti_bot_block,
    fetch_page_content,
    WebNavigatorTool,
)
from tools.base import registry


def test_clean_html_to_markdown():
    """Tests noise reduction and Markdown generation from dirty HTML."""
    raw_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Engineering Careers at Acme</title>
        <script src="tracker.js"></script>
        <style>.nav { color: blue; }</style>
    </head>
    <body>
        <nav class="navbar">
            <a href="/">Home</a> | <a href="/about">About</a>
        </nav>
        <div id="cookie-consent" class="cookie-banner">
            <p>We use cookies to improve your experience. <button>Accept</button></p>
        </div>
        <main>
            <h1>Staff AI Engineer</h1>
            <p>Acme Corp is seeking a visionary <strong>Staff AI Engineer</strong> to lead our LLM orchestrations.</p>
            <ul>
                <li>5+ years of Python & Distributed Systems</li>
                <li>Experience with Google Antigravity & Agentic Frameworks</li>
            </ul>
            <a href="https://acme.com/apply/123" class="btn">Apply Directly</a>
        </main>
        <footer class="footer">
            <p>&copy; 2026 Acme Corp. All rights reserved.</p>
        </footer>
    </body>
    </html>
    """

    markdown = clean_html_to_markdown(raw_html, "https://acme.com/jobs/123")

    # Assert main job content is preserved
    assert "Staff AI Engineer" in markdown
    assert "Acme Corp is seeking a visionary" in markdown
    assert "Google Antigravity" in markdown
    assert "[Apply Directly](https://acme.com/apply/123)" in markdown or "Apply Directly" in markdown

    # Assert noise tags are cleanly removed
    assert "navbar" not in markdown
    assert "Home | About" not in markdown
    assert "cookie-consent" not in markdown
    assert "We use cookies" not in markdown
    assert "All rights reserved" not in markdown
    assert "tracker.js" not in markdown


def test_anti_bot_block_detection():
    """Tests detection of anti-bot protections (Cloudflare, DataDome, 403s)."""
    # Cloudflare challenge
    cf_html = "<html><head><title>Just a moment...</title></head><body>Attention Required! | Cloudflare. Ray ID: 894a7e2b</body></html>"
    block_msg = check_for_anti_bot_block(cf_html, 403)
    assert block_msg is not None
    assert "Anti-bot" in block_msg or "403" in block_msg

    # DataDome block
    datadome_html = "<html><body>Access Denied. Blocked by DataDome.</body></html>"
    block_msg_dd = check_for_anti_bot_block(datadome_html, 200)
    assert block_msg_dd is not None
    assert "datadome" in block_msg_dd.lower()

    # Normal Page
    normal_html = "<html><body><h1>Careers at TechCorp</h1><p>Open Positions</p></body></html>"
    no_block = check_for_anti_bot_block(normal_html, 200)
    assert no_block is None


def test_tool_registry_registration():
    """Validates that WebNavigatorTool is registered in the global ToolRegistry."""
    tool = registry.get_tool("fetch_page_content")
    assert tool is not None
    assert isinstance(tool, WebNavigatorTool)
    assert tool.name == "fetch_page_content"


async def async_test_suite():
    """Runs all sync and async tests."""
    test_clean_html_to_markdown()
    test_anti_bot_block_detection()
    test_tool_registry_registration()
    print("\n[SUCCESS] All WebNavigator & Anti-Bot tests passed successfully!")


if __name__ == "__main__":
    asyncio.run(async_test_suite())
