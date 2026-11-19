"""
Company Official URL Discovery Engine.
Combines:
1. In-string domain extraction (e.g. 'Eleos (eleostech.com)', 'Spore.Bio')
2. Fast direct HTTP domain probing (https://{company}.com, https://{company}.io, etc.)
3. Multi-engine search with strict token verification and domain blocklisting.
"""

import asyncio
import re
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urlparse

import httpx
from config.settings import settings
from config.logging_config import get_logger
from tools.web_search import search_web
from utils.state_manager import state_manager

logger = get_logger("DomainFinder")

# Domains to explicitly block when searching for official company root URLs
BLOCKED_DOMAINS: Set[str] = {
    # Job boards & aggregators
    "linkedin.com",
    "glassdoor.com",
    "indeed.com",
    "simplyhired.com",
    "jooble.org",
    "jobgether.com",
    "dynamitejobs.com",
    "weworkremotely.com",
    "dice.com",
    "itch.io",
    "gamesindustry.biz",
    "onlinejobs.ph",
    "techcareers.com",
    "gamesjobsdirect.com",
    "monster.com",
    "ziprecruiter.com",
    "careerbuilder.com",
    "wellfound.com",
    "angellist.com",
    "remotive.com",
    "flexjobs.com",
    "builtin.com",
    "remoteok.com",
    "workingnomads.com",
    "otta.com",
    "salary.com",
    "comparably.com",
    "levels.fyi",
    "yelp.com",
    "bbb.org",
    "trustpilot.com",
    # Encyclopedias & directories
    "wikipedia.org",
    "crunchbase.com",
    "bloomberg.com",
    "zoominfo.com",
    "pitchbook.com",
    "owler.com",
    "zippia.com",
    # Social media & video
    "facebook.com",
    "twitter.com",
    "x.com",
    "instagram.com",
    "youtube.com",
    "reddit.com",
    "medium.com",
    "quora.com",
    "tiktok.com",
    "github.com",
    "threads.net",
    "pinterest.com",
}


def clean_company_name(name: str) -> str:
    """Strips common legal entities, bracketed descriptions, and location tags."""
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


def get_company_slug(company: str) -> str:
    """Converts company name into an alphanumeric slug for domain probing."""
    cleaned = clean_company_name(company)
    return re.sub(r"[^\w]", "", cleaned).lower().strip()


def is_blocked_domain(url: str) -> bool:
    """Checks if a URL belongs to a blocked directory, job board, or social media platform."""
    if not url:
        return True
    try:
        parsed = urlparse(url)
        netloc = parsed.netloc.lower()
        if not netloc:
            return True
        if netloc.startswith("www."):
            netloc = netloc[4:]
        return any(netloc == blocked or netloc.endswith("." + blocked) for blocked in BLOCKED_DOMAINS)
    except Exception:
        return True


def extract_root_domain(url: str) -> Optional[str]:
    """Extracts clean root domain URL (e.g. https://about.gitlab.com -> https://about.gitlab.com or https://gitlab.com)."""
    if not url:
        return None
    try:
        parsed = urlparse(url)
        scheme = parsed.scheme if parsed.scheme in ["http", "https"] else "https"
        netloc = parsed.netloc.lower().strip()
        if not netloc or "." not in netloc:
            return None
        return f"{scheme}://{netloc}"
    except Exception:
        return None


def calculate_domain_relevance(company_name: str, candidate_url: str, candidate_text: str = "") -> float:
    """Verifies that the candidate domain and title snippet contain actual company tokens."""
    if not company_name or not candidate_url:
        return 0.0

    parsed = urlparse(candidate_url)
    domain = parsed.netloc.lower()
    text = (candidate_text or "").lower()

    tokens = [t.lower() for t in clean_company_name(company_name).split() if len(t) >= 2]
    if not tokens:
        tokens = [company_name.lower().strip()]

    matched_tokens = 0
    for tok in tokens:
        if tok in domain or tok in text:
            matched_tokens += 1

    if matched_tokens == 0:
        return 0.0

    score = (matched_tokens / len(tokens)) * 3.0
    if all(tok in domain for tok in tokens):
        score += 1.5
    return score


