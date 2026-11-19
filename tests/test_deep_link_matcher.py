"""
Unit and integration tests for Deep Link Matcher & ATS Verification Engine (discovery/deep_link_matcher.py and StateManager updates).
"""

import asyncio
from pathlib import Path
import sys
import unittest.mock as mock

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from discovery.deep_link_matcher import (
    is_ats_or_direct_apply_link,
    tokenize_title,
    calculate_title_match_score,
    extract_iframe_src,
    find_direct_apply_link,
    verify_and_extract_direct_links,
)
from utils.state_manager import StateManager


def test_is_ats_or_direct_apply_link():
    """Validates detection of ATS platform domains and direct apply path routes."""
    assert is_ats_or_direct_apply_link("https://boards.greenhouse.io/stripe/jobs/5001") is True
    assert is_ats_or_direct_apply_link("https://jobs.lever.co/epicgames/1234-abcd") is True
    assert is_ats_or_direct_apply_link("https://epicgames.wd5.myworkdayjobs.com/Careers/job/123") is True
    assert is_ats_or_direct_apply_link("https://jobs.ashbyhq.com/anthropic/5678") is True
    assert is_ats_or_direct_apply_link("https://company.com/careers/job/backend-engineer/apply") is True
    assert is_ats_or_direct_apply_link("https://company.com/about/contact") is False


def test_tokenize_title_and_match_score():
    """Validates title tokenization and fuzzy matching logic."""
    tokens = tokenize_title("Senior UI/UX Designer")
    assert "senior" in tokens
    assert "ui" in tokens
    assert "ux" in tokens
    assert "designer" in tokens

    # Score should be high for matching UI/UX Designer to UI Designer on Greenhouse
    score_match = calculate_title_match_score(
        job_title="UI/UX Designer",
        candidate_text="UI Designer",
        candidate_url="https://boards.greenhouse.io/co/jobs/1",
    )
    score_mismatch = calculate_title_match_score(
        job_title="UI/UX Designer",
        candidate_text="Staff Infrastructure Engineer",
        candidate_url="https://company.com/engineering",
    )
    assert score_match > score_mismatch
    assert score_match >= 2.0


def test_extract_iframe_src():
    """Validates extraction of embedded Workday/Greenhouse iframes."""
    html_with_iframe = """
    <html><body>
        <div class="career-portal">
            <iframe src="https://myworkdayjobs.com/embed/company/jobs" width="100%"></iframe>
        </div>
    </body></html>
    """
    src = extract_iframe_src(html_with_iframe, "https://company.com/careers")
    assert src == "https://myworkdayjobs.com/embed/company/jobs"

    html_without_iframe = "<html><body><div>No iframe</div></body></html>"
    assert extract_iframe_src(html_without_iframe, "https://company.com") is None


async def test_find_direct_apply_link_mocked():
    """Tests scanning career portal HTML to find direct apply link."""
    career_html = """
    <html><body>
        <div class="jobs-list">
            <div class="job-item">
                <h3>Lead Gameplay Programmer</h3>
                <a href="https://jobs.lever.co/rockstargames/gameplay-prog-1">Apply on Lever</a>
            </div>
            <div class="job-item">
                <h3>Financial Analyst</h3>
                <a href="https://jobs.lever.co/rockstargames/finance-1">Apply on Lever</a>
            </div>
        </div>
    </body></html>
    """
    with mock.patch("discovery.deep_link_matcher.fetch_page_content", return_value=career_html):
        direct_url = await find_direct_apply_link(
            career_page_url="https://www.rockstargames.com/careers",
            job_title="Lead Gameplay Programmer",
        )
        assert direct_url == "https://jobs.lever.co/rockstargames/gameplay-prog-1"


async def test_verify_and_extract_direct_links_mocked(tmp_path: Path):
    """Tests batch direct link verification pipeline and StateManager updates."""
    test_state_file = tmp_path / "test_deep_link_state.json"
    temp_manager = StateManager(file_path=test_state_file)
    temp_manager.initialize_state(keyword="Programmer", location="Remote", target_boards=["GamesIndustry.biz"])

    # Add test jobs with career_page_url
    temp_manager.add_extracted_job({
        "title": "Lead Gameplay Programmer",
        "company": "Rockstar Games",
        "career_page_url": "https://www.rockstargames.com/careers",
        "source_board": "GamesIndustry.biz",
        "board_url": "https://jobs.gamesindustry.biz/job/1",
    })
    temp_manager.add_extracted_job({
        "title": "Senior AI Engineer",
        "company": "Stripe",
        "career_page_url": "https://stripe.com/jobs",
        "source_board": "WeWorkRemotely",
        "board_url": "https://weworkremotely.com/job/2",
    })

    async def mock_find_link(career_page_url: str = "", job_title: str = "", **kwargs):
        if "rockstar" in str(career_page_url).lower() and "programmer" in str(job_title).lower():
            return "https://jobs.lever.co/rockstargames/prog-1"
        return None  # Stripe job not verified on page

    with mock.patch("discovery.deep_link_matcher.state_manager", temp_manager):
        with mock.patch("discovery.deep_link_matcher.find_direct_apply_link", side_effect=mock_find_link):
            summary = await verify_and_extract_direct_links(rate_limit_delay=0.01)

            assert summary["status"] == "success"
            assert summary["total_pending_processed"] == 2
            assert summary["verified_direct_links_count"] == 1
            assert summary["unverified_count"] == 1

            jobs = temp_manager.state.extracted_jobs
            assert jobs[0]["direct_apply_link"] == "https://jobs.lever.co/rockstargames/prog-1"
            assert jobs[0]["verification_status"] == "verified_on_company_site"

            assert jobs[1]["direct_apply_link"] is None
            assert jobs[1]["verification_status"] == "unverified_on_company_site"


async def main():
    test_is_ats_or_direct_apply_link()
    test_tokenize_title_and_match_score()
    test_extract_iframe_src()
    await test_find_direct_apply_link_mocked()

    import tempfile
    with tempfile.TemporaryDirectory() as tmp_dir:
        await test_verify_and_extract_direct_links_mocked(Path(tmp_dir))

    print("\n[SUCCESS] All Deep Link Matcher & ATS Verification tests passed successfully!")


if __name__ == "__main__":
    asyncio.run(main())
