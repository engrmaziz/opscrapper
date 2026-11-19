"""
Stealth Web Navigator module.
Provides robust, anti-bot resilient, async web page fetching returning clean, LLM-ready Markdown.
Supports Crawl4AI, Playwright-stealth, and optional managed scraper API (ZenRows / ScraperAPI) fallback.
"""

import asyncio
from datetime import datetime
import re
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode, urlparse

from bs4 import BeautifulSoup

try:
    import html2text
except ImportError:
    html2text = None

import httpx

from config.settings import settings
from config.logging_config import get_logger
from .base import BaseAgentTool, registry

logger = get_logger("WebNavigator")

# Anti-Bot & Block Detection Signatures
BLOCK_SIGNATURES = [
    re.compile(r"attention required!?\s*\|\s*cloudflare", re.I),
    re.compile(r"just a moment\.{3}", re.I),
    re.compile(r"verify\s+(?:that\s+)?you\s+(?:are|'re)\s+(?:a\s+)?human", re.I),
    re.compile(r"datadome", re.I),
    re.compile(r"perimeterx", re.I),
    re.compile(r"access to this page has been denied", re.I),
    re.compile(r"pardon our interruption", re.I),
    re.compile(r"security check\s*\|\s*", re.I),
    re.compile(r"enable javascript and cookies to continue", re.I),
    re.compile(r"cf-turnstile", re.I),
    re.compile(r"ray id:\s*[a-f0-9]+", re.I),
    re.compile(r"<title>403 Forbidden</title>", re.I),
    re.compile(r"<title>Access Denied</title>", re.I),
]


def clean_html_to_markdown(raw_html: str, url: str) -> str:
    """Strips navigation bars, cookie banners, scripts, and converts clean HTML to Markdown.

    Args:
        raw_html: Raw HTML page string.
        url: Source URL for link resolution.

    Returns:
        Clean, structured Markdown text.
    """
    if not raw_html:
        return ""

    try:
        soup = BeautifulSoup(raw_html, "html.parser")

        # 1. Remove non-content and noise tags
        noise_selectors = [
            "script",
            "style",
            "noscript",
            "iframe",
            "svg",
            "canvas",
            "nav",
            "footer",
            "header",
            "[role='dialog']",
            "[role='banner']",
            "[role='navigation']",
            "[role='contentinfo']",
            ".cookie-banner",
            ".cookie-consent",
            "#cookie-banner",
            "#cookie-consent",
            ".modal",
            ".popup",
            "#consent-layer",
        ]
        for selector in noise_selectors:
            for node in soup.select(selector):
                node.decompose()

        # 2. Extract main container if present
        main_content = soup.find("main") or soup.find("body") or soup

        # 3. Convert to clean Markdown
        if html2text is not None:
            h2t = html2text.HTML2Text()
            h2t.ignore_links = False
            h2t.ignore_images = True
            h2t.ignore_emphasis = False
            h2t.body_width = 0  # No hard wrapping
            h2t.single_line_break = False
            markdown = h2t.handle(str(main_content))
        else:
            # High-signal fallback formatting using BeautifulSoup
            lines: List[str] = []
            for elem in main_content.find_all(["h1", "h2", "h3", "h4", "p", "li", "a"]):
                text = elem.get_text(strip=True)
                if not text:
                    continue
                if elem.name == "h1":
                    lines.append(f"# {text}\n")
                elif elem.name == "h2":
                    lines.append(f"## {text}\n")
                elif elem.name == "h3":
                    lines.append(f"### {text}\n")
                elif elem.name == "li":
                    lines.append(f"- {text}")
                elif elem.name == "a" and elem.get("href"):
                    href = elem["href"]
                    lines.append(f"[{text}]({href})")
                else:
                    lines.append(f"{text}\n")
            markdown = "\n".join(lines) if lines else main_content.get_text(separator="\n", strip=True)

        # 4. Collapse consecutive newlines and whitespace
        cleaned = re.sub(r"\n{3,}", "\n\n", markdown).strip()
        return cleaned

    except Exception as e:
        logger.warning(f"Error during HTML cleanup for {url}: {e}. Falling back to raw text.")
        return re.sub(r"\s+", " ", raw_html).strip()[:10000]


def check_for_anti_bot_block(content: str, status_code: int = 200) -> Optional[str]:
    """Inspects text and status code for anti-bot / CAPTCHA block signatures.

    Returns:
        String description of the block if detected, else None.
    """
    if status_code in [403, 429]:
        return f"HTTP {status_code} Access Denied / Rate Limited"

    snippet = content[:8000].lower()
    for pattern in BLOCK_SIGNATURES:
        match = pattern.search(snippet)
        if match:
            return f"Anti-bot protection detected: '{match.group(0)}'"

    return None


