"""
Level 3 Niche & Remote Job Board Scrapers:
1. Arise Work From Home (https://www.ariseworkfromhome.com/)
2. Maxibestof (https://maxibestof.one/jobs)
3. Dice (https://www.dice.com/jobs)
4. Game Devs of Color (https://www.gamedevsofcolor.org/jobs)
5. OnlineJobs.ph (https://www.onlinejobs.ph/jobseekers/jobsearch)
6. Techcareers (https://www.techcareers.com/jobs/search)
7. GamesJobsDirect (https://www.gamesjobsdirect.com/results)

Features JSON/HTML hybrid extraction, post-fetch keyword filtering,
aggressive error shielding for high-security boards, and throttled concurrency via asyncio.Semaphore.
"""

import asyncio
from datetime import datetime
import json
import re
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus, urljoin

from bs4 import BeautifulSoup
from config.settings import settings
from config.logging_config import get_logger
from tools.web_navigator import fetch_page_content
from utils.state_manager import state_manager
from utils.keyword_matcher import filter_jobs_by_keyword

logger = get_logger("Level3Niche")


def try_parse_json_payload(content: str) -> Optional[List[Dict[str, Any]]]:
    """Attempts to extract job listings from raw JSON or embedded JSON script tags."""
    if not content or not content.strip():
        return None

    # Check if content itself is pure JSON
    stripped = content.strip()
    if (stripped.startswith("{") and stripped.endswith("}")) or (stripped.startswith("[") and stripped.endswith("]")):
        try:
            data = json.loads(stripped)
            items = data if isinstance(data, list) else data.get("jobs") or data.get("data") or data.get("results") or []
            if isinstance(items, list) and items:
                extracted = []
                for it in items:
                    if isinstance(it, dict):
                        title = it.get("title") or it.get("jobTitle") or it.get("name")
                        company = it.get("company") or it.get("companyName") or it.get("employer") or "Hiring Company"
                        url = it.get("url") or it.get("link") or it.get("jobUrl") or ""
                        if title:
                            extracted.append({
                                "title": str(title).strip(),
                                "company": str(company).strip(),
                                "board_url": str(url).strip(),
                                "location": it.get("location", "Remote"),
                            })
                if extracted:
                    return extracted
        except Exception:
            pass

    # Check for embedded __NEXT_DATA__ or application/ld+json
    if "__NEXT_DATA__" in content:
        try:
            match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', content, re.DOTALL)
            if match:
                data = json.loads(match.group(1))
                page_props = data.get("props", {}).get("pageProps", {})
                jobs_data = page_props.get("jobs") or page_props.get("results") or page_props.get("initialState", {}).get("jobs", [])
                if isinstance(jobs_data, list) and jobs_data:
                    extracted = []
                    for it in jobs_data:
                        if isinstance(it, dict):
                            title = it.get("title") or it.get("jobTitle")
                            company = it.get("company") or it.get("companyName") or "Hiring Company"
                            url = it.get("url") or it.get("detailUrl") or ""
                            if title:
                                extracted.append({
                                    "title": str(title).strip(),
                                    "company": str(company).strip(),
                                    "board_url": str(url).strip(),
                                    "location": it.get("location", "Remote"),
                                })
                    if extracted:
                        return extracted
        except Exception:
            pass

    return None


# ==============================================================================
# 1. Arise Work From Home (https://www.ariseworkfromhome.com)
# ==============================================================================

