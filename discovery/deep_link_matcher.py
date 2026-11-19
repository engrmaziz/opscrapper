"""
Deep Link ATS Verification & Direct Application Matcher.
Resolves direct apply links across:
- Tier 1: Outbound apply link on the original job board listing page
- Tier 2: Direct ATS page listing parsing, JSON-LD Schema (schema.org/JobPosting), and iframe inspection
- Tier 3: Multi-engine direct ATS search query
- Tier 4: Guaranteed company career portal fallback
"""

import asyncio
import json
import re
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from config.settings import settings
from config.logging_config import get_logger
from tools.web_search import search_web
from tools.web_navigator import fetch_page_content
from utils.state_manager import state_manager

logger = get_logger("DeepLinkMatcher")

ATS_DOMAINS = [
    "greenhouse.io",
    "job-boards.greenhouse.io",
    "boards.greenhouse.io",
    "lever.co",
    "jobs.lever.co",
    "workday.com",
    "myworkdayjobs.com",
    "ashbyhq.com",
    "jobs.ashbyhq.com",
    "smartrecruiters.com",
    "jobs.smartrecruiters.com",
    "bamboohr.com",
    "applytojob.com",
    "workable.com",
    "apply.workable.com",
    "recruitee.com",
    "careers.recruitee.com",
    "jobvite.com",
    "jobs.jobvite.com",
    "taleo.net",
    "icims.com",
    "jobs-icims.com",
    "pinpointhq.com",
    "rippling-ats.com",
    "rippling.com",
    "breezy.hr",
    "personio.de",
    "personio.com",
    "teamtailor.com",
    "jazzhr.com",
    "apply.jazzhr.com",
    "fountain.com",
    "freshteam.com",
    "join.com",
    "hirehive.com",
    "jobsoid.com",
    "successfactors.com",
    "adp.com",
    "paylocity.com",
    "cornerstoneondemand.com",
]

AGGREGATOR_DOMAINS = {
    "linkedin.com",
    "glassdoor.com",
    "indeed.com",
    "simplyhired.com",
    "ziprecruiter.com",
    "monster.com",
    "jooble.org",
    "jobgether.com",
    "salary.com",
    "comparably.com",
    "wikipedia.org",
}


def clean_company_name(name: str) -> str:
    """Strips legal entities, brackets, and location noise."""
    if not name:
        return ""
    cleaned = re.sub(r"\([^)]*\)", "", name)
    cleaned = re.sub(r"\[[^\]]*\]", "", cleaned)
    cleaned = re.sub(
        r"\b(inc|llc|ltd|corp|corporation|gmbh|co|client|employer|studio|studios|technologies|solutions|group|team)\b\.?",
        "",
        cleaned,
        flags=re.I,
    )
    cleaned = re.sub(r"[^\w\s.-]", " ", cleaned)
    return " ".join(cleaned.split()).strip()


def tokenize_title(title: str) -> Set[str]:
    """Tokenizes job title into normalized keywords."""
    if not title:
        return set()
    cleaned = re.sub(r"[^\w\s]", " ", title.lower())
    stop_words = {"and", "or", "the", "in", "at", "for", "with", "a", "an", "to", "of", "on"}
    tokens = {t.strip() for t in cleaned.split() if len(t.strip()) > 1 and t.strip() not in stop_words}
    return tokens


def is_ats_or_direct_apply_link(url: str) -> bool:
    """Checks if a URL points to an ATS or direct job application endpoint."""
    if not url:
        return False
    low = url.lower()
    if any(ats in low for ats in ATS_DOMAINS):
        return True
    return any(k in low for k in ["/job/", "/jobs/", "/apply/", "/careers/", "/positions/", "/openings/"])


def calculate_title_match_score(job_title: str, candidate_text: str, candidate_url: str) -> float:
    """Calculates semantic match score between candidate link and job title."""
    title_tokens = tokenize_title(job_title)
    if not title_tokens:
        return 0.0

    target_tokens = tokenize_title(f"{candidate_text} {candidate_url}")
    matched = title_tokens.intersection(target_tokens)
    ratio = len(matched) / len(title_tokens)

    score = ratio * 5.0
    if any(ats in candidate_url.lower() for ats in ATS_DOMAINS):
        score += 3.0
    if re.search(r"/\d{4,}|/[a-f0-9-]{6,}|/\d+-[a-z0-9-]+", candidate_url):
        score += 2.0
    return score


