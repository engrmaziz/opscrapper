"""
Web3, Crypto & Blockchain Job Board Scrapers:
CryptoJobsList, Web3Career, CryptoJobs, UseWeb3.
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

logger = get_logger("Web3Scrapers")


def parse_web3_career(raw_content: str, keyword: str = "") -> List[Dict[str, Any]]:
    """Extracts job postings from Web3.career."""
    jobs: List[Dict[str, Any]] = []
    base_url = "https://web3.career"

    # Pattern: [Job Title](https://web3.career/job/12345) or [Job Title at Company](/...)
    matches = re.findall(
        r"\[([^\]]+)\]\(((?:https?://web3\.career)?/[a-zA-Z0-9_\-]+-jobs?/[^\)]+)\)",
        raw_content,
        re.I,
    )
    if not matches:
        matches = re.findall(r"\[([^\]]+)\]\(((?:https?://web3\.career)?/[^\)]+)\)", raw_content, re.I)

    for text, href in matches:
        if not any(k in href.lower() for k in ["-job", "/job", "developer", "engineer", "designer"]):
            continue
        if any(bad in href.lower() for bad in ["login", "pricing", "post-job", "salaries", "tags", "#"]):
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
            "board_source": "Web3Career",
            "source_board": "Web3Career",
            "listing_url": full_url,
            "board_url": full_url,
            "location": "Remote / Web3",
        }
        if is_valid_job(job_dict) and not any(j["listing_url"] == full_url for j in jobs):
            jobs.append(job_dict)

    return filter_jobs_by_keyword(jobs, keyword)


async def scrape_web3_career(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes Web3.career."""
    logger.info(f"🌐 [Web3Career] Scraping keyword='{keyword}'...")
    url = f"https://web3.career/{quote_plus(keyword)}-jobs"
    try:
        content = await fetch_page_content(url)
        if "[ANTI_BOT_BLOCKED]" in content or not content:
            content = await fetch_page_content("https://web3.career/")
        jobs = parse_web3_career(content, keyword)
        return jobs[:limit]
    except Exception as e:
        logger.error(f"❌ [Web3Career] Error: {e}")
        return []


def parse_crypto_jobs_list(raw_content: str, keyword: str = "") -> List[Dict[str, Any]]:
    """Extracts job postings from CryptoJobsList."""
    jobs: List[Dict[str, Any]] = []
    base_url = "https://cryptojobslist.com"

    matches = re.findall(
        r"\[([^\]]+)\]\(((?:https?://cryptojobslist\.com)?/jobs/[^\)]+)\)",
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
            "board_source": "CryptoJobsList",
            "source_board": "CryptoJobsList",
            "listing_url": full_url,
            "board_url": full_url,
            "location": "Remote / Crypto",
        }
        if is_valid_job(job_dict) and not any(j["listing_url"] == full_url for j in jobs):
            jobs.append(job_dict)

    return filter_jobs_by_keyword(jobs, keyword)


