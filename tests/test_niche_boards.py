"""
Unit and integration tests for Level 3 Niche & Remote Job Board Scrapers (Arise, Maxibestof, Dice, GameDevsOfColor, OnlineJobs.ph, Techcareers, GamesJobsDirect).
"""

import asyncio
from pathlib import Path
import sys
import unittest.mock as mock

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scrapers.niche_boards import (
    try_parse_json_payload,
    parse_arise_listings,
    parse_maxibestof_listings,
    parse_dice_listings,
    parse_gamedevsofcolor_listings,
    parse_onlinejobs_listings,
    parse_techcareers_listings,
    parse_gamesjobsdirect_listings,
    run_level_3_scrapers,
)
from utils.state_manager import StateManager


def test_try_parse_json_payload():
    """Validates raw JSON and __NEXT_DATA__ parsing."""
    json_str = '[{"title": "Staff Platform Engineer", "company": "Stripe", "url": "/jobs/123", "location": "Remote"}]'
    parsed = try_parse_json_payload(json_str)
    assert parsed is not None
    assert len(parsed) == 1
    assert parsed[0]["title"] == "Staff Platform Engineer"
    assert parsed[0]["company"] == "Stripe"


def test_parse_arise_listings():
    """Tests Arise opportunity parsing."""
    html = """
    <html><body>
        <div class="service-card">
            <h3><a href="/opportunity/customer-support-rep">Customer Support & Technical Opportunity</a></h3>
            <p>Work from home providing live tech assistance.</p>
        </div>
    </body></html>
    """
    jobs = parse_arise_listings(html, keyword="Support")
    assert len(jobs) >= 1
    assert "Customer Support" in jobs[0]["title"]
    assert jobs[0]["source_board"] == "Arise Work From Home"
    assert "https://www.ariseworkfromhome.com/opportunity" in jobs[0]["board_url"]


def test_parse_maxibestof_listings():
    """Tests Maxibestof curated design and frontend job extraction."""
    html = """
    <html><body>
        <div class="job-card">
            <h3 class="title"><a href="/jobs/mb101-lead-product-designer">Lead Product Designer</a></h3>
            <span class="company">Figma</span>
            <span class="location">Remote</span>
        </div>
    </body></html>
    """
    jobs = parse_maxibestof_listings(html, keyword="Product")
    assert len(jobs) == 1
    assert jobs[0]["title"] == "Lead Product Designer"
    assert jobs[0]["company"] == "Figma"
    assert jobs[0]["board_url"] == "https://maxibestof.one/jobs/mb101-lead-product-designer"
    assert jobs[0]["source_board"] == "Maxibestof"


def test_parse_dice_listings():
    """Tests Dice parsing with card and link extraction."""
    html = """
    <html><body>
        <div class="search-card">
            <h5><a href="/job-detail/dice201-senior-python-dev">Senior Python Engineer</a></h5>
            <span class="company">CyberCoders</span>
            <span class="location">Remote, US</span>
        </div>
    </body></html>
    """
    jobs = parse_dice_listings(html, keyword="Python")
    assert len(jobs) == 1
    assert jobs[0]["title"] == "Senior Python Engineer"
    assert jobs[0]["company"] == "CyberCoders"
    assert jobs[0]["board_url"] == "https://www.dice.com/job-detail/dice201-senior-python-dev"
    assert jobs[0]["source_board"] == "Dice"


def test_parse_gamedevsofcolor_listings():
    """Tests Game Devs of Color parsing."""
    html = """
    <html><body>
        <article class="job-card">
            <h3 class="title"><a href="/jobs/gdoc301-3d-environment-artist">3D Environment Artist</a></h3>
            <p class="company">Indie Studio Alliance</p>
        </article>
    </body></html>
    """
    jobs = parse_gamedevsofcolor_listings(html, keyword="Artist")
    assert len(jobs) == 1
    assert jobs[0]["title"] == "3D Environment Artist"
    assert jobs[0]["company"] == "Indie Studio Alliance"
    assert jobs[0]["source_board"] == "Game Devs of Color"


def test_parse_onlinejobs_listings():
    """Tests OnlineJobs.ph remote developer parsing."""
    html = """
    <html><body>
        <div class="jobpost-cat">
            <h4><a href="/jobseekers/job/ojp401-full-stack-laravel-developer">Full Stack Laravel Developer</a></h4>
            <span class="company">US E-commerce Client</span>
            <span class="salary">$1,800/mo</span>
        </div>
    </body></html>
    """
    jobs = parse_onlinejobs_listings(html, keyword="Laravel")
    assert len(jobs) == 1
    assert jobs[0]["title"] == "Full Stack Laravel Developer"
    assert jobs[0]["company"] == "US E-commerce Client"
    assert jobs[0]["board_url"] == "https://www.onlinejobs.ph/jobseekers/job/ojp401-full-stack-laravel-developer"
    assert jobs[0]["source_board"] == "OnlineJobs.ph"


