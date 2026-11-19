"""
Unit and integration tests for Career Page Navigator Engine (tools/link_extractor.py, discovery/career_finder.py, StateManager updates).
"""

import asyncio
from pathlib import Path
import sys
import unittest.mock as mock

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.link_extractor import extract_navigation_links
from discovery.career_finder import (
    is_ats_url,
    is_career_link,
    find_career_page,
    enrich_jobs_with_career_pages,
    probe_heuristic_career_path,
)
from utils.state_manager import StateManager


def test_is_ats_url():
    """Validates detection of known ATS platforms."""
    assert is_ats_url("https://boards.greenhouse.io/stripe/jobs/123") is True
    assert is_ats_url("https://jobs.lever.co/epicgames") is True
    assert is_ats_url("https://epicgames.wd5.myworkdayjobs.com/Careers") is True
    assert is_ats_url("https://jobs.ashbyhq.com/anthropic") is True
    assert is_ats_url("https://www.epicgames.com/site/en-US/home") is False


def test_is_career_link():
    """Validates career keyword identification and false-positive rejection."""
    assert is_career_link("Careers", "https://company.com/careers") is True
    assert is_career_link("Open Positions", "https://company.com/open-roles") is True
    assert is_career_link("Join Us", "https://company.com/join") is True
    assert is_career_link("Privacy Policy", "https://company.com/privacy") is False
    assert is_career_link("Terms of Service", "https://company.com/terms") is False


async def test_extract_navigation_links():
    """Validates HTML link parsing and relative URL resolution."""
    sample_html = """
    <html><body>
        <nav>
            <a href="/about">About Us</a>
            <a href="/careers" title="Explore Careers">Work With Us</a>
            <a href="https://boards.greenhouse.io/testcompany">Open Positions</a>
            <a href="#section-contact">Contact</a>
        </nav>
    </body></html>
    """
    with mock.patch("tools.link_extractor.fetch_page_content", return_value=sample_html):
        links = await extract_navigation_links("https://testcompany.com", timeout=5.0)

        assert "Work With Us" in links
        assert links["Work With Us"] == "https://testcompany.com/careers"
        assert links["Open Positions"] == "https://boards.greenhouse.io/testcompany"
        assert "Contact" not in links  # anchor href excluded


async def test_find_career_page_heuristic_hit():
    """Tests heuristic path discovery (/careers)."""
    with mock.patch("discovery.career_finder.probe_heuristic_career_path", return_value="https://testco.com/careers"):
        career_url = await find_career_page("https://testco.com")
        assert career_url == "https://testco.com/careers"


async def test_find_career_page_dom_search_hit():
    """Tests DOM search fallback when heuristic paths are not direct."""
    # Heuristic fails (returns None), DOM search succeeds
    with mock.patch("discovery.career_finder.probe_heuristic_career_path", return_value=None):
        mock_links = {
            "Home": "https://testco.com/",
            "Products": "https://testco.com/products",
            "Join Our Team": "https://testco.com/company/opportunities",
        }
        with mock.patch("discovery.career_finder.extract_navigation_links", return_value=mock_links):
            career_url = await find_career_page("https://testco.com")
            assert career_url == "https://testco.com/company/opportunities"


async def test_enrich_jobs_with_career_pages_mocked(tmp_path: Path):
    """Tests batch enrichment of career pages across state records."""
    test_state_file = tmp_path / "test_career_state.json"
    temp_manager = StateManager(file_path=test_state_file)
    temp_manager.initialize_state(keyword="Engineer", location="Remote", target_boards=["Itch.io"])

    temp_manager.add_extracted_job({
        "title": "Lead Gameplay Programmer",
        "company": "Rockstar Games",
        "company_url": "https://www.rockstargames.com",
        "source_board": "GamesIndustry.biz",
        "board_url": "https://jobs.gamesindustry.biz/job/1",
    })
    temp_manager.add_extracted_job({
        "title": "Staff Backend Engineer",
        "company": "Figma",
        "company_url": "https://www.figma.com",
        "source_board": "WeWorkRemotely",
        "board_url": "https://weworkremotely.com/job/2",
    })

    async def mock_find_career(url: str, timeout: float = 15.0):
        if "rockstargames" in url:
            return "https://www.rockstargames.com/careers"
        elif "figma" in url:
            return "https://www.figma.com/careers"
        return None

    with mock.patch("discovery.career_finder.state_manager", temp_manager):
        with mock.patch("discovery.career_finder.find_career_page", side_effect=mock_find_career):
            summary = await enrich_jobs_with_career_pages(rate_limit_delay=0.01)

            assert summary["status"] == "success"
            assert summary["unique_domains_processed"] == 2
            assert summary["discovered_career_pages_count"] == 2

            jobs = temp_manager.state.extracted_jobs
            assert jobs[0]["career_page_url"] == "https://www.rockstargames.com/careers"
            assert jobs[1]["career_page_url"] == "https://www.figma.com/careers"


async def main():
    test_is_ats_url()
    test_is_career_link()
    await test_extract_navigation_links()
    await test_find_career_page_heuristic_hit()
    await test_find_career_page_dom_search_hit()

    import tempfile
    with tempfile.TemporaryDirectory() as tmp_dir:
        await test_enrich_jobs_with_career_pages_mocked(Path(tmp_dir))

    print("\n[SUCCESS] All Career Page Navigator tests passed successfully!")


if __name__ == "__main__":
    asyncio.run(main())