def parse_arise_listings(raw_content: str, keyword: str = "") -> List[Dict[str, Any]]:
    """Extracts opportunities from Arise Work From Home with post-fetch filtering."""
    base_url = "https://www.ariseworkfromhome.com"
    jobs: List[Dict[str, Any]] = []

    if "<html" in raw_content.lower() or "<div" in raw_content.lower():
        try:
            soup = BeautifulSoup(raw_content, "html.parser")
            cards = soup.select(".opportunity-card, .job-item, article, div.service-card, a.opportunity-link")
            if not cards:
                cards = soup.find_all(["div", "section"], class_=re.compile(r"opportunity|role|service|job", re.I))

            for card in cards:
                title_elem = card.find(["h1", "h2", "h3", "h4", "a", "strong"], class_=re.compile(r"title|header|name", re.I)) or card.find(["h2", "h3", "a"])
                if not title_elem:
                    continue

                title = title_elem.get_text(strip=True)
                link_elem = card if card.name == "a" else (card.find("a") or title_elem.find("a"))
                href = link_elem.get("href", "") if link_elem else ""
                full_url = urljoin(base_url, href) if href else base_url

                if title and len(title) > 3 and "opportunity" in title.lower() or len(title) > 5:
                    jobs.append({
                        "title": title,
                        "company": "Arise Virtual Solutions / Partner Client",
                        "source_board": "Arise Work From Home",
                        "board_source": "Arise Work From Home",
                        "board_url": full_url,
                        "listing_url": full_url,
                        "location": "100% Remote / Work From Home",
                    })
        except Exception as e:
            logger.debug(f"Arise HTML parsing error: {e}")

    # Fallback to general opportunity listing
    if not jobs:
        matches = re.findall(r"\[([^\]]+)\]\((https?://(?:www\.)?ariseworkfromhome\.com/[^\)]+)\)", raw_content, re.I)
        for text, url in matches:
            if len(text) > 4 and not any(nav in text.lower() for nav in ["home", "about", "privacy", "terms", "contact"]):
                jobs.append({
                    "title": text.strip(),
                    "company": "Arise Virtual Solutions",
                    "source_board": "Arise Work From Home",
                    "board_source": "Arise Work From Home",
                    "board_url": url,
                    "listing_url": url,
                    "location": "100% Remote",
                })

    return filter_jobs_by_keyword(jobs, keyword)


