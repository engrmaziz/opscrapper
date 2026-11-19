"""
Command Line Interface (CLI) argument parser module for the Job Scraper Agent.
"""

import argparse
from typing import Optional
from .settings import settings


def parse_arguments(args: Optional[list[str]] = None) -> argparse.Namespace:
    """Parses command-line arguments for the Master Job Orchestrator.

    Supported options:
        --keyword (-k): Target job role keyword (e.g. 'AI Engineer', 'Staff Backend').
        --location (-l): Target location filter (default: 'Remote').
        --limit (-m): Max jobs to scrape per platform (default: 20).
        --boards (-b): Comma-separated list of job boards to target.
        --resume (-r): Resume from the last saved state file on disk.
        --ui (-u): Launch the FastAPI Web Application UI dashboard at http://127.0.0.1:8000.
        --interactive (-i): Optional interactive chat console session.
        --force-reset: Force fresh state and discard previous session.
        --log-level: Logging verbosity level.

    Returns:
        argparse.Namespace parsed argument object.
    """
    parser = argparse.ArgumentParser(
        prog="job_scraper_agent",
        description="Autonomous Multi-Platform Job-Scraping Agent with Direct ATS Enrichment & Web UI",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # Core required / optional search inputs
    parser.add_argument(
        "-k",
        "--keyword",
        type=str,
        default=None,
        help="Target job keyword or title (e.g. 'AI Engineer', 'Staff Backend Developer').",
    )
    parser.add_argument(
        "-l",
        "--location",
        type=str,
        default=settings.DEFAULT_LOCATION,
        help="Target location / country / remote filter (e.g. 'Remote', 'London, UK', 'New York').",
    )
    parser.add_argument(
        "-m",
        "--limit",
        type=int,
        default=settings.MAX_JOBS_PER_BOARD,
        help="Maximum jobs to scrape and enrich per platform (default: 20).",
    )
    parser.add_argument(
        "-r",
        "--resume",
        action="store_true",
        default=False,
        help="Resume scraping from the previous saved state file on disk.",
    )
    parser.add_argument(
        "-b",
        "--boards",
        type=str,
        default=None,
        help="Comma-separated subset of job boards to scrape (e.g. 'WeWorkRemotely,RemoteOK,Wellfound'). Defaults to all 55.",
    )
    parser.add_argument(
        "-u",
        "--ui",
        action="store_true",
        default=False,
        help="Launch the FastAPI Web Application Dashboard.",
    )
    parser.add_argument(
        "--host",
        type=str,
        default=settings.WEB_HOST,
        help=f"Host address for the Web UI server (default: {settings.WEB_HOST}).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=settings.WEB_PORT,
        help=f"Port number for the Web UI server (default: {settings.WEB_PORT}).",
    )
    parser.add_argument(
        "-i",
        "--interactive",
        action="store_true",
        default=False,
        help="Enable interactive chat loop with the Master Job Orchestrator agent.",
    )
    parser.add_argument(
        "--force-reset",
        action="store_true",
        default=False,
        help="Force fresh start and discard any existing scrape_state.json file.",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default=settings.LOG_LEVEL,
        help="Terminal and file logging verbosity level.",
    )

    parsed_args = parser.parse_args(args)

    if not parsed_args.resume and not parsed_args.keyword:
        parsed_args.keyword = settings.DEFAULT_KEYWORD

    return parsed_args
