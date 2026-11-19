"""
Programming Languages & Frameworks Job Board Scrapers:
Python.org, GolangProjects, RustJobs, ReactCareers, VueJobs, RubyOnRemote.
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

logger = get_logger("SpecializedTechScrapers")


def parse_python_org_jobs(raw_content: str, keyword: str = "") -> List[Dict[str, Any]]:
    """Extracts job postings from Python.org official job board."""
    jobs: List[Dict[str, Any]] = []
    base_url = "https://www.python.org"

    # Python.org format: [Job Title](https://www.python.org/jobs/1234/) followed by Company / Location
    matches = re.findall(
        r"\[([^\]]+)\]\(((?:https?://www\.python\.org)?/jobs/\d+/[^\)]*)\)",
        raw_content,
        re.I,
    )
    for text, href in matches:
        full_url = urljoin(base_url, href)
        title = text.replace("\ufffd", "-").strip()
        company = ""

        # Check for 'Title at Company' or 'Title - Company'
        if " at " in title:
            parts = title.split(" at ")
            title, company = parts[0].strip(), parts[1].strip()
        elif " - " in title:
            parts = title.split(" - ")
            title, company = parts[0].strip(), parts[1].strip()

        job_dict = {
            "title": title,
            "company": company or "Python Organization",
            "board_source": "Python.org",
            "source_board": "Python.org",
            "listing_url": full_url,
            "board_url": full_url,
            "location": "Remote / Worldwide",
        }
        if is_valid_job(job_dict) and not any(j["listing_url"] == full_url for j in jobs):
            jobs.append(job_dict)

    return filter_jobs_by_keyword(jobs, keyword)


async def scrape_python_org(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes Python.org official job board."""
    logger.info(f"🐍 [Python.org] Scraping keyword='{keyword}'...")
    url = "https://www.python.org/jobs/"
    try:
        content = await fetch_page_content(url)
        jobs = parse_python_org_jobs(content, keyword)
        return jobs[:limit]
    except Exception as e:
        logger.error(f"❌ [Python.org] Error: {e}")
        return []


def parse_golang_projects(raw_content: str, keyword: str = "") -> List[Dict[str, Any]]:
    """Extracts job postings from GolangProjects."""
    jobs: List[Dict[str, Any]] = []
    base_url = "https://golangprojects.com"

    matches = re.findall(
        r"\[([^\]]+)\]\(((?:https?://golangprojects\.com)?/golang-jobs/[^\)]+)\)",
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
            "board_source": "GolangProjects",
            "source_board": "GolangProjects",
            "listing_url": full_url,
            "board_url": full_url,
            "location": "Remote / Golang",
        }
        if is_valid_job(job_dict) and not any(j["listing_url"] == full_url for j in jobs):
            jobs.append(job_dict)

    return filter_jobs_by_keyword(jobs, keyword)


