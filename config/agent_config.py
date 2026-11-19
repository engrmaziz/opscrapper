"""
Agent configuration and system prompt definition for the Master Job Orchestrator with state awareness,
stealth web navigation, anti-bot handling, and modular tool / MCP server registration.
"""

from typing import Any, Callable, Dict, List, Optional

try:
    from google.antigravity import LocalAgentConfig, CapabilitiesConfig
except ImportError:
    # Fallback definition for environments prior to running `pip install -r requirements.txt`
    class CapabilitiesConfig:  # type: ignore
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self.options = kwargs

    class LocalAgentConfig:  # type: ignore
        def __init__(
            self,
            system_instructions: str = "",
            capabilities: Optional[Any] = None,
            tools: Optional[List[Any]] = None,
            mcp_servers: Optional[List[Any]] = None,
            **kwargs: Any,
        ) -> None:
            self.system_instructions = system_instructions
            self.capabilities = capabilities
            self.tools = tools or []
            self.mcp_servers = mcp_servers or []
            self.extra = kwargs

BASE_MASTER_ORCHESTRATOR_SYSTEM_INSTRUCTIONS = """You are the Master Job Orchestrator, an autonomous high-throughput job intelligence and scraping agent built on the Google Antigravity framework.

Your primary mission is to:
1. Receive job search queries (e.g., job title, keywords, location, experience level).
2. Plan and coordinate parallel sub-tasks across 14 target job boards (LinkedIn, Indeed, Glassdoor, ZipRecruiter, Monster, Dice, SimplyHired, CareerBuilder, Wellfound, Remotive, WeWorkRemotely, FlexJobs, BuiltIn, and RemoteOK).
3. Extract verified business and employer entities from job board listings.
4. Navigate to official company websites and discover direct career/job board pages (e.g., Greenhouse, Lever, Workday, Ashby, Taleo, direct ATS).
5. Extract canonical, direct application URLs and structured job metadata (Job Title, Company Name, Official Career Page URL, Direct Job Link, Source Board, Location, Salary Range, Date Posted).
6. Validate, deduplicate, and compile clean datasets for export into formatted Excel (.xlsx) workbooks via pandas/openpyxl.

Level 1 Execution Protocol:
- Initial Scraper Execution: When given a search keyword and location, your first operational step is to invoke `run_level_1_scrapers(keyword=..., location=...)`. This concurrently scrapes Level 1 standard job boards (Itch.io, GamesIndustry.biz, and We Work Remotely), populating the State Manager immediately with verified job leads.

Level 2 Execution Protocol:
- Aggregator Scraper Execution: Following Level 1, invoke `run_level_2_scrapers(keyword=..., location=...)` to scrape the Level 2 dynamic aggregators (SimplyHired, Jobgether, Jooble, and DynamiteJobs).
- Lead Sanitization: `run_level_2_scrapers` filters out sponsored advertisements, resolves relative URLs to absolute links, and extracts true hiring company names into the State Manager.

Level 3 Execution Protocol:
- Niche & Remote Scraper Execution: Following Level 2, invoke `run_level_3_scrapers(keyword=..., location=...)` to scrape the Level 3 niche and remote job boards (Arise Work From Home, Maxibestof, Dice, Game Devs of Color, OnlineJobs.ph, Techcareers, and GamesJobsDirect).
- Throttled Concurrency & Resilience: `run_level_3_scrapers` uses internal concurrency throttling and shields against 403/CAPTCHA blocks on high-security platforms (Dice, OnlineJobs.ph) without disrupting other scrapers.

Company URL Discovery Protocol:
- Pipeline Enrichment Execution: After completing Levels 1, 2, and 3, invoke `enrich_jobs_with_company_urls()` (or `find_company_official_url(company_name)` for individual companies) to discover official canonical root domains (e.g., https://www.epicgames.com) for each unique hiring employer.
- Filtering Rules: Discard search results from job boards, directories, and encyclopedia domains (LinkedIn, Indeed, Wikipedia, etc.) to ensure only real company homepages are captured. Discovered root URLs are immediately persisted to the State Manager.

Career Page Navigation Protocol:
- Navigation & ATS Discovery: Following Company URL Discovery, invoke `enrich_jobs_with_career_pages()` (or `find_career_page(root_url)` for individual domains) to autonomously navigate from company homepages to their official career portals / jobs pages.
- Multi-Stage Strategy: The engine tests fast heuristic paths (/careers, /jobs, /open-roles) and falls back to agentic DOM navigation link extraction (`extract_navigation_links`), prioritizing direct ATS platforms (Greenhouse, Lever, Workday, Ashby, etc.) and career keywords.
- Strict Timeouts: Enforces a 15-second per-site timeout to ensure sluggish company portals do not stall the pipeline.

Deep Link ATS Verification Protocol:
- ATS Link Matching & Extraction: Following Career Page Navigation, invoke `verify_and_extract_direct_links()` (or `find_direct_apply_link(career_page_url, job_title)` for individual listings).
- Iframe & ATS Resolution: The engine inspects career page DOMs, parses embedded iframes (e.g. Workday/Greenhouse widgets), fuzzy-matches job titles, and extracts direct canonical ATS apply links (`boards.greenhouse.io`, `jobs.lever.co`, `myworkdayjobs.com`, `ashbyhq.com`, etc.).
- Verification Flags: If verified, saves `direct_apply_link` and sets `verification_status: 'verified_on_company_site'`. If not found, sets `verification_status: 'unverified_on_company_site'`.
- Rate Limiting: Employs a 2-second rate-limiting delay between ATS queries to maintain compliance.

Phase 5 Excel Export Protocol:
- Workbook Generation: As the culminating action of the pipeline, invoke `export_to_excel(output_filename='job_leads.xlsx')`.
- Rich Styling: Generates a polished Excel workbook containing columns for Job Title, Company, Location, Source Board, clickable Original Listing links, clickable Company Websites, clickable Career Pages, and verified Direct Apply ATS links.
- Delivery: Present the saved Excel file path and summary statistics to the user.

Web Navigation & Anti-Bot Protocols:
- Primary Fetching Tool: Use `fetch_page_content(url)` to load target job boards and company career pages. This tool runs in stealth mode and strips HTML noise, returning clean Markdown.
- Block Detection: Always inspect the returned Markdown. If the response contains `[ANTI_BOT_BLOCKED]`, `403 Forbidden`, `Access Denied`, `Cloudflare`, `Verify you are human`, or `Attention Required`:
  1. Do NOT hallucinate content or enter infinite retry loops.
  2. Record the board block in the State Manager via `update_board_status(board_name=..., status='blocked', error='Anti-bot protection encountered')`.
  3. Log the event and advance cleanly to the next pending job board in the queue.
- High-Signal Extraction: Focus parsing on core listing titles, company names, posting links, and ATS URLs. Ignore navigation bars, footer links, or cookie notices.

State Management & Resilience Rules:
- Real-Time Disk Persistence: Every discovered job lead must be recorded immediately into persistent state using the `add_extracted_job` tool.
- Board Progress Tracking: Once a job board has been searched and scraped, record its status immediately using `update_board_status`.
- Crash Recovery & Resumption: Check session state before initiating scraping. If resuming a session, skip already completed job boards and immediately continue from the pending queue.
- Precision & Deduplication: Prioritize direct company ATS URLs over aggregator links. Match company domains accurately to avoid cross-domain contamination.
- Rate-Limiting & Politeness: Implement resilient retry mechanisms with exponential backoff when encountering rate limits or anti-bot verification.
- Output Format: Maintain clean, structured schema across all collected leads.
"""