async def scrape_arise(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes remote customer and tech opportunities from Arise Work From Home."""
    logger.info(f"🏠 [Arise] Scraping opportunities for keyword='{keyword}'...")
    target_url = "https://www.ariseworkfromhome.com/"

    try:
        content = await fetch_page_content(target_url)
        if "[ANTI_BOT_BLOCKED]" in content or "[ERROR" in content:
            logger.warning("⚠️ [Arise] Block or error detected.")
            return []

        jobs = parse_arise_listings(content, keyword)
        logger.info(f"✅ [Arise] Extracted {len(jobs)} opportunities.")
        return jobs[:limit]
    except Exception as e:
        logger.error(f"❌ [Arise] Failed: {e}", exc_info=True)
        return []


# ==============================================================================
# 2. Maxibestof (https://maxibestof.one/jobs)
# ==============================================================================

def parse_maxibestof_listings(raw_content: str, keyword: str = "") -> List[Dict[str, Any]]:
    """Extracts curated design & tech jobs from Maxibestof."""
    base_url = "https://maxibestof.one"
    jobs: List[Dict[str, Any]] = []

    if "<html" in raw_content.lower() or "<div" in raw_content.lower():
        try:
            soup = BeautifulSoup(raw_content, "html.parser")
            cards = soup.select(".job-row, .job-card, .job-item, article, a[href*='/jobs/']")
            if not cards:
                cards = soup.find_all("div", class_=re.compile(r"job|listing", re.I))

            seen_urls = set()
            for card in cards:
                title_elem = card.find(["h1", "h2", "h3", "h4", "span"], class_=re.compile(r"title|name|role", re.I)) or card
                if not title_elem:
                    continue

                title = title_elem.get_text(strip=True)
                link_elem = card if card.name == "a" else (card.find("a") or title_elem.find("a"))
                href = link_elem.get("href", "") if link_elem else ""
                full_url = urljoin(base_url, href) if href else base_url

                if full_url in seen_urls or full_url == base_url or not href:
                    continue

                comp_elem = card.find(["span", "div", "p"], class_=re.compile(r"company|studio|author|employer", re.I))
                company = comp_elem.get_text(strip=True) if comp_elem else "Maxibestof Curated Studio"

                loc_elem = card.find(["span", "div"], class_=re.compile(r"location|tag|badge", re.I))
                location = loc_elem.get_text(strip=True) if loc_elem else "Remote"

                if title and len(title) > 2:
                    seen_urls.add(full_url)
                    jobs.append({
                        "title": title,
                        "company": company,
                        "source_board": "Maxibestof",
                        "board_source": "Maxibestof",
                        "board_url": full_url,
                        "listing_url": full_url,
                        "location": location,
                    })
        except Exception as e:
            logger.debug(f"Maxibestof HTML parsing error: {e}")

    # Markdown Regex Fallback
    if not jobs:
        matches = re.findall(r"\[([^\]]+)\]\((/jobs/[^\)]+|https?://maxibestof\.one/jobs/[^\)]+)\)", raw_content, re.I)
        for text, url in matches:
            full_url = urljoin(base_url, url)
            parts = [p.strip() for p in text.split(" - ") if p.strip()]
            title = parts[0] if parts else text
            company = parts[1] if len(parts) > 1 else "Maxibestof Curated Studio"
            jobs.append({
                "title": title,
                "company": company,
                "source_board": "Maxibestof",
                "board_source": "Maxibestof",
                "board_url": full_url,
                "listing_url": full_url,
                "location": "Remote",
            })

    return filter_jobs_by_keyword(jobs, keyword)


async def scrape_maxibestof(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes curated design, UI/UX, and creative tech jobs from Maxibestof."""
    logger.info(f"🎨 [Maxibestof] Scraping curated jobs for keyword='{keyword}'...")
    target_url = "https://maxibestof.one/jobs"

    try:
        content = await fetch_page_content(target_url)
        if "[ANTI_BOT_BLOCKED]" in content or "[ERROR" in content:
            logger.warning("⚠️ [Maxibestof] Block or error detected.")
            return []

        jobs = parse_maxibestof_listings(content, keyword)
        logger.info(f"✅ [Maxibestof] Extracted {len(jobs)} jobs.")
        return jobs[:limit]
    except Exception as e:
        logger.error(f"❌ [Maxibestof] Failed: {e}", exc_info=True)
        return []


# ==============================================================================
# 3. Dice (https://www.dice.com)
# ==============================================================================

def parse_dice_listings(raw_content: str, keyword: str = "") -> List[Dict[str, Any]]:
    """Extracts tech job postings from Dice HTML, JSON, or Markdown."""
    base_url = "https://www.dice.com"
    jobs: List[Dict[str, Any]] = []

    # 1. Try JSON payload extraction
    json_jobs = try_parse_json_payload(raw_content)
    if json_jobs:
        for j in json_jobs:
            jobs.append({
                "title": j["title"],
                "company": j["company"],
                "source_board": "Dice",
                "board_source": "Dice",
                "board_url": urljoin(base_url, j["board_url"]),
                "listing_url": urljoin(base_url, j["board_url"]),
                "location": j.get("location", "Remote"),
            })
        return jobs

    # 2. Try HTML Parsing
    if "<html" in raw_content.lower() or "<div" in raw_content.lower():
        try:
            soup = BeautifulSoup(raw_content, "html.parser")
            cards = soup.select("d-card, [data-cy='card-container'], .card, .search-card, div[class*='card_container']")
            if not cards:
                cards = soup.find_all("div", class_=re.compile(r"card|search-result|job-item", re.I))

            for card in cards:
                title_elem = card.find(["a", "h2", "h3", "h4", "h5"], class_=re.compile(r"title|card-title-link", re.I)) or card.find("a")
                if not title_elem:
                    continue

                title = title_elem.get_text(strip=True)
                link_elem = title_elem if title_elem.name == "a" else (title_elem.find("a") or card.find("a"))
                href = link_elem.get("href", "") if link_elem else ""
                full_url = urljoin(base_url, href) if href else base_url

                comp_elem = card.find(["span", "div", "a"], class_=re.compile(r"company|employer|posted-by", re.I))
                company = comp_elem.get_text(strip=True) if comp_elem else "Tech Employer on Dice"

                loc_elem = card.find(["span", "div"], class_=re.compile(r"location|job-location", re.I))
                location = loc_elem.get_text(strip=True) if loc_elem else "Remote / US"

                if title and len(title) > 2 and full_url != base_url:
                    jobs.append({
                        "title": title,
                        "company": company,
                        "source_board": "Dice",
                        "board_source": "Dice",
                        "board_url": full_url,
                        "listing_url": full_url,
                        "location": location,
                    })
        except Exception as e:
            logger.debug(f"Dice HTML parsing error: {e}")

    # 3. Markdown Regex Fallback
    if not jobs:
        matches = re.findall(r"\[([^\]]+)\]\((/job-detail/[^\)]+|https?://www\.dice\.com/job-detail/[^\)]+)\)", raw_content, re.I)
        for text, url in matches:
            full_url = urljoin(base_url, url)
            parts = [p.strip() for p in text.split(" - ") if p.strip()]
            title = parts[0] if parts else text
            company = parts[1] if len(parts) > 1 else "Tech Employer on Dice"
            jobs.append({
                "title": title,
                "company": company,
                "source_board": "Dice",
                "board_source": "Dice",
                "board_url": full_url,
                "listing_url": full_url,
                "location": "Remote",
            })

    return filter_jobs_by_keyword(jobs, keyword)


async def scrape_dice(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes tech jobs from Dice with error shielding against anti-bot challenges."""
    logger.info(f"🎲 [Dice] Scraping keyword='{keyword}', location='{location}'...")
    search_url = f"https://www.dice.com/jobs?q={quote_plus(keyword)}&location={quote_plus(location)}"

    try:
        content = await fetch_page_content(search_url)
        if "[ANTI_BOT_BLOCKED]" in content or "[ERROR" in content:
            logger.warning("⚠️ [Dice] Anti-bot block encountered (Cloudflare/DataDome). Shielding pipeline.")
            return []

        jobs = parse_dice_listings(content, keyword)
        logger.info(f"✅ [Dice] Extracted {len(jobs)} jobs.")
        return jobs[:limit]
    except Exception as e:
        logger.warning(f"⚠️ [Dice] Handled scraper exception: {e}")
        return []


# ==============================================================================
# 4. Game Devs of Color (https://www.gamedevsofcolor.org/jobs)
# ==============================================================================

def parse_gamedevsofcolor_listings(raw_content: str, keyword: str = "") -> List[Dict[str, Any]]:
    """Extracts job postings from Game Devs of Color."""
    base_url = "https://www.gamedevsofcolor.org"
    jobs: List[Dict[str, Any]] = []

    if "<html" in raw_content.lower() or "<div" in raw_content.lower():
        try:
            soup = BeautifulSoup(raw_content, "html.parser")
            cards = soup.select(".job-item, .job-card, .job-post, article, div.summary-item")
            if not cards:
                cards = soup.find_all("div", class_=re.compile(r"job|post|summary", re.I))

            for card in cards:
                title_elem = card.find(["h1", "h2", "h3", "h4", "a"], class_=re.compile(r"title|heading", re.I)) or card.find("a")
                if not title_elem:
                    continue

                title = title_elem.get_text(strip=True)
                link_elem = title_elem if title_elem.name == "a" else (title_elem.find("a") or card.find("a"))
                href = link_elem.get("href", "") if link_elem else ""
                full_url = urljoin(base_url, href) if href else base_url

                comp_elem = card.find(["span", "div", "p"], class_=re.compile(r"company|studio|employer|organization", re.I))
                company = comp_elem.get_text(strip=True) if comp_elem else "Game Studio Partner"

                loc_elem = card.find(["span", "div"], class_=re.compile(r"location|geo", re.I))
                location = loc_elem.get_text(strip=True) if loc_elem else "Remote"

                if title and len(title) > 2 and full_url != base_url:
                    jobs.append({
                        "title": title,
                        "company": company,
                        "source_board": "Game Devs of Color",
                        "board_source": "Game Devs of Color",
                        "board_url": full_url,
                        "listing_url": full_url,
                        "location": location,
                    })
        except Exception as e:
            logger.debug(f"Game Devs of Color HTML parsing error: {e}")

    # Markdown Regex Fallback
    if not jobs:
        matches = re.findall(r"\[([^\]]+)\]\((https?://(?:www\.)?gamedevsofcolor\.org/jobs/[^\)]+)\)", raw_content, re.I)
        for text, url in matches:
            parts = [p.strip() for p in text.split(" - ") if p.strip()]
            title = parts[0] if parts else text
            company = parts[1] if len(parts) > 1 else "Game Studio Partner"
            jobs.append({
                "title": title,
                "company": company,
                "source_board": "Game Devs of Color",
                "board_source": "Game Devs of Color",
                "board_url": url,
                "listing_url": url,
                "location": "Remote",
            })

    return filter_jobs_by_keyword(jobs, keyword)


async def scrape_gamedevsofcolor(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes gaming & interactive media jobs from Game Devs of Color."""
    logger.info(f"🎮 [Game Devs of Color] Scraping keyword='{keyword}'...")
    target_url = "https://www.gamedevsofcolor.org/jobs"

    try:
        content = await fetch_page_content(target_url)
        if "[ANTI_BOT_BLOCKED]" in content or "[ERROR" in content:
            logger.warning("⚠️ [Game Devs of Color] Block or error detected.")
            return []

        jobs = parse_gamedevsofcolor_listings(content, keyword)
        logger.info(f"✅ [Game Devs of Color] Extracted {len(jobs)} jobs.")
        return jobs[:limit]
    except Exception as e:
        logger.error(f"❌ [Game Devs of Color] Failed: {e}", exc_info=True)
        return []


# ==============================================================================
# 5. OnlineJobs.ph (https://www.onlinejobs.ph)
# ==============================================================================

def parse_onlinejobs_listings(raw_content: str, keyword: str = "") -> List[Dict[str, Any]]:
    """Extracts remote job postings from OnlineJobs.ph."""
    base_url = "https://www.onlinejobs.ph"
    jobs: List[Dict[str, Any]] = []

    if "<html" in raw_content.lower() or "<div" in raw_content.lower():
        try:
            soup = BeautifulSoup(raw_content, "html.parser")
            cards = soup.select(".jobpost-cat, .job-details, div[class*='job-post'], div.jobpost")
            if not cards:
                cards = soup.find_all("div", class_=re.compile(r"jobpost|job-details|latest-job", re.I))

            for card in cards:
                title_elem = card.find(["h2", "h3", "h4", "a"], class_=re.compile(r"title|job-title|heading", re.I)) or card.find("a")
                if not title_elem:
                    continue

                title = title_elem.get_text(strip=True)
                link_elem = title_elem if title_elem.name == "a" else (title_elem.find("a") or card.find("a"))
                href = link_elem.get("href", "") if link_elem else ""
                full_url = urljoin(base_url, href) if href else base_url

                comp_elem = card.find(["span", "div", "p"], class_=re.compile(r"company|client|employer|posted", re.I))
                company = comp_elem.get_text(strip=True) if comp_elem else "OnlineJobs Client"

                loc_elem = card.find(["span", "div"], class_=re.compile(r"type|salary|wage", re.I))
                location = loc_elem.get_text(strip=True) if loc_elem else "100% Remote"

                if title and len(title) > 2 and "/jobseekers/job/" in full_url:
                    jobs.append({
                        "title": title,
                        "company": company,
                        "source_board": "OnlineJobs.ph",
                        "board_source": "OnlineJobs.ph",
                        "board_url": full_url,
                        "listing_url": full_url,
                        "location": "Remote",
                    })
        except Exception as e:
            logger.debug(f"OnlineJobs.ph HTML parsing error: {e}")

    # Markdown Regex Fallback
    if not jobs:
        matches = re.findall(r"\[([^\]]+)\]\((/jobseekers/job/[^\)]+|https?://www\.onlinejobs\.ph/jobseekers/job/[^\)]+)\)", raw_content, re.I)
        for text, url in matches:
            full_url = urljoin(base_url, url)
            jobs.append({
                "title": text.strip(),
                "company": "OnlineJobs.ph Client",
                "source_board": "OnlineJobs.ph",
                "board_source": "OnlineJobs.ph",
                "board_url": full_url,
                "listing_url": full_url,
                "location": "Remote",
            })

    return filter_jobs_by_keyword(jobs, keyword)


async def scrape_onlinejobs(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes remote tech & developer roles from OnlineJobs.ph with aggressive error shielding."""
    logger.info(f"🇵🇭 [OnlineJobs.ph] Scraping keyword='{keyword}'...")
    search_url = f"https://www.onlinejobs.ph/jobseekers/jobsearch?jobkeyword={quote_plus(keyword)}"

    try:
        content = await fetch_page_content(search_url)
        if "[ANTI_BOT_BLOCKED]" in content or "[ERROR" in content:
            logger.warning("⚠️ [OnlineJobs.ph] Bot protection triggered (403/Cloudflare). Shielding pipeline.")
            return []

        jobs = parse_onlinejobs_listings(content, keyword)
        logger.info(f"✅ [OnlineJobs.ph] Extracted {len(jobs)} jobs.")
        return jobs[:limit]
    except Exception as e:
        logger.warning(f"⚠️ [OnlineJobs.ph] Handled scraper exception: {e}")
        return []


# ==============================================================================
# 6. Techcareers (https://www.techcareers.com)
# ==============================================================================

def parse_techcareers_listings(raw_content: str, keyword: str = "") -> List[Dict[str, Any]]:
    """Extracts job postings from Techcareers."""
    base_url = "https://www.techcareers.com"
    jobs: List[Dict[str, Any]] = []

    if "<html" in raw_content.lower() or "<div" in raw_content.lower():
        try:
            soup = BeautifulSoup(raw_content, "html.parser")
            cards = soup.select(".job-result, .job-item, .search-result, article, div.job-card")
            if not cards:
                cards = soup.find_all("div", class_=re.compile(r"job-result|job-item|listing", re.I))

            for card in cards:
                title_elem = card.find(["h2", "h3", "h4", "a"], class_=re.compile(r"title|job-title", re.I)) or card.find("a")
                if not title_elem:
                    continue

                title = title_elem.get_text(strip=True)
                link_elem = title_elem if title_elem.name == "a" else (title_elem.find("a") or card.find("a"))
                href = link_elem.get("href", "") if link_elem else ""
                full_url = urljoin(base_url, href) if href else base_url

                comp_elem = card.find(["span", "div", "p"], class_=re.compile(r"company|employer", re.I))
                company = comp_elem.get_text(strip=True) if comp_elem else "Tech Employer"

                loc_elem = card.find(["span", "div"], class_=re.compile(r"location|city", re.I))
                location = loc_elem.get_text(strip=True) if loc_elem else "Remote / US"

                if title and len(title) > 2 and full_url != base_url:
                    jobs.append({
                        "title": title,
                        "company": company,
                        "source_board": "Techcareers",
                        "board_source": "Techcareers",
                        "board_url": full_url,
                        "listing_url": full_url,
                        "location": location,
                    })
        except Exception as e:
            logger.debug(f"Techcareers HTML parsing error: {e}")

    # Markdown Regex Fallback
    if not jobs:
        matches = re.findall(r"\[([^\]]+)\]\((/job/[^\)]+|https?://www\.techcareers\.com/job/[^\)]+)\)", raw_content, re.I)
        for text, url in matches:
            full_url = urljoin(base_url, url)
            parts = [p.strip() for p in text.split(" - ") if p.strip()]
            title = parts[0] if parts else text
            company = parts[1] if len(parts) > 1 else "Tech Employer"
            jobs.append({
                "title": title,
                "company": company,
                "source_board": "Techcareers",
                "board_source": "Techcareers",
                "board_url": full_url,
                "listing_url": full_url,
                "location": "Remote",
            })

    return filter_jobs_by_keyword(jobs, keyword)


async def scrape_techcareers(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes technology roles from Techcareers."""
    logger.info(f"💻 [Techcareers] Scraping keyword='{keyword}', location='{location}'...")
    search_url = f"https://www.techcareers.com/jobs/search?k={quote_plus(keyword)}&l={quote_plus(location)}"

    try:
        content = await fetch_page_content(search_url)
        if "[ANTI_BOT_BLOCKED]" in content or "[ERROR" in content:
            logger.warning("⚠️ [Techcareers] Block or error detected.")
            return []

        jobs = parse_techcareers_listings(content, keyword)
        logger.info(f"✅ [Techcareers] Extracted {len(jobs)} jobs.")
        return jobs[:limit]
    except Exception as e:
        logger.error(f"❌ [Techcareers] Failed: {e}", exc_info=True)
        return []


# ==============================================================================
# 7. GamesJobsDirect (https://www.gamesjobsdirect.com)
# ==============================================================================

def parse_gamesjobsdirect_listings(raw_content: str, keyword: str = "") -> List[Dict[str, Any]]:
    """Extracts game development jobs from GamesJobsDirect."""
    base_url = "https://www.gamesjobsdirect.com"
    jobs: List[Dict[str, Any]] = []

    if "<html" in raw_content.lower() or "<div" in raw_content.lower():
        try:
            soup = BeautifulSoup(raw_content, "html.parser")
            cards = soup.select(".job-result, .job-item, .listing, article, div[class*='job-result']")
            if not cards:
                cards = soup.find_all("div", class_=re.compile(r"job-result|result-item|vacancy", re.I))

            for card in cards:
                title_elem = card.find(["h2", "h3", "h4", "a"], class_=re.compile(r"title|job-title|heading", re.I)) or card.find("a")
                if not title_elem:
                    continue

                title = title_elem.get_text(strip=True)
                link_elem = title_elem if title_elem.name == "a" else (title_elem.find("a") or card.find("a"))
                href = link_elem.get("href", "") if link_elem else ""
                full_url = urljoin(base_url, href) if href else base_url

                comp_elem = card.find(["span", "div", "p"], class_=re.compile(r"company|recruiter|employer|client", re.I))
                company = comp_elem.get_text(strip=True) if comp_elem else "Gaming Studio"

                loc_elem = card.find(["span", "div"], class_=re.compile(r"location|city|country", re.I))
                location = loc_elem.get_text(strip=True) if loc_elem else "UK / Remote"

                if title and len(title) > 2 and full_url != base_url:
                    jobs.append({
                        "title": title,
                        "company": company,
                        "source_board": "GamesJobsDirect",
                        "board_source": "GamesJobsDirect",
                        "board_url": full_url,
                        "listing_url": full_url,
                        "location": location,
                    })
        except Exception as e:
            logger.debug(f"GamesJobsDirect HTML parsing error: {e}")

    # Markdown Regex Fallback
    if not jobs:
        matches = re.findall(r"\[([^\]]+)\]\((/job/[^\)]+|https?://www.gamesjobsdirect.com/job/[^\)]+)\)", raw_content, re.I)
        for text, url in matches:
            full_url = urljoin(base_url, url)
            parts = [p.strip() for p in text.split(" - ") if p.strip()]
            title = parts[0] if parts else text
            company = parts[1] if len(parts) > 1 else "Gaming Studio"
            jobs.append({
                "title": title,
                "company": company,
                "source_board": "GamesJobsDirect",
                "board_source": "GamesJobsDirect",
                "board_url": full_url,
                "listing_url": full_url,
                "location": "Remote",
            })

    return filter_jobs_by_keyword(jobs, keyword)


async def scrape_gamesjobsdirect(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes game studio roles from GamesJobsDirect."""
    logger.info(f"🎯 [GamesJobsDirect] Scraping keyword='{keyword}'...")
    search_url = f"https://www.gamesjobsdirect.com/results?keywords={quote_plus(keyword)}"

    try:
        content = await fetch_page_content(search_url)
        if "[ANTI_BOT_BLOCKED]" in content or "[ERROR" in content:
            logger.warning("⚠️ [GamesJobsDirect] Block or error detected.")
            return []

        jobs = parse_gamesjobsdirect_listings(content, keyword)
        logger.info(f"✅ [GamesJobsDirect] Extracted {len(jobs)} jobs.")
        return jobs[:limit]
    except Exception as e:
        logger.error(f"❌ [GamesJobsDirect] Failed: {e}", exc_info=True)
        return []


# ==============================================================================
# Throttled Concurrent Orchestrator Wrapper: run_level_3_scrapers
# ==============================================================================

async def run_level_3_scrapers(
    keyword: str,
    location: str = "Remote",
    max_concurrency: int = 3,
) -> Dict[str, Any]:
    """Executes Level 3 Niche & Remote Job Board Scrapers with throttled concurrency (Semaphore=3).

    Shields fragile boards (Dice, OnlineJobs) from crashing the run, resolves absolute URLs,
    and atomically saves extracted leads to StateManager.

    Args:
        keyword: Target search keyword.
        location: Target location or Remote.
        max_concurrency: Maximum simultaneous in-flight requests (default: 3).

    Returns:
        Summary dict containing counts, board statuses, and total leads extracted.
    """
    logger.info("=" * 80)
    logger.info(f"🚀 Launching Level 3 Niche & Remote Scrapers (Concurrency Limit: {max_concurrency})...")
    logger.info("=" * 80)

    semaphore = asyncio.Semaphore(max_concurrency)

    async def _throttled_task(board_name: str, coroutine_func):
        async with semaphore:
            await asyncio.sleep(0.3)  # Gentle stagger between requests
            try:
                res = await coroutine_func
                return board_name, res, None
            except Exception as e:
                logger.warning(f"⚠️ [{board_name}] Scraper error caught: {e}")
                return board_name, [], str(e)

    tasks = [
        _throttled_task("Arise Work From Home", scrape_arise(keyword, location)),
        _throttled_task("Maxibestof", scrape_maxibestof(keyword, location)),
        _throttled_task("Dice", scrape_dice(keyword, location)),
        _throttled_task("Game Devs of Color", scrape_gamedevsofcolor(keyword, location)),
        _throttled_task("OnlineJobs.ph", scrape_onlinejobs(keyword, location)),
        _throttled_task("Techcareers", scrape_techcareers(keyword, location)),
        _throttled_task("GamesJobsDirect", scrape_gamesjobsdirect(keyword, location)),
    ]

    results = await asyncio.gather(*tasks, return_exceptions=False)

    total_newly_added = 0
    summary_counts: Dict[str, int] = {}

    for board_name, jobs, err in results:
        if err:
            logger.error(f"❌ [{board_name}] Scraper error: {err}")
            state_manager.update_board_status(
                board_name=board_name,
                status="failed",
                error=err,
            )
            summary_counts[board_name] = 0
            continue

        added_for_board = 0
        if isinstance(jobs, list):
            for job in jobs:
                if state_manager.add_extracted_job(job):
                    added_for_board += 1

        total_newly_added += added_for_board
        count = len(jobs) if isinstance(jobs, list) else 0
        summary_counts[board_name] = count

        state_manager.update_board_status(
            board_name=board_name,
            status="completed",
            jobs_found=count,
        )
        logger.info(f"📊 [{board_name}] Scraped: {count} leads | Newly Persisted: {added_for_board}")

    logger.info("=" * 80)
    logger.info(f"🎉 Level 3 Niche Boards Finished! Total Jobs Extracted: {total_newly_added} newly persisted.")
    logger.info(f"Board Breakdown: {summary_counts}")
    logger.info("=" * 80)

    return {
        "status": "success",
        "keyword": keyword,
        "location": location,
        "boards_scraped": [r[0] for r in results],
        "jobs_found_per_board": summary_counts,
        "total_newly_persisted": total_newly_added,
        "total_session_jobs": state_manager.state.total_jobs_extracted if state_manager.state else total_newly_added,
    }
