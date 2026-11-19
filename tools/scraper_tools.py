"""
Job Board Scraper tools and schemas for Antigravity agent integration.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from .base import BaseAgentTool, registry


class JobListing(BaseModel):
    """Normalized schema for an extracted job listing."""

    job_title: str = Field(..., description="Title of the job posting")
    company_name: str = Field(..., description="Name of the hiring organization")
    location: str = Field(default="Remote", description="Job location or remote status")
    job_board_source: str = Field(..., description="Job board where listing was discovered")
    board_listing_url: str = Field(..., description="URL of the posting on the job board")
    company_website_url: Optional[str] = Field(default=None, description="Official company homepage")
    company_career_page_url: Optional[str] = Field(default=None, description="Direct company career portal / ATS")
    direct_job_link: Optional[str] = Field(default=None, description="Direct link to apply on company ATS")
    salary_range: Optional[str] = Field(default=None, description="Extracted salary or compensation")
    date_posted: Optional[str] = Field(default=None, description="Posting date or relative timestamp")


class RunLevel1ScrapersTool(BaseAgentTool):
    """Executes Level 1 Standard Job Board Scrapers (Itch.io, GamesIndustry.biz, WeWorkRemotely)."""

    name = "run_level_1_scrapers"
    description = (
        "Scrapes Level 1 standard job boards (Itch.io, GamesIndustry.biz, and We Work Remotely) concurrently. "
        "Extracts job titles, companies, locations, and direct listing URLs, saving them immediately to disk."
    )

    async def execute(
        self,
        keyword: str,
        location: str = "Remote",
    ) -> Dict[str, Any]:
        """Executes Level 1 scrapers."""
        from scrapers.standard_boards import run_level_1_scrapers
        return await run_level_1_scrapers(keyword=keyword, location=location)


class RunLevel2ScrapersTool(BaseAgentTool):
    """Executes Level 2 Aggregator Job Board Scrapers (SimplyHired, Jobgether, Jooble, DynamiteJobs)."""

    name = "run_level_2_scrapers"
    description = (
        "Scrapes Level 2 aggregator job boards (SimplyHired, Jobgether, Jooble, and DynamiteJobs) concurrently. "
        "Filters out sponsored ads, resolves absolute URLs, and extracts true hiring company names into persistent state."
    )

    async def execute(
        self,
        keyword: str,
        location: str = "Remote",
    ) -> Dict[str, Any]:
        """Executes Level 2 scrapers."""
        from scrapers.aggregator_boards import run_level_2_scrapers
        return await run_level_2_scrapers(keyword=keyword, location=location)


class RunLevel3ScrapersTool(BaseAgentTool):
    """Executes Level 3 Niche & Remote Job Board Scrapers (Arise, Maxibestof, Dice, GameDevsOfColor, OnlineJobs.ph, Techcareers, GamesJobsDirect)."""

    name = "run_level_3_scrapers"
    description = (
        "Scrapes Level 3 niche and remote job boards (Arise, Maxibestof, Dice, Game Devs of Color, OnlineJobs.ph, Techcareers, GamesJobsDirect) "
        "with throttled concurrency and robust error shielding against anti-bot challenges."
    )

    async def execute(
        self,
        keyword: str,
        location: str = "Remote",
        max_concurrency: int = 3,
    ) -> Dict[str, Any]:
        """Executes Level 3 scrapers."""
        from scrapers.niche_boards import run_level_3_scrapers
        return await run_level_3_scrapers(keyword=keyword, location=location, max_concurrency=max_concurrency)


class JobBoardScraperTool(BaseAgentTool):
    """General coordinator for scraping targeted job boards across all tiers."""

    name = "scrape_job_boards"
    description = "Scrapes search listings across all supported job boards for a target keyword and location."

    async def execute(
        self,
        keyword: str,
        location: str = "Remote",
        boards: Optional[List[str]] = None,
        limit_per_board: int = 10,
    ) -> Dict[str, Any]:
        """Runs scrapers across all levels."""
        from scrapers.standard_boards import run_level_1_scrapers
        from scrapers.aggregator_boards import run_level_2_scrapers
        from scrapers.niche_boards import run_level_3_scrapers

        l1_res = await run_level_1_scrapers(keyword=keyword, location=location)
        l2_res = await run_level_2_scrapers(keyword=keyword, location=location)
        l3_res = await run_level_3_scrapers(keyword=keyword, location=location)
        return {
            "level_1": l1_res,
            "level_2": l2_res,
            "level_3": l3_res,
        }


class CompanyCareerPageFinderTool(BaseAgentTool):
    """Stub tool for finding official company career portals and direct ATS links."""

    name = "find_company_career_pages"
    description = "Discovers official company career pages and direct ATS application links from employer names."

    async def execute(
        self,
        company_name: str,
        company_domain: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Placeholder execution for company career page discovery."""
        return {
            "status": "initialized",
            "company_name": company_name,
            "career_page_found": None,
            "direct_job_links": [],
        }


# Register tool instances into the global registry
registry.register(RunLevel1ScrapersTool())
registry.register(RunLevel2ScrapersTool())
registry.register(RunLevel3ScrapersTool())
registry.register(JobBoardScraperTool())
registry.register(CompanyCareerPageFinderTool())