async def scrape_golang_projects(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes GolangProjects."""
    logger.info(f"🐹 [GolangProjects] Scraping keyword='{keyword}'...")
    url = f"https://golangprojects.com/golang-jobs/{quote_plus(keyword)}"
    try:
        content = await fetch_page_content(url)
        if "[ANTI_BOT_BLOCKED]" in content or not content:
            content = await fetch_page_content("https://golangprojects.com/")
        jobs = parse_golang_projects(content, keyword)
        return jobs[:limit]
    except Exception as e:
        logger.error(f"❌ [GolangProjects] Error: {e}")
        return []


def parse_rust_jobs(raw_content: str, keyword: str = "") -> List[Dict[str, Any]]:
    """Extracts job postings from RustJobs.dev."""
    jobs: List[Dict[str, Any]] = []
    base_url = "https://rustjobs.dev"

    matches = re.findall(
        r"\[([^\]]+)\]\(((?:https?://rustjobs\.dev)?/jobs?/[^\)]+)\)",
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
            "board_source": "RustJobs",
            "source_board": "RustJobs",
            "listing_url": full_url,
            "board_url": full_url,
            "location": "Remote / Rust",
        }
        if is_valid_job(job_dict) and not any(j["listing_url"] == full_url for j in jobs):
            jobs.append(job_dict)

    return filter_jobs_by_keyword(jobs, keyword)


async def scrape_rust_jobs(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes RustJobs.dev."""
    logger.info(f"🦀 [RustJobs] Scraping keyword='{keyword}'...")
    url = "https://rustjobs.dev/"
    try:
        content = await fetch_page_content(url)
        jobs = parse_rust_jobs(content, keyword)
        return jobs[:limit]
    except Exception as e:
        logger.error(f"❌ [RustJobs] Error: {e}")
        return []


def parse_rubyonremote(raw_content: str, keyword: str = "") -> List[Dict[str, Any]]:
    """Extracts job postings from RubyOnRemote."""
    jobs: List[Dict[str, Any]] = []
    base_url = "https://rubyonremote.com"

    matches = re.findall(
        r"\[([^\]]+)\]\(((?:https?://rubyonremote\.com)?/jobs/[^\)]+)\)",
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
            "board_source": "RubyOnRemote",
            "source_board": "RubyOnRemote",
            "listing_url": full_url,
            "board_url": full_url,
            "location": "Remote / Ruby",
        }
        if is_valid_job(job_dict) and not any(j["listing_url"] == full_url for j in jobs):
            jobs.append(job_dict)

    return filter_jobs_by_keyword(jobs, keyword)


async def scrape_rubyonremote(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes RubyOnRemote."""
    logger.info(f"💎 [RubyOnRemote] Scraping keyword='{keyword}'...")
    url = f"https://rubyonremote.com/remote-jobs?search={quote_plus(keyword)}"
    try:
        content = await fetch_page_content(url)
        jobs = parse_rubyonremote(content, keyword)
        return jobs[:limit]
    except Exception as e:
        logger.error(f"❌ [RubyOnRemote] Error: {e}")
        return []


async def scrape_react_careers(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes ReactJobs / ReactCareers."""
    logger.info(f"⚛️ [ReactCareers] Scraping keyword='{keyword}'...")
    url = "https://reactcareers.com/"
    try:
        content = await fetch_page_content(url)
        matches = re.findall(r"\[([^\]]+)\]\(((?:https?://reactcareers\.com)?/job/[^\)]+)\)", content, re.I)
        jobs = []
        for text, href in matches:
            full_url = urljoin("https://reactcareers.com", href)
            parts = [p.strip() for p in text.split(" at ") if p.strip()]
            title = parts[0] if parts else text
            company = parts[1] if len(parts) > 1 else ""
            job_dict = {
                "title": title,
                "company": company,
                "board_source": "ReactCareers",
                "source_board": "ReactCareers",
                "listing_url": full_url,
                "board_url": full_url,
                "location": "Remote",
            }
            if is_valid_job(job_dict) and not any(j["listing_url"] == full_url for j in jobs):
                jobs.append(job_dict)
        return filter_jobs_by_keyword(jobs, keyword)[:limit]
    except Exception as e:
        logger.error(f"❌ [ReactCareers] Error: {e}")
        return []


async def scrape_vue_jobs(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes VueJobs."""
    logger.info(f"💚 [VueJobs] Scraping keyword='{keyword}'...")
    url = "https://vuejobs.com/"
    try:
        content = await fetch_page_content(url)
        matches = re.findall(r"\[([^\]]+)\]\(((?:https?://vuejobs\.com)?/jobs/[^\)]+)\)", content, re.I)
        jobs = []
        for text, href in matches:
            full_url = urljoin("https://vuejobs.com", href)
            parts = [p.strip() for p in text.split(" at ") if p.strip()]
            title = parts[0] if parts else text
            company = parts[1] if len(parts) > 1 else ""
            job_dict = {
                "title": title,
                "company": company,
                "board_source": "VueJobs",
                "source_board": "VueJobs",
                "listing_url": full_url,
                "board_url": full_url,
                "location": "Remote",
            }
            if is_valid_job(job_dict) and not any(j["listing_url"] == full_url for j in jobs):
                jobs.append(job_dict)
        return filter_jobs_by_keyword(jobs, keyword)[:limit]
    except Exception as e:
        logger.error(f"❌ [VueJobs] Error: {e}")
        return []


# ==============================================================================
# 7. ElixirJobs Scraper
# ==============================================================================

async def scrape_elixir_jobs(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes ElixirJobs."""
    logger.info(f"💧 [ElixirJobs] Scraping keyword='{keyword}'...")
    url = "https://elixirjobs.net/"
    try:
        content = await fetch_page_content(url)
        matches = re.findall(r"\[([^\]]+)\]\(((?:https?://elixirjobs\.net)?/jobs/[^\)]+)\)", content, re.I)
        jobs = []
        for text, href in matches:
            full_url = urljoin("https://elixirjobs.net", href)
            parts = [p.strip() for p in text.split(" at ") if p.strip()]
            title = parts[0] if parts else text
            company = parts[1] if len(parts) > 1 else "Elixir Studio"
            job_dict = {
                "title": title,
                "company": company,
                "board_source": "ElixirJobs",
                "source_board": "ElixirJobs",
                "listing_url": full_url,
                "board_url": full_url,
                "location": "Remote / Distributed",
            }
            if is_valid_job(job_dict) and not any(j["listing_url"] == full_url for j in jobs):
                jobs.append(job_dict)
        return filter_jobs_by_keyword(jobs, keyword)[:limit]
    except Exception as e:
        logger.error(f"❌ [ElixirJobs] Error: {e}")
        return []


# ==============================================================================
# 8. ScalaJobs Scraper
# ==============================================================================

async def scrape_scala_jobs(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes ScalaJobs."""
    logger.info(f"🔴 [ScalaJobs] Scraping keyword='{keyword}'...")
    url = "https://scalajobs.com/"
    try:
        content = await fetch_page_content(url)
        matches = re.findall(r"\[([^\]]+)\]\(([^\)]+)\)", content, re.I)
        jobs = []
        for text, href in matches:
            if "/job/" in href or "/jobs/" in href:
                full_url = urljoin("https://scalajobs.com", href)
                parts = [p.strip() for p in text.split(" at ") if p.strip()]
                title = parts[0] if parts else text
                company = parts[1] if len(parts) > 1 else "Scala Systems"
                job_dict = {
                    "title": title,
                    "company": company,
                    "board_source": "ScalaJobs",
                    "source_board": "ScalaJobs",
                    "listing_url": full_url,
                    "board_url": full_url,
                    "location": "Remote",
                }
                if is_valid_job(job_dict) and not any(j["listing_url"] == full_url for j in jobs):
                    jobs.append(job_dict)
        return filter_jobs_by_keyword(jobs, keyword)[:limit]
    except Exception as e:
        logger.error(f"❌ [ScalaJobs] Error: {e}")
        return []


# ==============================================================================
# 9. AndroidJobs Scraper
# ==============================================================================

async def scrape_android_jobs(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes AndroidJobs.io (Kotlin / Android Mobile)."""
    logger.info(f"🤖 [AndroidJobs] Scraping keyword='{keyword}'...")
    url = "https://androidjobs.io/"
    try:
        content = await fetch_page_content(url)
        matches = re.findall(r"\[([^\]]+)\]\(([^\)]+)\)", content, re.I)
        jobs = []
        for text, href in matches:
            if "/job/" in href:
                full_url = urljoin("https://androidjobs.io", href)
                parts = [p.strip() for p in text.split(" at ") if p.strip()]
                title = parts[0] if parts else text
                company = parts[1] if len(parts) > 1 else "Mobile Tech"
                job_dict = {
                    "title": title,
                    "company": company,
                    "board_source": "AndroidJobs",
                    "source_board": "AndroidJobs",
                    "listing_url": full_url,
                    "board_url": full_url,
                    "location": "Remote",
                }
                if is_valid_job(job_dict) and not any(j["listing_url"] == full_url for j in jobs):
                    jobs.append(job_dict)
        return filter_jobs_by_keyword(jobs, keyword)[:limit]
    except Exception as e:
        logger.error(f"❌ [AndroidJobs] Error: {e}")
        return []


# ==============================================================================
# 10. iOSDevJobs Scraper
# ==============================================================================

async def scrape_ios_dev_jobs(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes iOSDevJobs (Swift / SwiftUI / Apple)."""
    logger.info(f"🍏 [iOSDevJobs] Scraping keyword='{keyword}'...")
    url = "https://iosdevjobs.com/"
    try:
        content = await fetch_page_content(url)
        matches = re.findall(r"\[([^\]]+)\]\(([^\)]+)\)", content, re.I)
        jobs = []
        for text, href in matches:
            if "/job/" in href:
                full_url = urljoin("https://iosdevjobs.com", href)
                parts = [p.strip() for p in text.split(" at ") if p.strip()]
                title = parts[0] if parts else text
                company = parts[1] if len(parts) > 1 else "iOS Studio"
                job_dict = {
                    "title": title,
                    "company": company,
                    "board_source": "iOSDevJobs",
                    "source_board": "iOSDevJobs",
                    "listing_url": full_url,
                    "board_url": full_url,
                    "location": "Remote",
                }
                if is_valid_job(job_dict) and not any(j["listing_url"] == full_url for j in jobs):
                    jobs.append(job_dict)
        return filter_jobs_by_keyword(jobs, keyword)[:limit]
    except Exception as e:
        logger.error(f"❌ [iOSDevJobs] Error: {e}")
        return []


# ==============================================================================
# 11. CPlusPlusJobs Scraper
# ==============================================================================

async def scrape_cplusplus_jobs(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes CPlusPlusJobs (C++ / High Performance / Low Latency)."""
    logger.info(f"⚡ [CPlusPlusJobs] Scraping keyword='{keyword}'...")
    url = "https://cplusplusjobs.com/"
    try:
        content = await fetch_page_content(url)
        matches = re.findall(r"\[([^\]]+)\]\(([^\)]+)\)", content, re.I)
        jobs = []
        for text, href in matches:
            if "/job/" in href:
                full_url = urljoin("https://cplusplusjobs.com", href)
                parts = [p.strip() for p in text.split(" at ") if p.strip()]
                title = parts[0] if parts else text
                company = parts[1] if len(parts) > 1 else "Quant / C++ Systems"
                job_dict = {
                    "title": title,
                    "company": company,
                    "board_source": "CPlusPlusJobs",
                    "source_board": "CPlusPlusJobs",
                    "listing_url": full_url,
                    "board_url": full_url,
                    "location": "Remote / Chicago",
                }
                if is_valid_job(job_dict) and not any(j["listing_url"] == full_url for j in jobs):
                    jobs.append(job_dict)
        return filter_jobs_by_keyword(jobs, keyword)[:limit]
    except Exception as e:
        logger.error(f"❌ [CPlusPlusJobs] Error: {e}")
        return []


# ==============================================================================
# 12. GraphQLJobs Scraper
# ==============================================================================

async def scrape_graphql_jobs(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes GraphQLJobs (GraphQL / Apollo / APIs)."""
    logger.info(f"🕸️ [GraphQLJobs] Scraping keyword='{keyword}'...")
    url = "https://graphql.jobs/"
    try:
        content = await fetch_page_content(url)
        matches = re.findall(r"\[([^\]]+)\]\(([^\)]+)\)", content, re.I)
        jobs = []
        for text, href in matches:
            if "/job/" in href or "/jobs/" in href:
                full_url = urljoin("https://graphql.jobs", href)
                parts = [p.strip() for p in text.split(" at ") if p.strip()]
                title = parts[0] if parts else text
                company = parts[1] if len(parts) > 1 else "GraphQL Partner"
                job_dict = {
                    "title": title,
                    "company": company,
                    "board_source": "GraphQLJobs",
                    "source_board": "GraphQLJobs",
                    "listing_url": full_url,
                    "board_url": full_url,
                    "location": "Remote",
                }
                if is_valid_job(job_dict) and not any(j["listing_url"] == full_url for j in jobs):
                    jobs.append(job_dict)
        return filter_jobs_by_keyword(jobs, keyword)[:limit]
    except Exception as e:
        logger.error(f"❌ [GraphQLJobs] Error: {e}")
        return []


# ==============================================================================
# 13. PyJobs Scraper (https://www.pyjobs.com)
# ==============================================================================

def parse_pyjobs_listings(raw_content: str, keyword: str = "") -> List[Dict[str, Any]]:
    """Extracts Python, Backend, AI/ML, and Data Engineering roles from PyJobs."""
    jobs: List[Dict[str, Any]] = []
    try:
        soup = BeautifulSoup(raw_content, "html.parser")
        for a in soup.select('a[href*="/job/"]'):
            href = a.get("href", "")
            if not href or href == "/job/create" or "create" in href:
                continue
            full_url = href if href.startswith("http") else urljoin("https://www.pyjobs.com", href)
            text = a.get_text(separator=" ", strip=True)
            if not text or len(text) < 4:
                continue
            parts = text.split(" at ")
            title = parts[0].strip()
            company = parts[1].strip() if len(parts) > 1 else "PyJobs Partner"

            job_dict = {
                "title": title,
                "company": company,
                "board_source": "PyJobs",
                "source_board": "PyJobs",
                "listing_url": full_url,
                "board_url": full_url,
                "location": "100% Remote / Worldwide",
            }
            if is_valid_job(job_dict) and not any(existing["listing_url"] == full_url for existing in jobs):
                jobs.append(job_dict)
    except Exception as e:
        logger.debug(f"PyJobs parsing error: {e}")

    return filter_jobs_by_keyword(jobs, keyword)


async def scrape_pyjobs(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes 100% pure remote Python, Backend & AI roles from PyJobs."""
    logger.info(f"🐍 [PyJobs] Scraping Python & AI jobs for keyword='{keyword}'...")
    url = "https://www.pyjobs.com/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }
    try:
        async with httpx.AsyncClient(headers=headers, timeout=12.0, follow_redirects=True) as client:
            resp = await client.get(url)
            if resp.status_code == 200 and resp.text:
                jobs = parse_pyjobs_listings(resp.text, keyword)
                logger.info(f"✅ [PyJobs] Extracted {len(jobs)} jobs.")
                return jobs[:limit]
        return []
    except Exception as e:
        logger.error(f"❌ [PyJobs] Failed: {e}")
        return []


# ==============================================================================
# 14. RemotePython Scraper (https://www.remotepython.com)
# ==============================================================================

def parse_remotepython_listings(raw_content: str, keyword: str = "") -> List[Dict[str, Any]]:
    """Extracts 100% pure remote Python, Django, FastAPI roles from RemotePython."""
    jobs: List[Dict[str, Any]] = []
    try:
        soup = BeautifulSoup(raw_content, "html.parser")
        for it in soup.select("div.item"):
            h3 = it.select_one("h3")
            if not h3:
                continue
            a = h3.select_one("a")
            if not a:
                continue
            title = a.text.strip()
            href = a.get("href", "")
            if not title or not href:
                continue
            full_url = href if href.startswith("http") else urljoin("https://www.remotepython.com", href)
            meta = it.select_one(".color-white-muted") or it.select_one(".meta")
            company = meta.text.strip() if meta else "RemotePython Hiring Partner"

            job_dict = {
                "title": title,
                "company": company,
                "board_source": "RemotePython",
                "source_board": "RemotePython",
                "listing_url": full_url,
                "board_url": full_url,
                "location": "100% Remote / Worldwide",
            }
            if is_valid_job(job_dict) and not any(existing["listing_url"] == full_url for existing in jobs):
                jobs.append(job_dict)
    except Exception as e:
        logger.debug(f"RemotePython parsing error: {e}")

    return filter_jobs_by_keyword(jobs, keyword)


async def scrape_remotepython(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes 100% remote Python/FastAPI/Django jobs from RemotePython."""
    logger.info(f"🐍 [RemotePython] Scraping keyword='{keyword}'...")
    url = f"https://www.remotepython.com/jobs/?q={quote_plus(keyword)}" if keyword else "https://www.remotepython.com/jobs/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }
    try:
        async with httpx.AsyncClient(headers=headers, timeout=12.0, follow_redirects=True) as client:
            resp = await client.get(url)
            if resp.status_code == 200 and resp.text:
                jobs = parse_remotepython_listings(resp.text, keyword)
                logger.info(f"✅ [RemotePython] Extracted {len(jobs)} jobs.")
                return jobs[:limit]
        return []
    except Exception as e:
        logger.error(f"❌ [RemotePython] Failed: {e}")
        return []


# ==============================================================================
# 15. DjangoProject Community Jobs Scraper (https://www.djangoproject.com)
# ==============================================================================

def parse_djangoproject_feed(raw_xml: str, keyword: str = "") -> List[Dict[str, Any]]:
    """Extracts authentic Django/Python/FastAPI roles from the official Django Project community feed."""
    jobs: List[Dict[str, Any]] = []
    try:
        root = ET.fromstring(raw_xml)
        for it in root.findall(".//item"):
            title_elem = it.find("title")
            link_elem = it.find("link")
            if title_elem is None or link_elem is None:
                continue

            raw_title = (title_elem.text or "").strip()
            link = (link_elem.text or "").strip()
            if not raw_title or not link:
                continue

            company = "Django Community Partner"
            title = raw_title
            if " at " in raw_title:
                parts = raw_title.split(" at ", 1)
                title, company = parts[0].strip(), parts[1].strip()
            elif " - " in raw_title:
                parts = raw_title.split(" - ", 1)
                title, company = parts[0].strip(), parts[1].strip()

            job_dict = {
                "title": title,
                "company": company,
                "board_source": "DjangoProject",
                "source_board": "DjangoProject",
                "listing_url": link,
                "board_url": link,
                "location": "100% Remote / Worldwide",
            }
            if is_valid_job(job_dict) and not any(existing["listing_url"] == link for existing in jobs):
                jobs.append(job_dict)
    except Exception as e:
        logger.debug(f"DjangoProject parsing error: {e}")

    return filter_jobs_by_keyword(jobs, keyword)


async def scrape_djangoproject(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes official Django community jobs feed."""
    logger.info(f"🎸 [DjangoProject] Scraping official Django jobs for keyword='{keyword}'...")
    url = "https://www.djangoproject.com/rss/community/jobs/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }
    try:
        async with httpx.AsyncClient(headers=headers, timeout=12.0, follow_redirects=True) as client:
            resp = await client.get(url)
            if resp.status_code == 200 and resp.text:
                jobs = parse_djangoproject_feed(resp.text, keyword)
                logger.info(f"✅ [DjangoProject] Extracted {len(jobs)} jobs.")
                return jobs[:limit]
        return []
    except Exception as e:
        logger.error(f"❌ [DjangoProject] Failed: {e}")
        return []


# ==============================================================================
# 16. PythonJobsGithub Scraper (https://pythonjobs.github.io)
# ==============================================================================

def parse_pythonjobsgithub_listings(raw_content: str, keyword: str = "") -> List[Dict[str, Any]]:
    """Extracts open-source curated Python & Backend positions."""
    jobs: List[Dict[str, Any]] = []
    try:
        soup = BeautifulSoup(raw_content, "html.parser")
        for div in soup.select("div.job"):
            a_links = div.find_all("a", href=True)
            if not a_links:
                continue
            h = div.select_one("h1, h2, h3")
            raw_title = h.text.strip() if h else a_links[0].text.strip()
            link = a_links[0]["href"]
            full_url = link if link.startswith("http") else urljoin("https://pythonjobs.github.io", link)

            title = raw_title if raw_title and raw_title.lower() != "read more" else "Python Backend Engineer"
            company = "Python Open Source Ecosystem"

            # Check if company can be extracted from link slug: /jobs/bmat-senior-backend-engineer.html
            slug = link.replace("/jobs/", "").replace(".html", "")
            if "-" in slug:
                parts = slug.split("-")
                company = parts[0].upper()
                if raw_title.lower() == "read more":
                    title = " ".join(parts[1:]).title()

            job_dict = {
                "title": title,
                "company": company,
                "board_source": "PythonJobsGithub",
                "source_board": "PythonJobsGithub",
                "listing_url": full_url,
                "board_url": full_url,
                "location": "100% Remote",
            }
            if is_valid_job(job_dict) and not any(existing["listing_url"] == full_url for existing in jobs):
                jobs.append(job_dict)
    except Exception as e:
        logger.debug(f"PythonJobsGithub parsing error: {e}")

    return filter_jobs_by_keyword(jobs, keyword)


async def scrape_pythonjobsgithub(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes curated open-source Python engineering jobs from PythonJobsGithub."""
    logger.info(f"🐍 [PythonJobsGithub] Scraping keyword='{keyword}'...")
    url = "https://pythonjobs.github.io/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }
    try:
        async with httpx.AsyncClient(headers=headers, timeout=12.0, follow_redirects=True) as client:
            resp = await client.get(url)
            if resp.status_code == 200 and resp.text:
                jobs = parse_pythonjobsgithub_listings(resp.text, keyword)
                logger.info(f"✅ [PythonJobsGithub] Extracted {len(jobs)} jobs.")
                return jobs[:limit]
        return []
    except Exception as e:
        logger.error(f"❌ [PythonJobsGithub] Failed: {e}")
        return []

