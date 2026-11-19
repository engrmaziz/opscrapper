"""
Link Extraction Tool for discovering on-site navigation and career links.
Parses anchor tags and resolves relative paths to absolute URLs.
"""

import asyncio
import re
from typing import Dict, Optional
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from config.settings import settings
from config.logging_config import get_logger
from tools.web_navigator import fetch_page_content

logger = get_logger("LinkExtractor")


async def extract_navigation_links(url: str, timeout: float = 15.0) -> Dict[str, str]:
    """Extracts all clickable navigation and anchor links from a webpage, resolving relative URLs.

    Args:
        url: Webpage URL to inspect (e.g. 'https://www.epicgames.com').
        timeout: Maximum seconds to wait before timing out (default: 15.0s).

    Returns:
        Dict mapping link text / label to its resolved absolute URL: {"Careers": "https://...", ...}.
    """
    logger.info(f"🔗 Extracting navigation links from '{url}' (timeout={timeout}s)...")
    links_map: Dict[str, str] = {}

    if not url or not url.startswith("http"):
        return links_map

    content = ""
    try:
        # Fetch with strict timeout
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            headers = {
                "User-Agent": settings.DEFAULT_USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            }
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                content = resp.text
    except Exception as e:
        logger.debug(f"Direct HTTP fetch failed for {url} ({e}). Attempting stealth fetch...")

    # Fallback to stealth navigator fetcher if content is empty
    if not content:
        try:
            content = await asyncio.wait_for(fetch_page_content(url), timeout=timeout)
        except asyncio.TimeoutError:
            logger.warning(f"⏳ Timeout ({timeout}s) exceeded while fetching '{url}'.")
            return links_map
        except Exception as e:
            logger.warning(f"⚠️ Failed to load '{url}' for link extraction: {e}")
            return links_map

    if not content or "[ANTI_BOT_BLOCKED]" in content or "[ERROR" in content:
        return links_map

    # 1. Parse HTML anchor tags
    if "<html" in content.lower() or "<a " in content.lower() or "<nav" in content.lower():
        try:
            soup = BeautifulSoup(content, "html.parser")
            for a_tag in soup.find_all("a", href=True):
                href = a_tag["href"].strip()
                if not href or href.startswith("#") or href.startswith("javascript:") or href.startswith("mailto:") or href.startswith("tel:"):
                    continue

                full_url = urljoin(url, href)

                # Extract descriptive text
                text = a_tag.get_text(separator=" ", strip=True)
                if not text:
                    text = a_tag.get("aria-label") or a_tag.get("title") or ""

                text_clean = re.sub(r"\s+", " ", str(text)).strip()
                if not text_clean:
                    # Use last segment of path as fallback label
                    path_part = urlparse(full_url).path.strip("/").split("/")[-1]
                    text_clean = path_part if path_part else "Link"

                links_map[text_clean] = full_url
        except Exception as e:
            logger.debug(f"HTML link parsing exception for {url}: {e}")

    # 2. Parse Markdown links if content is markdown format
    if not links_map and "[" in content and "](" in content:
        for match in re.finditer(r"\[([^\]]+)\]\(([^)]+)\)", content):
            text = match.group(1).strip()
            href = match.group(2).strip()
            if href and not href.startswith("#") and not href.startswith("javascript:"):
                full_url = urljoin(url, href)
                links_map[text] = full_url

    logger.info(f"✅ Extracted {len(links_map)} navigation links from '{url}'.")
    return links_map
