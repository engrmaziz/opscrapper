"""
DevOps, Cloud, Systems Engineering & Cybersecurity Job Board Scrapers:
CyberSecJobs, InfoSecJobs, KubernetesJobs, CloudJobs, DevOpsJobs, LinuxJobs, SREJobs, ClearedJobs.
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

logger = get_logger("DevOpsCloudScrapers")


def parse_generic_devops_board(raw_content: str, board_name: str, base_url: str, keyword: str = "") -> List[Dict[str, Any]]:
    """Generic high-signal parser for DevOps, Cloud and Security job boards."""
    jobs: List[Dict[str, Any]] = []

    if "<html" in raw_content.lower() or "<div" in raw_content.lower():
        try:
            soup = BeautifulSoup(raw_content, "html.parser")
            for item in soup.select(".job, .job-listing, .job-item, article, li"):
                link = item.find("a", href=True)
                if not link:
                    continue
                href = link.get("href", "")
                if not any(k in href.lower() for k in ["/job/", "/jobs/", "/posting/", "/view/"]):
                    continue
                title = link.get_text(strip=True)
                comp_elem = item.find(class_=re.compile(r"company|employer|client", re.I))
                company = comp_elem.get_text(strip=True) if comp_elem else ""
                loc_elem = item.find(class_=re.compile(r"location|city", re.I))
                location = loc_elem.get_text(strip=True) if loc_elem else "Remote"
                full_url = urljoin(base_url, href)

                if title and len(title) > 2:
                    job_dict = {
                        "title": title.strip(),
                        "company": company.strip() or f"{board_name} Partner",
                        "board_source": board_name,
                        "source_board": board_name,
                        "listing_url": full_url,
                        "board_url": full_url,
                        "location": location,
                    }
                    if is_valid_job(job_dict) and not any(j["listing_url"] == full_url for j in jobs):
                        jobs.append(job_dict)
        except Exception:
            pass

    # Markdown regex fallback
    if not jobs:
        matches = re.findall(r"\[([^\]]+)\]\(([^\)]+)\)", raw_content)
        for text, href in matches:
            if any(k in href.lower() for k in ["/job/", "/jobs/", "/posting/"]):
                if not any(bad in href.lower() for bad in ["login", "register", "post", "#"]):
                    full_url = urljoin(base_url, href)
                    parts = [p.strip() for p in text.split(" at ") if p.strip()]
                    title = parts[0] if parts else text
                    company = parts[1] if len(parts) > 1 else ""
                    if " - " in title and not company:
                        h_parts = title.split(" - ")
                        title = h_parts[0].strip()
                        company = h_parts[1].strip()

                    job_dict = {
                        "title": title.strip(),
                        "company": company.strip() or f"{board_name} Partner",
                        "board_source": board_name,
                        "source_board": board_name,
                        "listing_url": full_url,
                        "board_url": full_url,
                        "location": "Remote",
                    }
                    if is_valid_job(job_dict) and not any(j["listing_url"] == full_url for j in jobs):
                        jobs.append(job_dict)

    return filter_jobs_by_keyword(jobs, keyword)


# ==============================================================================
# 1. CyberSecJobs Scraper
# ==============================================================================

async def scrape_cybersec_jobs(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes CyberSecJobs."""
    logger.info(f"🔒 [CyberSecJobs] Scraping keyword='{keyword}'...")
    url = f"https://cybersecjobs.com/jobs?q={quote_plus(keyword)}" if keyword else "https://cybersecjobs.com/jobs"
    try:
        content = await fetch_page_content(url)
        jobs = parse_generic_devops_board(content, "CyberSecJobs", "https://cybersecjobs.com", keyword)
        return jobs[:limit]
    except Exception as e:
        logger.error(f"❌ [CyberSecJobs] Error: {e}")
        return []


# ==============================================================================
# 2. InfoSecJobs Scraper
# ==============================================================================

