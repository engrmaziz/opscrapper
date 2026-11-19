"""
Career Page & ATS Navigator Engine.
Discovers official career portals, jobs landing pages, and direct ATS application links
from company root website domains using fast heuristic probing and agentic DOM link extraction.
"""

import asyncio
import re
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urljoin, urlparse

import httpx
from config.settings import settings
from config.logging_config import get_logger
from tools.link_extractor import extract_navigation_links
from utils.state_manager import state_manager

logger = get_logger("CareerFinder")

COMMON_CAREER_PATHS = [
    "/careers",
    "/jobs",
    "/careers/",
    "/jobs/",
    "/about/careers",
    "/join-us",
    "/work-with-us",
    "/open-roles",
    "/careers/search",
    "/jobs/search",
    "/careers/openings",
    "/en/careers",
    "/en/jobs",
]

CAREER_LINK_PATTERNS = [
    re.compile(r"\b(career|careers|job|jobs|join us|join our team|work with us|we are hiring|open positions|open roles|current openings|vacancies)\b", re.I),
]

KNOWN_ATS_DOMAINS = [
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
    "bamboohr.com",
    "applytojob.com",
    "workable.com",
    "apply.workable.com",
    "recruitee.com",
    "jobvite.com",
    "taleo.net",
    "icims.com",
    "pinpointhq.com",
    "rippling-ats.com",
    "personio.de",
    "personio.com",
    "teamtailor.com",
    "breezy.hr",
    "jazzhr.com",
    "fountain.com",
]


def is_ats_url(url: str) -> bool:
    """Checks if a URL points to a known Applicant Tracking System (ATS)."""
    if not url:
        return False
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        return any(ats in domain for ats in KNOWN_ATS_DOMAINS)
    except Exception:
        return False


def is_career_link(text: str, url: str) -> bool:
    """Checks if a link text or target URL indicates a career or jobs portal."""
    if is_ats_url(url):
        return True

    combined = f"{text} {url}".lower()
    for pat in CAREER_LINK_PATTERNS:
        if pat.search(combined):
            if not any(fp in combined for fp in ["privacy", "terms", "cookie", "login", "signin"]):
                return True
    return False


async def probe_ats_subdomains(company_slug: str) -> Optional[str]:
    """Probes top ATS platforms directly for company portal."""
    if not company_slug or len(company_slug) < 3:
        return None

    candidates = [
        f"https://job-boards.greenhouse.io/{company_slug}",
        f"https://boards.greenhouse.io/{company_slug}",
        f"https://jobs.lever.co/{company_slug}",
        f"https://jobs.ashbyhq.com/{company_slug}",
        f"https://{company_slug}.bamboohr.com/careers",
        f"https://apply.workable.com/{company_slug}",
        f"https://{company_slug}.smartrecruiters.com",
        f"https://{company_slug}.recruitee.com",
    ]

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    async with httpx.AsyncClient(timeout=3.5, follow_redirects=True) as client:
        for url in candidates:
            try:
                resp = await client.get(url, headers=headers)
                if resp.status_code == 200:
                    body_start = resp.text[:600].lower()
                    if not any(nf in body_start for nf in ["page not found", "404", "no longer exists", "doesn't exist"]):
                        logger.info(f"🎯 [Direct ATS Subdomain] Found: {resp.url}")
                        return str(resp.url)
            except Exception:
                continue

    return None


