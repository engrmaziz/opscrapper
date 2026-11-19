"""
Regional & Global Remote Job Board Scrapers:
OnlineJobs.ph, NoFluffJobs, Jobgether, EuroTechJobs, WorkInStartups, GermanTechJobs.
"""

import asyncio
from datetime import datetime
import re
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus, urljoin

from bs4 import BeautifulSoup
from config.logging_config import get_logger
from tools.web_navigator import fetch_page_content
from scrapers.standard_boards import is_valid_job
from utils.keyword_matcher import filter_jobs_by_keyword

logger = get_logger("RegionalScrapers")


def parse_onlinejobs_ph(raw_content: str, keyword: str = "") -> List[Dict[str, Any]]:
    """Extracts job postings from OnlineJobs.ph."""
    jobs: List[Dict[str, Any]] = []
    base_url = "https://www.onlinejobs.ph"

    matches = re.findall(
        r"\[([^\]]+)\]\(((?:https?://www\.onlinejobs\.ph)?/jobseekers/job/[^\)]+)\)",
        raw_content,
        re.I,
    )
    for text, href in matches:
        full_url = urljoin(base_url, href)
        title = text.replace("\ufffd", "-").strip()
        parts = [p.strip() for p in title.split(" - ") if p.strip()]
        job_title = parts[0] if parts else title
        company = parts[1] if len(parts) > 1 else "OnlineJobs Client"

        job_dict = {
            "title": job_title,
            "company": company,
            "board_source": "OnlineJobs.ph",
            "source_board": "OnlineJobs.ph",
            "listing_url": full_url,
            "board_url": full_url,
            "location": "Remote / Philippines",
        }
        if is_valid_job(job_dict) and not any(j["listing_url"] == full_url for j in jobs):
            jobs.append(job_dict)

    return filter_jobs_by_keyword(jobs, keyword)


