"""
Unit tests for Sequential Per-Job Deep ATS Enrichment Orchestrator.
"""

import asyncio
from pathlib import Path
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from discovery.per_job_orchestrator import process_single_job_lead, run_per_job_pipeline
from discovery.deep_link_matcher import tokenize_title, calculate_title_match_score, is_ats_or_direct_apply_link
from utils.state_manager import state_manager


def test_deep_link_matcher_heuristics():
    """Verify title tokenization, scoring, and ATS URL detection."""
    ats_url = "https://boards.greenhouse.io/stripe/jobs/123456"
    assert is_ats_or_direct_apply_link(ats_url) is True

    non_ats_url = "https://example.com/about"
    assert is_ats_or_direct_apply_link(non_ats_url) is False

    tokens = tokenize_title("Senior AI / Machine Learning Engineer")
    assert "senior" in tokens
    assert "ai" in tokens
    assert "machine" in tokens
    assert "learning" in tokens
    assert "engineer" in tokens

    score = calculate_title_match_score(
        job_title="AI Engineer",
        candidate_text="Senior AI Engineer - Remote",
        candidate_url="https://boards.greenhouse.io/company/jobs/987",
    )
    assert score >= 2.0, f"Expected match score >= 2.0, got {score}"
    print(f"✅ Deep Link Matcher verified with match score: {score:.2f}")


async def test_per_job_enrichment_flow():
    """Verify single job lead end-to-end enrichment."""
    raw_job = {
        "title": "Lead Software Engineer",
        "company": "GitLab",
        "listing_url": "https://weworkremotely.com/remote-jobs/gitlab-lead-engineer",
        "source_board": "WeWorkRemotely",
        "location": "Remote",
    }

    enriched = await process_single_job_lead(raw_job, keyword="Software Engineer", rate_limit_delay=0.0)
    assert enriched["title"] == "Lead Software Engineer"
    assert enriched["company"] == "GitLab"
    assert enriched["listing_url"] == raw_job["listing_url"]
    assert enriched["source_board"] == "WeWorkRemotely"
    print(f"✅ Single job lead enriched: company_url='{enriched.get('company_url')}', career_page_url='{enriched.get('career_page_url')}', direct_apply_link='{enriched.get('direct_apply_link')}'")


if __name__ == "__main__":
    test_deep_link_matcher_heuristics()
    asyncio.run(test_per_job_enrichment_flow())
    print("\n🎉 All Per-Job Orchestrator tests PASSED successfully!")