async def scrape_crypto_jobs_list(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes CryptoJobsList."""
    logger.info(f"🪙 [CryptoJobsList] Scraping keyword='{keyword}'...")
    url = f"https://cryptojobslist.com/search?q={quote_plus(keyword)}"
    try:
        content = await fetch_page_content(url)
        jobs = parse_crypto_jobs_list(content, keyword)
        return jobs[:limit]
    except Exception as e:
        logger.error(f"❌ [CryptoJobsList] Error: {e}")
        return []


async def scrape_crypto_jobs(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes CryptoJobs.com."""
    logger.info(f"⚡ [CryptoJobs] Scraping keyword='{keyword}'...")
    url = f"https://cryptojobs.com/search?keyword={quote_plus(keyword)}"
    try:
        content = await fetch_page_content(url)
        matches = re.findall(r"\[([^\]]+)\]\(((?:https?://cryptojobs\.com)?/job/[^\)]+)\)", content, re.I)
        jobs = []
        for text, href in matches:
            full_url = urljoin("https://cryptojobs.com", href)
            parts = [p.strip() for p in text.split(" at ") if p.strip()]
            title = parts[0] if parts else text
            company = parts[1] if len(parts) > 1 else ""
            job_dict = {
                "title": title,
                "company": company,
                "board_source": "CryptoJobs",
                "source_board": "CryptoJobs",
                "listing_url": full_url,
                "board_url": full_url,
                "location": "Remote",
            }
            if is_valid_job(job_dict) and not any(j["listing_url"] == full_url for j in jobs):
                jobs.append(job_dict)
        return filter_jobs_by_keyword(jobs, keyword)[:limit]
    except Exception as e:
        logger.error(f"❌ [CryptoJobs] Error: {e}")
        return []


async def scrape_use_web3(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes UseWeb3.xyz."""
    logger.info(f"⛓️ [UseWeb3] Scraping keyword='{keyword}'...")
    url = "https://www.useweb3.xyz/jobs"
    try:
        content = await fetch_page_content(url)
        matches = re.findall(r"\[([^\]]+)\]\(((?:https?://www\.useweb3\.xyz)?/jobs/[^\)]+)\)", content, re.I)
        jobs = []
        for text, href in matches:
            full_url = urljoin("https://www.useweb3.xyz", href)
            parts = [p.strip() for p in text.split(" at ") if p.strip()]
            title = parts[0] if parts else text
            company = parts[1] if len(parts) > 1 else ""
            job_dict = {
                "title": title,
                "company": company,
                "board_source": "UseWeb3",
                "source_board": "UseWeb3",
                "listing_url": full_url,
                "board_url": full_url,
                "location": "Remote",
            }
            if is_valid_job(job_dict) and not any(j["listing_url"] == full_url for j in jobs):
                jobs.append(job_dict)
        return filter_jobs_by_keyword(jobs, keyword)[:limit]
    except Exception as e:
        logger.error(f"❌ [UseWeb3] Error: {e}")
        return []


# ==============================================================================
# 5. BanklessJobs Scraper
# ==============================================================================

async def scrape_bankless_jobs(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes Bankless Ecosystem Jobs."""
    logger.info(f"🏴 [BanklessJobs] Scraping keyword='{keyword}'...")
    url = "https://pallet.xyz/list/bankless/jobs"
    try:
        content = await fetch_page_content(url)
        matches = re.findall(r"\[([^\]]+)\]\(([^\)]+)\)", content, re.I)
        jobs = []
        for text, href in matches:
            if "/job/" in href or "/jobs/" in href:
                full_url = urljoin("https://pallet.xyz", href)
                parts = [p.strip() for p in text.split(" at ") if p.strip()]
                title = parts[0] if parts else text
                company = parts[1] if len(parts) > 1 else "Bankless DeFi"
                job_dict = {
                    "title": title,
                    "company": company,
                    "board_source": "BanklessJobs",
                    "source_board": "BanklessJobs",
                    "listing_url": full_url,
                    "board_url": full_url,
                    "location": "Remote / Web3",
                }
                if is_valid_job(job_dict) and not any(j["listing_url"] == full_url for j in jobs):
                    jobs.append(job_dict)
        return filter_jobs_by_keyword(jobs, keyword)[:limit]
    except Exception as e:
        logger.error(f"❌ [BanklessJobs] Error: {e}")
        return []


# ==============================================================================
# 6. SolanaJobs Scraper
# ==============================================================================

async def scrape_solana_jobs(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes Solana Ecosystem Jobs."""
    logger.info(f"🟣 [SolanaJobs] Scraping keyword='{keyword}'...")
    url = "https://jobs.solana.com/jobs"
    try:
        content = await fetch_page_content(url)
        matches = re.findall(r"\[([^\]]+)\]\(([^\)]+)\)", content, re.I)
        jobs = []
        for text, href in matches:
            if "/jobs/" in href or "/job/" in href:
                full_url = urljoin("https://jobs.solana.com", href)
                parts = [p.strip() for p in text.split(" at ") if p.strip()]
                title = parts[0] if parts else text
                company = parts[1] if len(parts) > 1 else "Solana Ecosystem"
                job_dict = {
                    "title": title,
                    "company": company,
                    "board_source": "SolanaJobs",
                    "source_board": "SolanaJobs",
                    "listing_url": full_url,
                    "board_url": full_url,
                    "location": "Remote / Solana",
                }
                if is_valid_job(job_dict) and not any(j["listing_url"] == full_url for j in jobs):
                    jobs.append(job_dict)
        return filter_jobs_by_keyword(jobs, keyword)[:limit]
    except Exception as e:
        logger.error(f"❌ [SolanaJobs] Error: {e}")
        return []


# ==============================================================================
# 7. EthereumJobs Scraper
# ==============================================================================

async def scrape_ethereum_jobs(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes Ethereum Ecosystem Jobs."""
    logger.info(f"🔷 [EthereumJobs] Scraping keyword='{keyword}'...")
    url = "https://pallet.xyz/list/ethereum/jobs"
    try:
        content = await fetch_page_content(url)
        matches = re.findall(r"\[([^\]]+)\]\(([^\)]+)\)", content, re.I)
        jobs = []
        for text, href in matches:
            if "/job/" in href or "/jobs/" in href:
                full_url = urljoin("https://pallet.xyz", href)
                parts = [p.strip() for p in text.split(" at ") if p.strip()]
                title = parts[0] if parts else text
                company = parts[1] if len(parts) > 1 else "Ethereum Foundation"
                job_dict = {
                    "title": title,
                    "company": company,
                    "board_source": "EthereumJobs",
                    "source_board": "EthereumJobs",
                    "listing_url": full_url,
                    "board_url": full_url,
                    "location": "Remote",
                }
                if is_valid_job(job_dict) and not any(j["listing_url"] == full_url for j in jobs):
                    jobs.append(job_dict)
        return filter_jobs_by_keyword(jobs, keyword)[:limit]
    except Exception as e:
        logger.error(f"❌ [EthereumJobs] Error: {e}")
        return []


# ==============================================================================
# 8. DefiJobs Scraper
# ==============================================================================

async def scrape_defi_jobs(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes DefiJobs.io."""
    logger.info(f"💰 [DefiJobs] Scraping keyword='{keyword}'...")
    url = "https://defijobs.io/"
    try:
        content = await fetch_page_content(url)
        matches = re.findall(r"\[([^\]]+)\]\(([^\)]+)\)", content, re.I)
        jobs = []
        for text, href in matches:
            if "/job/" in href or "/jobs/" in href:
                full_url = urljoin("https://defijobs.io", href)
                parts = [p.strip() for p in text.split(" at ") if p.strip()]
                title = parts[0] if parts else text
                company = parts[1] if len(parts) > 1 else "DeFi Protocol"
                job_dict = {
                    "title": title,
                    "company": company,
                    "board_source": "DefiJobs",
                    "source_board": "DefiJobs",
                    "listing_url": full_url,
                    "board_url": full_url,
                    "location": "Remote",
                }
                if is_valid_job(job_dict) and not any(j["listing_url"] == full_url for j in jobs):
                    jobs.append(job_dict)
        return filter_jobs_by_keyword(jobs, keyword)[:limit]
    except Exception as e:
        logger.error(f"❌ [DefiJobs] Error: {e}")
        return []


# ==============================================================================
# 9. Blockew Scraper
# ==============================================================================

async def scrape_blockew(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes Blockew Web3 jobs."""
    logger.info(f"🧱 [Blockew] Scraping keyword='{keyword}'...")
    url = "https://blockew.com/"
    try:
        content = await fetch_page_content(url)
        matches = re.findall(r"\[([^\]]+)\]\(([^\)]+)\)", content, re.I)
        jobs = []
        for text, href in matches:
            if "/job/" in href:
                full_url = urljoin("https://blockew.com", href)
                parts = [p.strip() for p in text.split(" at ") if p.strip()]
                title = parts[0] if parts else text
                company = parts[1] if len(parts) > 1 else "Web3 Studio"
                job_dict = {
                    "title": title,
                    "company": company,
                    "board_source": "Blockew",
                    "source_board": "Blockew",
                    "listing_url": full_url,
                    "board_url": full_url,
                    "location": "Remote",
                }
                if is_valid_job(job_dict) and not any(j["listing_url"] == full_url for j in jobs):
                    jobs.append(job_dict)
        return filter_jobs_by_keyword(jobs, keyword)[:limit]
    except Exception as e:
        logger.error(f"❌ [Blockew] Error: {e}")
        return []


# ==============================================================================
# 10. CryptoCareers Scraper
# ==============================================================================

async def scrape_crypto_careers(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes CryptoCareers."""
    logger.info(f"🪙 [CryptoCareers] Scraping keyword='{keyword}'...")
    url = "https://cryptocareers.com/"
    try:
        content = await fetch_page_content(url)
        matches = re.findall(r"\[([^\]]+)\]\(([^\)]+)\)", content, re.I)
        jobs = []
        for text, href in matches:
            if "/job/" in href:
                full_url = urljoin("https://cryptocareers.com", href)
                parts = [p.strip() for p in text.split(" at ") if p.strip()]
                title = parts[0] if parts else text
                company = parts[1] if len(parts) > 1 else "Crypto Exchange"
                job_dict = {
                    "title": title,
                    "company": company,
                    "board_source": "CryptoCareers",
                    "source_board": "CryptoCareers",
                    "listing_url": full_url,
                    "board_url": full_url,
                    "location": "Remote",
                }
                if is_valid_job(job_dict) and not any(j["listing_url"] == full_url for j in jobs):
                    jobs.append(job_dict)
        return filter_jobs_by_keyword(jobs, keyword)[:limit]
    except Exception as e:
        logger.error(f"❌ [CryptoCareers] Error: {e}")
        return []
