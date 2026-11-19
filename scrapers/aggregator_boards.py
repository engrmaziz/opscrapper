"""
Level 2 Aggregator Job Board Scrapers: SimplyHired, Jobgether, Jooble, and DynamiteJobs.
Features resilient URL builders, anti-ad/sponsored filtering, absolute URL resolution,
and dynamic/LLM-assisted structured extraction.
"""

import asyncio
from datetime import datetime
import json
import re
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus, urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from config.settings import settings
from config.logging_config import get_logger
from tools.web_navigator import fetch_page_content
from utils.state_manager import state_manager
from utils.keyword_matcher import filter_jobs_by_keyword, normalize_search_keyword
from scrapers.standard_boards import is_valid_job

logger = get_logger("Level2Aggregators")

# Filter patterns for sponsored ads, promotions, and aggregator self-promotions
SPONSORED_PATTERNS = [
    re.compile(r"\b(sponsored|promoted|ad|advertisement|featured ad)\b", re.I),
    re.compile(r"\b(partner job|hiring urgently|sponsored listing)\b", re.I),
]

AGGREGATOR_GENERIC_COMPANIES = {
    "simplyhired",
    "jooble",
    "jobgether",
    "dynamite jobs",
    "dynamitejobs",
    "partner network",
    "confidential employer",
    "confidential",
    "various employers",
}


def is_sponsored_or_spam(text: str, class_names: str = "") -> bool:
    """Checks whether a listing card or text block is a sponsored advertisement."""
    combined = f"{text} {class_names}".lower()
    for pat in SPONSORED_PATTERNS:
        if pat.search(combined):
            return True
    return False


def clean_company_name(company: str, default_name: str) -> str:
    """Cleans aggregator artifacts and normalizes hiring employer name."""
    if not company or not company.strip():
        return default_name

    cleaned = re.sub(r"\s+", " ", company).strip()
    cleaned = re.sub(r"^(at|by|for|via)\s+", "", cleaned, flags=re.I).strip()
    cleaned = re.sub(r"[\-–—]\s*(easy apply|urgently hiring|sponsored|promoted).*$", "", cleaned, flags=re.I).strip()

    if cleaned.lower() in AGGREGATOR_GENERIC_COMPANIES:
        return default_name
    return cleaned if len(cleaned) >= 2 else default_name


# ==============================================================================
# 1. SimplyHired Scraper (https://www.simplyhired.com)
# ==============================================================================

def parse_simplyhired_listings(raw_content: str, base_url: str = "https://www.simplyhired.com", keyword: str = "") -> List[Dict[str, Any]]:
    """Extracts job postings from SimplyHired HTML / Markdown."""
    jobs: List[Dict[str, Any]] = []

    if "<html" in raw_content.lower() or "<div" in raw_content.lower():
        try:
            soup = BeautifulSoup(raw_content, "html.parser")
            cards = soup.select("[data-testid='searchSerpJob'], .SerpJob-jobCard, .job-item, article[data-jobkey], div.chakra-card")
            if not cards:
                cards = soup.find_all("li", class_=re.compile(r"SerpJob|job-card", re.I))

            for card in cards:
                card_text = card.get_text(separator=" ", strip=True)
                card_classes = " ".join(card.get("class", []))
                if is_sponsored_or_spam(card_text, card_classes):
                    continue

                # Title & URL
                title_elem = card.find(["h2", "h3", "a"], class_=re.compile(r"title|job-title|chakra-heading", re.I)) or card.find("a")
                if not title_elem:
                    continue

                title = title_elem.get_text(strip=True)
                link_elem = title_elem if title_elem.name == "a" else (title_elem.find("a") or card.find("a"))
                href = link_elem.get("href", "") if link_elem else ""
                full_url = urljoin(base_url, href) if href else base_url

                # Company
                comp_elem = card.find(["span", "div", "a"], class_=re.compile(r"company|employer|source", re.I))
                company_raw = comp_elem.get_text(strip=True) if comp_elem else ""
                company = clean_company_name(company_raw, "SimplyHired Employer")

                # Location
                loc_elem = card.find(["span", "div"], class_=re.compile(r"location|city|region", re.I))
                location = loc_elem.get_text(strip=True) if loc_elem else "Remote / US"

                if title and len(title) > 2 and full_url != base_url:
                    jobs.append({
                        "title": title,
                        "company": company,
                        "source_board": "SimplyHired",
                        "board_source": "SimplyHired",
                        "board_url": full_url,
                        "listing_url": full_url,
                        "location": location,
                    })
        except Exception as e:
            logger.debug(f"SimplyHired HTML parsing error: {e}")

    # Markdown Regex Fallback
    if not jobs:
        matches = re.findall(r"\[([^\]]+)\]\((/job/[^\)]+|https?://www\.simplyhired\.com/job/[^\)]+)\)", raw_content, re.I)
        for text, url in matches:
            full_url = urljoin(base_url, url)
            parts = [p.strip() for p in text.split(" - ") if p.strip()]
            title = parts[0] if parts else text
            company = parts[1] if len(parts) > 1 else "SimplyHired Employer"
            jobs.append({
                "title": title,
                "company": clean_company_name(company, "SimplyHired Employer"),
                "source_board": "SimplyHired",
                "board_source": "SimplyHired",
                "board_url": full_url,
                "listing_url": full_url,
                "location": "Remote",
            })

    return filter_jobs_by_keyword(jobs, keyword)


