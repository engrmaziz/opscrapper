"""
Gaming, Creative Engineering & Design Job Board Scrapers:
GamesJobsDirect, GameDevsOfColor, Hitmarker, WorkWithIndies, Maxibestof, Dribbble, ProductHunt, DesignJobs.
"""

import asyncio
from datetime import datetime
import re
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus, urljoin

from bs4 import BeautifulSoup
import httpx
from config.logging_config import get_logger
from tools.web_navigator import fetch_page_content
from scrapers.standard_boards import is_valid_job
from utils.keyword_matcher import filter_jobs_by_keyword

logger = get_logger("GamingDesignScrapers")


def parse_hitmarker(raw_content: str, keyword: str = "") -> List[Dict[str, Any]]:
    """Extracts job postings from Hitmarker Gaming & Esports."""
    jobs: List[Dict[str, Any]] = []
    base_url = "https://hitmarker.net"

    matches = re.findall(
        r"\[([^\]]+)\]\(((?:https?://hitmarker\.net)?/jobs/[^\)]+)\)",
        raw_content,
        re.I,
    )
    for text, href in matches:
        full_url = urljoin(base_url, href)
        parts = [p.strip() for p in text.split(" at ") if p.strip()]
        if len(parts) >= 2:
            title, company = parts[0], parts[1]
        else:
            hyphen_parts = [p.strip() for p in text.split(" - ") if p.strip()]
            title = hyphen_parts[0] if hyphen_parts else text
            company = hyphen_parts[1] if len(hyphen_parts) > 1 else ""

        job_dict = {
            "title": title.replace("\ufffd", "-").strip(),
            "company": company.replace("\ufffd", "").strip(),
            "board_source": "Hitmarker",
            "source_board": "Hitmarker",
            "listing_url": full_url,
            "board_url": full_url,
            "location": "Remote / Gaming",
        }
        if is_valid_job(job_dict) and not any(j["listing_url"] == full_url for j in jobs):
            jobs.append(job_dict)

    return filter_jobs_by_keyword(jobs, keyword)