async def scrape_infosec_jobs(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes InfoSec-Jobs.com."""
    logger.info(f"🛡️ [InfoSecJobs] Scraping keyword='{keyword}'...")
    url = f"https://infosec-jobs.com/search/?q={quote_plus(keyword)}" if keyword else "https://infosec-jobs.com/"
    try:
        content = await fetch_page_content(url)
        jobs = parse_generic_devops_board(content, "InfoSecJobs", "https://infosec-jobs.com", keyword)
        return jobs[:limit]
    except Exception as e:
        logger.error(f"❌ [InfoSecJobs] Error: {e}")
        return []


# ==============================================================================
# 3. KubernetesJobs Scraper
# ==============================================================================

async def scrape_kubernetes_jobs(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes KubernetesJobs.com."""
    logger.info(f"☸️ [KubernetesJobs] Scraping keyword='{keyword}'...")
    url = "https://kubernetesjobs.com/"
    try:
        content = await fetch_page_content(url)
        jobs = parse_generic_devops_board(content, "KubernetesJobs", "https://kubernetesjobs.com", keyword)
        return jobs[:limit]
    except Exception as e:
        logger.error(f"❌ [KubernetesJobs] Error: {e}")
        return []


# ==============================================================================
# 4. CloudJobs Scraper
# ==============================================================================

async def scrape_cloud_jobs(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes CloudJobs.io (AWS / GCP / Azure)."""
    logger.info(f"☁️ [CloudJobs] Scraping keyword='{keyword}'...")
    url = "https://cloudjobs.io/"
    try:
        content = await fetch_page_content(url)
        jobs = parse_generic_devops_board(content, "CloudJobs", "https://cloudjobs.io", keyword)
        return jobs[:limit]
    except Exception as e:
        logger.error(f"❌ [CloudJobs] Error: {e}")
        return []


# ==============================================================================
# 5. DevOpsJobs Scraper
# ==============================================================================

async def scrape_devops_jobs(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes DevOpsJobs.io."""
    logger.info(f"⚙️ [DevOpsJobs] Scraping keyword='{keyword}'...")
    url = "https://devopsjobs.io/"
    try:
        content = await fetch_page_content(url)
        jobs = parse_generic_devops_board(content, "DevOpsJobs", "https://devopsjobs.io", keyword)
        return jobs[:limit]
    except Exception as e:
        logger.error(f"❌ [DevOpsJobs] Error: {e}")
        return []


# ==============================================================================
# 6. LinuxJobs Scraper
# ==============================================================================

async def scrape_linux_jobs(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes LinuxJobs.io."""
    logger.info(f"🐧 [LinuxJobs] Scraping keyword='{keyword}'...")
    url = "https://linuxjobs.io/"
    try:
        content = await fetch_page_content(url)
        jobs = parse_generic_devops_board(content, "LinuxJobs", "https://linuxjobs.io", keyword)
        return jobs[:limit]
    except Exception as e:
        logger.error(f"❌ [LinuxJobs] Error: {e}")
        return []


# ==============================================================================
# 7. SREJobs Scraper
# ==============================================================================

async def scrape_sre_jobs(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes SREJobs.io (Site Reliability Engineering)."""
    logger.info(f"🚨 [SREJobs] Scraping keyword='{keyword}'...")
    url = "https://srejobs.io/"
    try:
        content = await fetch_page_content(url)
        jobs = parse_generic_devops_board(content, "SREJobs", "https://srejobs.io", keyword)
        return jobs[:limit]
    except Exception as e:
        logger.error(f"❌ [SREJobs] Error: {e}")
        return []


# ==============================================================================
# 8. ClearedJobs Scraper
# ==============================================================================

async def scrape_cleared_jobs(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes ClearedJobs.net (Security Cleared Tech & Engineering)."""
    logger.info(f"🎖️ [ClearedJobs] Scraping keyword='{keyword}'...")
    url = "https://clearedjobs.net/jobs"
    try:
        content = await fetch_page_content(url)
        jobs = parse_generic_devops_board(content, "ClearedJobs", "https://clearedjobs.net", keyword)
        return jobs[:limit]
    except Exception as e:
        logger.error(f"❌ [ClearedJobs] Error: {e}")
        return []
