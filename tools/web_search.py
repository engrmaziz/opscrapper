"""
Web Search Tool for discovering company official domains, career portals, and direct ATS links.
Supports Multi-Engine Search: Bing HTML search with URL unwrapping, DDGS text search,
and DuckDuckGo HTML Lite fallback.
"""

import asyncio
import base64
import re
from typing import Any, Dict, List, Optional
import urllib.parse
from urllib.parse import quote_plus, urlparse

import httpx
from bs4 import BeautifulSoup
from config.settings import settings
from config.logging_config import get_logger

logger = get_logger("WebSearch")


def unwrap_bing_url(bing_url: str) -> str:
    """Decodes Bing redirect URLs containing base64 encoded destination targets."""
    try:
        if "u=" in bing_url:
            parsed = urllib.parse.parse_qs(urllib.parse.urlparse(bing_url).query)
            u_val = parsed.get("u", [""])[0]
            if u_val.startswith("a1"):
                padded = u_val[2:] + "=="
                decoded = base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8", errors="ignore")
                if decoded.startswith("http"):
                    return decoded
    except Exception:
        pass
    return bing_url


def unwrap_ddg_url(ddg_url: str) -> str:
    """Decodes DuckDuckGo redirect uddg parameters."""
    try:
        if "uddg=" in ddg_url:
            parsed_uddg = urllib.parse.parse_qs(urllib.parse.urlparse(ddg_url).query).get("uddg")
            if parsed_uddg and parsed_uddg[0].startswith("http"):
                return parsed_uddg[0]
    except Exception:
        pass
    return ddg_url


async def search_web(query: str, num_results: int = 5) -> List[Dict[str, str]]:
    """Performs an async multi-engine web search and returns top ranked results.

    Args:
        query: Search query string.
        num_results: Max number of results to return (default: 5).

    Returns:
        List of dictionaries with keys: 'title', 'url', 'snippet'.
    """
    logger.info(f"🔎 Executing web search: '{query}' (limit={num_results})...")
    results: List[Dict[str, str]] = []

    # 1. Primary Engine: Bing HTML search (High reliability, fast response, no 202 bot challenges)
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
        bing_url = f"https://www.bing.com/search?q={quote_plus(query)}"
        async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
            resp = await client.get(bing_url, headers=headers)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                for li in soup.select("li.b_algo"):
                    h2 = li.find("h2")
                    if h2 and h2.find("a"):
                        raw_href = h2.find("a").get("href", "")
                        real_url = unwrap_bing_url(raw_href)
                        title_text = h2.get_text(strip=True)
                        snippet_elem = li.find("p")
                        snippet_text = snippet_elem.get_text(strip=True) if snippet_elem else ""

                        if real_url and real_url.startswith("http") and not any(r["url"] == real_url for r in results):
                            results.append({
                                "title": title_text,
                                "url": real_url,
                                "snippet": snippet_text,
                            })

        if results:
            logger.info(f"✅ Bing search returned {len(results)} results.")
            return results[:num_results]
    except Exception as e:
        logger.debug(f"Bing search error: {e}")

    # 2. Secondary Engine: DDGS Package
    try:
        from duckduckgo_search import DDGS

        def _sync_ddgs():
            with DDGS() as ddgs:
                return list(ddgs.text(query, max_results=num_results))

        ddg_results = await asyncio.to_thread(_sync_ddgs)
        for item in ddg_results:
            url = item.get("href") or item.get("url") or ""
            title = item.get("title") or ""
            snippet = item.get("body") or item.get("snippet") or ""
            if url and url.startswith("http") and not any(r["url"] == url for r in results):
                results.append({
                    "title": title.strip(),
                    "url": url.strip(),
                    "snippet": snippet.strip(),
                })

        if results:
            logger.info(f"✅ DDGS returned {len(results)} search results.")
            return results[:num_results]
    except Exception as e:
        logger.debug(f"DDGS search error: {e}")

    # 3. Tertiary Engine: DuckDuckGo HTML Lite Fallback
    try:
        ddg_headers = {
            "User-Agent": settings.DEFAULT_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
        async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
            resp = await client.get(url, headers=ddg_headers)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                for res in soup.select(".result, .results_links, .result__body"):
                    title_elem = res.find(["a", "h2"], class_=re.compile(r"result__title|result__a|title", re.I)) or res.find("a")
                    if title_elem:
                        raw_href = title_elem.get("href", "")
                        clean_url = unwrap_ddg_url(raw_href)
                        title_text = title_elem.get_text(strip=True)
                        if clean_url and clean_url.startswith("http") and not any(r["url"] == clean_url for r in results):
                            results.append({
                                "title": title_text,
                                "url": clean_url,
                                "snippet": "",
                            })

        if results:
            return results[:num_results]
    except Exception as e:
        logger.warning(f"⚠️ DuckDuckGo HTML search fallback failed: {e}")

    return results[:num_results]
