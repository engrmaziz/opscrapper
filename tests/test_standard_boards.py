"""
Unit and integration tests for Level 1 Standard Job Board Scrapers (Itch.io, GamesIndustry.biz, WeWorkRemotely).
"""

import asyncio
from pathlib import Path
import sys
import unittest.mock as mock

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scrapers.standard_boards import (
    parse_itch_io_listings,
    parse_gamesindustry_listings,
    parse_wwr_listings,
    run_level_1_scrapers,
)
from utils.state_manager import StateManager, state_manager


def test_parse_itch_io_listings():
    """Tests Itch.io HTML and Markdown parsing."""
    sample_itch_html = """
    <html><body>
        <div class="job_listing">
            <h2><a href="/jobs/101-senior-unity-dev">Senior Unity 3D Developer</a></h2>
            <div class="company">PixelForge Games</div>
            <div class="location">Remote (Global)</div>
        </div>
        <div class="job_listing">
            <h2><a href="/jobs/102-game-audio-artist">Lead Game Audio Artist</a></h2>
            <div class="company">SoundScape Interactive</div>
            <div class="location">Remote (EU)</div>
        </div>
    </body></html>
    """
    jobs = parse_itch_io_listings(sample_itch_html, keyword="Unity")
    assert len(jobs) >= 1
    assert jobs[0]["title"] == "Senior Unity 3D Developer"
    assert jobs[0]["company"] == "PixelForge Games"
    assert jobs[0]["source_board"] == "Itch.io"
    assert "https://itch.io/jobs/101" in jobs[0]["board_url"]


def test_parse_gamesindustry_listings():
    """Tests GamesIndustry.biz HTML and Markdown parsing."""
    sample_gi_html = """
    <html><body>
        <div class="job-item">
            <h3 class="job-title"><a href="/job/5001-lead-game-designer">Lead Game Designer</a></h3>
            <div class="recruiter">Rockstar North</div>
            <div class="location">Edinburgh, United Kingdom</div>
        </div>
        <div class="job-item">
            <h3 class="job-title"><a href="/job/5002-unreal-engine-coder">Senior Unreal Engine Coder</a></h3>
            <div class="recruiter">Ubisoft</div>
            <div class="location">Newcastle, UK</div>
        </div>
    </body></html>
    """
    jobs = parse_gamesindustry_listings(sample_gi_html, keyword="Game Designer")
    assert len(jobs) >= 1
    assert jobs[0]["title"] == "Lead Game Designer"
    assert jobs[0]["company"] == "Rockstar North"
    assert jobs[0]["source_board"] == "GamesIndustry.biz"
    assert "jobs.gamesindustry.biz/job/5001" in jobs[0]["board_url"]


def test_parse_wwr_listings():
    """Tests We Work Remotely HTML and Markdown parsing."""
    sample_wwr_html = """
    <html><body>
        <section class="jobs">
            <ul>
                <li class="feature">
                    <a href="/remote-jobs/12345-senior-full-stack-python-engineer">
                        <span class="company">Automattic</span>
                        <span class="title">Senior Full Stack Python Engineer</span>
                        <span class="region">Anywhere in the World</span>
                    </a>
                </li>
                <li>
                    <a href="/remote-jobs/12346-lead-ui-ux-designer">
                        <span class="company">Doist</span>
                        <span class="title">Lead UI/UX Designer</span>
                        <span class="region">100% Remote</span>
                    </a>
                </li>
            </ul>
        </section>
    </body></html>
    """
    jobs = parse_wwr_listings(sample_wwr_html, keyword="Python")
    assert len(jobs) >= 1
    assert jobs[0]["title"] == "Senior Full Stack Python Engineer"
    assert jobs[0]["company"] == "Automattic"
    assert jobs[0]["source_board"] == "WeWorkRemotely"
    assert "weworkremotely.com/remote-jobs/12345" in jobs[0]["board_url"]


async def test_run_level_1_scrapers_mocked(tmp_path: Path):
    """Tests concurrent execution of Level 1 scrapers and persistence in StateManager."""
    test_state_file = tmp_path / "test_level_1_state.json"
    temp_manager = StateManager(file_path=test_state_file)
    temp_manager.initialize_state(
        keyword="Game Developer",
        location="Remote",
        target_boards=["Itch.io", "GamesIndustry.biz", "WeWorkRemotely"],
    )

    # Temporarily bind state_manager to temp_manager for isolated test
    with mock.patch("scrapers.standard_boards.state_manager", temp_manager):
        # Mock fetch_page_content to return synthetic job listings for each board
        async def mock_fetch(url: str, *args, **kwargs) -> str:
            if "itch.io" in url:
                return '<html><body><div class="job_listing"><h2><a href="/jobs/1">Unity Coder</a></h2><div class="company">IndieStudio</div></div></body></html>'
            elif "gamesindustry" in url:
                return '<html><body><div class="job-item"><h3 class="job-title"><a href="/job/2">Level Designer</a></h3><div class="recruiter">BigStudio</div></div></body></html>'
            elif "weworkremotely" in url:
                return '<html><body><section class="jobs"><ul><li><a href="/remote-jobs/3"><span class="title">Python Dev</span><span class="company">RemoteCo</span></a></li></ul></section></body></html>'
            return ""

        with mock.patch("scrapers.standard_boards.fetch_page_content", side_effect=mock_fetch):
            summary = await run_level_1_scrapers(keyword="Dev", location="Remote")

            assert summary["status"] == "success"
            assert "Itch.io" in summary["boards_scraped"]
            assert "GamesIndustry.biz" in summary["boards_scraped"]
            assert "WeWorkRemotely" in summary["boards_scraped"]

            # Validate StateManager persistence
            assert temp_manager.state is not None
            assert temp_manager.state.total_jobs_extracted >= 3
            assert "Itch.io" in temp_manager.state.job_boards_completed
            assert "GamesIndustry.biz" in temp_manager.state.job_boards_completed
            assert "WeWorkRemotely" in temp_manager.state.job_boards_completed


async def main():
    test_parse_itch_io_listings()
    test_parse_gamesindustry_listings()
    test_parse_wwr_listings()

    import tempfile
    with tempfile.TemporaryDirectory() as tmp_dir:
        await test_run_level_1_scrapers_mocked(Path(tmp_dir))

    print("\n[SUCCESS] All Level 1 Scraper tests passed successfully!")


if __name__ == "__main__":
    asyncio.run(main())