async def scrape_onlinejobs_ph(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes OnlineJobs.ph."""
    logger.info(f"🇵🇭 [OnlineJobs.ph] Scraping keyword='{keyword}'...")
    url = f"https://www.onlinejobs.ph/jobseekers/jobsearch?jobkeyword={quote_plus(keyword)}"
    try:
        content = await fetch_page_content(url)
        jobs = parse_onlinejobs_ph(content, keyword)
        return jobs[:limit]
    except Exception as e:
        logger.error(f"❌ [OnlineJobs.ph] Error: {e}")
        return []


def parse_nofluffjobs(raw_content: str, keyword: str = "") -> List[Dict[str, Any]]:
    """Extracts job postings from NoFluffJobs."""
    jobs: List[Dict[str, Any]] = []
    base_url = "https://nofluffjobs.com"

    matches = re.findall(
        r"\[([^\]]+)\]\(((?:https?://nofluffjobs\.com)?/job/[^\)]+)\)",
        raw_content,
        re.I,
    )
    for text, href in matches:
        full_url = urljoin(base_url, href)
        parts = [p.strip() for p in text.split(" at ") if p.strip()]
        title = parts[0] if parts else text
        company = parts[1] if len(parts) > 1 else ""

        job_dict = {
            "title": title.replace("\ufffd", "-").strip(),
            "company": company.replace("\ufffd", "").strip(),
            "board_source": "NoFluffJobs",
            "source_board": "NoFluffJobs",
            "listing_url": full_url,
            "board_url": full_url,
            "location": "Remote / Europe",
        }
        if is_valid_job(job_dict) and not any(j["listing_url"] == full_url for j in jobs):
            jobs.append(job_dict)

    return filter_jobs_by_keyword(jobs, keyword)


async def scrape_nofluffjobs(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes NoFluffJobs."""
    logger.info(f"🇪🇺 [NoFluffJobs] Scraping keyword='{keyword}'...")
    url = f"https://nofluffjobs.com/jobs?criteria=keyword%3D{quote_plus(keyword)}"
    try:
        content = await fetch_page_content(url)
        jobs = parse_nofluffjobs(content, keyword)
        return jobs[:limit]
    except Exception as e:
        logger.error(f"❌ [NoFluffJobs] Error: {e}")
        return []


async def scrape_jobgether(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes Jobgether."""
    logger.info(f"🌍 [Jobgether] Scraping keyword='{keyword}'...")
    url = f"https://jobgether.com/offers?search={quote_plus(keyword)}"
    try:
        content = await fetch_page_content(url)
        matches = re.findall(r"\[([^\]]+)\]\(((?:https?://jobgether\.com)?/offer/[^\)]+)\)", content, re.I)
        jobs = []
        for text, href in matches:
            full_url = urljoin("https://jobgether.com", href)
            parts = [p.strip() for p in text.split(" at ") if p.strip()]
            title = parts[0] if parts else text
            company = parts[1] if len(parts) > 1 else ""
            job_dict = {
                "title": title,
                "company": company,
                "board_source": "Jobgether",
                "source_board": "Jobgether",
                "listing_url": full_url,
                "board_url": full_url,
                "location": "Remote",
            }
            if is_valid_job(job_dict) and not any(j["listing_url"] == full_url for j in jobs):
                jobs.append(job_dict)
        return filter_jobs_by_keyword(jobs, keyword)[:limit]
    except Exception as e:
        logger.error(f"❌ [Jobgether] Error: {e}")
        return []


async def scrape_euro_tech_jobs(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes EuroTechJobs."""
    logger.info(f"🇪🇺 [EuroTechJobs] Scraping keyword='{keyword}'...")
    url = f"https://www.eurotechjobs.com/job_search?keyword={quote_plus(keyword)}"
    try:
        content = await fetch_page_content(url)
        matches = re.findall(r"\[([^\]]+)\]\(((?:https?://www\.eurotechjobs\.com)?/job/[^\)]+)\)", content, re.I)
        jobs = []
        for text, href in matches:
            full_url = urljoin("https://www.eurotechjobs.com", href)
            parts = [p.strip() for p in text.split(" - ") if p.strip()]
            title = parts[0] if parts else text
            company = parts[1] if len(parts) > 1 else ""
            job_dict = {
                "title": title,
                "company": company,
                "board_source": "EuroTechJobs",
                "source_board": "EuroTechJobs",
                "listing_url": full_url,
                "board_url": full_url,
                "location": "Europe / Remote",
            }
            if is_valid_job(job_dict) and not any(j["listing_url"] == full_url for j in jobs):
                jobs.append(job_dict)
        return filter_jobs_by_keyword(jobs, keyword)[:limit]
    except Exception as e:
        logger.error(f"❌ [EuroTechJobs] Error: {e}")
        return []


async def scrape_work_in_startups(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes WorkInStartups (UK)."""
    logger.info(f"🇬🇧 [WorkInStartups] Scraping keyword='{keyword}'...")
    url = f"https://workinstartups.com/job-board/jobs/?q={quote_plus(keyword)}"
    try:
        content = await fetch_page_content(url)
        matches = re.findall(r"\[([^\]]+)\]\(((?:https?://workinstartups\.com)?/job-board/job/[^\)]+)\)", content, re.I)
        jobs = []
        for text, href in matches:
            full_url = urljoin("https://workinstartups.com", href)
            parts = [p.strip() for p in text.split(" at ") if p.strip()]
            title = parts[0] if parts else text
            company = parts[1] if len(parts) > 1 else ""
            job_dict = {
                "title": title,
                "company": company,
                "board_source": "WorkInStartups",
                "source_board": "WorkInStartups",
                "listing_url": full_url,
                "board_url": full_url,
                "location": "UK / Remote",
            }
            if is_valid_job(job_dict) and not any(j["listing_url"] == full_url for j in jobs):
                jobs.append(job_dict)
        return filter_jobs_by_keyword(jobs, keyword)[:limit]
    except Exception as e:
        logger.error(f"❌ [WorkInStartups] Error: {e}")
        return []


async def scrape_german_tech_jobs(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes GermanTechJobs."""
    logger.info(f"🇩🇪 [GermanTechJobs] Scraping keyword='{keyword}'...")
    url = f"https://germantechjobs.de/jobs/search?q={quote_plus(keyword)}"
    try:
        content = await fetch_page_content(url)
        matches = re.findall(r"\[([^\]]+)\]\(((?:https?://germantechjobs\.de)?/jobs/[^\)]+)\)", content, re.I)
        jobs = []
        for text, href in matches:
            full_url = urljoin("https://germantechjobs.de", href)
            parts = [p.strip() for p in text.split(" at ") if p.strip()]
            title = parts[0] if parts else text
            company = parts[1] if len(parts) > 1 else ""
            job_dict = {
                "title": title,
                "company": company,
                "board_source": "GermanTechJobs",
                "source_board": "GermanTechJobs",
                "listing_url": full_url,
                "board_url": full_url,
                "location": "Germany / Remote",
            }
            if is_valid_job(job_dict) and not any(j["listing_url"] == full_url for j in jobs):
                jobs.append(job_dict)
        return filter_jobs_by_keyword(jobs, keyword)[:limit]
    except Exception as e:
        logger.error(f"❌ [GermanTechJobs] Error: {e}")
        return []


# ==============================================================================
# 7. SwissDevJobs Scraper
# ==============================================================================

async def scrape_swiss_dev_jobs(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes SwissDevJobs (Switzerland Tech)."""
    logger.info(f"🇨🇭 [SwissDevJobs] Scraping keyword='{keyword}'...")
    url = f"https://swissdevjobs.ch/jobs/all?q={quote_plus(keyword)}" if keyword else "https://swissdevjobs.ch/jobs/all"
    try:
        content = await fetch_page_content(url)
        matches = re.findall(r"\[([^\]]+)\]\(((?:https?://swissdevjobs\.ch)?/jobs/[^\)]+)\)", content, re.I)
        jobs = []
        for text, href in matches:
            full_url = urljoin("https://swissdevjobs.ch", href)
            parts = [p.strip() for p in text.split(" at ") if p.strip()]
            title = parts[0] if parts else text
            company = parts[1] if len(parts) > 1 else "Swiss Tech Enterprise"
            job_dict = {
                "title": title,
                "company": company,
                "board_source": "SwissDevJobs",
                "source_board": "SwissDevJobs",
                "listing_url": full_url,
                "board_url": full_url,
                "location": "Zurich / Geneva / Remote",
            }
            if is_valid_job(job_dict) and not any(j["listing_url"] == full_url for j in jobs):
                jobs.append(job_dict)
        return filter_jobs_by_keyword(jobs, keyword)[:limit]
    except Exception as e:
        logger.error(f"❌ [SwissDevJobs] Error: {e}")
        return []


# ==============================================================================
# 8. UkDevJobs Scraper
# ==============================================================================

async def scrape_uk_dev_jobs(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes UkDevJobs (United Kingdom Tech)."""
    logger.info(f"🇬🇧 [UkDevJobs] Scraping keyword='{keyword}'...")
    url = f"https://ukdevjobs.co.uk/jobs/all?q={quote_plus(keyword)}" if keyword else "https://ukdevjobs.co.uk/jobs/all"
    try:
        content = await fetch_page_content(url)
        matches = re.findall(r"\[([^\]]+)\]\(((?:https?://ukdevjobs\.co\.uk)?/jobs/[^\)]+)\)", content, re.I)
        jobs = []
        for text, href in matches:
            full_url = urljoin("https://ukdevjobs.co.uk", href)
            parts = [p.strip() for p in text.split(" at ") if p.strip()]
            title = parts[0] if parts else text
            company = parts[1] if len(parts) > 1 else "UK Tech Co"
            job_dict = {
                "title": title,
                "company": company,
                "board_source": "UkDevJobs",
                "source_board": "UkDevJobs",
                "listing_url": full_url,
                "board_url": full_url,
                "location": "London / UK Remote",
            }
            if is_valid_job(job_dict) and not any(j["listing_url"] == full_url for j in jobs):
                jobs.append(job_dict)
        return filter_jobs_by_keyword(jobs, keyword)[:limit]
    except Exception as e:
        logger.error(f"❌ [UkDevJobs] Error: {e}")
        return []


# ==============================================================================
# 9. Landing.jobs Scraper
# ==============================================================================

async def scrape_landing_jobs(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes Landing.jobs (European Tech Careers)."""
    logger.info(f"🛬 [Landing.jobs] Scraping keyword='{keyword}'...")
    url = f"https://landing.jobs/jobs?q={quote_plus(keyword)}" if keyword else "https://landing.jobs/jobs"
    try:
        content = await fetch_page_content(url)
        matches = re.findall(r"\[([^\]]+)\]\(((?:https?://landing\.jobs)?/jobs/[^\)]+)\)", content, re.I)
        jobs = []
        for text, href in matches:
            full_url = urljoin("https://landing.jobs", href)
            parts = [p.strip() for p in text.split(" at ") if p.strip()]
            title = parts[0] if parts else text
            company = parts[1] if len(parts) > 1 else "European Tech Employer"
            job_dict = {
                "title": title,
                "company": company,
                "board_source": "Landing.jobs",
                "source_board": "Landing.jobs",
                "listing_url": full_url,
                "board_url": full_url,
                "location": "Lisbon / Berlin / Remote EU",
            }
            if is_valid_job(job_dict) and not any(j["listing_url"] == full_url for j in jobs):
                jobs.append(job_dict)
        return filter_jobs_by_keyword(jobs, keyword)[:limit]
    except Exception as e:
        logger.error(f"❌ [Landing.jobs] Error: {e}")
        return []


# ==============================================================================
# 10. TokyoDev Scraper
# ==============================================================================

async def scrape_tokyo_dev(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes TokyoDev (International Tech in Japan & Remote APAC)."""
    logger.info(f"🗾 [TokyoDev] Scraping keyword='{keyword}'...")
    url = "https://www.tokyodev.com/jobs"
    try:
        content = await fetch_page_content(url)
        matches = re.findall(r"\[([^\]]+)\]\(((?:https?://www\.tokyodev\.com)?/jobs/[^\)]+)\)", content, re.I)
        jobs = []
        for text, href in matches:
            full_url = urljoin("https://www.tokyodev.com", href)
            parts = [p.strip() for p in text.split(" at ") if p.strip()]
            title = parts[0] if parts else text
            company = parts[1] if len(parts) > 1 else "Japan Tech Enterprise"
            job_dict = {
                "title": title,
                "company": company,
                "board_source": "TokyoDev",
                "source_board": "TokyoDev",
                "listing_url": full_url,
                "board_url": full_url,
                "location": "Tokyo / Remote Japan",
            }
            if is_valid_job(job_dict) and not any(j["listing_url"] == full_url for j in jobs):
                jobs.append(job_dict)
        return filter_jobs_by_keyword(jobs, keyword)[:limit]
    except Exception as e:
        logger.error(f"❌ [TokyoDev] Error: {e}")
        return []