def test_parse_techcareers_listings():
    """Tests Techcareers parsing."""
    html = """
    <html><body>
        <div class="job-result">
            <h3 class="title"><a href="/job/tc501-cloud-security-engineer">Cloud Security Engineer</a></h3>
            <span class="company">CrowdStrike</span>
        </div>
    </body></html>
    """
    jobs = parse_techcareers_listings(html, keyword="Security")
    assert len(jobs) == 1
    assert jobs[0]["title"] == "Cloud Security Engineer"
    assert jobs[0]["company"] == "CrowdStrike"
    assert jobs[0]["board_url"] == "https://www.techcareers.com/job/tc501-cloud-security-engineer"
    assert jobs[0]["source_board"] == "Techcareers"


def test_parse_gamesjobsdirect_listings():
    """Tests GamesJobsDirect parsing."""
    html = """
    <html><body>
        <div class="job-result">
            <h3 class="title"><a href="/job/gjd601-senior-technical-artist">Senior Technical Artist</a></h3>
            <span class="company">Epic Games</span>
            <span class="location">Guildford, UK</span>
        </div>
    </body></html>
    """
    jobs = parse_gamesjobsdirect_listings(html, keyword="Artist")
    assert len(jobs) == 1
    assert jobs[0]["title"] == "Senior Technical Artist"
    assert jobs[0]["company"] == "Epic Games"
    assert jobs[0]["board_url"] == "https://www.gamesjobsdirect.com/job/gjd601-senior-technical-artist"
    assert jobs[0]["source_board"] == "GamesJobsDirect"


async def test_run_level_3_scrapers_mocked(tmp_path: Path):
    """Tests throttled concurrent execution of Level 3 scrapers with error shielding."""
    test_state_file = tmp_path / "test_level_3_state.json"
    temp_manager = StateManager(file_path=test_state_file)
    temp_manager.initialize_state(
        keyword="Developer",
        location="Remote",
        target_boards=[
            "Arise Work From Home",
            "Maxibestof",
            "Dice",
            "Game Devs of Color",
            "OnlineJobs.ph",
            "Techcareers",
            "GamesJobsDirect",
        ],
    )

    with mock.patch("scrapers.niche_boards.state_manager", temp_manager):
        async def mock_fetch(url: str, *args, **kwargs) -> str:
            # Simulate 403 Block on Dice to test error shielding
            if "dice.com" in url:
                return "[ANTI_BOT_BLOCKED] Cloudflare 403 Access Denied"
            elif "ariseworkfromhome" in url:
                return '<html><body><div class="service-card"><h3><a href="/opportunity/1">Dev Opportunity</a></h3></div></body></html>'
            elif "maxibestof" in url:
                return '<html><body><div class="job-card"><h3 class="title"><a href="/jobs/2">Maxi Dev</a></h3><span class="company">Co2</span></div></body></html>'
            elif "gamedevsofcolor" in url:
                return '<html><body><article class="job-card"><h3 class="title"><a href="/jobs/3">Game Dev</a></h3></article></body></html>'
            elif "onlinejobs" in url:
                return '<html><body><div class="jobpost-cat"><h4><a href="/jobseekers/job/4">Remote Dev</a></h4><span class="company">Co4</span></div></body></html>'
            elif "techcareers" in url:
                return '<html><body><div class="job-result"><h3 class="title"><a href="/job/5">Tech Dev</a></h3><span class="company">Co5</span></div></body></html>'
            elif "gamesjobsdirect" in url:
                return '<html><body><div class="job-result"><h3 class="title"><a href="/job/6">Games Dev</a></h3><span class="company">Co6</span></div></body></html>'
            return ""

        with mock.patch("scrapers.niche_boards.fetch_page_content", side_effect=mock_fetch):
            summary = await run_level_3_scrapers(keyword="Dev", location="Remote", max_concurrency=3)

            assert summary["status"] == "success"
            assert len(summary["boards_scraped"]) == 7

            # Validate that Dice block did not crash the remaining 6 boards
            assert temp_manager.state is not None
            assert temp_manager.state.total_jobs_extracted >= 6
            assert "Arise Work From Home" in temp_manager.state.job_boards_completed
            assert "Maxibestof" in temp_manager.state.job_boards_completed
            assert "Dice" in temp_manager.state.job_boards_completed
            assert "OnlineJobs.ph" in temp_manager.state.job_boards_completed


async def main():
    test_try_parse_json_payload()
    test_parse_arise_listings()
    test_parse_maxibestof_listings()
    test_parse_dice_listings()
    test_parse_gamedevsofcolor_listings()
    test_parse_onlinejobs_listings()
    test_parse_techcareers_listings()
    test_parse_gamesjobsdirect_listings()

    import tempfile
    with tempfile.TemporaryDirectory() as tmp_dir:
        await test_run_level_3_scrapers_mocked(Path(tmp_dir))

    print("\n[SUCCESS] All Level 3 Niche Scraper tests passed successfully!")


if __name__ == "__main__":
    asyncio.run(main())