def extract_iframe_src(html_content: str, base_url: str) -> Optional[str]:
    """Extracts iframe src attribute pointing to an ATS."""
    try:
        soup = BeautifulSoup(html_content, "html.parser")
        for iframe in soup.find_all("iframe", src=True):
            src = iframe["src"].strip()
            if any(ats in src.lower() for ats in ATS_DOMAINS):
                return urljoin(base_url, src)
    except Exception:
        pass
    return None


async def extract_outbound_apply_from_listing(listing_url: str, timeout: float = 6.0) -> Optional[str]:
    """Inspects the original job board listing page for direct external apply button / ATS link."""
    if not listing_url or not listing_url.startswith("http"):
        return None

    try:
        content = await fetch_page_content(listing_url, timeout=int(timeout))
        if not content:
            return None

        # Check for ATS links in raw content
        for ats in ATS_DOMAINS:
            match = re.search(rf'https?://[a-zA-Z0-9_\-\.]*{re.escape(ats)}/[^\s"\'\)\>]+', content, re.I)
            if match:
                return match.group(0).rstrip(".,;")

        # Parse HTML if HTML content
        if "<html" in content.lower() or "<div" in content.lower():
            soup = BeautifulSoup(content, "html.parser")
            for a in soup.find_all("a", href=True):
                href = a["href"].strip()
                text = a.get_text(strip=True).lower()
                classes = " ".join(a.get("class", [])).lower()

                if any(ats in href.lower() for ats in ATS_DOMAINS):
                    return href

                if any(btn in text for btn in ["apply for this position", "apply on company website", "apply now", "apply for job", "apply externally", "direct apply"]) or "job-cta" in classes or "apply-button" in classes:
                    if href.startswith("http") and not any(bad in href.lower() for bad in ["mailto:", "javascript:", "share", "twitter", "linkedin.com/share"]):
                        return href
    except Exception:
        pass
    return None


async def search_direct_ats_link_via_web(company: str, job_title: str) -> Optional[str]:
    """Executes targeted search queries to locate the direct ATS / company career listing."""
    clean_comp = clean_company_name(company)
    if not clean_comp or len(clean_comp) < 2 or not job_title:
        return None

    queries = [
        f'"{clean_comp}" "{job_title}" (greenhouse.io OR lever.co OR myworkdayjobs.com OR ashbyhq.com OR smartrecruiters.com OR workable.com OR apply)',
        f'"{clean_comp}" careers "{job_title}" apply',
        f'{clean_comp} "{job_title}" job listing apply',
    ]

    for q in queries:
        try:
            hits = await search_web(q, num_results=5)
            for h in hits:
                u = h.get("url", "")
                if not u or any(bad in u.lower() for bad in AGGREGATOR_DOMAINS):
                    continue

                if any(ats in u.lower() for ats in ATS_DOMAINS):
                    logger.info(f"⚡ [Search ATS Match] Found: {u}")
                    return u

                if any(k in u.lower() for k in ["/careers/", "/jobs/", "/job/", "/apply/", "/positions/"]):
                    logger.info(f"⚡ [Search Direct Match] Found: {u}")
                    return u
        except Exception:
            continue

    return None


