"""
AI, Data Science, and Machine Learning Job Board Scrapers:
AI-Jobs.net, DataYoshi, DeepLearningAI, AiCareers, OuterJoin, AnalyticsJobs.
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

logger = get_logger("AIDataScrapers")


def parse_ai_jobs_net(raw_content: str, keyword: str = "") -> List[Dict[str, Any]]:
    """Extracts job postings from AI-Jobs.net Markdown / HTML."""
    jobs: List[Dict[str, Any]] = []
    base_url = "https://ai-jobs.net"

    # Markdown links format: [Title at Company](https://ai-jobs.net/job/123-title/) or [Title](url)
    matches = re.findall(
        r"\[([^\]]+)\]\(((?:https?://ai-jobs\.net)?/job/[^\)]+)\)",
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

        # If company still missing, check URL slug: /job/12345-senior-ai-engineer-company-name/
        if not company:
            slug = href.rstrip("/").split("/")[-1]
            slug_clean = re.sub(r"^\d+-", "", slug).replace("-", " ")
            company = slug_clean.split()[-1].title() if slug_clean else ""

        job_dict = {
            "title": title.replace("\ufffd", "-").strip(),
            "company": company.replace("\ufffd", "").strip(),
            "board_source": "AI-Jobs.net",
            "source_board": "AI-Jobs.net",
            "listing_url": full_url,
            "board_url": full_url,
            "location": "Remote / Worldwide",
        }
        if is_valid_job(job_dict) and not any(j["listing_url"] == full_url for j in jobs):
            jobs.append(job_dict)

    return filter_jobs_by_keyword(jobs, keyword)


async def scrape_ai_jobs_net(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes AI-Jobs.net."""
    logger.info(f"🧠 [AI-Jobs.net] Scraping keyword='{keyword}'...")
    search_url = f"https://ai-jobs.net/?q={quote_plus(keyword)}"
    try:
        content = await fetch_page_content(search_url)
        if "[ANTI_BOT_BLOCKED]" in content:
            content = await fetch_page_content("https://ai-jobs.net/")
        jobs = parse_ai_jobs_net(content, keyword)
        return jobs[:limit]
    except Exception as e:
        logger.error(f"❌ [AI-Jobs.net] Error: {e}")
        return []


def parse_datayoshi(raw_content: str, keyword: str = "") -> List[Dict[str, Any]]:
    """Extracts job postings from DataYoshi."""
    jobs: List[Dict[str, Any]] = []
    base_url = "https://www.datayoshi.com"

    matches = re.findall(
        r"\[([^\]]+)\]\(((?:https?://www\.datayoshi\.com)?/jobs/[^\)]+)\)",
        raw_content,
        re.I,
    )
    for text, href in matches:
        full_url = urljoin(base_url, href)
        parts = [p.strip() for p in text.split(" - ") if p.strip()]
        title = parts[0] if parts else text
        company = parts[1] if len(parts) > 1 else ""

        if not company:
            parts_at = [p.strip() for p in text.split(" at ") if p.strip()]
            if len(parts_at) >= 2:
                title, company = parts_at[0], parts_at[1]

        job_dict = {
            "title": title.replace("\ufffd", "-").strip(),
            "company": company.replace("\ufffd", "").strip(),
            "board_source": "DataYoshi",
            "source_board": "DataYoshi",
            "listing_url": full_url,
            "board_url": full_url,
            "location": "Remote",
        }
        if is_valid_job(job_dict) and not any(j["listing_url"] == full_url for j in jobs):
            jobs.append(job_dict)

    return filter_jobs_by_keyword(jobs, keyword)