async def probe_direct_domain(company_name: str) -> Optional[str]:
    """Probes standard domain extensions directly before issuing web searches."""
    # 1. Embedded domain in string: e.g. "Eleos (eleostech.com)" or "Spore.Bio"
    embedded = re.search(r"([a-zA-Z0-9_-]+\.(?:com|io|co|org|net|ai|dev|app|tech|so|me|bio))", company_name, re.I)
    if embedded:
        clean_emb = embedded.group(1).lower().strip()
        if not is_blocked_domain(f"https://{clean_emb}"):
            return f"https://{clean_emb}"

    slug = get_company_slug(company_name)
    if not slug or len(slug) < 3:
        return None

    # Common domain candidates
    candidates = [
        f"https://{slug}.com",
        f"https://www.{slug}.com",
        f"https://{slug}.io",
        f"https://{slug}.ai",
        f"https://{slug}.co",
        f"https://{slug}.org",
    ]

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    async with httpx.AsyncClient(timeout=3.5, follow_redirects=True) as client:
        for url in candidates:
            try:
                resp = await client.get(url, headers=headers)
                if resp.status_code == 200:
                    final_url = str(resp.url)
                    root = extract_root_domain(final_url)
                    if root and not is_blocked_domain(root):
                        logger.info(f"✨ [Direct Probe] Discovered official domain for '{company_name}': {root}")
                        return root
            except Exception:
                continue

    return None


async def find_company_official_url(company_name: str) -> Optional[str]:
    """Discovers the canonical official homepage URL for a target hiring company.

    Args:
        company_name: Name of the hiring company (e.g. 'GitLab', 'Stripe', 'PermitFlow').

    Returns:
        Canonical root domain URL or None.
    """
    if not company_name or len(company_name.strip()) < 2:
        return None

    # Filter out generic placeholder names
    if any(generic in company_name.lower() for generic in ["various employers", "confidential", "job board", "partner client"]):
        return None

    clean_name = clean_company_name(company_name) or company_name.strip()

    # Step 1: Fast Direct Probe
    direct_domain = await probe_direct_domain(company_name)
    if direct_domain:
        return direct_domain

    # Step 2: Multi-Engine Web Search with Strict Token Relevance
    query = f"{clean_name} company official website"
    logger.info(f"🏢 Finding official URL for company: '{clean_name}'...")

    try:
        search_hits = await search_web(query, num_results=6)
        if not search_hits:
            return None

        best_url: Optional[str] = None
        best_score: float = 0.0

        for hit in search_hits:
            raw_url = hit.get("url", "")
            if not raw_url or is_blocked_domain(raw_url):
                continue

            root_url = extract_root_domain(raw_url)
            if not root_url or is_blocked_domain(root_url):
                continue

            score = calculate_domain_relevance(clean_name, root_url)
            if score > best_score:
                best_score = score
                best_url = root_url

        if best_url and best_score >= 1.0:
            logger.info(f"✨ [Search] Discovered URL for '{company_name}': {best_url} (Score: {best_score:.2f})")
            return best_url

        # Fallback: slug.com if clean
        slug = get_company_slug(company_name)
        if slug and len(slug) >= 3:
            return f"https://{slug}.com"

        return None
    except Exception as e:
        logger.error(f"❌ Error finding official URL for '{company_name}': {e}")
        return None


async def enrich_jobs_with_company_urls(rate_limit_delay: float = 0.5) -> Dict[str, Any]:
    """Pipeline function to iterate through all extracted jobs in StateManager,
    discover their company official root URLs, and save them back to disk.
    """
    if not state_manager.state or not state_manager.state.extracted_jobs:
        return {"status": "empty", "urls_discovered_count": 0}

    jobs = state_manager.state.extracted_jobs
    unique_companies: Set[str] = set()

    for job in jobs:
        comp = job.get("company")
        comp_url = job.get("company_url")
        if comp and (not comp_url or not comp_url.strip()):
            unique_companies.add(comp.strip())

    discovered_count = 0
    for idx, company in enumerate(unique_companies, 1):
        official_url = await find_company_official_url(company)
        if official_url:
            state_manager.update_jobs_company_url(company, official_url)
            discovered_count += 1

        if idx < len(unique_companies) and rate_limit_delay > 0:
            await asyncio.sleep(rate_limit_delay)

    return {
        "status": "success",
        "unique_companies_processed": len(unique_companies),
        "urls_discovered_count": discovered_count,
        "total_jobs_in_state": len(jobs),
    }
