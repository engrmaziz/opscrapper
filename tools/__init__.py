"""
Tools package for the Autonomous Job-Scraping Agent.
"""

from .base import BaseAgentTool, ToolMetadata, ToolRegistry, registry, tool
from .scraper_tools import (
    JobListing,
    RunLevel1ScrapersTool,
    RunLevel2ScrapersTool,
    RunLevel3ScrapersTool,
    JobBoardScraperTool,
    CompanyCareerPageFinderTool,
)
from .export_tools import ExcelExportTool
from .state_tools import AddExtractedJobTool, UpdateBoardStatusTool, GetScrapeStateTool
from .web_navigator import WebNavigatorTool, fetch_page_content
from .web_search import search_web
from .link_extractor import extract_navigation_links
from .discovery_tools import (
    FindCompanyOfficialUrlTool,
    EnrichJobsWithCompanyUrlsTool,
    ExtractNavigationLinksTool,
    FindCareerPageTool,
    EnrichJobsWithCareerPagesTool,
    FindDirectApplyLinkTool,
    VerifyAndExtractDirectLinksTool,
)

__all__ = [
    "BaseAgentTool",
    "ToolMetadata",
    "ToolRegistry",
    "registry",
    "tool",
    "JobListing",
    "RunLevel1ScrapersTool",
    "RunLevel2ScrapersTool",
    "RunLevel3ScrapersTool",
    "JobBoardScraperTool",
    "CompanyCareerPageFinderTool",
    "ExcelExportTool",
    "AddExtractedJobTool",
    "UpdateBoardStatusTool",
    "GetScrapeStateTool",
    "WebNavigatorTool",
    "fetch_page_content",
    "search_web",
    "extract_navigation_links",
    "FindCompanyOfficialUrlTool",
    "EnrichJobsWithCompanyUrlsTool",
    "ExtractNavigationLinksTool",
    "FindCareerPageTool",
    "EnrichJobsWithCareerPagesTool",
    "FindDirectApplyLinkTool",
    "VerifyAndExtractDirectLinksTool",
]
