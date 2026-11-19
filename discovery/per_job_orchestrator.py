"""
Sequential Per-Job Deep ATS Enrichment Orchestrator.
Processes each job platform up to `max_jobs_per_board` (default 20), executing an immediate end-to-end trace:
Platform Listing -> Official Company Domain -> Career Portal -> Direct ATS Apply Link
for each job before advancing to the next job and platform.
"""

import asyncio
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from config.settings import settings
from config.logging_config import get_logger
from scrapers.board_registry import get_board_runner, get_board_metadata
from scrapers.standard_boards import is_valid_job
from discovery.domain_finder import find_company_official_url
from discovery.career_finder import find_career_page
from discovery.deep_link_matcher import find_direct_apply_link
from utils.state_manager import state_manager, JobRecord
from utils.excel_exporter import export_to_excel

logger = get_logger("PerJobOrchestrator")


async def process_single_job_lead(
    raw_job: Dict[str, Any],
    keyword: str,
    rate_limit_delay: float = 0.5,
) -> Dict[str, Any]:
    """Executes the full end-to-end enrichment pipeline on a single job posting:
    1. Discovers official company website URL.
    2. Navigates to official career portal / ATS landing page.
    3. Matches and extracts the direct application ATS link.

    Args:
        raw_job: Initial job dictionary extracted from a job board.
        keyword: Target role keyword.
        rate_limit_delay: Delay in seconds between network queries.

    Returns:
        Fully enriched and validated job dictionary.
    """
    title = raw_job.get("title", "Unknown Role").strip()
    company = raw_job.get("company", "Unknown Company").strip()
    listing_url = raw_job.get("listing_url") or raw_job.get("board_url", "")
    source_board = raw_job.get("source_board") or raw_job.get("board_source", "Direct")
    location = raw_job.get("location", "Remote")

    logger.info(f"🔎 [Enriching Lead] '{title}' at '{company}' [{source_board}]...")

    company_url: Optional[str] = raw_job.get("company_url")
    career_page_url: Optional[str] = raw_job.get("career_page_url")
    direct_apply_link: Optional[str] = raw_job.get("direct_apply_link")
    verification_status = "board_extracted"

    # Step 1: Discover Official Company Domain
    if not company_url and company and len(company) >= 2:
        try:
            company_url = await find_company_official_url(company)
            if company_url:
                verification_status = "domain_discovered"
                logger.info(f"  🏢 Company Domain: {company_url}")
        except Exception as e:
            logger.debug(f"Domain discovery error for '{company}': {e}")

    # Step 2: Discover Career Page / ATS Portal
    if (company_url or company) and not career_page_url:
        try:
            career_page_url = await find_career_page(company_url or "", company_name=company, timeout=12.0)
            if career_page_url:
                verification_status = "career_page_found"
                logger.info(f"  🎯 Career Portal: {career_page_url}")
        except Exception as e:
            logger.debug(f"Career page search error for '{company_url}': {e}")

    # Step 3: Extract Direct ATS Apply Link (Greenhouse, Lever, Workday, etc.)
    target_portal = career_page_url or company_url
    if not direct_apply_link:
        try:
            direct_apply_link = await find_direct_apply_link(
                career_page_url=target_portal,
                job_title=title,
                company_name=company,
                listing_url=listing_url,
                timeout=12.0,
            )
            if direct_apply_link:
                verification_status = "verified_on_company_site"
                logger.info(f"  ⚡ Direct ATS Apply Link: {direct_apply_link}")
            else:
                direct_apply_link = career_page_url or company_url
                verification_status = "career_page_found" if career_page_url else "domain_discovered"
        except Exception as e:
            logger.debug(f"Direct link extraction error for '{title}': {e}")
            direct_apply_link = career_page_url or company_url

    enriched_job = {
        "title": title,
        "company": company,
        "source_board": source_board,
        "board_source": source_board,
        "listing_url": listing_url,
        "board_url": listing_url,
        "location": location,
        "company_url": company_url,
        "career_page_url": career_page_url,
        "direct_apply_link": direct_apply_link,
        "verification_status": verification_status,
        "extracted_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }

    if rate_limit_delay > 0:
        await asyncio.sleep(rate_limit_delay)

    return enriched_job


async def run_per_job_pipeline(
    keyword: str = "AI Engineer",
    location: str = "Remote",
    target_boards: Optional[List[str]] = None,
    max_jobs_per_board: int = 20,
    resume: bool = False,
    progress_callback: Optional[Callable[[Dict[str, Any]], Any]] = None,
) -> Dict[str, Any]:
    """Executes the full sequential per-job deep enrichment scraping orchestrator across all target platforms.

    Args:
        keyword: Target role keyword (e.g. 'Staff Backend Engineer', 'AI Engineer').
        location: Target location or Remote.
        target_boards: Optional list of board names to scrape (defaults to all 55 boards).
        max_jobs_per_board: Maximum number of jobs to scrape and enrich per board (default: 20).
        resume: Whether to resume from previous saved state file.
        progress_callback: Optional async callback for UI updates.

    Returns:
        Summary dict containing overall pipeline metrics and output Excel path.
    """
    logger.info("=" * 80)
    logger.info(f"🌟 Starting Multi-Platform Job Scraper Agent (Max {max_jobs_per_board} jobs/board)")
    logger.info(f"🎯 Keyword: '{keyword}' | Location: '{location}'")
    logger.info("=" * 80)

    # Initialize State
    boards = target_boards or settings.TARGET_JOB_BOARDS
    state_manager.initialize_state(
        keyword=keyword,
        location=location,
        target_boards=boards,
        force_reset=not resume,
    )

    total_enriched_in_run = 0
    board_summaries: Dict[str, int] = {}

    for board_idx, board_name in enumerate(boards, 1):
        if resume and state_manager.is_board_completed(board_name):
            logger.info(f"⏩ Skipping already completed board [{board_idx}/{len(boards)}]: '{board_name}'")
            continue

        runner = get_board_runner(board_name)
        if not runner:
            logger.warning(f"⚠️ No scraper runner registered for board: '{board_name}'. Marking skipped.")
            state_manager.update_board_status(board_name, status="skipped")
            continue

        state_manager.set_current_board(board_name)
        logger.info(f"\n{'='*40}\n📌 [{board_idx}/{len(boards)}] Scraping Platform: '{board_name}'\n{'='*40}")

        try:
            # 1. Fetch raw listings from this board
            raw_listings: List[Dict[str, Any]] = await runner(
                keyword=keyword,
                location=location,
                limit=max_jobs_per_board,
            )

            valid_listings = [j for j in raw_listings if is_valid_job(j)][:max_jobs_per_board]
            logger.info(f"📋 Found {len(valid_listings)} valid job leads on '{board_name}'. Enriching per job...")

            enriched_for_board = 0

            # 2. Enrich each job lead sequentially
            for job_idx, raw_job in enumerate(valid_listings, 1):
                logger.info(f"  ➜ [{board_name}] Job {job_idx}/{len(valid_listings)}: '{raw_job.get('title')}' at '{raw_job.get('company')}'")
                enriched_job = await process_single_job_lead(raw_job, keyword=keyword)

                # Add to persistent state immediately
                if state_manager.add_extracted_job(enriched_job):
                    enriched_for_board += 1
                    total_enriched_in_run += 1

                if progress_callback:
                    try:
                        res = progress_callback({
                            "type": "job_enriched",
                            "board": board_name,
                            "job": enriched_job,
                            "board_progress": f"{job_idx}/{len(valid_listings)}",
                            "total_jobs": state_manager.state.total_jobs_extracted if state_manager.state else total_enriched_in_run,
                        })
                        if asyncio.iscoroutine(res):
                            await res
                    except Exception:
                        pass

            board_summaries[board_name] = enriched_for_board
            state_manager.update_board_status(
                board_name=board_name,
                status="completed",
                jobs_found=enriched_for_board,
            )
            logger.info(f"✅ Completed '{board_name}' with {enriched_for_board} leads fully enriched.")

        except Exception as e:
            logger.error(f"❌ Error during scrape of '{board_name}': {e}", exc_info=True)
            board_summaries[board_name] = 0
            state_manager.update_board_status(
                board_name=board_name,
                status="failed",
                error=str(e),
            )

        # Generate intermediate Excel checkpoint
        try:
            export_to_excel(output_filename=settings.DEFAULT_EXCEL_FILENAME)
        except Exception as exc:
            logger.warning(f"Excel export checkpoint warning: {exc}")

    # Final Export
    final_excel_path = export_to_excel(output_filename=settings.DEFAULT_EXCEL_FILENAME)
    total_jobs = state_manager.state.total_jobs_extracted if state_manager.state else total_enriched_in_run

    logger.info("\n" + "=" * 80)
    logger.info("🎉 Multi-Platform Job Scraping & Deep ATS Enrichment Pipeline Complete!")
    logger.info(f"📊 Total Leads Enriched: {total_jobs}")
    logger.info(f"📁 Output Excel Workbook: {final_excel_path}")
    logger.info("=" * 80 + "\n")

    return {
        "status": "completed",
        "keyword": keyword,
        "location": location,
        "total_jobs_extracted": total_jobs,
        "boards_processed": len(boards),
        "board_summaries": board_summaries,
        "excel_path": str(final_excel_path),
    }
