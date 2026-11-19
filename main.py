"""
Main execution entry point for the Autonomous Job-Scraping Agent.
Supports:
1. Sequential Per-Job Deep ATS Enrichment Pipeline across 55+ Job Platforms.
2. Sleek Real-Time Web Application UI & Telemetry Server (http://127.0.0.1:8000).
3. Polished Excel (.xlsx) Report Generation with 4 Clickable Links.
"""

import asyncio
from datetime import datetime, timezone
from pathlib import Path
import sys
import time
from typing import Any, Dict, List, Optional

# Ensure UTF-8 output encoding across Windows terminals
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure project root is on sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

try:
    from google.antigravity import Agent
except ImportError:
    Agent = None

from config.settings import settings
from config.logging_config import setup_logging, get_logger
from config.agent_config import get_orchestrator_config
from config.cli import parse_arguments
from utils.state_manager import state_manager
from utils.excel_exporter import export_to_excel
from discovery.per_job_orchestrator import run_per_job_pipeline
import tools  # noqa: F401

logger = get_logger("MainOrchestrator")


def print_rich_terminal_summary(
    session_id: str,
    keyword: str,
    location: str,
    elapsed_seconds: float,
    export_path: Optional[Path],
) -> None:
    """Prints a polished rich summary box of the entire scraping and discovery mission."""
    extracted = len(state_manager.state.extracted_jobs) if state_manager.state else 0
    domains = sum(1 for j in (state_manager.state.extracted_jobs if state_manager.state else []) if j.get("company_url"))
    career_pages = sum(1 for j in (state_manager.state.extracted_jobs if state_manager.state else []) if j.get("career_page_url"))
    direct_links = sum(1 for j in (state_manager.state.extracted_jobs if state_manager.state else []) if j.get("direct_apply_link"))

    file_size_kb = (export_path.stat().st_size / 1024) if export_path and export_path.exists() else 0.0

    try:
        from rich.console import Console
        from rich.panel import Panel
        from rich.table import Table

        console = Console()
        table = Table(title="📊 FINAL SCRAPING & ATS DISCOVERY METRICS", show_header=True, header_style="bold cyan")
        table.add_column("Pipeline Stage", style="dim", width=35)
        table.add_column("Count / Status", justify="right", style="bold green")

        table.add_row("Target Search Role", f"{keyword} ({location})")
        table.add_row("Session Identifier", session_id)
        table.add_row("Target Platforms Available", f"{len(settings.TARGET_JOB_BOARDS)} Job Boards")
        table.add_row("Total Initial Leads Extracted", f"{extracted} Jobs")
        table.add_row("Company Root Websites Discovered", f"{domains} Domains")
        table.add_row("Official Career Portals Discovered", f"{career_pages} Portals")
        table.add_row("Direct ATS Application Links Verified", f"{direct_links} Verified Links (MUST)")
        table.add_row("Total Execution Runtime", f"{elapsed_seconds:.2f} seconds")
        table.add_row("Formatted Excel Report", f"{export_path.name if export_path else 'N/A'} ({file_size_kb:.1f} KB)")

        console.print()
        console.print(Panel(table, title="[bold green]MISSION COMPLETE[/bold green]", subtitle=f"[cyan]{export_path}[/cyan]"))
        console.print()
    except Exception:
        # Fallback ASCII Box
        print("\n" + "=" * 80)
        print("🎉 MISSION COMPLETE: FINAL SUMMARY METRICS")
        print("=" * 80)
        print(f"• Keyword: {keyword} | Location: {location}")
        print(f"• Total Jobs Extracted: {extracted}")
        print(f"• Company Domains Discovered: {domains}")
        print(f"• Career Portals Discovered: {career_pages}")
        print(f"• Direct ATS Apply Links Verified: {direct_links}")
        print(f"• Runtime: {elapsed_seconds:.2f}s")
        print(f"• Excel Output: {export_path}")
        print("=" * 80 + "\n")


async def run_orchestrator(
    keyword: str,
    location: str = "Remote",
    target_boards: Optional[List[str]] = None,
    max_jobs_per_board: int = 20,
    resume: bool = False,
    force_reset: bool = False,
) -> Dict[str, Any]:
    """Runs the full sequential per-job pipeline."""
    start_time = time.time()

    if force_reset:
        state_manager.clear_state()

    result = await run_per_job_pipeline(
        keyword=keyword,
        location=location,
        target_boards=target_boards,
        max_jobs_per_board=max_jobs_per_board,
        resume=resume,
    )

    elapsed = time.time() - start_time
    session_id = state_manager.state.session_id if state_manager.state else "scrape_completed"
    excel_path = Path(result.get("excel_path", str(settings.EXPORTS_DATA_DIR / settings.DEFAULT_EXCEL_FILENAME)))

    print_rich_terminal_summary(
        session_id=session_id,
        keyword=keyword,
        location=location,
        elapsed_seconds=elapsed,
        export_path=excel_path,
    )

    return result


def main() -> None:
    """Main CLI entrypoint."""
    args = parse_arguments()
    setup_logging(log_level=args.log_level)

    # Launch Web UI if --ui flag is passed
    if args.ui:
        import uvicorn
        web_host = args.host or settings.WEB_HOST
        web_port = args.port or settings.WEB_PORT
        logger.info(f"🌐 Launching Web UI at http://{web_host}:{web_port} (and LAN IP:8060)...")
        uvicorn.run("app.main:app", host=web_host, port=web_port, reload=True)
        return

    # Parse target boards list if provided
    boards_list = None
    if args.boards:
        boards_list = [b.strip() for b in args.boards.split(",") if b.strip()]

    asyncio.run(
        run_orchestrator(
            keyword=args.keyword,
            location=args.location,
            target_boards=boards_list,
            max_jobs_per_board=args.limit,
            resume=args.resume,
            force_reset=args.force_reset,
        )
    )


if __name__ == "__main__":
    main()