async def scrape_simplyhired(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes job postings from SimplyHired with absolute URL resolution.

    Args:
        keyword: Target role keyword (e.g. 'Frontend Developer').
        location: Geographic location or Remote.
        limit: Maximum number of jobs to return.

    Returns:
        List of standardized job dictionaries.
    """
    logger.info(f"🔍 [SimplyHired] Scraping keyword='{keyword}', location='{location}'...")
    base_url = "https://www.simplyhired.com"
    search_url = f"https://www.simplyhired.com/search?q={quote_plus(keyword)}&l={quote_plus(location)}"

    try:
        content = await fetch_page_content(search_url)
        if "[ANTI_BOT_BLOCKED]" in content or "[ERROR" in content:
            logger.warning("⚠️ [SimplyHired] Block or error detected.")
            return []

        jobs = parse_simplyhired_listings(content, base_url, keyword)
        logger.info(f"✅ [SimplyHired] Extracted {len(jobs)} jobs.")
        return jobs[:limit]
    except Exception as e:
        logger.error(f"❌ [SimplyHired] Failed: {e}", exc_info=True)
        return []


# ==============================================================================
# 2. Jobgether Scraper (https://jobgether.com)
# ==============================================================================

def parse_jobgether_listings(raw_content: str, base_url: str = "https://jobgether.com", keyword: str = "") -> List[Dict[str, Any]]:
    """Extracts job postings from Jobgether HTML / Markdown."""
    jobs: List[Dict[str, Any]] = []

    if "<html" in raw_content.lower() or "<div" in raw_content.lower():
        try:
            soup = BeautifulSoup(raw_content, "html.parser")
            cards = soup.select(".offer-card, .job-card, [data-testid='offer-item'], div[class*='offer']")
            if not cards:
                cards = soup.find_all("div", class_=re.compile(r"offer|card|job", re.I))

            for card in cards:
                card_text = card.get_text(separator=" ", strip=True)
                if is_sponsored_or_spam(card_text):
                    continue

                title_elem = card.find(["h2", "h3", "h4", "a"], class_=re.compile(r"title|heading|role", re.I)) or card.find("a")
                if not title_elem:
                    continue

                title = title_elem.get_text(strip=True)
                link_elem = title_elem if title_elem.name == "a" else (title_elem.find("a") or card.find("a"))
                href = link_elem.get("href", "") if link_elem else ""
                full_url = urljoin(base_url, href) if href else base_url

                comp_elem = card.find(["span", "div", "p"], class_=re.compile(r"company|recruiter|organization", re.I))
                company = clean_company_name(comp_elem.get_text(strip=True) if comp_elem else "", "Jobgether Employer")

                loc_elem = card.find(["span", "div"], class_=re.compile(r"location|city|country|remote", re.I))
                location = loc_elem.get_text(strip=True) if loc_elem else "100% Remote"

                if title and len(title) > 2 and full_url != base_url:
                    jobs.append({
                        "title": title,
                        "company": company,
                        "source_board": "Jobgether",
                        "board_source": "Jobgether",
                        "board_url": full_url,
                        "listing_url": full_url,
                        "location": location,
                    })
        except Exception as e:
            logger.debug(f"Jobgether HTML parsing error: {e}")

    # Markdown Regex Fallback
    if not jobs:
        matches = re.findall(r"\[([^\]]+)\]\((/offer/[^\)]+|https?://jobgether\.com/offer/[^\)]+)\)", raw_content, re.I)
        for text, url in matches:
            full_url = urljoin(base_url, url)
            parts = [p.strip() for p in text.split(" - ") if p.strip()]
            title = parts[0] if parts else text
            company = parts[1] if len(parts) > 1 else "Jobgether Employer"
            jobs.append({
                "title": title,
                "company": clean_company_name(company, "Jobgether Employer"),
                "source_board": "Jobgether",
                "board_source": "Jobgether",
                "board_url": full_url,
                "listing_url": full_url,
                "location": "Remote",
            })

    return filter_jobs_by_keyword(jobs, keyword)


async def scrape_jobgether(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes remote job listings from Jobgether with absolute URL resolution.

    Args:
        keyword: Target role keyword (e.g. 'DevOps Engineer').
        location: Target location or Remote.
        limit: Maximum jobs to return.

    Returns:
        List of standardized job dictionaries.
    """
    logger.info(f"🌐 [Jobgether] Scraping keyword='{keyword}'...")
    base_url = "https://jobgether.com"
    search_url = f"https://jobgether.com/search-offers?keyword={quote_plus(keyword)}"

    try:
        content = await fetch_page_content(search_url)
        if "[ANTI_BOT_BLOCKED]" in content or "[ERROR" in content:
            logger.warning("⚠️ [Jobgether] Block or error detected.")
            return []

        jobs = parse_jobgether_listings(content, base_url, keyword)
        logger.info(f"✅ [Jobgether] Extracted {len(jobs)} jobs.")
        return jobs[:limit]
    except Exception as e:
        logger.error(f"❌ [Jobgether] Failed: {e}", exc_info=True)
        return []


# ==============================================================================
# 3. Jooble Scraper (https://jooble.org)
# ==============================================================================

def parse_jooble_listings(raw_content: str, base_url: str = "https://jooble.org", keyword: str = "") -> List[Dict[str, Any]]:
    """Extracts job postings from Jooble HTML / Markdown."""
    jobs: List[Dict[str, Any]] = []

    if "<html" in raw_content.lower() or "<div" in raw_content.lower():
        try:
            soup = BeautifulSoup(raw_content, "html.parser")
            cards = soup.select("article[data-test-name='_jobCard'], .job-card, [data-test-name='jobCard'], article.vac-item")
            if not cards:
                cards = soup.find_all("article", class_=re.compile(r"job|vac|card", re.I))

            for card in cards:
                card_text = card.get_text(separator=" ", strip=True)
                if is_sponsored_or_spam(card_text):
                    continue

                title_elem = card.find(["h2", "h3", "a"], class_=re.compile(r"title|header|vacancy", re.I)) or card.find("a")
                if not title_elem:
                    continue

                title = title_elem.get_text(strip=True)
                link_elem = title_elem if title_elem.name == "a" else (title_elem.find("a") or card.find("a"))
                href = link_elem.get("href", "") if link_elem else ""
                full_url = urljoin(base_url, href) if href else base_url

                comp_elem = card.find(["span", "div", "p"], class_=re.compile(r"company|employer|source", re.I))
                company = clean_company_name(comp_elem.get_text(strip=True) if comp_elem else "", "Jooble Employer")

                loc_elem = card.find(["span", "div"], class_=re.compile(r"location|city|region", re.I))
                location = loc_elem.get_text(strip=True) if loc_elem else "Remote"

                if title and len(title) > 2 and full_url != base_url:
                    jobs.append({
                        "title": title,
                        "company": company,
                        "source_board": "Jooble",
                        "board_source": "Jooble",
                        "board_url": full_url,
                        "listing_url": full_url,
                        "location": location,
                    })
        except Exception as e:
            logger.debug(f"Jooble HTML parsing error: {e}")

    # Markdown Regex Fallback
    if not jobs:
        matches = re.findall(r"\[([^\]]+)\]\((/desc/[^\)]+|https?://[^/]*jooble\.org/desc/[^\)]+)\)", raw_content, re.I)
        for text, url in matches:
            full_url = urljoin(base_url, url)
            parts = [p.strip() for p in text.split(" - ") if p.strip()]
            title = parts[0] if parts else text
            company = parts[1] if len(parts) > 1 else "Jooble Employer"
            jobs.append({
                "title": title,
                "company": clean_company_name(company, "Jooble Employer"),
                "source_board": "Jooble",
                "board_source": "Jooble",
                "board_url": full_url,
                "listing_url": full_url,
                "location": "Remote",
            })

    return filter_jobs_by_keyword(jobs, keyword)


async def scrape_jooble(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes job postings from Jooble with regional domain adaptation.

    Args:
        keyword: Target role keyword (e.g. 'Data Scientist').
        location: Geographic location or Remote.
        limit: Maximum jobs to return.

    Returns:
        List of standardized job dictionaries.
    """
    logger.info(f"🔎 [Jooble] Scraping keyword='{keyword}', location='{location}'...")

    # Regional TLD adaptation
    if location and ("uk" in location.lower() or "united kingdom" in location.lower() or "london" in location.lower()):
        base_url = "https://uk.jooble.org"
        search_url = f"https://uk.jooble.org/SearchResult?ukw={quote_plus(keyword)}"
    else:
        base_url = "https://jooble.org"
        search_url = f"https://jooble.org/SearchResult?ukw={quote_plus(keyword)}&reg={quote_plus(location)}"

    try:
        content = await fetch_page_content(search_url)
        if "[ANTI_BOT_BLOCKED]" in content or "[ERROR" in content:
            logger.warning("⚠️ [Jooble] Block or error detected.")
            return []

        jobs = parse_jooble_listings(content, base_url, keyword)
        logger.info(f"✅ [Jooble] Extracted {len(jobs)} jobs.")
        return jobs[:limit]
    except Exception as e:
        logger.error(f"❌ [Jooble] Failed: {e}", exc_info=True)
        return []


# ==============================================================================
# 4. DynamiteJobs Scraper (https://dynamitejobs.com)
# ==============================================================================

def parse_dynamitejobs_listings(raw_content: str, base_url: str = "https://dynamitejobs.com", keyword: str = "") -> List[Dict[str, Any]]:
    """Extracts job postings from DynamiteJobs HTML / Markdown."""
    jobs: List[Dict[str, Any]] = []

    if "<html" in raw_content.lower() or "<div" in raw_content.lower():
        try:
            soup = BeautifulSoup(raw_content, "html.parser")
            cards = soup.select(".job-card, .job-item, [data-testid='job-card']")
            if not cards:
                cards = soup.find_all("a", href=re.compile(r"/remote-jobs/", re.I))
            if not cards:
                cards = soup.find_all("div", class_=re.compile(r"job|card|listing", re.I))

            seen_urls = set()
            for card in cards:
                card_text = card.get_text(separator=" ", strip=True)
                if is_sponsored_or_spam(card_text):
                    continue

                title_elem = card.find(["h1", "h2", "h3", "h4", "span"], class_=re.compile(r"title|heading|role", re.I)) or card
                if not title_elem:
                    continue

                title = title_elem.get_text(strip=True)
                link_elem = card if card.name == "a" else (card.find("a") or title_elem.find("a"))
                href = link_elem.get("href", "") if link_elem else ""
                full_url = urljoin(base_url, href) if href else base_url

                if full_url in seen_urls or full_url == base_url:
                    continue

                comp_elem = card.find(["span", "div", "p"], class_=re.compile(r"company|employer|client", re.I))
                company = clean_company_name(comp_elem.get_text(strip=True) if comp_elem else "", "DynamiteJobs Organization")

                loc_elem = card.find(["span", "div"], class_=re.compile(r"location|timezone|geo", re.I))
                location = loc_elem.get_text(strip=True) if loc_elem else "100% Remote"

                if title and len(title) > 2 and "/remote-jobs/" in full_url:
                    seen_urls.add(full_url)
                    jobs.append({
                        "title": title,
                        "company": company,
                        "source_board": "DynamiteJobs",
                        "board_source": "DynamiteJobs",
                        "board_url": full_url,
                        "listing_url": full_url,
                        "location": location,
                    })
        except Exception as e:
            logger.debug(f"DynamiteJobs HTML parsing error: {e}")

    # Markdown Regex Fallback
    if not jobs:
        matches = re.findall(r"\[([^\]]+)\]\((/remote-jobs/[^\)]+|https?://dynamitejobs\.com/remote-jobs/[^\)]+)\)", raw_content, re.I)
        for text, url in matches:
            full_url = urljoin(base_url, url)
            parts = [p.strip() for p in text.split(" at ") if p.strip()]
            if len(parts) >= 2:
                title, company = parts[0], parts[1]
            else:
                title = text
                company = "DynamiteJobs Organization"

            jobs.append({
                "title": title,
                "company": clean_company_name(company, "DynamiteJobs Organization"),
                "source_board": "DynamiteJobs",
                "board_source": "DynamiteJobs",
                "board_url": full_url,
                "listing_url": full_url,
                "location": "Remote",
            })

    return filter_jobs_by_keyword(jobs, keyword)


async def scrape_dynamitejobs(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes remote jobs from DynamiteJobs with absolute URL resolution.

    Args:
        keyword: Target role keyword (e.g. 'Full Stack Engineer').
        location: Target location or Remote.
        limit: Maximum jobs to return.

    Returns:
        List of standardized job dictionaries.
    """
    logger.info(f"🧨 [DynamiteJobs] Scraping keyword='{keyword}'...")
    base_url = "https://dynamitejobs.com"
    search_url = f"https://dynamitejobs.com/remote-jobs/search?q={quote_plus(keyword)}"

    try:
        content = await fetch_page_content(search_url)
        if "[ANTI_BOT_BLOCKED]" in content or "[ERROR" in content:
            logger.warning("⚠️ [DynamiteJobs] Block or error detected.")
            return []

        jobs = parse_dynamitejobs_listings(content, base_url, keyword)
        logger.info(f"✅ [DynamiteJobs] Extracted {len(jobs)} jobs.")
        return jobs[:limit]
    except Exception as e:
        logger.error(f"❌ [DynamiteJobs] Failed: {e}", exc_info=True)
        return []


async def scrape_careerbuilder(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes CareerBuilder."""
    logger.info(f"📁 [CareerBuilder] Scraping keyword='{keyword}'...")
    url = f"https://www.careerbuilder.com/jobs?keywords={quote_plus(keyword)}&location={quote_plus(location)}"
    try:
        content = await fetch_page_content(url)
        matches = re.findall(r"\[([^\]]+)\]\(((?:https?://www\.careerbuilder\.com)?/job/[^\)]+)\)", content, re.I)
        jobs = []
        for text, href in matches:
            full_url = urljoin("https://www.careerbuilder.com", href)
            parts = [p.strip() for p in text.split(" - ") if p.strip()]
            title = parts[0] if parts else text
            company = parts[1] if len(parts) > 1 else ""
            if not company and " at " in title:
                at_parts = title.split(" at ")
                title, company = at_parts[0].strip(), at_parts[1].strip()
            job_dict = {
                "title": title,
                "company": company or "CareerBuilder Employer",
                "source_board": "CareerBuilder",
                "board_source": "CareerBuilder",
                "listing_url": full_url,
                "board_url": full_url,
                "location": location,
            }
            if full_url not in [j["listing_url"] for j in jobs]:
                jobs.append(job_dict)
        return jobs[:limit]
    except Exception as e:
        logger.error(f"❌ [CareerBuilder] Error: {e}")
        return []


async def scrape_arise(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes Arise Work From Home."""
    from scrapers.niche_boards import scrape_arise as scrape_niche_arise
    return await scrape_niche_arise(keyword=keyword, location=location)


async def scrape_flexjobs(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes FlexJobs."""
    logger.info(f"🌟 [FlexJobs] Scraping keyword='{keyword}'...")
    url = f"https://www.flexjobs.com/search?search={quote_plus(keyword)}"
    try:
        content = await fetch_page_content(url)
        matches = re.findall(r"\[([^\]]+)\]\(((?:https?://www\.flexjobs\.com)?/jobs/[^\)]+)\)", content, re.I)
        jobs = []
        for text, href in matches:
            full_url = urljoin("https://www.flexjobs.com", href)
            parts = [p.strip() for p in text.split(" - ") if p.strip()]
            title = parts[0] if parts else text
            company = parts[1] if len(parts) > 1 else ""
            job_dict = {
                "title": title,
                "company": company or "FlexJobs Employer",
                "source_board": "FlexJobs",
                "board_source": "FlexJobs",
                "listing_url": full_url,
                "board_url": full_url,
                "location": "Remote",
            }
            if full_url not in [j["listing_url"] for j in jobs]:
                jobs.append(job_dict)
        return jobs[:limit]
    except Exception as e:
        logger.error(f"❌ [FlexJobs] Error: {e}")
        return []


# ==============================================================================
# 6. TheMuse Scraper
# ==============================================================================

async def scrape_themuse(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes TheMuse (Company Culture & High-Growth Jobs)."""
    logger.info(f"🏛️ [TheMuse] Scraping keyword='{keyword}'...")
    url = f"https://www.themuse.com/jobs?filter=true&keyword={quote_plus(keyword)}" if keyword else "https://www.themuse.com/jobs"
    try:
        content = await fetch_page_content(url)
        matches = re.findall(r"\[([^\]]+)\]\(((?:https?://www\.themuse\.com)?/jobs/[^\)]+)\)", content, re.I)
        jobs = []
        for text, href in matches:
            full_url = urljoin("https://www.themuse.com", href)
            parts = [p.strip() for p in text.split(" at ") if p.strip()]
            title = parts[0] if parts else text
            company = parts[1] if len(parts) > 1 else "TheMuse Partner Company"
            job_dict = {
                "title": title,
                "company": company,
                "source_board": "TheMuse",
                "board_source": "TheMuse",
                "listing_url": full_url,
                "board_url": full_url,
                "location": "Remote / Hybrid",
            }
            if is_valid_job(job_dict) and full_url not in [j["listing_url"] for j in jobs]:
                jobs.append(job_dict)
        return filter_jobs_by_keyword(jobs, keyword)[:limit]
    except Exception as e:
        logger.error(f"❌ [TheMuse] Error: {e}")
        return []


# ==============================================================================
# 7. Ladders Scraper
# ==============================================================================

async def scrape_ladders(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes Ladders ($100k+ Executive & Senior Roles)."""
    logger.info(f"🪜 [Ladders] Scraping keyword='{keyword}'...")
    url = f"https://www.theladders.com/jobs/search?keywords={quote_plus(keyword)}" if keyword else "https://www.theladders.com/jobs"
    try:
        content = await fetch_page_content(url)
        matches = re.findall(r"\[([^\]]+)\]\(((?:https?://www\.theladders\.com)?/jobs/[^\)]+)\)", content, re.I)
        jobs = []
        for text, href in matches:
            full_url = urljoin("https://www.theladders.com", href)
            parts = [p.strip() for p in text.split(" - ") if p.strip()]
            title = parts[0] if parts else text
            company = parts[1] if len(parts) > 1 else "Executive Employer"
            job_dict = {
                "title": title,
                "company": company,
                "board_source": "Ladders",
                "board_source": "Ladders",
                "listing_url": full_url,
                "board_url": full_url,
                "location": "Remote / Nationwide",
            }
            if is_valid_job(job_dict) and full_url not in [j["listing_url"] for j in jobs]:
                jobs.append(job_dict)
        return filter_jobs_by_keyword(jobs, keyword)[:limit]
    except Exception as e:
        logger.error(f"❌ [Ladders] Error: {e}")
        return []


# ==============================================================================
# 8. Jobserve Scraper
# ==============================================================================

async def scrape_jobserve(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes Jobserve (IT & Tech Contracting / Permanent)."""
    logger.info(f"🏢 [Jobserve] Scraping keyword='{keyword}'...")
    url = f"https://www.jobserve.com/gb/en/JobSearch.aspx?keywords={quote_plus(keyword)}" if keyword else "https://www.jobserve.com/"
    try:
        content = await fetch_page_content(url)
        matches = re.findall(r"\[([^\]]+)\]\(((?:https?://www\.jobserve\.com)?/[^\)]+)\)", content, re.I)
        jobs = []
        for text, href in matches:
            if "job" in href.lower() and len(href) > 10:
                full_url = urljoin("https://www.jobserve.com", href)
                parts = [p.strip() for p in text.split(" - ") if p.strip()]
                title = parts[0] if parts else text
                company = parts[1] if len(parts) > 1 else "IT Contract Partner"
                job_dict = {
                    "title": title,
                    "company": company,
                    "source_board": "Jobserve",
                    "board_source": "Jobserve",
                    "listing_url": full_url,
                    "board_url": full_url,
                    "location": "UK / Global Remote",
                }
                if is_valid_job(job_dict) and full_url not in [j["listing_url"] for j in jobs]:
                    jobs.append(job_dict)
        return filter_jobs_by_keyword(jobs, keyword)[:limit]
    except Exception as e:
        logger.error(f"❌ [Jobserve] Error: {e}")
        return []


# ==============================================================================
# 9. Arbeitnow & Jobicy Scrapers (Live Public Remote APIs)
# ==============================================================================

async def scrape_arbeitnow(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes verified live jobs from Arbeitnow public API."""
    norm_kw = normalize_search_keyword(keyword)
    logger.info(f"🌐 [Arbeitnow] Scraping keyword='{norm_kw}' (original='{keyword}')...")
    url = f"https://www.arbeitnow.com/api/job-board-api?search={quote_plus(norm_kw)}"
    jobs: List[Dict[str, Any]] = []
    try:
        async with httpx.AsyncClient(headers={"User-Agent": settings.DEFAULT_USER_AGENT}, timeout=12.0) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                data = resp.json().get("data", [])
                for item in data:
                    t = item.get("title", "")
                    c = item.get("company_name", "")
                    u = item.get("url", "")
                    loc = item.get("location", "Remote")
                    tags = item.get("tags") or []
                    desc = item.get("description", "")
                    job_dict = {
                        "title": t.strip(),
                        "company": c.strip(),
                        "board_source": "Arbeitnow",
                        "source_board": "Arbeitnow",
                        "listing_url": u,
                        "board_url": u,
                        "location": loc,
                        "tags": tags,
                        "description": desc,
                    }
                    if is_valid_job(job_dict) and not any(j["listing_url"] == u for j in jobs):
                        jobs.append(job_dict)
    except Exception as e:
        logger.debug(f"Arbeitnow fetch error: {e}")

    return filter_jobs_by_keyword(jobs, keyword)[:limit]


async def scrape_jobicy(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes verified live remote jobs from Jobicy public API."""
    norm_kw = normalize_search_keyword(keyword).lower()
    tag = ""
    if any(k in norm_kw for k in ["marketing", "marketer", "seo", "content", "growth", "copywriter"]):
        tag = "marketing"
    elif any(k in norm_kw for k in ["design", "ui", "ux"]):
        tag = "design-multimedia"
    elif any(k in norm_kw for k in ["data", "ai", "machine learning", "analyst"]):
        tag = "data-science"
    elif any(k in norm_kw for k in ["dev", "engineer", "software", "backend", "frontend"]):
        tag = "dev"

    logger.info(f"🌍 [Jobicy] Scraping keyword='{norm_kw}' (tag='{tag}')...")
    url = "https://jobicy.com/api/v2/remote-jobs?count=50"
    if tag:
        url += f"&tag={tag}"
    jobs: List[Dict[str, Any]] = []
    try:
        async with httpx.AsyncClient(headers={"User-Agent": settings.DEFAULT_USER_AGENT}, timeout=12.0) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                data = resp.json().get("jobs", [])
                for item in data:
                    t = item.get("jobTitle", "")
                    c = item.get("companyName", "")
                    u = item.get("url", "")
                    loc = item.get("jobGeo", "Remote")
                    tags = item.get("jobIndustry") or []
                    if isinstance(tags, str):
                        tags = [tags]
                    job_dict = {
                        "title": t.strip(),
                        "company": c.strip(),
                        "board_source": "Jobicy",
                        "source_board": "Jobicy",
                        "listing_url": u,
                        "board_url": u,
                        "location": loc,
                        "tags": tags,
                    }
                    if is_valid_job(job_dict) and not any(j["listing_url"] == u for j in jobs):
                        jobs.append(job_dict)
    except Exception as e:
        logger.debug(f"Jobicy fetch error: {e}")

    return filter_jobs_by_keyword(jobs, keyword)[:limit]



# ==============================================================================
# Concurrent Orchestration Wrapper: run_level_2_scrapers
# ==============================================================================

async def run_level_2_scrapers(keyword: str, location: str = "Remote") -> Dict[str, Any]:
    """Executes Level 2 Aggregator Scrapers (SimplyHired, Jobgether, Jooble, DynamiteJobs)
    concurrently using asyncio.gather(..., return_exceptions=True).

    Extracts leads, resolves absolute URLs, and saves immediately to StateManager.

    Args:
        keyword: Target job role / keyword.
        location: Geographic location or 'Remote'.

    Returns:
        Summary dict containing counts, board statuses, and total leads extracted.
    """
    logger.info("=" * 80)
    logger.info(f"🚀 Launching Level 2 Aggregators for keyword='{keyword}', location='{location}'...")
    logger.info("=" * 80)

    # Launch all 4 aggregator scrapers concurrently
    sh_task = scrape_simplyhired(keyword=keyword, location=location)
    jg_task = scrape_jobgether(keyword=keyword, location=location)
    jb_task = scrape_jooble(keyword=keyword, location=location)
    dj_task = scrape_dynamitejobs(keyword=keyword, location=location)

    results = await asyncio.gather(sh_task, jg_task, jb_task, dj_task, return_exceptions=True)

    board_results: Dict[str, List[Dict[str, Any]]] = {
        "SimplyHired": results[0] if isinstance(results[0], list) else [],
        "Jobgether": results[1] if isinstance(results[1], list) else [],
        "Jooble": results[2] if isinstance(results[2], list) else [],
        "DynamiteJobs": results[3] if isinstance(results[3], list) else [],
    }

    board_errors: Dict[str, Optional[str]] = {
        "SimplyHired": str(results[0]) if isinstance(results[0], Exception) else None,
        "Jobgether": str(results[1]) if isinstance(results[1], Exception) else None,
        "Jooble": str(results[2]) if isinstance(results[2], Exception) else None,
        "DynamiteJobs": str(results[3]) if isinstance(results[3], Exception) else None,
    }

    total_newly_added = 0
    summary_counts: Dict[str, int] = {}

    # Persist leads immediately to StateManager on a per-board basis
    for board_name, jobs in board_results.items():
        err = board_errors.get(board_name)
        if err:
            logger.error(f"❌ [{board_name}] Aggregator error: {err}")
            state_manager.update_board_status(
                board_name=board_name,
                status="failed",
                error=err,
            )
            summary_counts[board_name] = 0
            continue

        added_for_board = 0
        for job in jobs:
            if state_manager.add_extracted_job(job):
                added_for_board += 1

        total_newly_added += added_for_board
        summary_counts[board_name] = len(jobs)

        state_manager.update_board_status(
            board_name=board_name,
            status="completed",
            jobs_found=len(jobs),
        )
        logger.info(f"📊 [{board_name}] Scraped: {len(jobs)} leads | Newly Persisted: {added_for_board}")

    logger.info("=" * 80)
    logger.info(f"🎉 Level 2 Aggregators Finished! Total Jobs Extracted: {total_newly_added} newly persisted.")
    logger.info(f"Board Breakdown: {summary_counts}")
    logger.info("=" * 80)

    return {
        "status": "success",
        "keyword": keyword,
        "location": location,
        "boards_scraped": list(board_results.keys()),
        "jobs_found_per_board": summary_counts,
        "total_newly_persisted": total_newly_added,
        "total_session_jobs": state_manager.state.total_jobs_extracted if state_manager.state else total_newly_added,
    }


# ==============================================================================
# 10. LinkedIn Scraper (https://www.linkedin.com)
# ==============================================================================

def parse_linkedin_listings(raw_content: str, keyword: str = "") -> List[Dict[str, Any]]:
    """Extracts job postings from LinkedIn Guest Search API HTML."""
    jobs: List[Dict[str, Any]] = []
    try:
        soup = BeautifulSoup(raw_content, "html.parser")
        cards = soup.select("li, .base-search-card")
        for card in cards:
            title_elem = card.select_one(".base-search-card__title")
            comp_elem = card.select_one(".base-search-card__subtitle")
            loc_elem = card.select_one(".job-search-card__location")
            link_elem = card.select_one("a.base-card__full-link") or card.find("a", href=True)

            title = title_elem.get_text(strip=True) if title_elem else ""
            company = comp_elem.get_text(strip=True) if comp_elem else "LinkedIn Employer"
            location = loc_elem.get_text(strip=True) if loc_elem else "Remote"
            raw_href = link_elem.get("href", "") if link_elem else ""
            clean_href = raw_href.split("?")[0] if raw_href else ""

            if title and len(title) > 2 and clean_href.startswith("http"):
                job_dict = {
                    "title": title,
                    "company": clean_company_name(company, "LinkedIn Employer"),
                    "source_board": "LinkedIn",
                    "board_source": "LinkedIn",
                    "board_url": clean_href,
                    "listing_url": clean_href,
                    "location": location,
                }
                if not any(j["listing_url"] == clean_href for j in jobs):
                    jobs.append(job_dict)
    except Exception as e:
        logger.debug(f"LinkedIn parsing error: {e}")

    return filter_jobs_by_keyword(jobs, keyword)


async def scrape_linkedin(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes LinkedIn via public guest search API with zero login requirements."""
    logger.info(f"💼 [LinkedIn] Scraping keyword='{keyword}', location='{location}'...")
    url = f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords={quote_plus(keyword)}&location={quote_plus(location)}"
    try:
        from curl_cffi import requests as cffi_requests
        resp = await asyncio.to_thread(cffi_requests.get, url, impersonate="chrome120", timeout=12)
        if resp.status_code == 200 and resp.text:
            jobs = parse_linkedin_listings(resp.text, keyword)
            logger.info(f"✅ [LinkedIn] Extracted {len(jobs)} jobs.")
            return jobs[:limit]
        content = await fetch_page_content(url)
        jobs = parse_linkedin_listings(content, keyword)
        return jobs[:limit]
    except Exception as e:
        logger.error(f"❌ [LinkedIn] Failed: {e}")
        return []


# ==============================================================================
# 11. Indeed Scraper (https://www.indeed.com)
# ==============================================================================

def parse_indeed_listings(raw_content: str, keyword: str = "") -> List[Dict[str, Any]]:
    """Extracts job postings from Indeed HTML / Mosaic Data."""
    jobs: List[Dict[str, Any]] = []
    # 1. Try Mosaic JSON provider
    try:
        soup = BeautifulSoup(raw_content, "html.parser")
        script = soup.find("script", id=re.compile(r"mosaic-data"))
        if script and script.string:
            m = re.search(r"window\.mosaic\.providerData\[\"mosaic-provider-jobcards\"\]\s*=\s*(\{.*?\});", script.string)
            if m:
                data = json.loads(m.group(1))
                results = data.get("metaData", {}).get("mosaicProviderJobCardsModel", {}).get("results", [])
                for it in results:
                    title = it.get("title")
                    comp = it.get("company")
                    loc = it.get("formattedLocation", "Remote")
                    jk = it.get("jobkey")
                    if title and jk:
                        full_url = f"https://www.indeed.com/viewjob?jk={jk}"
                        job_dict = {
                            "title": str(title).strip(),
                            "company": clean_company_name(str(comp).strip() if comp else "", "Indeed Employer"),
                            "source_board": "Indeed",
                            "board_source": "Indeed",
                            "board_url": full_url,
                            "listing_url": full_url,
                            "location": str(loc).strip(),
                        }
                        if not any(j["listing_url"] == full_url for j in jobs):
                            jobs.append(job_dict)
    except Exception as e:
        logger.debug(f"Indeed JSON parsing error: {e}")

    # 2. HTML fallback
    if not jobs:
        try:
            soup = BeautifulSoup(raw_content, "html.parser")
            cards = soup.select(".job_seen_beacon, td.resultContent, div.result")
            for c in cards:
                t_elem = c.select_one("h2.jobTitle, a[data-jk]")
                comp_elem = c.select_one("[data-testid='company-name'], span.companyName")
                loc_elem = c.select_one("[data-testid='text-location'], div.companyLocation")
                link_elem = c.find("a", href=True)

                title = t_elem.get_text(strip=True) if t_elem else ""
                company = comp_elem.get_text(strip=True) if comp_elem else "Indeed Employer"
                location = loc_elem.get_text(strip=True) if loc_elem else "Remote"

                link = ""
                if link_elem and "jk=" in link_elem["href"]:
                    jk = link_elem["href"].split("jk=")[1].split("&")[0]
                    link = f"https://www.indeed.com/viewjob?jk={jk}"
                elif link_elem and link_elem.get("data-jk"):
                    link = f"https://www.indeed.com/viewjob?jk={link_elem['data-jk']}"
                elif link_elem:
                    link = urljoin("https://www.indeed.com", link_elem["href"])

                if title and link:
                    job_dict = {
                        "title": title,
                        "company": clean_company_name(company, "Indeed Employer"),
                        "source_board": "Indeed",
                        "board_source": "Indeed",
                        "board_url": link,
                        "listing_url": link,
                        "location": location,
                    }
                    if not any(j["listing_url"] == link for j in jobs):
                        jobs.append(job_dict)
        except Exception as e:
            logger.debug(f"Indeed HTML parsing error: {e}")

    return filter_jobs_by_keyword(jobs, keyword)


async def scrape_indeed(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes Indeed using Chrome impersonation TLS fingerprinting."""
    logger.info(f"🔎 [Indeed] Scraping keyword='{keyword}', location='{location}'...")
    url = f"https://www.indeed.com/jobs?q={quote_plus(keyword)}&l={quote_plus(location)}"
    try:
        from curl_cffi import requests as cffi_requests
        resp = await asyncio.to_thread(cffi_requests.get, url, impersonate="chrome120", timeout=12)
        if resp.status_code == 200 and resp.text:
            jobs = parse_indeed_listings(resp.text, keyword)
            logger.info(f"✅ [Indeed] Extracted {len(jobs)} jobs.")
            return jobs[:limit]
        content = await fetch_page_content(url)
        jobs = parse_indeed_listings(content, keyword)
        return jobs[:limit]
    except Exception as e:
        logger.error(f"❌ [Indeed] Failed: {e}")
        return []


# ==============================================================================
# 12. Talent.com Scraper (https://www.talent.com)
# ==============================================================================

def parse_talent_listings(raw_content: str, keyword: str = "") -> List[Dict[str, Any]]:
    """Extracts job postings from Talent.com HTML."""
    jobs: List[Dict[str, Any]] = []
    try:
        soup = BeautifulSoup(raw_content, "html.parser")
        articles = soup.find_all("article", class_=re.compile(r"JobCard_card"))
        for art in articles:
            p = art.parent
            job_id = p.get("data-job-id") or p.get("data-new-id") if p else None
            t_elem = art.find("h2")
            title = t_elem.get_text(strip=True) if t_elem else ""

            heading = art.find("div", class_=re.compile(r"JobCard_heading"))
            comp = "Talent.com Employer"
            loc = "Remote / US"
            if heading:
                parts = [x.strip() for x in heading.get_text(separator="|").split("|") if x.strip() and x.strip() != "·"]
                if len(parts) > 1:
                    comp = parts[1]
                if len(parts) > 2:
                    loc = parts[2]

            full_url = f"https://www.talent.com/view?id={job_id}" if job_id else ""
            if not full_url:
                a_elem = art.find("a", href=True)
                if a_elem:
                    full_url = urljoin("https://www.talent.com", a_elem["href"])

            if title and full_url:
                job_dict = {
                    "title": title,
                    "company": clean_company_name(comp, "Talent.com Employer"),
                    "source_board": "Talent.com",
                    "board_source": "Talent.com",
                    "board_url": full_url,
                    "listing_url": full_url,
                    "location": loc,
                }
                if not any(j["listing_url"] == full_url for j in jobs):
                    jobs.append(job_dict)
    except Exception as e:
        logger.debug(f"Talent.com parsing error: {e}")

    return filter_jobs_by_keyword(jobs, keyword)


async def scrape_talent(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes Talent.com global aggregator."""
    logger.info(f"🌐 [Talent.com] Scraping keyword='{keyword}', location='{location}'...")
    url = f"https://www.talent.com/jobs?k={quote_plus(keyword)}&l={quote_plus(location)}"
    try:
        from curl_cffi import requests as cffi_requests
        resp = await asyncio.to_thread(cffi_requests.get, url, impersonate="chrome120", timeout=12)
        if resp.status_code == 200 and resp.text:
            jobs = parse_talent_listings(resp.text, keyword)
            logger.info(f"✅ [Talent.com] Extracted {len(jobs)} jobs.")
            return jobs[:limit]
        content = await fetch_page_content(url)
        jobs = parse_talent_listings(content, keyword)
        return jobs[:limit]
    except Exception as e:
        logger.error(f"❌ [Talent.com] Failed: {e}")
        return []