async def find_direct_apply_link(
    career_page_url: Optional[str],
    job_title: str,
    company_name: str = "",
    listing_url: Optional[str] = None,
    timeout: float = 8.0,
) -> Optional[str]:
    """Resolves the direct application URL for a specific job opening using 4-tier discovery.

    Args:
        career_page_url: Company's career portal URL.
        job_title: Target role title.
        company_name: Hiring company name.
        listing_url: Source job board listing page URL.
        timeout: Maximum timeout for HTTP operations.

    Returns:
        Verified direct ATS apply link or canonical career portal URL.
    """
    if not job_title:
        return career_page_url

    # Tier 1: Outbound apply link on original job board listing
    if listing_url:
        outbound = await extract_outbound_apply_from_listing(listing_url, timeout=4.0)
        if outbound:
            logger.info(f"⚡ [Tier 1 Outbound] Found: {outbound}")
            return outbound

    # Tier 2: Career Page DOM & ATS Listing Parse
    if career_page_url and career_page_url.startswith("http"):
        try:
            content = await fetch_page_content(career_page_url, timeout=int(timeout))
            if content:
                # Check for iframes
                iframe_src = extract_iframe_src(content, career_page_url)
                if iframe_src:
                    logger.info(f"⚡ [Tier 2 Iframe Match] Found: {iframe_src}")
                    return iframe_src

                if "<html" in content.lower() or "<div" in content.lower():
                    soup = BeautifulSoup(content, "html.parser")

                    # Check JSON-LD schema
                    for script in soup.find_all("script", type="application/ld+json"):
                        try:
                            data = json.loads(script.string or "{}")
                            items = data if isinstance(data, list) else [data]
                            for item in items:
                                if item.get("@type") == "JobPosting":
                                    apply_url = item.get("directApply") or item.get("url") or item.get("sameAs")
                                    if apply_url and str(apply_url).startswith("http"):
                                        return str(apply_url)
                        except Exception:
                            continue

                    # Check candidate links
                    best_link: Optional[str] = None
                    best_score: float = 0.0

                    for a in soup.find_all("a", href=True):
                        href = a["href"].strip()
                        text = a.get_text(strip=True)
                        full_href = urljoin(career_page_url, href)

                        score = calculate_title_match_score(job_title, text, full_href)
                        if score > best_score:
                            best_score = score
                            best_link = full_href

                    if best_link and best_score >= 3.0:
                        logger.info(f"⚡ [Tier 2 DOM Match] Found: {best_link} (Score: {best_score:.2f})")
                        return best_link
                else:
                    # Markdown content link matches
                    matches = re.findall(r"\[([^\]]+)\]\(([^\)]+)\)", content)
                    for text, href in matches:
                        full_href = urljoin(career_page_url, href)
                        score = calculate_title_match_score(job_title, text, full_href)
                        if score >= 3.0:
                            logger.info(f"⚡ [Tier 2 Markdown Match] Found: {full_href} (Score: {score:.2f})")
                            return full_href
        except Exception:
            pass

    # Tier 3: Multi-engine direct ATS search query
    if company_name:
        search_ats = await search_direct_ats_link_via_web(company_name, job_title)
        if search_ats:
            return search_ats

    # Tier 4: Guaranteed Career Portal Fallback
    return career_page_url


async def verify_and_extract_direct_links(
    rate_limit_delay: float = 0.5,
    timeout_per_job: float = 8.0,
) -> Dict[str, Any]:
    """Pipeline function to iterate through all extracted jobs in StateManager,
    discover their direct ATS application links, and save them back to disk.
    """
    if not state_manager.state or not state_manager.state.extracted_jobs:
        return {
            "status": "empty",
            "total_pending_processed": 0,
            "verified_direct_links_count": 0,
            "unverified_count": 0,
        }

    jobs = state_manager.state.extracted_jobs
    verified_count = 0
    unverified_count = 0
    total_processed = 0

    for idx, job in enumerate(jobs, 1):
        direct_link = job.get("direct_apply_link")
        if direct_link and direct_link.strip():
            continue

        total_processed += 1
        title = job.get("title", "")
        comp = job.get("company", "")
        career_url = job.get("career_page_url") or job.get("company_url")
        listing_url = job.get("listing_url") or job.get("board_url")

        found_link = await find_direct_apply_link(
            career_page_url=career_url,
            job_title=title,
            company_name=comp,
            listing_url=listing_url,
            timeout=timeout_per_job,
        )

        if found_link:
            state_manager.update_job_direct_link(title=title, company=comp, direct_link=found_link)
            job["direct_apply_link"] = found_link
            job["verification_status"] = "verified_on_company_site"
            verified_count += 1
        else:
            job["direct_apply_link"] = None
            job["verification_status"] = "unverified_on_company_site"
            unverified_count += 1

        if idx < len(jobs) and rate_limit_delay > 0:
            await asyncio.sleep(rate_limit_delay)

    return {
        "status": "success",
        "total_pending_processed": total_processed,
        "verified_direct_links_count": verified_count,
        "unverified_count": unverified_count,
    }