async def scrape_datayoshi(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes DataYoshi."""
    logger.info(f"📊 [DataYoshi] Scraping keyword='{keyword}'...")
    search_url = f"https://www.datayoshi.com/?s={quote_plus(keyword)}"
    try:
        content = await fetch_page_content(search_url)
        jobs = parse_datayoshi(content, keyword)
        return jobs[:limit]
    except Exception as e:
        logger.error(f"❌ [DataYoshi] Error: {e}")
        return []


def parse_outerjoin(raw_content: str, keyword: str = "") -> List[Dict[str, Any]]:
    """Extracts job postings from OuterJoin (Data & ML roles)."""
    jobs: List[Dict[str, Any]] = []
    base_url = "https://outerjoin.us"

    matches = re.findall(
        r"\[([^\]]+)\]\(((?:https?://outerjoin\.us)?/jobs?/[^\)]+)\)",
        raw_content,
        re.I,
    )
    for text, href in matches:
        full_url = urljoin(base_url, href)
        parts = [p.strip() for p in text.split(" | ") if p.strip()]
        title = parts[0] if parts else text
        company = parts[1] if len(parts) > 1 else ""

        job_dict = {
            "title": title.strip(),
            "company": company.strip(),
            "board_source": "OuterJoin",
            "source_board": "OuterJoin",
            "listing_url": full_url,
            "board_url": full_url,
            "location": "Remote",
        }
        if is_valid_job(job_dict) and not any(j["listing_url"] == full_url for j in jobs):
            jobs.append(job_dict)

    return filter_jobs_by_keyword(jobs, keyword)


async def scrape_outerjoin(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes OuterJoin."""
    logger.info(f"🔗 [OuterJoin] Scraping keyword='{keyword}'...")
    search_url = f"https://outerjoin.us/jobs?q={quote_plus(keyword)}"
    try:
        content = await fetch_page_content(search_url)
        jobs = parse_outerjoin(content, keyword)
        return jobs[:limit]
    except Exception as e:
        logger.error(f"❌ [OuterJoin] Error: {e}")
        return []


def parse_generic_ai_board(raw_content: str, board_name: str, base_url: str, keyword: str = "") -> List[Dict[str, Any]]:
    """Generic high-signal parser for AI and ML niche boards."""
    jobs: List[Dict[str, Any]] = []
    matches = re.findall(r"\[([^\]]+)\]\(([^\)]+)\)", raw_content)

    for text, href in matches:
        if not any(k in href.lower() for k in ["/job/", "/position/", "/career/", "/jobs/"]):
            continue
        if any(bad in href.lower() for bad in ["#", "javascript", "login", "register", "post-a-job"]):
            continue

        full_url = urljoin(base_url, href)
        parts = [p.strip() for p in text.split(" - ") if p.strip()]
        title = parts[0] if parts else text
        company = parts[1] if len(parts) > 1 else ""

        if " at " in title and not company:
            at_parts = title.split(" at ")
            title = at_parts[0].strip()
            company = at_parts[1].strip()

        job_dict = {
            "title": title.replace("\ufffd", "-").strip(),
            "company": company.replace("\ufffd", "").strip(),
            "board_source": board_name,
            "source_board": board_name,
            "listing_url": full_url,
            "board_url": full_url,
            "location": "Remote",
        }
        if is_valid_job(job_dict) and not any(j["listing_url"] == full_url for j in jobs):
            jobs.append(job_dict)

    return filter_jobs_by_keyword(jobs, keyword)


async def scrape_deeplearning_ai(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes DeepLearning.AI Job Board."""
    logger.info(f"🤖 [DeepLearningAI] Scraping keyword='{keyword}'...")
    url = "https://jobs.deeplearning.ai/"
    try:
        content = await fetch_page_content(url)
        jobs = parse_generic_ai_board(content, "DeepLearningAI", url, keyword)
        return jobs[:limit]
    except Exception as e:
        logger.error(f"❌ [DeepLearningAI] Error: {e}")
        return []


async def scrape_aicareers(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes AiCareers.com."""
    logger.info(f"💡 [AiCareers] Scraping keyword='{keyword}'...")
    url = f"https://aicareers.com/jobs?query={quote_plus(keyword)}"
    try:
        content = await fetch_page_content(url)
        jobs = parse_generic_ai_board(content, "AiCareers", "https://aicareers.com", keyword)
        return jobs[:limit]
    except Exception as e:
        logger.error(f"❌ [AiCareers] Error: {e}")
        return []


async def scrape_analytics_jobs(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes AnalyticsJobs."""
    logger.info(f"📈 [AnalyticsJobs] Scraping keyword='{keyword}'...")
    url = f"https://analyticsjobs.co/jobs?q={quote_plus(keyword)}"
    try:
        content = await fetch_page_content(url)
        jobs = parse_generic_ai_board(content, "AnalyticsJobs", "https://analyticsjobs.co", keyword)
        return jobs[:limit]
    except Exception as e:
        logger.error(f"❌ [AnalyticsJobs] Error: {e}")
        return []


# ==============================================================================
# 7. DataJobs Scraper
# ==============================================================================

async def scrape_datajobs(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes DataJobs."""
    logger.info(f"📊 [DataJobs] Scraping keyword='{keyword}'...")
    url = f"https://datajobs.com/"
    try:
        content = await fetch_page_content(url)
        jobs = parse_generic_ai_board(content, "DataJobs", "https://datajobs.com", keyword)
        return jobs[:limit]
    except Exception as e:
        logger.error(f"❌ [DataJobs] Error: {e}")
        return []


# ==============================================================================
# 8. DataScienceJobs Scraper
# ==============================================================================

async def scrape_datasciencejobs(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes DataScienceJobs."""
    logger.info(f"🔬 [DataScienceJobs] Scraping keyword='{keyword}'...")
    url = f"https://datasciencejobs.com/"
    try:
        content = await fetch_page_content(url)
        jobs = parse_generic_ai_board(content, "DataScienceJobs", "https://datasciencejobs.com", keyword)
        return jobs[:limit]
    except Exception as e:
        logger.error(f"❌ [DataScienceJobs] Error: {e}")
        return []


# ==============================================================================
# 9. MachineLearningJobs Scraper
# ==============================================================================

async def scrape_machinelearningjobs(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes MachineLearningJobs.io."""
    logger.info(f"🤖 [MachineLearningJobs] Scraping keyword='{keyword}'...")
    url = f"https://machinelearningjobs.io/"
    try:
        content = await fetch_page_content(url)
        jobs = parse_generic_ai_board(content, "MachineLearningJobs", "https://machinelearningjobs.io", keyword)
        return jobs[:limit]
    except Exception as e:
        logger.error(f"❌ [MachineLearningJobs] Error: {e}")
        return []


# ==============================================================================
# 10. R-users Scraper
# ==============================================================================

async def scrape_r_users(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes R-users.com (Data Analysis & Statistics)."""
    logger.info(f"📊 [R-users] Scraping keyword='{keyword}'...")
    url = f"https://www.r-users.com/"
    try:
        content = await fetch_page_content(url)
        jobs = parse_generic_ai_board(content, "R-users", "https://www.r-users.com", keyword)
        return jobs[:limit]
    except Exception as e:
        logger.error(f"❌ [R-users] Error: {e}")
        return []


# ==============================================================================
# 11. Kaggle Jobs Scraper
# ==============================================================================

async def scrape_kaggle_jobs(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes Kaggle Jobs / ML Competitions hiring boards."""
    logger.info(f"🏆 [Kaggle Jobs] Scraping keyword='{keyword}'...")
    url = "https://www.kaggle.com/jobs"
    try:
        content = await fetch_page_content(url)
        jobs = parse_generic_ai_board(content, "Kaggle Jobs", "https://www.kaggle.com", keyword)
        return jobs[:limit]
    except Exception as e:
        logger.error(f"❌ [Kaggle Jobs] Error: {e}")
        return []


# ==============================================================================
# 12. HuggingFace Jobs Scraper
# ==============================================================================

async def scrape_huggingface_jobs(keyword: str, location: str = "Remote", limit: int = 20) -> List[Dict[str, Any]]:
    """Scrapes Hugging Face Open-Source AI Ecosystem Jobs."""
    logger.info(f"🤗 [HuggingFace Jobs] Scraping keyword='{keyword}'...")
    url = "https://huggingface.co/jobs"
    try:
        content = await fetch_page_content(url)
        jobs = parse_generic_ai_board(content, "HuggingFace Jobs", "https://huggingface.co", keyword)
        return jobs[:limit]
    except Exception as e:
        logger.error(f"❌ [HuggingFace Jobs] Error: {e}")
        return []