async def fetch_with_managed_api(url: str, timeout: int) -> Optional[Dict[str, Any]]:
    """Fetches a page using a commercial scraping proxy API if configured (e.g. ZenRows or ScraperAPI)."""
    api_key = settings.MANAGED_SCRAPER_API_KEY
    service = (settings.MANAGED_SCRAPER_SERVICE or "zenrows").lower()
    if not api_key:
        return None

    logger.info(f"Using managed scraper proxy ({service}) for: {url}")

    if service == "zenrows":
        proxy_url = f"https://api.zenrows.com/v1/?apikey={api_key}&url={url}&js_render=true&premium_proxy=true"
    elif service == "scraperapi":
        proxy_url = f"http://api.scraperapi.com/?api_key={api_key}&url={url}&render=true"
    else:
        proxy_url = f"https://api.zenrows.com/v1/?apikey={api_key}&url={url}&js_render=true"

    try:
        async with httpx.AsyncClient(timeout=float(timeout), follow_redirects=True) as client:
            response = await client.get(proxy_url)
            html = response.text
            return {
                "html": html,
                "status_code": response.status_code,
                "url": url,
            }
    except Exception as e:
        logger.warning(f"Managed scraper proxy request failed: {e}")
        return None


async def fetch_with_curl_cffi(url: str, timeout: int = 30) -> Optional[Dict[str, Any]]:
    """Stealth page fetch using curl_cffi with full Chrome TLS fingerprint impersonation.
    Effectively bypasses Cloudflare, DataDome, and anti-bot TLS fingerprinting.
    """
    try:
        from curl_cffi.requests import AsyncSession
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "DNT": "1",
            "Upgrade-Insecure-Requests": "1",
        }
        async with AsyncSession(impersonate="chrome120") as session:
            resp = await session.get(url, headers=headers, timeout=float(timeout), allow_redirects=True)
            if resp.status_code == 200 or len(resp.text) > 500:
                return {
                    "html": resp.text,
                    "status_code": resp.status_code,
                    "url": str(resp.url),
                }
    except Exception as e:
        logger.debug(f"curl_cffi fetch error for {url}: {e}")
    return None


async def fetch_with_crawl4ai(url: str, wait_for_selector: Optional[str] = None, timeout: int = 30) -> Optional[Dict[str, Any]]:
    """Attempts page fetch using Crawl4AI with stealth configuration."""
    try:
        from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig

        browser_config = BrowserConfig(
            headless=settings.STEALTH_HEADLESS,
            verbose=False,
            user_agent=settings.DEFAULT_USER_AGENT,
        )

        run_config = CrawlerRunConfig(
            word_count_threshold=10,
            wait_for=wait_for_selector,
            page_timeout=timeout * 1000,
        )

        async with AsyncWebCrawler(config=browser_config) as crawler:
            result = await crawler.arun(url=url, config=run_config)
            if result and result.success:
                return {
                    "html": result.html or "",
                    "markdown": result.markdown or "",
                    "status_code": result.status_code or 200,
                    "url": url,
                }
            elif result:
                logger.warning(f"Crawl4AI fetch returned status {result.status_code} for {url}")
                return {
                    "html": result.html or "",
                    "markdown": result.markdown or "",
                    "status_code": result.status_code or 400,
                    "url": url,
                }
    except ImportError:
        logger.debug("Crawl4AI not installed; falling back to Playwright / HTTPX stealth driver.")
    except Exception as e:
        logger.warning(f"Crawl4AI execution error for {url}: {e}")

    return None


