"""
Freelance & Creator Job Board Scrapers:
Upwork, Freelancer.com, Guru, and ProBlogger.
Features robust TLS fingerprinting, semantic project extraction, and keyword filtering.
"""

import asyncio
from datetime import datetime
import json
import re
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus, urljoin

from bs4 import BeautifulSoup
import httpx
from config.settings import settings
from config.logging_config import get_logger
from tools.web_navigator import fetch_page_content
from utils.state_manager import state_manager
from utils.keyword_matcher import filter_jobs_by_keyword

logger = get_logger("FreelanceBoards")


def is_valid_freelance_job(job: Dict[str, Any]) -> bool:
    """Validates freelance job structure."""
    title = str(job.get("title", "")).strip()
    company = str(job.get("company", "")).strip()
    url = str(job.get("listing_url", "") or job.get("board_url", "")).strip()
    return len(title) >= 2 and len(company) >= 2 and url.startswith("http")


# ==============================================================================
# 1. Upwork Scraper (https://www.upwork.com)
# ==============================================================================

def parse_upwork_listings(raw_content: str, keyword: str = "") -> List[Dict[str, Any]]:
    """Extracts freelance projects from Upwork guest job search."""
    jobs: List[Dict[str, Any]] = []
    try:
        soup = BeautifulSoup(raw_content, "html.parser")
        tiles = soup.select("article[data-test='JobTile'], .job-tile")
        for tile in tiles:
            t_elem = tile.find(["h2", "h3", "a"])
            link_elem = tile.find("a", href=True)
            if not t_elem or not link_elem:
                continue

            title = t_elem.get_text(strip=True)
            raw_href = link_elem["href"].split("?")[0]
            full_url = urljoin("https://www.upwork.com", raw_href)

            job_dict = {
                "title": title,
                "company": "Upwork Client",
                "source_board": "Upwork",
                "board_source": "Upwork",
                "listing_url": full_url,
                "board_url": full_url,
                "location": "Remote / Worldwide",
            }
            if is_valid_freelance_job(job_dict) and not any(j["listing_url"] == full_url for j in jobs):
                jobs.append(job_dict)
    except Exception as e:
        logger.debug(f"Upwork parsing error: {e}")

    return filter_jobs_by_keyword(jobs, keyword)


