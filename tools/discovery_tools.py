"""
Company Domain Discovery, Career Page Navigation, and Deep Link ATS Extraction Tools for Antigravity Agent.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from .base import BaseAgentTool, registry


class FindCompanyOfficialUrlTool(BaseAgentTool):
    """Discovers official canonical root website URL for a given hiring company."""

    name = "find_company_official_url"
    description = (
        "Finds the official canonical website URL (e.g., https://www.epicgames.com) for a target company name. "
        "Filters out job boards, encyclopedias, and directories."
    )

    async def execute(self, company_name: str) -> Optional[str]:
        """Finds official URL for company."""
        from discovery.domain_finder import find_company_official_url
        return await find_company_official_url(company_name=company_name)


class EnrichJobsWithCompanyUrlsTool(BaseAgentTool):
    """Enriches all extracted jobs in StateManager with discovered official company URLs."""

    name = "enrich_jobs_with_company_urls"
    description = (
        "Iterates over all extracted job leads in the State Manager, discovers the official website URL "
        "for each unique company, and saves the updated URLs back to disk."
    )

    async def execute(self, rate_limit_delay: float = 1.0) -> Dict[str, Any]:
        """Runs company URL enrichment across all pending jobs in state."""
        from discovery.domain_finder import enrich_jobs_with_company_urls
        return await enrich_jobs_with_company_urls(rate_limit_delay=rate_limit_delay)


class ExtractNavigationLinksTool(BaseAgentTool):
    """Extracts on-site navigation and anchor links from a company website."""

    name = "extract_navigation_links"
    description = "Parses all clickable anchor links from a webpage and resolves them to absolute URLs."

    async def execute(self, url: str, timeout: float = 15.0) -> Dict[str, str]:
        """Extracts navigation links from URL."""
        from tools.link_extractor import extract_navigation_links
        return await extract_navigation_links(url=url, timeout=timeout)


class FindCareerPageTool(BaseAgentTool):
    """Navigates from a company root domain to its official career portal / jobs page."""

    name = "find_career_page"
    description = (
        "Discovers the official career portal, jobs landing page, or direct ATS link from a company root website "
        "using heuristic paths and DOM navigation parsing."
    )

    async def execute(self, root_url: str, timeout: float = 15.0) -> Optional[str]:
        """Finds career portal for root URL."""
        from discovery.career_finder import find_career_page
        return await find_career_page(root_url=root_url, timeout=timeout)


class EnrichJobsWithCareerPagesTool(BaseAgentTool):
    """Enriches all extracted jobs in StateManager with discovered career portal URLs."""

    name = "enrich_jobs_with_career_pages"
    description = (
        "Iterates over all extracted jobs with a valid company_url in State Manager, navigates to their official "
        "career portals / ATS pages, and saves the career_page_url to disk."
    )

    async def execute(
        self,
        rate_limit_delay: float = 1.0,
        timeout_per_site: float = 15.0,
    ) -> Dict[str, Any]:
        """Runs career page discovery across all company domains in state."""
        from discovery.career_finder import enrich_jobs_with_career_pages
        return await enrich_jobs_with_career_pages(rate_limit_delay=rate_limit_delay, timeout_per_site=timeout_per_site)


class FindDirectApplyLinkTool(BaseAgentTool):
    """Finds the direct ATS application link on a company career page matching the job title."""

    name = "find_direct_apply_link"
    description = (
        "Scans a company career portal / jobs page, handles embedded ATS iframes (e.g. Workday/Greenhouse), "
        "and extracts the direct application link matching the job title."
    )

    async def execute(
        self,
        career_page_url: str,
        job_title: str,
        timeout: float = 15.0,
    ) -> Optional[str]:
        """Finds direct apply link for job title."""
        from discovery.deep_link_matcher import find_direct_apply_link
        return await find_direct_apply_link(career_page_url=career_page_url, job_title=job_title, timeout=timeout)


class VerifyAndExtractDirectLinksTool(BaseAgentTool):
    """Enriches all extracted jobs in StateManager with verified direct ATS application links."""

    name = "verify_and_extract_direct_links"
    description = (
        "Iterates through all jobs in State Manager with a career_page_url, verifies the job posting, "
        "and extracts the direct ATS application link (or flags as unverified_on_company_site)."
    )

    async def execute(self, rate_limit_delay: float = 2.0) -> Dict[str, Any]:
        """Runs direct link ATS extraction pipeline across all jobs in state."""
        from discovery.deep_link_matcher import verify_and_extract_direct_links
        return await verify_and_extract_direct_links(rate_limit_delay=rate_limit_delay)


# Register all discovery & navigation tools into global registry
registry.register(FindCompanyOfficialUrlTool())
registry.register(EnrichJobsWithCompanyUrlsTool())
registry.register(ExtractNavigationLinksTool())
registry.register(FindCareerPageTool())
registry.register(EnrichJobsWithCareerPagesTool())
registry.register(FindDirectApplyLinkTool())
registry.register(VerifyAndExtractDirectLinksTool())