async def fetch_with_playwright_stealth(
    url: str,
    wait_for_selector: Optional[str] = None,
    timeout: int = 30,
) -> Optional[Dict[str, Any]]:
    """Attempts page fetch using Playwright with stealth modifications."""
    try:
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=settings.STEALTH_HEADLESS,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-features=IsolateOrigins,site-per-process",
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                ],
            )
            context = await browser.new_context(
                user_agent=settings.DEFAULT_USER_AGENT,
                viewport={"width": 1440, "height": 900},
                locale="en-US",
                timezone_id="America/New_York",
            )

            # Apply stealth scripts to hide webdriver
            await context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                window.chrome = { runtime: {} };
            """)

            page = await context.new_page()
            response = await page.goto(
                url,
                timeout=timeout * 1000,
                wait_until="domcontentloaded",
            )

            if wait_for_selector:
                try:
                    await page.wait_for_selector(wait_for_selector, timeout=5000)
                except Exception:
                    pass

            # Short settle pause for dynamic JS rendering
            await asyncio.sleep(1.5)

            html = await page.content()
            status_code = response.status if response else 200
            await browser.close()

            return {
                "html": html,
                "status_code": status_code,
                "url": url,
            }

    except ImportError:
        logger.debug("Playwright not installed; falling back to HTTPX stealth client.")
    except Exception as e:
        logger.warning(f"Playwright stealth fetch error for {url}: {e}")

    return None


async def fetch_with_httpx(url: str, timeout: int = 30) -> Dict[str, Any]:
    """Fallback stealth HTTP client with browser headers."""
    headers = {
        "User-Agent": settings.DEFAULT_USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
    }

    try:
        import h2  # noqa: F401
        use_http2 = True
    except ImportError:
        use_http2 = False

    async with httpx.AsyncClient(
        headers=headers,
        timeout=float(timeout),
        follow_redirects=True,
        http2=use_http2,
    ) as client:
        response = await client.get(url)
        return {
            "html": response.text,
            "status_code": response.status_code,
            "url": str(response.url),
        }


async def fetch_page_content(
    url: str,
    wait_for_selector: Optional[str] = None,
    timeout: Optional[int] = None,
) -> str:
    """Primary asynchronous web navigation tool.
    Bypasses anti-bot barriers and returns clean, LLM-ready Markdown text.

    Args:
        url: Target web page URL to fetch.
        wait_for_selector: Optional CSS selector to wait for before extracting DOM.
        timeout: Request timeout in seconds. Defaults to settings.DEFAULT_PAGE_TIMEOUT.

    Returns:
        Structured Markdown text of the page content or anti-bot block diagnostics.
    """
    timeout_sec = timeout or settings.DEFAULT_PAGE_TIMEOUT
    logger.info(f"🌐 Stealth fetching: {url} (Timeout: {timeout_sec}s)...")
    start_time = time.perf_counter()

    raw_result: Optional[Dict[str, Any]] = None

    # Step 1: Check if managed proxy API is configured
    if settings.MANAGED_SCRAPER_API_KEY:
        raw_result = await fetch_with_managed_api(url, timeout_sec)

    # Step 2: Try curl_cffi with full Chrome TLS fingerprint impersonation (fast & bypasses Cloudflare)
    if not raw_result:
        raw_result = await fetch_with_curl_cffi(url, timeout_sec)

    # Step 3: Try Crawl4AI open-source stealth engine
    if not raw_result:
        raw_result = await fetch_with_crawl4ai(url, wait_for_selector, timeout_sec)

    # Step 4: Try Playwright with stealth patches
    if not raw_result:
        raw_result = await fetch_with_playwright_stealth(url, wait_for_selector, timeout_sec)

    # Step 5: Fallback to HTTPX client
    if not raw_result:
        try:
            raw_result = await fetch_with_httpx(url, timeout_sec)
        except httpx.HTTPStatusError as e:
            elapsed = time.perf_counter() - start_time
            logger.error(f"HTTP error {e.response.status_code} fetching {url} in {elapsed:.2f}s")
            return f"[ERROR: HTTP {e.response.status_code}] Failed to access {url}: {e}"
        except httpx.TimeoutException:
            elapsed = time.perf_counter() - start_time
            logger.error(f"Timeout fetching {url} after {elapsed:.2f}s")
            return f"[ERROR: TIMEOUT] Timed out while attempting to load {url} after {timeout_sec}s."
        except Exception as e:
            elapsed = time.perf_counter() - start_time
            logger.error(f"Network error fetching {url} in {elapsed:.2f}s: {e}")
            return f"[ERROR: NETWORK] Failed to connect to {url}: {e}"

    elapsed = time.perf_counter() - start_time
    html_content = raw_result.get("html", "")
    status_code = raw_result.get("status_code", 200)

    # Step 5: Check for Anti-Bot / CAPTCHA Block
    block_reason = check_for_anti_bot_block(html_content, status_code)
    if block_reason:
        logger.warning(f"⚠️ Anti-bot block detected for {url} ({block_reason}) in {elapsed:.2f}s")
        return (
            f"[ANTI_BOT_BLOCKED]\n"
            f"URL: {url}\n"
            f"Status Code: {status_code}\n"
            f"Reason: {block_reason}\n"
            f"Action: Note this board failure in StateManager and pause or advance to next target."
        )

    # Step 6: Convert to clean LLM-ready Markdown
    markdown = raw_result.get("markdown") or clean_html_to_markdown(html_content, url)

    logger.info(f"✅ Successfully fetched {url} in {elapsed:.2f}s ({len(markdown)} chars Markdown).")
    return (
        f"# Content from: {url}\n"
        f"Fetched At: {datetime.utcnow().isoformat()}Z | HTTP Status: {status_code}\n\n"
        f"{markdown}"
    )


class WebNavigatorTool(BaseAgentTool):
    """Tool exposing fetch_page_content to the Antigravity Agent."""

    name = "fetch_page_content"
    description = (
        "Navigates to any target URL, bypasses anti-bot barriers (Cloudflare, etc.), "
        "and returns clean, structured Markdown text without navigation noise."
    )

    async def execute(
        self,
        url: str,
        wait_for_selector: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> str:
        """Executes the fetch_page_content tool."""
        return await fetch_page_content(
            url=url,
            wait_for_selector=wait_for_selector,
            timeout=timeout,
        )


# Register WebNavigatorTool into global registry
registry.register(WebNavigatorTool())
