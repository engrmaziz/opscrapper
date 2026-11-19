"""
Startup & Venture-Backed Job Board Scrapers:
Wellfound, WorkAtAStartup (YC), DynamiteJobs, WelcomeToTheJungle, F6S, Startupers, EUStartups, Underdog.
"""

import asyncio
from datetime import datetime
import re
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus, urljoin
import xml.etree.ElementTree as ET

from bs4 import BeautifulSoup
import httpx
from config.logging_config import get_logger
from tools.web_navigator import fetch_page_content
from scrapers.standard_boards import is_valid_job
from utils.keyword_matcher import filter_jobs_by_keyword

logger = get_logger("StartupScrapers")


def parse_work_at_a_startup(raw_content: str, keyword: str = "") -> List[Dict[str, Any]]:
    """Extracts job postings from Y Combinator Work At A Startup."""
    jobs: List[Dict[str, Any]] = []
    base_url = "https://www.workatastartup.com"

    # Pattern: [Job Title](https://www.workatastartup.com/jobs/12345) followed by Company Name
    matches = re.findall(
        r"\[([^\]]+)\]\(((?:https?://www\.workatastartup\.com)?/jobs/[^\)]+)\)",
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

        # Extract company from URL slug if empty: /jobs/1234-stripe-software-engineer
        if not company:
            slug = href.rstrip("/").split("/")[-1]
            slug_clean = re.sub(r"^\d+-", "", slug)
            if "-" in slug_clean:
                company = slug_clean.split("-")[0].title()

        job_dict = {
            "title": title.replace("\ufffd", "-").strip(),
            "company": company.replace("\ufffd", "").strip(),
            "board_source": "WorkAtAStartup",
            "source_board": "WorkAtAStartup",
            "listing_url": full_url,
            "board_url": full_url,
            "location": "Remote / San Francisco",
        }
        if is_valid_job(job_dict) and not any(j["listing_url"] == full_url for j in jobs):
            jobs.append(job_dict)

    return filter_jobs_by_keyword(jobs, keyword)


async def scrape_work_at_a_startup(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes Y Combinator's Work At A Startup platform."""
    logger.info(f"🚀 [WorkAtAStartup] Scraping keyword='{keyword}'...")
    url = f"https://www.workatastartup.com/jobs?query={quote_plus(keyword)}"
    try:
        content = await fetch_page_content(url)
        if "[ANTI_BOT_BLOCKED]" in content:
            content = await fetch_page_content("https://www.workatastartup.com/jobs")
        jobs = parse_work_at_a_startup(content, keyword)
        return jobs[:limit]
    except Exception as e:
        logger.error(f"❌ [WorkAtAStartup] Error: {e}")
        return []


def parse_dynamite_jobs(raw_content: str, keyword: str = "") -> List[Dict[str, Any]]:
    """Extracts job postings from DynamiteJobs."""
    jobs: List[Dict[str, Any]] = []
    base_url = "https://dynamitejobs.com"

    matches = re.findall(
        r"\[([^\]]+)\]\(((?:https?://dynamitejobs\.com)?/company/[^/]+/remote-job/[^\)]+)\)",
        raw_content,
        re.I,
    )
    if not matches:
        matches = re.findall(
            r"\[([^\]]+)\]\(((?:https?://dynamitejobs\.com)?/remote-job/[^\)]+)\)",
            raw_content,
            re.I,
        )

    for text, href in matches:
        full_url = urljoin(base_url, href)
        company = ""
        # If URL has /company/company-name/remote-job/...
        comp_url_match = re.search(r"/company/([a-zA-Z0-9_-]+)/", href)
        if comp_url_match:
            company = comp_url_match.group(1).replace("-", " ").title()

        parts = [p.strip() for p in text.split(" at ") if p.strip()]
        if len(parts) >= 2:
            title = parts[0]
            if not company:
                company = parts[1]
        else:
            title = text

        job_dict = {
            "title": title.replace("\ufffd", "-").strip(),
            "company": company.replace("\ufffd", "").strip(),
            "board_source": "DynamiteJobs",
            "source_board": "DynamiteJobs",
            "listing_url": full_url,
            "board_url": full_url,
            "location": "100% Remote",
        }
        if is_valid_job(job_dict) and not any(j["listing_url"] == full_url for j in jobs):
            jobs.append(job_dict)

    return filter_jobs_by_keyword(jobs, keyword)


async def scrape_dynamite_jobs(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes DynamiteJobs."""
    logger.info(f"🧨 [DynamiteJobs] Scraping keyword='{keyword}'...")
    url = f"https://dynamitejobs.com/remote-jobs?search={quote_plus(keyword)}"
    try:
        content = await fetch_page_content(url)
        jobs = parse_dynamite_jobs(content, keyword)
        return jobs[:limit]
    except Exception as e:
        logger.error(f"❌ [DynamiteJobs] Error: {e}")
        return []


def parse_f6s_jobs(raw_content: str, keyword: str = "") -> List[Dict[str, Any]]:
    """Extracts job postings from F6S Startup Jobs."""
    jobs: List[Dict[str, Any]] = []
    base_url = "https://www.f6s.com"

    matches = re.findall(
        r"\[([^\]]+)\]\(((?:https?://www\.f6s\.com)?/jobs/[^\)]+)\)",
        raw_content,
        re.I,
    )
    for text, href in matches:
        full_url = urljoin(base_url, href)
        parts = [p.strip() for p in text.split(" - ") if p.strip()]
        title = parts[0] if parts else text
        company = parts[1] if len(parts) > 1 else ""

        if not company:
            at_parts = [p.strip() for p in text.split(" at ") if p.strip()]
            if len(at_parts) >= 2:
                title, company = at_parts[0], at_parts[1]

        job_dict = {
            "title": title.replace("\ufffd", "-").strip(),
            "company": company.replace("\ufffd", "").strip(),
            "board_source": "F6S",
            "source_board": "F6S",
            "listing_url": full_url,
            "board_url": full_url,
            "location": "Remote / Startup",
        }
        if is_valid_job(job_dict) and not any(j["listing_url"] == full_url for j in jobs):
            jobs.append(job_dict)

    return filter_jobs_by_keyword(jobs, keyword)


async def scrape_f6s(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes F6S."""
    logger.info(f"🌐 [F6S] Scraping keyword='{keyword}'...")
    url = f"https://www.f6s.com/jobs?query={quote_plus(keyword)}"
    try:
        content = await fetch_page_content(url)
        jobs = parse_f6s_jobs(content, keyword)
        return jobs[:limit]
    except Exception as e:
        logger.error(f"❌ [F6S] Error: {e}")
        return []


def parse_generic_startup_board(raw_content: str, board_name: str, base_url: str, keyword: str = "") -> List[Dict[str, Any]]:
    """Extracts startup job listings from Markdown text."""
    jobs: List[Dict[str, Any]] = []
    matches = re.findall(r"\[([^\]]+)\]\(([^\)]+)\)", raw_content)

    for text, href in matches:
        if not any(k in href.lower() for k in ["/job/", "/jobs/", "/career/", "/position/", "/offers/"]):
            continue
        if any(bad in href.lower() for bad in ["#", "javascript", "login", "register", "post-a-job"]):
            continue

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
            "board_source": board_name,
            "source_board": board_name,
            "listing_url": full_url,
            "board_url": full_url,
            "location": "Remote",
        }
        if is_valid_job(job_dict) and not any(j["listing_url"] == full_url for j in jobs):
            jobs.append(job_dict)

    return filter_jobs_by_keyword(jobs, keyword)


async def scrape_wellfound(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes Wellfound (AngelList Talent)."""
    logger.info(f"✌️ [Wellfound] Scraping keyword='{keyword}'...")
    url = f"https://wellfound.com/jobs"
    try:
        content = await fetch_page_content(url)
        jobs = parse_generic_startup_board(content, "Wellfound", "https://wellfound.com", keyword)
        return jobs[:limit]
    except Exception as e:
        logger.error(f"❌ [Wellfound] Error: {e}")
        return []


async def scrape_welcome_to_the_jungle(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes Welcome to the Jungle / Otta."""
    logger.info(f"🌴 [WelcomeToTheJungle] Scraping keyword='{keyword}'...")
    url = f"https://www.welcometothejungle.com/en/jobs?query={quote_plus(keyword)}"
    try:
        content = await fetch_page_content(url)
        jobs = parse_generic_startup_board(content, "WelcomeToTheJungle", "https://www.welcometothejungle.com", keyword)
        return jobs[:limit]
    except Exception as e:
        logger.error(f"❌ [WelcomeToTheJungle] Error: {e}")
        return []


async def scrape_startupers(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes Startupers."""
    logger.info(f"💡 [Startupers] Scraping keyword='{keyword}'...")
    url = f"https://www.startupers.com/jobs"
    try:
        content = await fetch_page_content(url)
        jobs = parse_generic_startup_board(content, "Startupers", "https://www.startupers.com", keyword)
        return jobs[:limit]
    except Exception as e:
        logger.error(f"❌ [Startupers] Error: {e}")
        return []


async def scrape_eu_startups(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes EU-Startups Jobs."""
    logger.info(f"🇪🇺 [EUStartups] Scraping keyword='{keyword}'...")
    url = f"https://www.eu-startups.com/jobs/"
    try:
        content = await fetch_page_content(url)
        jobs = parse_generic_startup_board(content, "EUStartups", "https://www.eu-startups.com", keyword)
        return jobs[:limit]
    except Exception as e:
        logger.error(f"❌ [EUStartups] Error: {e}")
        return []


async def scrape_underdog(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes Underdog.io."""
    logger.info(f"🐕 [Underdog] Scraping keyword='{keyword}'...")
    url = "https://underdog.io/"
    try:
        content = await fetch_page_content(url)
        jobs = parse_generic_startup_board(content, "Underdog", "https://underdog.io", keyword)
        return jobs[:limit]
    except Exception as e:
        logger.error(f"❌ [Underdog] Error: {e}")
        return []


# ==============================================================================
# 9. Techstars Jobs Scraper
# ==============================================================================

async def scrape_techstars_jobs(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes Techstars Portfolio Jobs."""
    logger.info(f"🌟 [Techstars Jobs] Scraping keyword='{keyword}'...")
    url = f"https://jobs.techstars.com/jobs?query={quote_plus(keyword)}" if keyword else "https://jobs.techstars.com/jobs"
    try:
        content = await fetch_page_content(url)
        jobs = parse_generic_startup_board(content, "Techstars Jobs", "https://jobs.techstars.com", keyword)
        return jobs[:limit]
    except Exception as e:
        logger.error(f"❌ [Techstars Jobs] Error: {e}")
        return []


# ==============================================================================
# 10. Climatebase Scraper
# ==============================================================================

async def scrape_climatebase(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes Climatebase."""
    logger.info(f"🌱 [Climatebase] Scraping keyword='{keyword}'...")
    url = f"https://climatebase.org/jobs?q={quote_plus(keyword)}" if keyword else "https://climatebase.org/jobs"
    try:
        content = await fetch_page_content(url)
        jobs = parse_generic_startup_board(content, "Climatebase", "https://climatebase.org", keyword)
        return jobs[:limit]
    except Exception as e:
        logger.error(f"❌ [Climatebase] Error: {e}")
        return []


# ==============================================================================
# 11. ClimateTechList Scraper
# ==============================================================================

async def scrape_climatetechlist(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes ClimateTechList."""
    logger.info(f"🌿 [ClimateTechList] Scraping keyword='{keyword}'...")
    url = "https://www.climatetechlist.com/"
    try:
        content = await fetch_page_content(url)
        jobs = parse_generic_startup_board(content, "ClimateTechList", "https://www.climatetechlist.com", keyword)
        return jobs[:limit]
    except Exception as e:
        logger.error(f"❌ [ClimateTechList] Error: {e}")
        return []


# ==============================================================================
# 12. Startups.gallery Scraper
# ==============================================================================

async def scrape_startups_gallery(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes Startups.gallery (Top Tier VC Startups)."""
    logger.info(f"🖼️ [Startups.gallery] Scraping keyword='{keyword}'...")
    url = "https://startups.gallery/"
    try:
        content = await fetch_page_content(url)
        jobs = parse_generic_startup_board(content, "Startups.gallery", "https://startups.gallery", keyword)
        return jobs[:limit]
    except Exception as e:
        logger.error(f"❌ [Startups.gallery] Error: {e}")
        return []


# ==============================================================================
# 13. StartupJobs.cz Scraper
# ==============================================================================

async def scrape_startupjobs_cz(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes StartupJobs.com (European & Global Startups)."""
    logger.info(f"🚀 [StartupJobs.cz] Scraping keyword='{keyword}'...")
    url = f"https://www.startupjobs.com/offers?superfilter={quote_plus(keyword)}" if keyword else "https://www.startupjobs.com/offers"
    try:
        content = await fetch_page_content(url)
        jobs = parse_generic_startup_board(content, "StartupJobs.cz", "https://www.startupjobs.com", keyword)
        return jobs[:limit]
    except Exception as e:
        logger.error(f"❌ [StartupJobs.cz] Error: {e}")
        return []


# ==============================================================================
# 14. VCPlatform Scraper
# ==============================================================================

async def scrape_vcplatform(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes VC Platform Jobs."""
    logger.info(f"💼 [VCPlatform] Scraping keyword='{keyword}'...")
    url = "https://jobs.vcplatform.com/"
    try:
        content = await fetch_page_content(url)
        jobs = parse_generic_startup_board(content, "VCPlatform", "https://jobs.vcplatform.com", keyword)
        return jobs[:limit]
    except Exception as e:
        logger.error(f"❌ [VCPlatform] Error: {e}")
        return []


# ==============================================================================
# 15. Seedcamp Jobs Scraper
# ==============================================================================

async def scrape_seedcamp_jobs(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes Seedcamp European Seed Fund Portfolio Jobs."""
    logger.info(f"🌱 [Seedcamp Jobs] Scraping keyword='{keyword}'...")
    url = "https://jobs.seedcamp.com/"
    try:
        content = await fetch_page_content(url)
        jobs = parse_generic_startup_board(content, "Seedcamp Jobs", "https://jobs.seedcamp.com", keyword)
        return jobs[:limit]
    except Exception as e:
        logger.error(f"❌ [Seedcamp Jobs] Error: {e}")
        return []


# ==============================================================================
# 16. BerlinStartupJobs Scraper (https://berlinstartupjobs.com)
# ==============================================================================

def parse_berlinstartupjobs_listings(raw_content: str, keyword: str = "") -> List[Dict[str, Any]]:
    """Extracts Frontend, Backend, AI & Engineering roles from BerlinStartupJobs."""
    jobs: List[Dict[str, Any]] = []
    try:
        soup = BeautifulSoup(raw_content, "html.parser")
        for h in soup.find_all(["h2", "h3", "h4"]):
            a = h.find("a")
            if not a:
                continue
            title = a.text.strip()
            href = a.get("href", "")
            if not title or not href or href.rstrip("/") == "https://berlinstartupjobs.com/engineering":
                continue
            full_url = href if href.startswith("http") else urljoin("https://berlinstartupjobs.com", href)

            # Extract company from slug or title
            company = "European Tech Startup"
            slug = href.rstrip("/").split("/")[-1]
            if "-" in slug:
                parts = slug.split("-")
                company = parts[-1].replace(".html", "").title()
                if company.lower() in ["gmbh", "ag", "ug", "ev", "inc", "co", "ltd"] and len(parts) >= 2:
                    company = f"{parts[-2].title()} {company.upper()}"

            job_dict = {
                "title": title,
                "company": company,
                "board_source": "BerlinStartupJobs",
                "source_board": "BerlinStartupJobs",
                "listing_url": full_url,
                "board_url": full_url,
                "location": "Remote / Worldwide Hybrid",
            }
            if is_valid_job(job_dict) and not any(existing["listing_url"] == full_url for existing in jobs):
                jobs.append(job_dict)
    except Exception as e:
        logger.debug(f"BerlinStartupJobs parsing error: {e}")

    return filter_jobs_by_keyword(jobs, keyword)


async def scrape_berlinstartupjobs(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes remote tech & startup jobs from BerlinStartupJobs."""
    logger.info(f"🚀 [BerlinStartupJobs] Scraping keyword='{keyword}'...")
    url = "https://berlinstartupjobs.com/engineering/"
    try:
        from curl_cffi import requests as cffi_requests
        resp = await asyncio.to_thread(cffi_requests.get, url, impersonate="chrome120", timeout=12)
        if resp.status_code == 200 and resp.text:
            jobs = parse_berlinstartupjobs_listings(resp.text, keyword)
            logger.info(f"✅ [BerlinStartupJobs] Extracted {len(jobs)} jobs.")
            return jobs[:limit]
        content = await fetch_page_content(url)
        jobs = parse_berlinstartupjobs_listings(content, keyword)
        return jobs[:limit]
    except Exception as e:
        logger.error(f"❌ [BerlinStartupJobs] Failed: {e}")
        return []


# ==============================================================================
# 17. Hasjob Scraper (https://hasjob.co)
# ==============================================================================

def parse_hasjob_feed(raw_xml: str, keyword: str = "") -> List[Dict[str, Any]]:
    """Extracts tech, AI, backend and frontend roles from Hasjob Atom feed."""
    jobs: List[Dict[str, Any]] = []
    try:
        root = ET.fromstring(raw_xml)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        for entry in root.findall("atom:entry", ns):
            title_elem = entry.find("atom:title", ns)
            link_elem = entry.find("atom:link", ns)
            if title_elem is None or link_elem is None:
                continue

            raw_title = (title_elem.text or "").strip()
            link = link_elem.attrib.get("href", "").strip()
            if not raw_title or not link:
                continue

            author_elem = entry.find("atom:author/atom:name", ns)
            company = author_elem.text.strip() if author_elem is not None and author_elem.text else "Hasjob Community"

            title = raw_title
            if " at " in raw_title:
                parts = raw_title.split(" at ", 1)
                title = parts[0].strip()
                if not company or company == "Hasjob Community":
                    company = parts[1].split("-")[0].split(",")[0].strip()
            elif " - " in raw_title:
                parts = raw_title.split(" - ", 1)
                title = parts[0].strip()

            job_dict = {
                "title": title,
                "company": company or "Verified Tech Employer",
                "board_source": "Hasjob",
                "source_board": "Hasjob",
                "listing_url": link,
                "board_url": link,
                "location": "100% Remote / Worldwide",
            }
            if is_valid_job(job_dict) and not any(existing["listing_url"] == link for existing in jobs):
                jobs.append(job_dict)
    except Exception as e:
        logger.debug(f"Hasjob parsing error: {e}")

    return filter_jobs_by_keyword(jobs, keyword)


async def scrape_hasjob(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes tech and AI developer jobs from Hasjob official feed."""
    logger.info(f"⚡ [Hasjob] Scraping keyword='{keyword}'...")
    url = "https://hasjob.co/feed"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }
    try:
        async with httpx.AsyncClient(headers=headers, timeout=12.0, follow_redirects=True) as client:
            resp = await client.get(url)
            if resp.status_code == 200 and resp.text:
                jobs = parse_hasjob_feed(resp.text, keyword)
                logger.info(f"✅ [Hasjob] Extracted {len(jobs)} jobs.")
                return jobs[:limit]
        return []
    except Exception as e:
        logger.error(f"❌ [Hasjob] Failed: {e}")
        return []

