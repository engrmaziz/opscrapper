"""
Unit and integration tests for Company URL Discovery Engine (tools/web_search.py, discovery/domain_finder.py, and StateManager updates).
"""

import asyncio
from pathlib import Path
import sys
import unittest.mock as mock

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from discovery.domain_finder import (
    is_blocked_domain,
    extract_root_domain,
    calculate_domain_relevance,
    find_company_official_url,
    enrich_jobs_with_company_urls,
)
from utils.state_manager import StateManager


def test_blocked_domain_filtering():
    """Validates that job boards, directories, and social platforms are properly blocked."""
    assert is_blocked_domain("https://www.linkedin.com/company/epic-games") is True
    assert is_blocked_domain("https://glassdoor.com/Reviews/Stripe") is True
    assert is_blocked_domain("https://en.wikipedia.org/wiki/Rockstar_Games") is True
    assert is_blocked_domain("https://indeed.com/cmp/Epic-Games") is True
    assert is_blocked_domain("https://twitter.com/stripe") is True

    # Real company domains should not be blocked
    assert is_blocked_domain("https://www.epicgames.com") is False
    assert is_blocked_domain("https://stripe.com") is False
    assert is_blocked_domain("https://about.gitlab.com") is False


def test_extract_root_domain():
    """Validates clean root domain extraction and scheme normalization."""
    assert extract_root_domain("https://www.epicgames.com/site/en-US/home") == "https://www.epicgames.com"
    assert extract_root_domain("http://stripe.com/docs/api") == "http://stripe.com"
    assert extract_root_domain("https://sub.domain.co.uk/page/123") == "https://sub.domain.co.uk"
    assert extract_root_domain("invalid-url-string") is None


def test_calculate_domain_relevance():
    """Tests relevance scoring between company names and Candidate domains."""
    score_epic = calculate_domain_relevance("Epic Games", "https://www.epicgames.com", "Epic Games Official Site")
    score_random = calculate_domain_relevance("Epic Games", "https://www.random-unrelated-blog.org", "Random Tech Blog")
    assert score_epic > score_random
    assert score_epic >= 1.5

    score_stripe = calculate_domain_relevance("Stripe Inc", "https://stripe.com", "Stripe: Financial Infrastructure")
    assert score_stripe >= 1.5


async def test_find_company_official_url_mocked():
    """Tests official URL discovery with mocked search results."""
    mock_hits = [
        {"title": "Epic Games - Wikipedia", "url": "https://en.wikipedia.org/wiki/Epic_Games", "snippet": "Encyclopedia entry"},
        {"title": "Working at Epic Games | LinkedIn", "url": "https://www.linkedin.com/company/epic-games", "snippet": "Job board"},
        {"title": "Epic Games | Store, Games & Unreal Engine", "url": "https://www.epicgames.com/site/en-US/home", "snippet": "Official site"},
    ]

    with mock.patch("discovery.domain_finder.probe_direct_domain", return_value=None):
        with mock.patch("discovery.domain_finder.search_web", return_value=mock_hits):
            official_url = await find_company_official_url("Epic Games")
            assert official_url == "https://www.epicgames.com"


async def test_enrich_jobs_with_company_urls_mocked(tmp_path: Path):
    """Tests end-to-end enrichment pipeline and StateManager updates."""
    test_state_file = tmp_path / "test_enrichment_state.json"
    temp_manager = StateManager(file_path=test_state_file)
    temp_manager.initialize_state(keyword="Dev", location="Remote", target_boards=["Itch.io"])

    # Add test jobs missing company_url
    temp_manager.add_extracted_job({
        "title": "Lead Game Designer",
        "company": "Epic Games",
        "source_board": "Itch.io",
        "board_url": "https://itch.io/jobs/1",
    })
    temp_manager.add_extracted_job({
        "title": "Senior Frontend Engineer",
        "company": "Stripe",
        "source_board": "WeWorkRemotely",
        "board_url": "https://weworkremotely.com/jobs/2",
    })

    # Test update_job_field directly
    assert temp_manager.update_job_field(0, "location", "Cary, NC") is True
    assert temp_manager.state.extracted_jobs[0]["location"] == "Cary, NC"

    # Mock domain finder responses
    async def mock_find_url(company: str):
        if "epic" in company.lower():
            return "https://www.epicgames.com"
        elif "stripe" in company.lower():
            return "https://stripe.com"
        return None

    with mock.patch("discovery.domain_finder.state_manager", temp_manager):
        with mock.patch("discovery.domain_finder.find_company_official_url", side_effect=mock_find_url):
            summary = await enrich_jobs_with_company_urls(rate_limit_delay=0.01)

            assert summary["status"] == "success"
            assert summary["unique_companies_processed"] == 2
            assert summary["urls_discovered_count"] == 2

            # Verify that state records have company_url populated and saved
            jobs = temp_manager.state.extracted_jobs
            assert jobs[0]["company_url"] == "https://www.epicgames.com"
            assert jobs[1]["company_url"] == "https://stripe.com"


async def main():
    test_blocked_domain_filtering()
    test_extract_root_domain()
    test_calculate_domain_relevance()
    await test_find_company_official_url_mocked()

    import tempfile
    with tempfile.TemporaryDirectory() as tmp_dir:
        await test_enrich_jobs_with_company_urls_mocked(Path(tmp_dir))

    print("\n[SUCCESS] All Company URL Discovery Engine tests passed successfully!")


if __name__ == "__main__":
    asyncio.run(main())