async def scrape_hitmarker(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes Hitmarker."""
    logger.info(f"🎮 [Hitmarker] Scraping keyword='{keyword}'...")
    url = f"https://hitmarker.net/jobs?keyword={quote_plus(keyword)}"
    try:
        content = await fetch_page_content(url)
        jobs = parse_hitmarker(content, keyword)
        return jobs[:limit]
    except Exception as e:
        logger.error(f"❌ [Hitmarker] Error: {e}")
        return []


async def scrape_work_with_indies(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes WorkWithIndies."""
    logger.info(f"🕹️ [WorkWithIndies] Scraping keyword='{keyword}'...")
    url = "https://www.workwithindies.com/"
    try:
        content = await fetch_page_content(url)
        matches = re.findall(r"\[([^\]]+)\]\(((?:https?://www\.workwithindies\.com)?/careers/[^\)]+)\)", content, re.I)
        jobs = []
        for text, href in matches:
            full_url = urljoin("https://www.workwithindies.com", href)
            parts = [p.strip() for p in text.split(" at ") if p.strip()]
            title = parts[0] if parts else text
            company = parts[1] if len(parts) > 1 else ""
            job_dict = {
                "title": title,
                "company": company,
                "board_source": "WorkWithIndies",
                "source_board": "WorkWithIndies",
                "listing_url": full_url,
                "board_url": full_url,
                "location": "Remote / Indie Games",
            }
            if is_valid_job(job_dict) and not any(j["listing_url"] == full_url for j in jobs):
                jobs.append(job_dict)
        return filter_jobs_by_keyword(jobs, keyword)[:limit]
    except Exception as e:
        logger.error(f"❌ [WorkWithIndies] Error: {e}")
        return []


async def scrape_games_jobs_direct(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes GamesJobsDirect."""
    from scrapers.niche_boards import scrape_gamesjobsdirect
    return await scrape_gamesjobsdirect(keyword=keyword, location=location)


async def scrape_game_devs_of_color(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes Game Devs of Color."""
    from scrapers.niche_boards import scrape_gamedevsofcolor
    return await scrape_gamedevsofcolor(keyword=keyword, location=location)


async def scrape_maxibestof(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes Maxibestof Design Jobs."""
    from scrapers.niche_boards import scrape_maxibestof
    return await scrape_maxibestof(keyword=keyword, location=location)


async def scrape_dribbble_jobs(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes Dribbble Jobs."""
    logger.info(f"🎨 [Dribbble] Scraping keyword='{keyword}'...")
    url = f"https://dribbble.com/jobs?keyword={quote_plus(keyword)}"
    try:
        content = await fetch_page_content(url)
        matches = re.findall(r"\[([^\]]+)\]\(((?:https?://dribbble\.com)?/jobs/[^\)]+)\)", content, re.I)
        jobs = []
        for text, href in matches:
            full_url = urljoin("https://dribbble.com", href)
            parts = [p.strip() for p in text.split(" at ") if p.strip()]
            title = parts[0] if parts else text
            company = parts[1] if len(parts) > 1 else ""
            job_dict = {
                "title": title,
                "company": company,
                "board_source": "Dribbble",
                "source_board": "Dribbble",
                "listing_url": full_url,
                "board_url": full_url,
                "location": "Remote / Design",
            }
            if is_valid_job(job_dict) and not any(j["listing_url"] == full_url for j in jobs):
                jobs.append(job_dict)
        return filter_jobs_by_keyword(jobs, keyword)[:limit]
    except Exception as e:
        logger.error(f"❌ [Dribbble] Error: {e}")
        return []


async def scrape_product_hunt_jobs(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes ProductHunt Jobs."""
    logger.info(f"🐱 [ProductHunt] Scraping keyword='{keyword}'...")
    url = "https://www.producthunt.com/jobs"
    try:
        content = await fetch_page_content(url)
        matches = re.findall(r"\[([^\]]+)\]\(((?:https?://www\.producthunt\.com)?/jobs/[^\)]+)\)", content, re.I)
        jobs = []
        for text, href in matches:
            full_url = urljoin("https://www.producthunt.com", href)
            parts = [p.strip() for p in text.split(" at ") if p.strip()]
            title = parts[0] if parts else text
            company = parts[1] if len(parts) > 1 else ""
            job_dict = {
                "title": title,
                "company": company,
                "board_source": "ProductHunt",
                "source_board": "ProductHunt",
                "listing_url": full_url,
                "board_url": full_url,
                "location": "Remote / Product",
            }
            if is_valid_job(job_dict) and not any(j["listing_url"] == full_url for j in jobs):
                jobs.append(job_dict)
        return filter_jobs_by_keyword(jobs, keyword)[:limit]
    except Exception as e:
        logger.error(f"❌ [ProductHunt] Error: {e}")
        return []


async def scrape_design_jobs(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes DesignJobs.co."""
    logger.info(f"✨ [DesignJobs] Scraping keyword='{keyword}'...")
    url = f"https://designjobs.co/jobs?q={quote_plus(keyword)}"
    try:
        content = await fetch_page_content(url)
        matches = re.findall(r"\[([^\]]+)\]\(((?:https?://designjobs\.co)?/job/[^\)]+)\)", content, re.I)
        jobs = []
        for text, href in matches:
            full_url = urljoin("https://designjobs.co", href)
            parts = [p.strip() for p in text.split(" at ") if p.strip()]
            title = parts[0] if parts else text
            company = parts[1] if len(parts) > 1 else ""
            job_dict = {
                "title": title,
                "company": company,
                "board_source": "DesignJobs",
                "source_board": "DesignJobs",
                "listing_url": full_url,
                "board_url": full_url,
                "location": "Remote / Design",
            }
            if is_valid_job(job_dict) and not any(j["listing_url"] == full_url for j in jobs):
                jobs.append(job_dict)
        return filter_jobs_by_keyword(jobs, keyword)[:limit]
    except Exception as e:
        logger.error(f"❌ [DesignJobs] Error: {e}")
        return []


# ==============================================================================
# 9. GameJobHunter Scraper
# ==============================================================================

async def scrape_game_job_hunter(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes GameJobHunter (AAA & Indie Game Development)."""
    logger.info(f"🎯 [GameJobHunter] Scraping keyword='{keyword}'...")
    url = "https://gamejobhunter.com/job-postings/"
    try:
        content = await fetch_page_content(url)
        matches = re.findall(r"\[([^\]]+)\]\(((?:https?://gamejobhunter\.com)?/jobs?/[^\)]+)\)", content, re.I)
        jobs = []
        for text, href in matches:
            full_url = urljoin("https://gamejobhunter.com", href)
            parts = [p.strip() for p in text.split(" - ") if p.strip()]
            title = parts[0] if parts else text
            company = parts[1] if len(parts) > 1 else "AAA Game Studio"
            job_dict = {
                "title": title,
                "company": company,
                "board_source": "GameJobHunter",
                "source_board": "GameJobHunter",
                "listing_url": full_url,
                "board_url": full_url,
                "location": "Remote / Game Dev",
            }
            if is_valid_job(job_dict) and not any(j["listing_url"] == full_url for j in jobs):
                jobs.append(job_dict)
        return filter_jobs_by_keyword(jobs, keyword)[:limit]
    except Exception as e:
        logger.error(f"❌ [GameJobHunter] Error: {e}")
        return []


# ==============================================================================
# 10. BehanceJobs Scraper
# ==============================================================================

async def scrape_behance_jobs(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes Adobe Behance Creative & UI/UX Jobs."""
    logger.info(f"🎨 [BehanceJobs] Scraping keyword='{keyword}'...")
    url = "https://www.behance.net/joblist"
    try:
        content = await fetch_page_content(url)
        matches = re.findall(r"\[([^\]]+)\]\(((?:https?://www\.behance\.net)?/job/[^\)]+)\)", content, re.I)
        jobs = []
        for text, href in matches:
            full_url = urljoin("https://www.behance.net", href)
            parts = [p.strip() for p in text.split(" at ") if p.strip()]
            title = parts[0] if parts else text
            company = parts[1] if len(parts) > 1 else "Adobe Creative Partner"
            job_dict = {
                "title": title,
                "company": company,
                "board_source": "BehanceJobs",
                "source_board": "BehanceJobs",
                "listing_url": full_url,
                "board_url": full_url,
                "location": "Remote / Creative",
            }
            if is_valid_job(job_dict) and not any(j["listing_url"] == full_url for j in jobs):
                jobs.append(job_dict)
        return filter_jobs_by_keyword(jobs, keyword)[:limit]
    except Exception as e:
        logger.error(f"❌ [BehanceJobs] Error: {e}")
        return []


# ==============================================================================
# 11. Designhill Scraper (https://www.designhill.com)
# ==============================================================================

def parse_designhill_listings(raw_content: str, keyword: str = "") -> List[Dict[str, Any]]:
    """Extracts design opportunities and contests from Designhill."""
    jobs: List[Dict[str, Any]] = []
    try:
        soup = BeautifulSoup(raw_content, "html.parser")
        links = [a for a in soup.find_all("a", href=True) if "/contest/" in a["href"]]
        for a in links:
            title = a.get_text(strip=True)
            if not title or len(title) < 4:
                continue
            full_url = urljoin("https://www.designhill.com", a["href"])
            job_dict = {
                "title": title,
                "company": "Designhill Client",
                "board_source": "Designhill",
                "source_board": "Designhill",
                "listing_url": full_url,
                "board_url": full_url,
                "location": "Remote / Global",
            }
            if is_valid_job(job_dict) and not any(j["listing_url"] == full_url for j in jobs):
                jobs.append(job_dict)
    except Exception as e:
        logger.debug(f"Designhill parsing error: {e}")
    return filter_jobs_by_keyword(jobs, keyword)


async def scrape_designhill(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes Designhill design and creative projects."""
    logger.info(f"🎨 [Designhill] Scraping keyword='{keyword}'...")
    url = "https://www.designhill.com/design-contests"
    try:
        from curl_cffi import requests as cffi_requests
        resp = await asyncio.to_thread(cffi_requests.get, url, impersonate="chrome120", timeout=12)
        if resp.status_code == 200 and resp.text:
            jobs = parse_designhill_listings(resp.text, keyword)
            logger.info(f"✅ [Designhill] Extracted {len(jobs)} jobs.")
            return jobs[:limit]
        content = await fetch_page_content(url)
        jobs = parse_designhill_listings(content, keyword)
        return jobs[:limit]
    except Exception as e:
        logger.error(f"❌ [Designhill] Failed: {e}")
        return []


# ==============================================================================
# 14. UIUXJobsBoard Scraper (https://uiuxjobsboard.com)
# ==============================================================================

def parse_uiuxjobsboard_listings(raw_content: str, keyword: str = "") -> List[Dict[str, Any]]:
    """Extracts curated 100% remote Product Design, UI/UX, and Visual Design roles."""
    jobs: List[Dict[str, Any]] = []
    try:
        soup = BeautifulSoup(raw_content, "html.parser")
        for a in soup.select('a[href*="/job/"]'):
            href = a.get("href", "")
            if not href or "post-a-job" in href or "create" in href:
                continue
            full_url = href if href.startswith("http") else urljoin("https://uiuxjobsboard.com", href)
            text = a.get_text(separator=" | ", strip=True)
            parts = [p.strip() for p in text.split("|") if p.strip() and p.strip() != "is hiring"]
            if len(parts) >= 2:
                company = parts[0]
                title = parts[-1]
            elif len(parts) == 1:
                title = parts[0]
                company = "UI/UX Partner"
            else:
                continue

            job_dict = {
                "title": title,
                "company": company,
                "board_source": "UIUXJobsBoard",
                "source_board": "UIUXJobsBoard",
                "listing_url": full_url,
                "board_url": full_url,
                "location": "100% Remote / Worldwide",
            }
            if is_valid_job(job_dict) and not any(existing["listing_url"] == full_url for existing in jobs):
                jobs.append(job_dict)
    except Exception as e:
        logger.debug(f"UIUXJobsBoard parsing error: {e}")

    return filter_jobs_by_keyword(jobs, keyword)


async def scrape_uiuxjobsboard(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes curated remote UI/UX & Product Design roles from UIUXJobsBoard."""
    logger.info(f"🎨 [UIUXJobsBoard] Scraping remote design jobs for keyword='{keyword}'...")
    url = "https://uiuxjobsboard.com/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }
    try:
        async with httpx.AsyncClient(headers=headers, timeout=12.0, follow_redirects=True) as client:
            resp = await client.get(url)
            if resp.status_code == 200 and resp.text:
                jobs = parse_uiuxjobsboard_listings(resp.text, keyword)
                logger.info(f"✅ [UIUXJobsBoard] Extracted {len(jobs)} jobs.")
                return jobs[:limit]
        return []
    except Exception as e:
        logger.error(f"❌ [UIUXJobsBoard] Failed: {e}")
        return []


# ==============================================================================
# 15. RemoteGameJobs Scraper (https://remotegamejobs.com)
# ==============================================================================

def parse_remotegamejobs_listings(raw_content: str, keyword: str = "") -> List[Dict[str, Any]]:
    """Extracts 100% remote 3D, UI/UX, Frontend & Gaming roles."""
    jobs: List[Dict[str, Any]] = []
    try:
        soup = BeautifulSoup(raw_content, "html.parser")
        for a in soup.select('a[href*="/jobs/"]'):
            href = a.get("href", "")
            if not href or href == "/jobs" or href.endswith("/jobs/"):
                continue
            full_url = href if href.startswith("http") else urljoin("https://remotegamejobs.com", href)
            text = a.get_text(separator=" | ", strip=True)
            parts = [p.strip() for p in text.split("|") if p.strip()]
            if not parts:
                continue
            title = parts[0]
            company = parts[1] if len(parts) > 1 else "Remote Game Partner"

            job_dict = {
                "title": title,
                "company": company,
                "board_source": "RemoteGameJobs",
                "source_board": "RemoteGameJobs",
                "listing_url": full_url,
                "board_url": full_url,
                "location": "100% Remote",
            }
            if is_valid_job(job_dict) and not any(existing["listing_url"] == full_url for existing in jobs):
                jobs.append(job_dict)
    except Exception as e:
        logger.debug(f"RemoteGameJobs parsing error: {e}")

    return filter_jobs_by_keyword(jobs, keyword)


async def scrape_remotegamejobs(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes 100% remote gaming, 3D, and design jobs from RemoteGameJobs."""
    logger.info(f"🎮 [RemoteGameJobs] Scraping keyword='{keyword}'...")
    url = "https://remotegamejobs.com/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }
    try:
        async with httpx.AsyncClient(headers=headers, timeout=12.0, follow_redirects=True) as client:
            resp = await client.get(url)
            if resp.status_code == 200 and resp.text:
                jobs = parse_remotegamejobs_listings(resp.text, keyword)
                logger.info(f"✅ [RemoteGameJobs] Extracted {len(jobs)} jobs.")
                return jobs[:limit]
        return []
    except Exception as e:
        logger.error(f"❌ [RemoteGameJobs] Failed: {e}")
        return []