async def probe_heuristic_career_path(root_url: str, path: str, timeout: float = 3.5) -> Optional[str]:
    """Probes a candidate career path on a root domain with a quick GET request."""
    full_url = urljoin(root_url, path)
    try:
        headers = {
            "User-Agent": settings.DEFAULT_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            resp = await client.get(full_url, headers=headers)
            if resp.status_code == 200:
                final_url = str(resp.url)
                final_path = urlparse(final_url).path.lower().rstrip("/")
                root_path = urlparse(root_url).path.lower().rstrip("/")
                if final_path != root_path:
                    return final_url
    except Exception:
        pass
    return None


async def find_career_page(root_url: str, company_name: str = "", timeout: float = 12.0) -> Optional[str]:
    """Discovers the official career portal / jobs landing page for a company root website.

    Args:
        root_url: Canonical root URL (e.g. 'https://stripe.com').
        company_name: Optional company name for ATS subdomain probe.
        timeout: Maximum execution timeout in seconds.

    Returns:
        Discovered career page URL.
    """
    if not root_url and not company_name:
        return None

    clean_root = root_url.rstrip("/") if root_url else ""

    # Step 1: Fast Heuristic Paths Probe on root domain
    if clean_root and clean_root.startswith("http"):
        heuristic_tasks = [
            probe_heuristic_career_path(clean_root, path, timeout=3.0)
            for path in COMMON_CAREER_PATHS[:6]
        ]
        heuristic_results = await asyncio.gather(*heuristic_tasks, return_exceptions=True)
        for res in heuristic_results:
            if isinstance(res, str) and res:
                logger.info(f"🎯 [Heuristic] Found career page for {clean_root}: {res}")
                return res

        # Step 2: DOM Navigation Links Search
        try:
            links_map = await asyncio.wait_for(
                extract_navigation_links(clean_root, timeout=timeout - 3.0),
                timeout=timeout,
            )

            for text, link_url in links_map.items():
                if is_ats_url(link_url):
                    logger.info(f"🎯 [ATS Direct Link in DOM] Found: {link_url}")
                    return link_url

            for text, link_url in links_map.items():
                if is_career_link(text, link_url):
                    logger.info(f"🎯 [DOM Search] Found career page: {link_url}")
                    return link_url
        except Exception:
            pass

    # Step 3: Direct ATS Subdomain Probe (Greenhouse, Lever, Ashby, BambooHR)
    slug = re.sub(r"[^\w]", "", company_name or (urlparse(clean_root).netloc.split(".")[0] if clean_root else "")).lower().strip()
    if slug and len(slug) >= 3:
        try:
            ats_portal = await probe_ats_subdomains(slug)
            if ats_portal:
                return ats_portal
        except Exception:
            pass

    if clean_root and clean_root.startswith("http"):
        # Guaranteed Fallback: Standard /careers endpoint
        fallback_url = f"{clean_root}/careers"
        logger.info(f"🎯 [Default Fallback] Assigned career portal: {fallback_url}")
        return fallback_url

    return f"https://{slug}.com/careers" if slug else None


async def enrich_jobs_with_career_pages(
    rate_limit_delay: float = 0.5,
    timeout_per_site: float = 12.0,
) -> Dict[str, Any]:
    """Pipeline function to iterate through all extracted jobs in StateManager,
    discover their company career portal URLs, and save them back to disk.
    """
    if not state_manager.state or not state_manager.state.extracted_jobs:
        return {"status": "empty", "discovered_career_pages_count": 0, "unique_domains_processed": 0}

    jobs = state_manager.state.extracted_jobs
    pending_roots: Set[str] = set()

    for job in jobs:
        comp_url = job.get("company_url")
        career_url = job.get("career_page_url")
        if comp_url and (not career_url or not career_url.strip()):
            pending_roots.add(comp_url.strip())

    discovered_count = 0
    for idx, root_url in enumerate(pending_roots, 1):
        career_url = await find_career_page(root_url, timeout=timeout_per_site)
        if career_url:
            state_manager.update_jobs_career_page_url(root_url, career_url)
            discovered_count += 1

        if idx < len(pending_roots) and rate_limit_delay > 0:
            await asyncio.sleep(rate_limit_delay)

    return {
        "status": "success",
        "unique_domains_processed": len(pending_roots),
        "discovered_career_pages_count": discovered_count,
        "total_jobs_in_state": len(jobs),
    }