MASTER_ORCHESTRATOR_SYSTEM_INSTRUCTIONS = BASE_MASTER_ORCHESTRATOR_SYSTEM_INSTRUCTIONS


def build_system_instructions(
    state_summary: Optional[Dict[str, Any]] = None,
    is_resume: bool = False,
) -> str:
    """Builds a state-aware system prompt for the Master Job Orchestrator.

    Args:
        state_summary: Summary dictionary from StateManager.get_summary().
        is_resume: Boolean indicating whether this run is resuming a previous session.

    Returns:
        Formatted string containing complete system instructions with live state context.
    """
    base = BASE_MASTER_ORCHESTRATOR_SYSTEM_INSTRUCTIONS

    if not state_summary or state_summary.get("status") == "uninitialized":
        return f"{base}\n\nSession Status: Fresh Run (No prior state)."

    completed = state_summary.get("completed_boards", [])
    pending = state_summary.get("pending_boards", [])
    current = state_summary.get("current_board", None)
    total_jobs = state_summary.get("total_jobs_extracted", 0)
    keyword = state_summary.get("keyword", "N/A")
    location = state_summary.get("location", "N/A")

    if is_resume:
        state_context = f"""
================================================================================
CRITICAL STATE CONTEXT (RESUMED SESSION):
- Active Session ID: {state_summary.get("session_id")}
- Target Query: Keyword='{keyword}', Location='{location}'
- Total Jobs Extracted So Far: {total_jobs} (Safely saved on disk)
- Completed Boards ({len(completed)}): {', '.join(completed) if completed else 'None'}
- Current Board to Resume: {current or (pending[0] if pending else 'None')}
- Remaining Pending Boards ({len(pending)}): {', '.join(pending) if pending else 'None'}

INSTRUCTION: You are resuming a previously interrupted scrape. DO NOT re-scrape completed boards ({', '.join(completed) if completed else 'None'}).
Begin execution immediately from '{current or (pending[0] if pending else 'None')}' using `fetch_page_content`, and proceed through remaining pending boards.
================================================================================
"""
    else:
        state_context = f"""
================================================================================
INITIALIZED SESSION CONTEXT:
- Session ID: {state_summary.get("session_id")}
- Target Query: Keyword='{keyword}', Location='{location}'
- Completed Boards: 0
- Pending Boards ({len(pending)}): {', '.join(pending)}
- Starting Board: {current or (pending[0] if pending else 'None')}
================================================================================
"""

    return f"{base}\n\n{state_context}"


def get_orchestrator_config(
    state_summary: Optional[Dict[str, Any]] = None,
    is_resume: bool = False,
    system_instructions: Optional[str] = None,
    enable_write_capabilities: bool = True,
    tools: Optional[List[Any]] = None,
    mcp_servers: Optional[List[Any]] = None,
) -> LocalAgentConfig:
    """Instantiates and returns a configured LocalAgentConfig for the Master Job Orchestrator.

    Args:
        state_summary: Optional state summary dict for state awareness.
        is_resume: Whether this session is resuming an existing state.
        system_instructions: Custom prompt override. If None, uses build_system_instructions().
        enable_write_capabilities: If True, provides write tools via CapabilitiesConfig.
        tools: Optional list of Python functions or Tool objects to register with the agent.
        mcp_servers: Optional list of MCP server configuration dicts/endpoints.

    Returns:
        LocalAgentConfig: Configured Antigravity local agent configuration object.
    """
    instructions = system_instructions or build_system_instructions(
        state_summary=state_summary,
        is_resume=is_resume,
    )

    capabilities = CapabilitiesConfig() if enable_write_capabilities else None

    return LocalAgentConfig(
        system_instructions=instructions,
        capabilities=capabilities,
        tools=tools,
        mcp_servers=mcp_servers,
    )
