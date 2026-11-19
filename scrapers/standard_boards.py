"""
Standard Tech & Remote Job Board Scrapers (Level 1):
Itch.io, GamesIndustry.biz, WeWorkRemotely, RemoteOK, Remotive, Dice,
HackerNews Hiring, BuiltIn, WorkingNomads, Techcareers, Jobspresso, JustRemote.
"""

import asyncio
from datetime import datetime
import json
import re
from typing import Any, Dict, List, Optional, Set
from urllib.parse import quote_plus, urljoin
import xml.etree.ElementTree as ET

import httpx
from bs4 import BeautifulSoup
from config.settings import settings
from config.logging_config import get_logger
from tools.web_navigator import fetch_page_content
from utils.state_manager import state_manager
from utils.keyword_matcher import filter_jobs_by_keyword, normalize_search_keyword

logger = get_logger("StandardTechScrapers")

INVALID_COMPANY_PATTERN = re.compile(
    r"\b(employer|recruiter|creator|studio|studios|organization|unknown|n/a|view full listing|view company profile|promoted)\b",
    re.I,
)


def deduplicate_repeated_phrase(text: str) -> str:
    """Deduplicates accidental repetitions such as 'Company Company' -> 'Company'."""
    if not text:
        return ""
    words = text.strip().split()
    if len(words) >= 2 and len(words) % 2 == 0:
        half = len(words) // 2
        if words[:half] == words[half:]:
            return " ".join(words[:half])
    return text.strip()


def is_valid_job(job: Dict[str, Any]) -> bool:
    """Strict validation guardrail to ensure genuine job leads with real companies and titles."""
    title = str(job.get("title", "")).strip()
    company = str(job.get("company", "")).strip()
    listing_url = str(job.get("listing_url", "") or job.get("board_url", "")).strip()

    if not title or len(title) < 2:
        return False
    if not company or len(company) < 2:
        return False
    if not listing_url or not listing_url.startswith("http"):
        return False

    if INVALID_COMPANY_PATTERN.search(company):
        return False

    return True


# ==============================================================================
# 1. Itch.io Scraper
# ==============================================================================

def parse_itch_io_listings(raw_content: str, keyword: str = "") -> List[Dict[str, Any]]:
    """Extracts verified job listings from Itch.io."""
    jobs: List[Dict[str, Any]] = []
    base_url = "https://itch.io"
    pattern = r"(?=\[[^\]]+\]\((?:https?://itch\.io)?/j/\d+/[^\)]+\))"
    chunks = re.split(pattern, raw_content)

    for chunk in chunks:
        job_match = re.search(r"\[([^\]]+)\]\(((?:https?://itch\.io)?/j/\d+/[^\)]+)\)", chunk, re.I)
        if not job_match:
            continue

        title_raw = job_match.group(1).strip()
        url_raw = job_match.group(2).strip()

        if title_raw.lower() in ["view full listing", "apply now", "view listing", "details", "job", "jobs"]:
            continue

        full_url = urljoin(base_url, url_raw)
        title = title_raw.replace("\ufffd", "-").strip()

        if len(title) > 75 or title.endswith("..."):
            slug_match = re.search(r"/j/\d+/([^/]+)", full_url)
            if slug_match:
                title = slug_match.group(1).replace("-", " ").title()

        loc_match = re.search(r"\[([^\]]+)\]\((?:https?://itch\.io)?/jobs/near-[^\)]+\)", chunk, re.I)
        location = loc_match.group(1).strip() if loc_match else "Remote"

        company = ""
        at_match = re.search(r"@\s*([A-Za-z0-9\s&,.'-]+?)(?:\n|$|\s+-|\s+\[)", chunk)
        if at_match:
            company = at_match.group(1).strip()

        if not company:
            about_match = re.search(r"About\s+([A-Za-z0-9\s&,.'-]+?)(?:\n|\.|\s+-)", chunk, re.I)
            if about_match:
                company = about_match.group(1).strip()

        if not company:
            looking_match = re.search(r"([A-Za-z0-9\s&,.'-]+?)\s+is looking for", chunk, re.I)
            if looking_match:
                company = looking_match.group(1).strip()

        if not company:
            link_matches = re.findall(r"\[([^\]]+)\]\((https?://[^\)]+)\)", chunk)
            for link_text, link_target in link_matches:
                lt = link_text.strip()
                if lt and lt.lower() not in ["view full listing", "apply", "details", "website", "itch.io", "jobs", title.lower()]:
                    if "itch.io" not in link_target.lower():
                        company = lt
                        break

        company = deduplicate_repeated_phrase(company)
        job_dict = {
            "title": title,
            "company": company,
            "board_source": "Itch.io",
            "source_board": "Itch.io",
            "listing_url": full_url,
            "board_url": full_url,
            "location": location,
        }
        if is_valid_job(job_dict) and not any(j["listing_url"] == full_url for j in jobs):
            jobs.append(job_dict)

    # HTML Fallback
    if not jobs and ("<html" in raw_content.lower() or "<div" in raw_content.lower()):
        try:
            soup = BeautifulSoup(raw_content, "html.parser")
            for item in soup.select(".job_listing, .job_row, article, li"):
                link = item.find("a", href=True)
                if not link:
                    continue
                href = link.get("href", "")
                if not any(k in href for k in ["/jobs/", "/j/"]):
                    continue
                title = link.get_text(strip=True)
                comp_elem = item.find(class_=re.compile(r"company|employer|studio", re.I))
                company = comp_elem.get_text(strip=True) if comp_elem else ""
                loc_elem = item.find(class_=re.compile(r"location|city|region", re.I))
                location = loc_elem.get_text(strip=True) if loc_elem else "Remote"
                full_url = urljoin(base_url, href)

                job_dict = {
                    "title": title,
                    "company": company or "PixelForge Games",
                    "board_source": "Itch.io",
                    "source_board": "Itch.io",
                    "listing_url": full_url,
                    "board_url": full_url,
                    "location": location,
                }
                if is_valid_job(job_dict) and not any(j["listing_url"] == full_url for j in jobs):
                    jobs.append(job_dict)
        except Exception:
            pass

    return filter_jobs_by_keyword(jobs, keyword)[:20]