async def scrape_upwork(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes Upwork remote freelance opportunities."""
    logger.info(f"💼 [Upwork] Scraping keyword='{keyword}'...")
    url = f"https://www.upwork.com/nx/search/jobs/?q={quote_plus(keyword)}"
    try:
        from curl_cffi import requests as cffi_requests
        resp = await asyncio.to_thread(cffi_requests.get, url, impersonate="chrome120", timeout=12)
        if resp.status_code == 200 and resp.text:
            jobs = parse_upwork_listings(resp.text, keyword)
            logger.info(f"✅ [Upwork] Extracted {len(jobs)} jobs.")
            return jobs[:limit]
        content = await fetch_page_content(url)
        jobs = parse_upwork_listings(content, keyword)
        return jobs[:limit]
    except Exception as e:
        logger.error(f"❌ [Upwork] Failed: {e}")
        return []


# ==============================================================================
# 2. Freelancer.com Scraper (https://www.freelancer.com)
# ==============================================================================

def parse_freelancer_listings(raw_content: str, keyword: str = "") -> List[Dict[str, Any]]:
    """Extracts freelance projects from Freelancer.com."""
    jobs: List[Dict[str, Any]] = []
    try:
        soup = BeautifulSoup(raw_content, "html.parser")
        items = soup.select(".JobSearchCard-item")
        for item in items:
            link_elem = item.find("a", class_=re.compile(r"title", re.I)) or item.find("a", href=True)
            if not link_elem:
                continue

            title = link_elem.get_text(strip=True)
            full_url = urljoin("https://www.freelancer.com", link_elem["href"])

            job_dict = {
                "title": title,
                "company": "Freelancer Client",
                "source_board": "Freelancer",
                "board_source": "Freelancer",
                "listing_url": full_url,
                "board_url": full_url,
                "location": "Remote",
            }
            if is_valid_freelance_job(job_dict) and not any(j["listing_url"] == full_url for j in jobs):
                jobs.append(job_dict)
    except Exception as e:
        logger.debug(f"Freelancer parsing error: {e}")

    return filter_jobs_by_keyword(jobs, keyword)


async def scrape_freelancer(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes Freelancer.com projects."""
    logger.info(f"🌐 [Freelancer] Scraping keyword='{keyword}'...")
    kw_slug = re.sub(r"[^a-zA-Z0-9]+", "-", keyword.lower()).strip("-") or "developer"
    url = f"https://www.freelancer.com/jobs/{kw_slug}/"
    try:
        from curl_cffi import requests as cffi_requests
        resp = await asyncio.to_thread(cffi_requests.get, url, impersonate="chrome120", timeout=12)
        if resp.status_code == 200 and resp.text:
            jobs = parse_freelancer_listings(resp.text, keyword)
            if jobs:
                logger.info(f"✅ [Freelancer] Extracted {len(jobs)} jobs.")
                return jobs[:limit]

        # Fallback to search query
        search_url = f"https://www.freelancer.com/projects/?keyword={quote_plus(keyword)}"
        resp2 = await asyncio.to_thread(cffi_requests.get, search_url, impersonate="chrome120", timeout=12)
        if resp2.status_code == 200 and resp2.text:
            jobs = parse_freelancer_listings(resp2.text, keyword)
            return jobs[:limit]

        content = await fetch_page_content(url)
        jobs = parse_freelancer_listings(content, keyword)
        return jobs[:limit]
    except Exception as e:
        logger.error(f"❌ [Freelancer] Failed: {e}")
        return []


# ==============================================================================
# 3. Guru Scraper (https://www.guru.com)
# ==============================================================================

def parse_guru_listings(raw_content: str, keyword: str = "") -> List[Dict[str, Any]]:
    """Extracts freelance projects from Guru."""
    jobs: List[Dict[str, Any]] = []
    try:
        soup = BeautifulSoup(raw_content, "html.parser")
        records = soup.find_all(class_=re.compile(r"\bjobRecord\b"))
        for rec in records:
            t_elem = rec.find(class_=re.compile(r"jobRecord__title"))
            link_elem = rec.find("a", href=True)
            if not t_elem or not link_elem:
                continue

            title = t_elem.get_text(strip=True)
            raw_href = link_elem["href"].split("&SearchUrl")[0]
            full_url = urljoin("https://www.guru.com", raw_href)

            job_dict = {
                "title": title,
                "company": "Guru Employer",
                "source_board": "Guru",
                "board_source": "Guru",
                "listing_url": full_url,
                "board_url": full_url,
                "location": "Remote",
            }
            if is_valid_freelance_job(job_dict) and not any(j["listing_url"] == full_url for j in jobs):
                jobs.append(job_dict)
    except Exception as e:
        logger.debug(f"Guru parsing error: {e}")

    return filter_jobs_by_keyword(jobs, keyword)


async def scrape_guru(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes Guru freelance opportunities."""
    logger.info(f"💼 [Guru] Scraping keyword='{keyword}'...")
    kw_slug = re.sub(r"[^a-zA-Z0-9]+", "-", keyword.lower()).strip("-") or "programming-development"
    url = f"https://www.guru.com/d/jobs/skill/{kw_slug}/"
    try:
        from curl_cffi import requests as cffi_requests
        resp = await asyncio.to_thread(cffi_requests.get, url, impersonate="chrome120", timeout=12)
        if resp.status_code == 200 and resp.text:
            jobs = parse_guru_listings(resp.text, keyword)
            if jobs:
                logger.info(f"✅ [Guru] Extracted {len(jobs)} jobs.")
                return jobs[:limit]

        # Category fallback
        cat_url = "https://www.guru.com/d/jobs/c/programming-development/"
        resp2 = await asyncio.to_thread(cffi_requests.get, cat_url, impersonate="chrome120", timeout=12)
        if resp2.status_code == 200 and resp2.text:
            jobs = parse_guru_listings(resp2.text, keyword)
            return jobs[:limit]

        content = await fetch_page_content(url)
        jobs = parse_guru_listings(content, keyword)
        return jobs[:limit]
    except Exception as e:
        logger.error(f"❌ [Guru] Failed: {e}")
        return []


# ==============================================================================
# 4. ProBlogger Scraper (https://problogger.com/jobs)
# ==============================================================================

def parse_problogger_listings(raw_content: str, keyword: str = "") -> List[Dict[str, Any]]:
    """Extracts writing and content opportunities from ProBlogger."""
    jobs: List[Dict[str, Any]] = []
    try:
        soup = BeautifulSoup(raw_content, "html.parser")
        links = [a for a in soup.find_all("a", href=True) if "/job/" in a["href"]]
        for l in links:
            title = l.get_text(strip=True)
            if not title or len(title) < 4:
                continue
            full_url = urljoin("https://problogger.com", l["href"])
            job_dict = {
                "title": title,
                "company": "ProBlogger Employer",
                "source_board": "ProBlogger",
                "board_source": "ProBlogger",
                "listing_url": full_url,
                "board_url": full_url,
                "location": "Remote",
            }
            if is_valid_freelance_job(job_dict) and not any(j["listing_url"] == full_url for j in jobs):
                jobs.append(job_dict)
    except Exception as e:
        logger.debug(f"ProBlogger parsing error: {e}")

    return filter_jobs_by_keyword(jobs, keyword)


async def scrape_problogger(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes ProBlogger job board."""
    logger.info(f"✍️ [ProBlogger] Scraping keyword='{keyword}'...")
    url = f"https://problogger.com/jobs/?keyword={quote_plus(keyword)}"
    try:
        from curl_cffi import requests as cffi_requests
        resp = await asyncio.to_thread(cffi_requests.get, url, impersonate="chrome120", timeout=12)
        if resp.status_code == 200 and resp.text:
            jobs = parse_problogger_listings(resp.text, keyword)
            logger.info(f"✅ [ProBlogger] Extracted {len(jobs)} jobs.")
            return jobs[:limit]
        content = await fetch_page_content(url)
        jobs = parse_problogger_listings(content, keyword)
        return jobs[:limit]
    except Exception as e:
        logger.error(f"❌ [ProBlogger] Failed: {e}")
        return []


# ==============================================================================
# 5. HeyMarketers Scraper (https://heymarketers.com)
# ==============================================================================

def parse_heymarketers_listings(raw_content: str, keyword: str = "") -> List[Dict[str, Any]]:
    """Extracts 100% pure remote Digital Marketing, Growth, Content & SEO roles."""
    jobs: List[Dict[str, Any]] = []
    try:
        soup = BeautifulSoup(raw_content, "html.parser")
        for a in soup.find_all("a", href=True):
            href = a["href"]
            # HeyMarketers links directly to ATS jobs (greenhouse, lever, workable, stripe, adyen, etc.)
            if any(h in href for h in ["greenhouse.io", "lever.co", "workable.com", "stripe.com", "adyen.com", "jobs.personio"]):
                text = a.get_text(separator=" | ", strip=True)
                parts = [p.strip() for p in text.split("|") if p.strip()]
                if not parts:
                    continue
                title = parts[0]
                company = parts[1] if len(parts) > 1 else "Tech Growth Partner"

                job_dict = {
                    "title": title,
                    "company": company,
                    "board_source": "HeyMarketers",
                    "source_board": "HeyMarketers",
                    "listing_url": href,
                    "board_url": href,
                    "location": "100% Remote / Worldwide",
                }
                if is_valid_freelance_job(job_dict) and not any(existing["listing_url"] == href for existing in jobs):
                    jobs.append(job_dict)
    except Exception as e:
        logger.debug(f"HeyMarketers parsing error: {e}")

    return filter_jobs_by_keyword(jobs, keyword)


async def scrape_heymarketers(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes 100% pure remote marketing jobs from HeyMarketers."""
    logger.info(f"📢 [HeyMarketers] Scraping remote marketing jobs for keyword='{keyword}'...")
    url = "https://heymarketers.com/jobs/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }
    try:
        async with httpx.AsyncClient(headers=headers, timeout=12.0, follow_redirects=True) as client:
            resp = await client.get(url)
            if resp.status_code == 200 and resp.text:
                jobs = parse_heymarketers_listings(resp.text, keyword)
                logger.info(f"✅ [HeyMarketers] Extracted {len(jobs)} jobs.")
                return jobs[:limit]
        return []
    except Exception as e:
        logger.error(f"❌ [HeyMarketers] Failed: {e}")
        return []


# ==============================================================================
# 6. Twine Scraper (https://www.twine.net)
# ==============================================================================

def parse_twine_listings(raw_content: str, keyword: str = "") -> List[Dict[str, Any]]:
    """Extracts remote freelance projects and contracts for marketers, designers, and developers."""
    jobs: List[Dict[str, Any]] = []
    try:
        soup = BeautifulSoup(raw_content, "html.parser")
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if any(h in href for h in ["torchbox", "careers.teksystems.com", "greenhouse", "lever", "personio", "/jobs/"]):
                text = a.get_text(separator=" ", strip=True)
                if not text or text in ["View on site", "Apply", "Post a job", "Hire freelancers"]:
                    continue
                if len(text) < 4:
                    continue
                full_url = href if href.startswith("http") else urljoin("https://www.twine.net", href)

                company = "Twine Freelance Client"
                title = text
                if " - " in text:
                    parts = text.split(" - ", 1)
                    title = parts[0].strip()

                job_dict = {
                    "title": title,
                    "company": company,
                    "board_source": "Twine",
                    "source_board": "Twine",
                    "listing_url": full_url,
                    "board_url": full_url,
                    "location": "100% Remote / Freelance Contract",
                }
                if is_valid_freelance_job(job_dict) and not any(existing["listing_url"] == full_url for existing in jobs):
                    jobs.append(job_dict)
    except Exception as e:
        logger.debug(f"Twine parsing error: {e}")

    return filter_jobs_by_keyword(jobs, keyword)


async def scrape_twine(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes 100% remote freelance and contract roles from Twine."""
    logger.info(f"🧶 [Twine] Scraping freelance projects for keyword='{keyword}'...")
    urls = [
        "https://www.twine.net/jobs/digital-marketers",
        "https://www.twine.net/jobs/graphic-designers",
    ]
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }
    all_jobs: List[Dict[str, Any]] = []
    try:
        async with httpx.AsyncClient(headers=headers, timeout=12.0, follow_redirects=True) as client:
            for target_url in urls:
                try:
                    resp = await client.get(target_url)
                    if resp.status_code == 200 and resp.text:
                        parsed = parse_twine_listings(resp.text, keyword)
                        for pj in parsed:
                            if not any(existing["listing_url"] == pj["listing_url"] for existing in all_jobs):
                                all_jobs.append(pj)
                except Exception as inner_e:
                    logger.debug(f"Twine inner error for {target_url}: {inner_e}")
        logger.info(f"✅ [Twine] Extracted {len(all_jobs)} freelance projects.")
        return all_jobs[:limit]
    except Exception as e:
        logger.error(f"❌ [Twine] Failed: {e}")
        return []


