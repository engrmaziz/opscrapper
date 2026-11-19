import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from discovery.per_job_orchestrator import run_per_job_pipeline
from utils.state_manager import state_manager

async def test_live():
    # Test with user's exact typo: "digital markter"
    keyword = "digital markter"
    print(f"Testing live per-job pipeline for keyword: '{keyword}'...")
    
    # Test on top verified public boards that have live APIs
    target_boards = ["Arbeitnow", "Jobicy", "RemoteOK", "Himalayas", "Remotive"]
    
    result = await run_per_job_pipeline(
        keyword=keyword,
        location="Remote",
        target_boards=target_boards,
        max_jobs_per_board=5,
        resume=False,
    )
    
    print("\n" + "=" * 60)
    print("RESULTS:")
    print("=" * 60)
    print(f"Total jobs extracted: {result.get('total_jobs_extracted')}")
    print(f"Excel export: {result.get('excel_path')}")
    
    jobs = state_manager.state.extracted_jobs if state_manager.state else []
    for idx, j in enumerate(jobs, 1):
        print(f"\n[{idx}] {j.get('title')} at {j.get('company')}")
        print(f"    Board: {j.get('source_board')} ({j.get('board_url')})")
        print(f"    Company URL: {j.get('company_url')}")
        print(f"    Career URL: {j.get('career_page_url')}")
        print(f"    Direct ATS Link: {j.get('direct_apply_link')}")
        
    # Validation checks
    assert len(jobs) > 0, "No jobs were returned!"
    for j in jobs:
        # Verify no AI Engineer jobs
        title_lower = j.get('title', '').lower()
        assert "ai engineer" not in title_lower, f"Unexpected AI Engineer job: {j.get('title')}"
        # Verify genuine company
        assert j.get('company') not in ["QuantData Analytics", "Amperon Sustainability", "YC Y-Combinator Backed Startup"], f"Fake company found: {j.get('company')}"

if __name__ == "__main__":
    asyncio.run(test_live())