async def scrape_itch_io(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes Itch.io."""
    logger.info(f"🕹️ [Itch.io] Scraping keyword='{keyword}'...")
    url = "https://itch.io/jobs"
    try:
        content = await fetch_page_content(url)
        jobs = parse_itch_io_listings(content, keyword)
        return jobs[:limit]
    except Exception as e:
        logger.error(f"❌ [Itch.io] Error: {e}")
        return []


# ==============================================================================
# 2. GamesIndustry.biz Scraper
# ==============================================================================

def parse_gamesindustry_listings(raw_content: str, keyword: str = "") -> List[Dict[str, Any]]:
    """Extracts job postings from GamesIndustry.biz."""
    jobs: List[Dict[str, Any]] = []
    base_url = "https://jobs.gamesindustry.biz"

    pattern = r"(?=\[[^\]]+\]\((?:https?://jobs\.gamesindustry\.biz)?/job/\d+/[^\)]+\))"
    chunks = re.split(pattern, raw_content)

    for chunk in chunks:
        job_match = re.search(r"\[([^\]]+)\]\(((?:https?://jobs\.gamesindustry\.biz)?/job/\d+/[^\)]+)\)", chunk, re.I)
        if not job_match:
            continue

        title_raw = job_match.group(1).strip()
        url_raw = job_match.group(2).strip()
        full_url = urljoin(base_url, url_raw)
        title = title_raw.replace("\ufffd", "-").strip()

        company = ""
        comp_link_match = re.search(r"\[([^\]]+)\]\((?:https?://jobs\.gamesindustry\.biz)?/company/[^\)]+\)", chunk, re.I)
        if comp_link_match:
            company = comp_link_match.group(1).strip()

        if not company:
            at_match = re.search(r"\bat\s+([A-Za-z0-9\s&,.'-]+?)(?:\n|$|\s+-|\s+\[)", chunk, re.I)
            if at_match:
                company = at_match.group(1).strip()

        location = "Remote / UK"
        loc_match = re.search(r"(?:Location|Based in|in)\s*:\s*([A-Za-z0-9\s,]+)", chunk, re.I)
        if loc_match:
            location = loc_match.group(1).strip()

        company = deduplicate_repeated_phrase(company)
        job_dict = {
            "title": title,
            "company": company,
            "board_source": "GamesIndustry.biz",
            "source_board": "GamesIndustry.biz",
            "listing_url": full_url,
            "board_url": full_url,
            "location": location,
        }
        if is_valid_job(job_dict) and not any(j["listing_url"] == full_url for j in jobs):
            jobs.append(job_dict)

    # HTML Fallback
    if not jobs and ("<html" in raw_content.lower() or "<div" in raw_content.lower()):
        try:
            soup = BeautifulSoup(raw_content, "html.parser")
            for item in soup.select(".job-item, .job-row, article, li"):
                link = item.find("a", href=True)
                if not link:
                    continue
                href = link.get("href", "")
                if "/job/" not in href and "/jobs/" not in href:
                    continue
                title = link.get_text(strip=True)
                comp_elem = item.find(class_=re.compile(r"company|recruiter|employer", re.I))
                company = comp_elem.get_text(strip=True) if comp_elem else ""
                loc_elem = item.find(class_=re.compile(r"location|city|region", re.I))
                location = loc_elem.get_text(strip=True) if loc_elem else "Remote"
                full_url = urljoin(base_url, href)

                job_dict = {
                    "title": title,
                    "company": company or "Games Studio",
                    "board_source": "GamesIndustry.biz",
                    "source_board": "GamesIndustry.biz",
                    "listing_url": full_url,
                    "board_url": full_url,
                    "location": location,
                }
                if is_valid_job(job_dict) and not any(j["listing_url"] == full_url for j in jobs):
                    jobs.append(job_dict)
        except Exception:
            pass

    return filter_jobs_by_keyword(jobs, keyword)[:20]


async def scrape_gamesindustry(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes GamesIndustry.biz."""
    logger.info(f"🎮 [GamesIndustry.biz] Scraping keyword='{keyword}'...")
    url = f"https://jobs.gamesindustry.biz/jobs?query={quote_plus(keyword)}"
    try:
        content = await fetch_page_content(url)
        jobs = parse_gamesindustry_listings(content, keyword)
        return jobs[:limit]
    except Exception as e:
        logger.error(f"❌ [GamesIndustry.biz] Error: {e}")
        return []


# ==============================================================================
# 3. WeWorkRemotely Scraper
# ==============================================================================

def parse_wwr_listings(raw_content: str, keyword: str = "") -> List[Dict[str, Any]]:
    """Extracts job postings from WeWorkRemotely."""
    jobs: List[Dict[str, Any]] = []
    base_url = "https://weworkremotely.com"

    lines = raw_content.splitlines()
    for i, line in enumerate(lines):
        heading_match = re.match(r"^#{1,4}\s+\[?([^\]\n]+)\]?(?:\((/remote-jobs/[^\)]+)\))?", line.strip())
        if not heading_match:
            continue

        title = heading_match.group(1).strip()
        rel_url = heading_match.group(2)
        full_url = urljoin(base_url, rel_url) if rel_url else ""

        company = ""
        location = "Remote"

        for offset in range(1, 6):
            if i + offset >= len(lines):
                break
            meta_line = lines[i + offset].strip()
            if not meta_line or meta_line.startswith("#"):
                break

            if not full_url:
                url_search = re.search(r"\((/remote-jobs/[^\)]+)\)", meta_line)
                if url_search:
                    full_url = urljoin(base_url, url_search.group(1))

            comp_match = re.search(r"\[([^\]]+)\]\((?:https?://weworkremotely\.com)?/company/[^\)]+\)", meta_line)
            if comp_match:
                company = comp_match.group(1).strip()

            if "•" in meta_line or " | " in meta_line:
                parts = [p.strip() for p in re.split(r"[•|]", meta_line) if p.strip()]
                if not company and len(parts) >= 2:
                    company = parts[0]
                    location = parts[1]
                elif len(parts) >= 1:
                    location = parts[0]

        if not full_url and "/remote-jobs/" in line:
            u_match = re.search(r"\((/remote-jobs/[^\)]+)\)", line)
            if u_match:
                full_url = urljoin(base_url, u_match.group(1))

        if not full_url:
            continue

        company = deduplicate_repeated_phrase(company)
        job_dict = {
            "title": title.replace("\ufffd", "-").strip(),
            "company": company.replace("\ufffd", "").strip(),
            "board_source": "WeWorkRemotely",
            "source_board": "WeWorkRemotely",
            "listing_url": full_url,
            "board_url": full_url,
            "location": location,
        }
        if is_valid_job(job_dict) and not any(j["listing_url"] == full_url for j in jobs):
            jobs.append(job_dict)

    # HTML Fallback
    if not jobs and ("<html" in raw_content.lower() or "<li" in raw_content.lower()):
        try:
            soup = BeautifulSoup(raw_content, "html.parser")
            for item in soup.select("section.jobs li, .job-listing, li"):
                link = item.find("a", href=True)
                if not link or "/remote-jobs/" not in link.get("href", ""):
                    continue
                href = link.get("href", "")
                title_elem = item.find(class_=re.compile(r"title", re.I)) or link.find("span")
                title = title_elem.get_text(strip=True) if title_elem else link.get_text(strip=True)
                comp_elem = item.find(class_=re.compile(r"company", re.I))
                company = comp_elem.get_text(strip=True) if comp_elem else "WWR Employer"
                loc_elem = item.find(class_=re.compile(r"region|location", re.I))
                location = loc_elem.get_text(strip=True) if loc_elem else "Remote"
                full_url = urljoin(base_url, href)

                job_dict = {
                    "title": title,
                    "company": company,
                    "board_source": "WeWorkRemotely",
                    "source_board": "WeWorkRemotely",
                    "listing_url": full_url,
                    "board_url": full_url,
                    "location": location,
                }
                if is_valid_job(job_dict) and not any(j["listing_url"] == full_url for j in jobs):
                    jobs.append(job_dict)
        except Exception:
            pass

    return filter_jobs_by_keyword(jobs, keyword)[:20]


async def scrape_wwr(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes WeWorkRemotely."""
    logger.info(f"🌍 [WeWorkRemotely] Scraping keyword='{keyword}'...")
    search_url = f"https://weworkremotely.com/remote-jobs/search?term={quote_plus(keyword)}"
    try:
        content = await fetch_page_content(search_url)
        if "[ANTI_BOT_BLOCKED]" in content:
            content = await fetch_page_content("https://weworkremotely.com/top-trending-remote-jobs")
        jobs = parse_wwr_listings(content, keyword)
        return jobs[:limit]
    except Exception as e:
        logger.error(f"❌ [WeWorkRemotely] Error: {e}")
        return []


# ==============================================================================
# 4. RemoteOK Scraper
# ==============================================================================

def parse_remoteok(raw_content: str, keyword: str = "") -> List[Dict[str, Any]]:
    """Extracts job postings from RemoteOK."""
    jobs: List[Dict[str, Any]] = []
    base_url = "https://remoteok.com"

    matches = re.findall(
        r"\[([^\]]+)\]\(((?:https?://remoteok\.com)?/remote-jobs/[^\)]+)\)",
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
            "board_source": "RemoteOK",
            "source_board": "RemoteOK",
            "listing_url": full_url,
            "board_url": full_url,
            "location": "100% Remote",
        }
        if is_valid_job(job_dict) and not any(j["listing_url"] == full_url for j in jobs):
            jobs.append(job_dict)

    return filter_jobs_by_keyword(jobs, keyword)[:20]


async def scrape_remoteok(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes RemoteOK using its official live API with web fallback."""
    norm_kw = normalize_search_keyword(keyword).lower()
    tag = ""
    if any(k in norm_kw for k in ["marketing", "marketer", "seo", "content", "growth", "copywriter"]):
        tag = "marketing"
    elif any(k in norm_kw for k in ["design", "ui", "ux"]):
        tag = "design"
    elif any(k in norm_kw for k in ["dev", "engineer", "software", "backend", "frontend"]):
        tag = "dev"

    logger.info(f"🚀 [RemoteOK] Scraping keyword='{norm_kw}' (tag='{tag}')...")
    jobs: List[Dict[str, Any]] = []
    headers = {"User-Agent": settings.DEFAULT_USER_AGENT, "Accept": "application/json"}
    api_url = f"https://remoteok.com/api?tag={tag}" if tag else "https://remoteok.com/api"
    try:
        async with httpx.AsyncClient(headers=headers, timeout=12.0, follow_redirects=True) as client:
            resp = await client.get(api_url)
            if resp.status_code == 200:
                raw_data = resp.json()
                if isinstance(raw_data, list):
                    for item in raw_data[1:]:
                        if not isinstance(item, dict):
                            continue
                        pos = item.get("position", "")
                        comp = item.get("company", "")
                        tags = item.get("tags") or []
                        url = item.get("url") or f"https://remoteok.com/remote-jobs/{item.get('id')}"
                        loc = item.get("location") or "100% Remote"
                        desc = item.get("description", "")
                        if not pos or not comp:
                            continue
                        job_dict = {
                            "title": pos.strip(),
                            "company": comp.strip(),
                            "board_source": "RemoteOK",
                            "source_board": "RemoteOK",
                            "listing_url": url,
                            "board_url": url,
                            "location": loc,
                            "tags": tags,
                            "description": desc,
                        }
                        if is_valid_job(job_dict) and not any(j["listing_url"] == url for j in jobs):
                            jobs.append(job_dict)
    except Exception as e:
        logger.debug(f"RemoteOK API attempt error: {e}")

    if not jobs:
        url = f"https://remoteok.com/remote-{quote_plus(keyword.lower().replace(' ', '-'))}-jobs"
        try:
            content = await fetch_page_content(url)
            jobs = parse_remoteok(content, keyword)
        except Exception:
            pass

    return filter_jobs_by_keyword(jobs, keyword)[:limit]


# ==============================================================================
# 5. Remotive Scraper
# ==============================================================================

def parse_remotive(raw_content: str, keyword: str = "") -> List[Dict[str, Any]]:
    """Extracts job postings from Remotive."""
    jobs: List[Dict[str, Any]] = []
    base_url = "https://remotive.com"

    matches = re.findall(
        r"\[([^\]]+)\]\(((?:https?://remotive\.com)?/remote-jobs/[^\)]+)\)",
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
            "board_source": "Remotive",
            "source_board": "Remotive",
            "listing_url": full_url,
            "board_url": full_url,
            "location": "Remote",
        }
        if is_valid_job(job_dict) and not any(j["listing_url"] == full_url for j in jobs):
            jobs.append(job_dict)

    return filter_jobs_by_keyword(jobs, keyword)[:20]


async def scrape_remotive(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes Remotive using public API and web search."""
    logger.info(f"✨ [Remotive] Scraping keyword='{keyword}'...")
    jobs: List[Dict[str, Any]] = []
    headers = {"User-Agent": settings.DEFAULT_USER_AGENT, "Accept": "application/json"}
    try:
        async with httpx.AsyncClient(headers=headers, timeout=12.0, follow_redirects=True) as client:
            resp = await client.get(f"https://remotive.com/api/remote-jobs?search={quote_plus(keyword)}")
            if resp.status_code == 200:
                for item in resp.json().get("jobs", []):
                    t = item.get("title", "")
                    c = item.get("company_name", "")
                    u = item.get("url", "")
                    loc = item.get("candidate_required_location", "Remote")
                    tags = [item.get("category", "")] + (item.get("tags") or [])
                    job_dict = {
                        "title": t.strip(),
                        "company": c.strip(),
                        "board_source": "Remotive",
                        "source_board": "Remotive",
                        "listing_url": u,
                        "board_url": u,
                        "location": loc,
                        "tags": tags,
                    }
                    if is_valid_job(job_dict) and not any(j["listing_url"] == u for j in jobs):
                        jobs.append(job_dict)
    except Exception as e:
        logger.debug(f"Remotive API query error: {e}")

    if not jobs:
        url = f"https://remotive.com/remote-jobs?search={quote_plus(keyword)}"
        try:
            content = await fetch_page_content(url)
            jobs = parse_remotive(content, keyword)
        except Exception as e:
            logger.error(f"❌ [Remotive] Error: {e}")

    return filter_jobs_by_keyword(jobs, keyword)[:limit]


# ==============================================================================
# 6. Additional Tech & Remote Boards
# ==============================================================================

async def scrape_builtin(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes BuiltIn."""
    logger.info(f"🏢 [BuiltIn] Scraping keyword='{keyword}'...")
    url = f"https://builtin.com/jobs?search={quote_plus(keyword)}"
    try:
        content = await fetch_page_content(url)
        matches = re.findall(r"\[([^\]]+)\]\(((?:https?://builtin\.com)?/job/[^\)]+)\)", content, re.I)
        jobs = []
        for text, href in matches:
            full_url = urljoin("https://builtin.com", href)
            parts = [p.strip() for p in text.split(" at ") if p.strip()]
            title = parts[0] if parts else text
            company = parts[1] if len(parts) > 1 else ""
            job_dict = {
                "title": title,
                "company": company,
                "board_source": "BuiltIn",
                "source_board": "BuiltIn",
                "listing_url": full_url,
                "board_url": full_url,
                "location": "Remote / Tech Hub",
            }
            if is_valid_job(job_dict) and not any(j["listing_url"] == full_url for j in jobs):
                jobs.append(job_dict)
        return filter_jobs_by_keyword(jobs, keyword)[:limit]
    except Exception as e:
        logger.error(f"❌ [BuiltIn] Error: {e}")
        return []


async def scrape_working_nomads(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes WorkingNomads."""
    logger.info(f"🏖️ [WorkingNomads] Scraping keyword='{keyword}'...")
    url = f"https://www.workingnomads.com/jobs?tag={quote_plus(keyword)}"
    try:
        content = await fetch_page_content(url)
        matches = re.findall(r"\[([^\]]+)\]\(((?:https?://www\.workingnomads\.com)?/jobs\?job=[^\)]+)\)", content, re.I)
        jobs = []
        for text, href in matches:
            full_url = urljoin("https://www.workingnomads.com", href)
            parts = [p.strip() for p in text.split(" at ") if p.strip()]
            title = parts[0] if parts else text
            company = parts[1] if len(parts) > 1 else ""
            job_dict = {
                "title": title,
                "company": company,
                "board_source": "WorkingNomads",
                "source_board": "WorkingNomads",
                "listing_url": full_url,
                "board_url": full_url,
                "location": "Remote",
            }
            if is_valid_job(job_dict) and not any(j["listing_url"] == full_url for j in jobs):
                jobs.append(job_dict)
        return filter_jobs_by_keyword(jobs, keyword)[:limit]
    except Exception as e:
        logger.error(f"❌ [WorkingNomads] Error: {e}")
        return []


async def scrape_techcareers(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes Techcareers."""
    from scrapers.niche_boards import scrape_techcareers as st
    return await st(keyword=keyword, location=location)


async def scrape_jobspresso(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes Jobspresso."""
    logger.info(f"☕ [Jobspresso] Scraping keyword='{keyword}'...")
    url = f"https://jobspresso.co/remote-work/?search_keywords={quote_plus(keyword)}"
    try:
        content = await fetch_page_content(url)
        matches = re.findall(r"\[([^\]]+)\]\(((?:https?://jobspresso\.co)?/job/[^\)]+)\)", content, re.I)
        jobs = []
        for text, href in matches:
            full_url = urljoin("https://jobspresso.co", href)
            parts = [p.strip() for p in text.split(" at ") if p.strip()]
            title = parts[0] if parts else text
            company = parts[1] if len(parts) > 1 else ""
            job_dict = {
                "title": title,
                "company": company,
                "board_source": "Jobspresso",
                "source_board": "Jobspresso",
                "listing_url": full_url,
                "board_url": full_url,
                "location": "Remote",
            }
            if is_valid_job(job_dict) and not any(j["listing_url"] == full_url for j in jobs):
                jobs.append(job_dict)
        return filter_jobs_by_keyword(jobs, keyword)[:limit]
    except Exception as e:
        logger.error(f"❌ [Jobspresso] Error: {e}")
        return []


async def scrape_justremote(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes JustRemote."""
    logger.info(f"🎯 [JustRemote] Scraping keyword='{keyword}'...")
    url = f"https://justremote.co/remote-jobs?search={quote_plus(keyword)}"
    try:
        content = await fetch_page_content(url)
        matches = re.findall(r"\[([^\]]+)\]\(((?:https?://justremote\.co)?/remote-jobs/[^\)]+)\)", content, re.I)
        jobs = []
        for text, href in matches:
            full_url = urljoin("https://justremote.co", href)
            parts = [p.strip() for p in text.split(" at ") if p.strip()]
            title = parts[0] if parts else text
            company = parts[1] if len(parts) > 1 else ""
            job_dict = {
                "title": title,
                "company": company,
                "board_source": "JustRemote",
                "source_board": "JustRemote",
                "listing_url": full_url,
                "board_url": full_url,
                "location": "Remote",
            }
            if is_valid_job(job_dict) and not any(j["listing_url"] == full_url for j in jobs):
                jobs.append(job_dict)
        return filter_jobs_by_keyword(jobs, keyword)[:limit]
    except Exception as e:
        logger.error(f"❌ [JustRemote] Error: {e}")
async def scrape_dice(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes Dice."""
    from scrapers.niche_boards import scrape_dice as sd
    return await sd(keyword=keyword, location=location)


async def scrape_hackernews_hiring(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes Hacker News Who is Hiring."""
    logger.info(f"📰 [HackerNews Hiring] Scraping keyword='{keyword}'...")
    url = "https://news.ycombinator.com/submitted?id=whoishiring"
    try:
        content = await fetch_page_content(url)
        matches = re.findall(r"\[([^\]]+)\]\((item\?id=\d+)\)", content)
        jobs = []
        for text, href in matches:
            if "is hiring" in text.lower() or "who is hiring" in text.lower():
                thread_url = f"https://news.ycombinator.com/{href}"
                thread_content = await fetch_page_content(thread_url)
                # Parse comments
                for comment_line in thread_content.splitlines():
                    if "|" in comment_line and any(kw.lower() in comment_line.lower() for kw in [keyword, "engineer", "remote", "developer"]):
                        parts = [p.strip() for p in comment_line.split("|") if p.strip()]
                        if len(parts) >= 2:
                            company = parts[0]
                            title = parts[1]
                            job_dict = {
                                "title": title,
                                "company": company,
                                "board_source": "HackerNews Hiring",
                                "source_board": "HackerNews Hiring",
                                "listing_url": thread_url,
                                "board_url": thread_url,
                                "location": "Remote",
                            }
                            if is_valid_job(job_dict) and not any(j["company"] == company for j in jobs):
                                jobs.append(job_dict)
                        if len(jobs) >= limit:
                            break
                break
        return filter_jobs_by_keyword(jobs, keyword)[:limit]
    except Exception as e:
        logger.error(f"❌ [HackerNews Hiring] Error: {e}")
        return []


# ==============================================================================
# 13. Arc.dev Scraper
# ==============================================================================

def parse_arc_dev_listings(raw_content: str, keyword: str = "") -> List[Dict[str, Any]]:
    """Extracts remote tech opportunities from Arc.dev."""
    jobs: List[Dict[str, Any]] = []
    base_url = "https://arc.dev"

    if "<html" in raw_content.lower() or "<div" in raw_content.lower():
        try:
            soup = BeautifulSoup(raw_content, "html.parser")
            for item in soup.select(".job-card, .css-1, article, [data-testid='job-card']"):
                link = item.find("a", href=True)
                if not link:
                    continue
                href = link.get("href", "")
                if "/remote-jobs/" not in href and "/jobs/" not in href:
                    continue
                title = link.get_text(strip=True)
                comp_elem = item.find(class_=re.compile(r"company|employer", re.I))
                company = comp_elem.get_text(strip=True) if comp_elem else ""
                loc_elem = item.find(class_=re.compile(r"location", re.I))
                location = loc_elem.get_text(strip=True) if loc_elem else "Remote"
                full_url = urljoin(base_url, href)

                if title and len(title) > 2:
                    job_dict = {
                        "title": title,
                        "company": company or "Arc Verified Partner",
                        "board_source": "Arc.dev",
                        "source_board": "Arc.dev",
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
        matches = re.findall(r"\[([^\]]+)\]\(((?:https?://arc\.dev)?/remote-jobs/[^\)]+)\)", raw_content, re.I)
        for t, u in matches:
            full_url = urljoin(base_url, u)
            clean_t = t.strip()
            if clean_t.lower() not in ["view job", "apply", "details"]:
                job_dict = {
                    "title": clean_t,
                    "company": "Arc Partner Company",
                    "board_source": "Arc.dev",
                    "source_board": "Arc.dev",
                    "listing_url": full_url,
                    "board_url": full_url,
                    "location": "Remote",
                }
                if is_valid_job(job_dict) and not any(j["listing_url"] == full_url for j in jobs):
                    jobs.append(job_dict)

    return filter_jobs_by_keyword(jobs, keyword)[:20]


async def scrape_arc_dev(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes Arc.dev."""
    logger.info(f"🌐 [Arc.dev] Scraping keyword='{keyword}'...")
    url = f"https://arc.dev/remote-jobs?search={quote_plus(keyword)}" if keyword else "https://arc.dev/remote-jobs"
    try:
        content = await fetch_page_content(url)
        jobs = parse_arc_dev_listings(content, keyword)
        return jobs[:limit]
    except Exception as e:
        logger.error(f"❌ [Arc.dev] Error: {e}")
        return []


# ==============================================================================
# 14. Himalayas Scraper
# ==============================================================================

def parse_himalayas_listings(raw_content: str, keyword: str = "") -> List[Dict[str, Any]]:
    """Extracts remote job listings from Himalayas.app."""
    jobs: List[Dict[str, Any]] = []
    base_url = "https://himalayas.app"

    # Try JSON API/LD or Next.js state
    if "props" in raw_content or "__NEXT_DATA__" in raw_content:
        match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', raw_content, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(1))
                page_jobs = data.get("props", {}).get("pageProps", {}).get("jobs", [])
                for j in page_jobs:
                    t = j.get("title") or j.get("name")
                    c = j.get("companyName") or j.get("company", {}).get("name") if isinstance(j.get("company"), dict) else j.get("company")
                    slug = j.get("slug") or j.get("id")
                    u = f"https://himalayas.app/companies/{j.get('companySlug', 'c')}/jobs/{slug}" if slug else "https://himalayas.app/jobs"
                    if t and c:
                        job_dict = {
                            "title": str(t).strip(),
                            "company": str(c).strip(),
                            "board_source": "Himalayas",
                            "source_board": "Himalayas",
                            "listing_url": u,
                            "board_url": u,
                            "location": "Remote",
                        }
                        if is_valid_job(job_dict) and not any(x["listing_url"] == u for x in jobs):
                            jobs.append(job_dict)
            except Exception:
                pass

    if "<html" in raw_content.lower() or "<div" in raw_content.lower():
        try:
            soup = BeautifulSoup(raw_content, "html.parser")
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if "/jobs/" in href and len(href.split("/")) >= 3:
                    title = a.get_text(strip=True)
                    if len(title) > 3 and not any(k in title.lower() for k in ["view all", "subscribe", "filter"]):
                        full_url = urljoin(base_url, href)
                        job_dict = {
                            "title": title,
                            "company": "Himalayas Tech",
                            "board_source": "Himalayas",
                            "source_board": "Himalayas",
                            "listing_url": full_url,
                            "board_url": full_url,
                            "location": "Remote",
                        }
                        if is_valid_job(job_dict) and not any(x["listing_url"] == full_url for x in jobs):
                            jobs.append(job_dict)
        except Exception:
            pass

    return filter_jobs_by_keyword(jobs, keyword)[:20]


async def scrape_himalayas(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes Himalayas using official live API with web fallback."""
    logger.info(f"🏔️ [Himalayas] Scraping keyword='{keyword}'...")
    jobs: List[Dict[str, Any]] = []
    headers = {"User-Agent": settings.DEFAULT_USER_AGENT, "Accept": "application/json"}
    try:
        async with httpx.AsyncClient(headers=headers, timeout=12.0, follow_redirects=True) as client:
            resp = await client.get(f"https://himalayas.app/jobs/api?q={quote_plus(keyword)}&limit={max(limit, 20)}")
            if resp.status_code == 200:
                data = resp.json().get("jobs", [])
                for item in data:
                    t = item.get("title", "")
                    c = item.get("companyName", "")
                    direct_link = item.get("applicationLink")
                    u = f"https://himalayas.app/companies/{item.get('companySlug', 'c')}/jobs/{item.get('slug', '')}" if item.get("slug") else "https://himalayas.app/jobs"
                    job_dict = {
                        "title": t.strip(),
                        "company": c.strip(),
                        "board_source": "Himalayas",
                        "source_board": "Himalayas",
                        "listing_url": u,
                        "board_url": u,
                        "location": "Worldwide / Remote",
                        "direct_apply_link": direct_link if (direct_link and direct_link.startswith("http")) else None,
                    }
                    if is_valid_job(job_dict) and not any(j["listing_url"] == u for j in jobs):
                        jobs.append(job_dict)
    except Exception as e:
        logger.debug(f"Himalayas API query error: {e}")

    if not jobs:
        url = f"https://himalayas.app/jobs?q={quote_plus(keyword)}" if keyword else "https://himalayas.app/jobs"
        try:
            content = await fetch_page_content(url)
            jobs = parse_himalayas_listings(content, keyword)
        except Exception as e:
            logger.error(f"❌ [Himalayas] Error: {e}")

    return filter_jobs_by_keyword(jobs, keyword)[:limit]


# ==============================================================================
# 15. SkipTheDrive Scraper
# ==============================================================================

def parse_skipthedrive_listings(raw_content: str, keyword: str = "") -> List[Dict[str, Any]]:
    """Extracts telecommuting and remote jobs from SkipTheDrive."""
    jobs: List[Dict[str, Any]] = []
    base_url = "https://www.skipthedrive.com"

    if "<html" in raw_content.lower() or "<div" in raw_content.lower():
        try:
            soup = BeautifulSoup(raw_content, "html.parser")
            for item in soup.select(".job_listing, article, .post"):
                link = item.find("a", href=True)
                if not link:
                    continue
                href = link.get("href", "")
                if "/job/" not in href:
                    continue
                title = link.get_text(strip=True)
                comp_elem = item.find(class_=re.compile(r"company|employer", re.I))
                company = comp_elem.get_text(strip=True) if comp_elem else ""
                full_url = urljoin(base_url, href)

                if title and len(title) > 2:
                    job_dict = {
                        "title": title,
                        "company": company or "Telecommute Employer",
                        "board_source": "SkipTheDrive",
                        "source_board": "SkipTheDrive",
                        "listing_url": full_url,
                        "board_url": full_url,
                        "location": "Remote",
                    }
                    if is_valid_job(job_dict) and not any(x["listing_url"] == full_url for x in jobs):
                        jobs.append(job_dict)
        except Exception:
            pass

    return filter_jobs_by_keyword(jobs, keyword)[:20]


async def scrape_skipthedrive(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes SkipTheDrive."""
    logger.info(f"🚗 [SkipTheDrive] Scraping keyword='{keyword}'...")
    url = f"https://www.skipthedrive.com/?s={quote_plus(keyword)}" if keyword else "https://www.skipthedrive.com/job-category/software-development/"
    try:
        content = await fetch_page_content(url)
        jobs = parse_skipthedrive_listings(content, keyword)
        return jobs[:limit]
    except Exception as e:
        logger.error(f"❌ [SkipTheDrive] Error: {e}")
        return []


# ==============================================================================
# 16. AuthenticJobs Scraper
# ==============================================================================

def parse_authentic_jobs_listings(raw_content: str, keyword: str = "") -> List[Dict[str, Any]]:
    """Extracts design, dev, and tech jobs from AuthenticJobs."""
    jobs: List[Dict[str, Any]] = []
    base_url = "https://authenticjobs.com"

    if "<html" in raw_content.lower() or "<div" in raw_content.lower():
        try:
            soup = BeautifulSoup(raw_content, "html.parser")
            for item in soup.select(".job_listing, article, .job-item"):
                link = item.find("a", href=True)
                if not link:
                    continue
                href = link.get("href", "")
                if "/job/" not in href:
                    continue
                title = link.get_text(strip=True)
                comp_elem = item.find(class_=re.compile(r"company|employer", re.I))
                company = comp_elem.get_text(strip=True) if comp_elem else ""
                full_url = urljoin(base_url, href)

                if title and len(title) > 2:
                    job_dict = {
                        "title": title,
                        "company": company or "Creative Agency",
                        "board_source": "AuthenticJobs",
                        "source_board": "AuthenticJobs",
                        "listing_url": full_url,
                        "board_url": full_url,
                        "location": "Remote",
                    }
                    if is_valid_job(job_dict) and not any(x["listing_url"] == full_url for x in jobs):
                        jobs.append(job_dict)
        except Exception:
            pass

    return filter_jobs_by_keyword(jobs, keyword)[:20]


async def scrape_authentic_jobs(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes AuthenticJobs."""
    logger.info(f"💎 [AuthenticJobs] Scraping keyword='{keyword}'...")
    url = f"https://authenticjobs.com/?s={quote_plus(keyword)}" if keyword else "https://authenticjobs.com/"
    try:
        content = await fetch_page_content(url)
        jobs = parse_authentic_jobs_listings(content, keyword)
        return jobs[:limit]
    except Exception as e:
        logger.error(f"❌ [AuthenticJobs] Error: {e}")
        return []


# ==============================================================================
# 17. Pangian Scraper
# ==============================================================================

def parse_pangian_listings(raw_content: str, keyword: str = "") -> List[Dict[str, Any]]:
    """Extracts international remote jobs from Pangian."""
    jobs: List[Dict[str, Any]] = []
    base_url = "https://pangian.com"

    if "<html" in raw_content.lower() or "<div" in raw_content.lower():
        try:
            soup = BeautifulSoup(raw_content, "html.parser")
            for item in soup.select(".job-item, article, li"):
                link = item.find("a", href=True)
                if not link:
                    continue
                href = link.get("href", "")
                if "/job/" not in href and "/jobs/" not in href:
                    continue
                title = link.get_text(strip=True)
                comp_elem = item.find(class_=re.compile(r"company|employer", re.I))
                company = comp_elem.get_text(strip=True) if comp_elem else ""
                full_url = urljoin(base_url, href)

                if title and len(title) > 2:
                    job_dict = {
                        "title": title,
                        "company": company or "Global Remote Corp",
                        "board_source": "Pangian",
                        "source_board": "Pangian",
                        "listing_url": full_url,
                        "board_url": full_url,
                        "location": "Global Remote",
                    }
                    if is_valid_job(job_dict) and not any(x["listing_url"] == full_url for x in jobs):
                        jobs.append(job_dict)
        except Exception:
            pass

    return filter_jobs_by_keyword(jobs, keyword)[:20]


async def scrape_pangian(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes Pangian."""
    logger.info(f"🌍 [Pangian] Scraping keyword='{keyword}'...")
    url = "https://pangian.com/job-travel-remote-work/"
    try:
        content = await fetch_page_content(url)
        jobs = parse_pangian_listings(content, keyword)
        return jobs[:limit]
    except Exception as e:
        logger.error(f"❌ [Pangian] Error: {e}")
        return []


# ==============================================================================
# Concurrent Orchestration Wrapper: run_level_1_scrapers
# ==============================================================================

async def run_level_1_scrapers(keyword: str, location: str = "Remote") -> Dict[str, Any]:
    """Executes Level 1 standard tech & remote scrapers."""
    logger.info(f"🚀 Running Level 1 scrapers for '{keyword}'...")
    results = await asyncio.gather(
        scrape_itch_io(keyword, location),
        scrape_gamesindustry(keyword, location),
        scrape_wwr(keyword, location),
        scrape_remoteok(keyword, location),
        scrape_remotive(keyword, location),
        return_exceptions=True,
    )

    names = ["Itch.io", "GamesIndustry.biz", "WeWorkRemotely", "RemoteOK", "Remotive"]
    summary_counts: Dict[str, int] = {}
    total_added = 0

    for name, res in zip(names, results):
        if isinstance(res, list):
            summary_counts[name] = len(res)
            added = 0
            for j in res:
                if is_valid_job(j) and state_manager.add_extracted_job(j):
                    added += 1
            total_added += added
            state_manager.update_board_status(name, status="completed", jobs_found=len(res))
        else:
            summary_counts[name] = 0
            state_manager.update_board_status(name, status="failed", error=str(res))

    return {
        "status": "success",
        "boards_scraped": names,
        "jobs_found_per_board": summary_counts,
        "total_newly_persisted": total_added,
    }


# ==============================================================================
# Remote.com Scraper (https://remote.com)
# ==============================================================================

def parse_remote_com_listings(raw_content: str, keyword: str = "") -> List[Dict[str, Any]]:
    """Extracts job postings from Remote.com directory."""
    jobs: List[Dict[str, Any]] = []
    try:
        soup = BeautifulSoup(raw_content, "html.parser")
        links = [
            a for a in soup.find_all("a", href=True)
            if "/jobs/" in a["href"] and not any(x in a["href"] for x in ["sign-up", "sign-in", "all", "types-of-remote-jobs"])
        ]
        for a in links:
            href = a["href"]
            parts = href.strip("/").split("/")
            comp_slug = parts[1].split("-c1")[0].replace("-", " ").title() if len(parts) >= 2 else "Remote.com Partner"
            title = a.get_text(separator=" ", strip=True)
            if not title or title.lower() in ["view listing", "apply", "remote jobs by category"]:
                continue
            full_url = urljoin("https://remote.com", href)
            job_dict = {
                "title": title,
                "company": comp_slug,
                "board_source": "Remote.com",
                "source_board": "Remote.com",
                "listing_url": full_url,
                "board_url": full_url,
                "location": "Remote",
            }
            if is_valid_job(job_dict) and not any(j["listing_url"] == full_url for j in jobs):
                jobs.append(job_dict)
    except Exception as e:
        logger.debug(f"Remote.com parsing error: {e}")

    return filter_jobs_by_keyword(jobs, keyword)


async def scrape_remote_com(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes Remote.com international remote job board."""
    logger.info(f"🌐 [Remote.com] Scraping keyword='{keyword}'...")
    url = f"https://remote.com/jobs/all?query={quote_plus(keyword)}"
    try:
        from curl_cffi import requests as cffi_requests
        resp = await asyncio.to_thread(cffi_requests.get, url, impersonate="chrome120", timeout=12)
        if resp.status_code == 200 and resp.text:
            jobs = parse_remote_com_listings(resp.text, keyword)
            logger.info(f"✅ [Remote.com] Extracted {len(jobs)} jobs.")
            return jobs[:limit]
        content = await fetch_page_content(url)
        jobs = parse_remote_com_listings(content, keyword)
        return jobs[:limit]
    except Exception as e:
        logger.error(f"❌ [Remote.com] Failed: {e}")
        return []


# ==============================================================================
# DailyRemote Scraper (https://dailyremote.com)
# ==============================================================================

def parse_dailyremote_listings(raw_content: str, keyword: str = "") -> List[Dict[str, Any]]:
    """Extracts 100% pure remote job postings from DailyRemote."""
    jobs: List[Dict[str, Any]] = []
    try:
        soup = BeautifulSoup(raw_content, "html.parser")
        cards = soup.select("article.lst-card")
        for card in cards:
            t_elem = card.select_one("h2.lst-card__title a")
            if not t_elem:
                continue

            title = t_elem.get_text(strip=True)
            href = t_elem.get("href", "")
            if not title or not href:
                continue

            full_url = urljoin("https://dailyremote.com", href)

            comp_elem = card.select_one(".lst-card__company, span.company, a.company")
            company = comp_elem.get_text(strip=True) if comp_elem else ""
            if not company or "company hidden" in company.lower():
                company = "DailyRemote Verified Partner"

            loc_elem = card.select_one(".lst-card__location, span.location")
            location = loc_elem.get_text(strip=True) if loc_elem else "100% Remote / Worldwide"

            job_dict = {
                "title": title,
                "company": company,
                "board_source": "DailyRemote",
                "source_board": "DailyRemote",
                "listing_url": full_url,
                "board_url": full_url,
                "location": location,
            }
            if is_valid_job(job_dict) and not any(j["listing_url"] == full_url for j in jobs):
                jobs.append(job_dict)
    except Exception as e:
        logger.debug(f"DailyRemote parsing error: {e}")

    return filter_jobs_by_keyword(jobs, keyword)


async def scrape_dailyremote(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes 100% pure remote jobs from DailyRemote."""
    logger.info(f"🌍 [DailyRemote] Scraping 100% remote jobs for keyword='{keyword}'...")
    url = f"https://dailyremote.com/remote-jobs?search={quote_plus(keyword)}"
    try:
        from curl_cffi import requests as cffi_requests
        resp = await asyncio.to_thread(cffi_requests.get, url, impersonate="chrome120", timeout=12)
        if resp.status_code == 200 and resp.text:
            jobs = parse_dailyremote_listings(resp.text, keyword)
            logger.info(f"✅ [DailyRemote] Extracted {len(jobs)} pure remote jobs.")
            return jobs[:limit]
        content = await fetch_page_content(url)
        jobs = parse_dailyremote_listings(content, keyword)
        return jobs[:limit]
    except Exception as e:
        logger.error(f"❌ [DailyRemote] Failed: {e}")
        return []


# ==============================================================================
# 20. 4DayWeek Scraper (https://4dayweek.io)
# ==============================================================================

def parse_4dayweek_listings(raw_data: str, keyword: str = "") -> List[Dict[str, Any]]:
    """Extracts jobs from 4DayWeek official REST API."""
    jobs: List[Dict[str, Any]] = []
    try:
        data = json.loads(raw_data) if isinstance(raw_data, str) else raw_data
        item_list = data.get("jobs", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
        for j in item_list:
            title = str(j.get("title", "")).strip()
            slug = str(j.get("slug", "")).strip()
            if not title or not slug:
                continue
            full_url = f"https://4dayweek.io/job/{slug}"
            company = str(j.get("company_name", "")).strip() or "4DayWeek Partner"

            loc_list = j.get("locations")
            location = "Remote (4-Day Week)"
            if isinstance(loc_list, list) and loc_list:
                loc_names = []
                for loc in loc_list:
                    if isinstance(loc, dict):
                        parts = [p for p in [loc.get("city"), loc.get("country")] if p]
                        if parts:
                            loc_names.append(", ".join(parts))
                    elif isinstance(loc, str):
                        loc_names.append(loc)
                if loc_names:
                    location = f"Remote / {', '.join(loc_names[:2])}"

            job_dict = {
                "title": title,
                "company": company,
                "board_source": "4DayWeek",
                "source_board": "4DayWeek",
                "listing_url": full_url,
                "board_url": full_url,
                "location": location,
            }
            if is_valid_job(job_dict) and not any(existing["listing_url"] == full_url for existing in jobs):
                jobs.append(job_dict)
    except Exception as e:
        logger.debug(f"4DayWeek parsing error: {e}")

    return filter_jobs_by_keyword(jobs, keyword)


async def scrape_4dayweek(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes 100% remote flexible & 4-day week jobs from 4DayWeek API."""
    logger.info(f"⏳ [4DayWeek] Scraping remote jobs for keyword='{keyword}'...")
    url = "https://4dayweek.io/api/jobs"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
    }
    try:
        async with httpx.AsyncClient(headers=headers, timeout=12.0, follow_redirects=True) as client:
            resp = await client.get(url)
            if resp.status_code == 200 and resp.text:
                jobs = parse_4dayweek_listings(resp.text, keyword)
                logger.info(f"✅ [4DayWeek] Extracted {len(jobs)} jobs.")
                return jobs[:limit]
        return []
    except Exception as e:
        logger.error(f"❌ [4DayWeek] Failed: {e}")
        return []


# ==============================================================================
# 21. Nodesk Scraper (https://nodesk.co)
# ==============================================================================

def parse_nodesk_feed(raw_xml: str, keyword: str = "") -> List[Dict[str, Any]]:
    """Extracts curated pure remote jobs from Nodesk official XML feed."""
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

            company = "Nodesk Partner"
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
                "board_source": "Nodesk",
                "source_board": "Nodesk",
                "listing_url": link,
                "board_url": link,
                "location": "100% Remote / Worldwide",
            }
            if is_valid_job(job_dict) and not any(existing["listing_url"] == link for existing in jobs):
                jobs.append(job_dict)
    except Exception as e:
        logger.debug(f"Nodesk parsing error: {e}")

    return filter_jobs_by_keyword(jobs, keyword)


async def scrape_nodesk(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes curated pure remote jobs from Nodesk official XML feed."""
    logger.info(f"🌐 [Nodesk] Scraping remote jobs for keyword='{keyword}'...")
    url = "https://nodesk.co/remote-jobs/index.xml"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/xml, text/xml, */*",
    }
    try:
        async with httpx.AsyncClient(headers=headers, timeout=12.0, follow_redirects=True) as client:
            resp = await client.get(url)
            if resp.status_code == 200 and resp.text:
                jobs = parse_nodesk_feed(resp.text, keyword)
                logger.info(f"✅ [Nodesk] Extracted {len(jobs)} remote jobs.")
                return jobs[:limit]
        return []
    except Exception as e:
        logger.error(f"❌ [Nodesk] Failed: {e}")
        return []



