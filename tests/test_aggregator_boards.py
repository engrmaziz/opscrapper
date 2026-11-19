"""
Unit and integration tests for Level 2 Aggregator Job Board Scrapers (SimplyHired, Jobgether, Jooble, DynamiteJobs).
"""

import asyncio
from pathlib import Path
import sys
import unittest.mock as mock
import pytest

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scrapers.aggregator_boards import (
    parse_simplyhired_listings,
    parse_jobgether_listings,
    parse_jooble_listings,
    parse_dynamitejobs_listings,
    run_level_2_scrapers,
    is_sponsored_or_spam,
    clean_company_name,
)
from utils.state_manager import StateManager


def test_anti_sponsored_filtering_and_cleaners():
    """Validates filtering of sponsored ads and company name cleanup."""
    assert is_sponsored_or_spam("Sponsored Listing - Urgent Hiring", "card sponsored") is True
    assert is_sponsored_or_spam("Senior Python Engineer at Stripe", "job-card") is False

    assert clean_company_name("at Stripe - Easy Apply", "Default") == "Stripe"
    assert clean_company_name("SimplyHired", "Default Employer") == "Default Employer"


def test_parse_simplyhired_listings():
    """Tests SimplyHired parsing, relative URL resolution, and company identification."""
    sample_html = """
    <html><body>
        <div data-testid="searchSerpJob">
            <h2><a href="/job/sh1001-senior-react-dev">Senior React Engineer</a></h2>
            <span class="company">Vercel Inc</span>
            <span class="location">Remote</span>
        </div>
        <div class="sponsored-card">
            <h2><a href="/job/ad-1">Sponsored Ad Listing</a></h2>
            <span class="company">Ad Network</span>
        </div>
    </body></html>
    """
    jobs = parse_simplyhired_listings(sample_html, base_url="https://www.simplyhired.com", keyword="React")
    assert len(jobs) == 1
    assert jobs[0]["title"] == "Senior React Engineer"
    assert jobs[0]["company"] == "Vercel Inc"
    assert jobs[0]["board_url"] == "https://www.simplyhired.com/job/sh1001-senior-react-dev"
    assert jobs[0]["source_board"] == "SimplyHired"


def test_parse_jobgether_listings():
    """Tests Jobgether parsing and absolute URL conversion."""
    sample_html = """
    <html><body>
        <div class="offer-card">
            <h3 class="title"><a href="/offer/jg2001-backend-go-engineer">Backend Go Engineer</a></h3>
            <p class="company">Docker</p>
            <span class="location">100% Remote</span>
        </div>
    </body></html>
    """
    jobs = parse_jobgether_listings(sample_html, base_url="https://jobgether.com", keyword="Go")
    assert len(jobs) == 1
    assert jobs[0]["title"] == "Backend Go Engineer"
    assert jobs[0]["company"] == "Docker"
    assert jobs[0]["board_url"] == "https://jobgether.com/offer/jg2001-backend-go-engineer"
    assert jobs[0]["source_board"] == "Jobgether"


def test_parse_jooble_listings():
    """Tests Jooble parsing with regional domain URL resolution."""
    sample_html = """
    <html><body>
        <article data-test-name="_jobCard">
            <h2 class="title"><a href="/desc/jb3001-cloud-architect">Cloud Solutions Architect</a></h2>
            <span class="company">Amazon Web Services</span>
            <span class="location">London, UK</span>
        </article>
    </body></html>
    """
    jobs = parse_jooble_listings(sample_html, base_url="https://uk.jooble.org", keyword="Cloud")
    assert len(jobs) == 1
    assert jobs[0]["title"] == "Cloud Solutions Architect"
    assert jobs[0]["company"] == "Amazon Web Services"
    assert jobs[0]["board_url"] == "https://uk.jooble.org/desc/jb3001-cloud-architect"
    assert jobs[0]["source_board"] == "Jooble"


def test_parse_dynamitejobs_listings():
    """Tests DynamiteJobs remote listing extraction."""
    sample_html = """
    <html><body>
        <div class="job-card">
            <a href="/remote-jobs/dj4001-lead-product-designer">
                <h3 class="title">Lead Product Designer</h3>
                <span class="company">GitLab</span>
                <span class="location">Remote</span>
            </a>
        </div>
    </body></html>
    """
    jobs = parse_dynamitejobs_listings(sample_html, base_url="https://dynamitejobs.com", keyword="Designer")
    assert len(jobs) == 1
    assert jobs[0]["title"] == "Lead Product Designer"
    assert jobs[0]["company"] == "GitLab"
    assert jobs[0]["board_url"] == "https://dynamitejobs.com/remote-jobs/dj4001-lead-product-designer"
    assert jobs[0]["source_board"] == "DynamiteJobs"


@pytest.mark.asyncio
async def test_run_level_2_scrapers_mocked(tmp_path: Path):
    """Tests concurrent execution of Level 2 aggregators and atomic state persistence."""
    test_state_file = tmp_path / "test_level_2_state.json"
    temp_manager = StateManager(file_path=test_state_file)
    temp_manager.initialize_state(
        keyword="Software Engineer",
        location="Remote",
        target_boards=["SimplyHired", "Jobgether", "Jooble", "DynamiteJobs"],
    )

    with mock.patch("scrapers.aggregator_boards.state_manager", temp_manager):
        async def mock_fetch(url: str, *args, **kwargs) -> str:
            if "simplyhired" in url:
                return '<html><body><div data-testid="searchSerpJob"><h2><a href="/job/1">Dev 1</a></h2><span class="company">Co1</span></div></body></html>'
            elif "jobgether" in url:
                return '<html><body><div class="offer-card"><h3 class="title"><a href="/offer/2">Dev 2</a></h3><p class="company">Co2</p></div></body></html>'
            elif "jooble" in url:
                return '<html><body><article data-test-name="_jobCard"><h2 class="title"><a href="/desc/3">Dev 3</a></h2><span class="company">Co3</span></article></body></html>'
            elif "dynamitejobs" in url:
                return '<html><body><div class="job-card"><a href="/remote-jobs/4"><h3 class="title">Dev 4</h3><span class="company">Co4</span></a></div></body></html>'
            return ""

        with mock.patch("scrapers.aggregator_boards.fetch_page_content", side_effect=mock_fetch):
            summary = await run_level_2_scrapers(keyword="Dev", location="Remote")

            assert summary["status"] == "success"
            assert len(summary["boards_scraped"]) == 4
            assert temp_manager.state is not None
            assert temp_manager.state.total_jobs_extracted >= 4
            assert "SimplyHired" in temp_manager.state.job_boards_completed
            assert "Jobgether" in temp_manager.state.job_boards_completed
            assert "Jooble" in temp_manager.state.job_boards_completed
            assert "DynamiteJobs" in temp_manager.state.job_boards_completed


async def main():
    test_anti_sponsored_filtering_and_cleaners()
    test_parse_simplyhired_listings()
    test_parse_jobgether_listings()
    test_parse_jooble_listings()
    test_parse_dynamitejobs_listings()

    import tempfile
    with tempfile.TemporaryDirectory() as tmp_dir:
        await test_run_level_2_scrapers_mocked(Path(tmp_dir))

    print("\n[SUCCESS] All Level 2 Aggregator tests passed successfully!")


if __name__ == "__main__":
    asyncio.run(main())
