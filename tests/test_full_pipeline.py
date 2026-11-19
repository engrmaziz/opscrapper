"""
End-to-End Integration Test for the complete 5-phase Job Scraping & ATS Discovery Pipeline.
"""

import asyncio
from pathlib import Path
import sys
import tempfile
import unittest.mock as mock
import openpyxl

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from main import run_orchestrator
from utils.state_manager import StateManager
from utils.excel_exporter import export_to_excel


async def test_complete_orchestration_pipeline():
    """Runs a mocked full 5-phase pipeline and validates Excel report generation."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        test_state_file = Path(tmp_dir) / "e2e_state.json"
        temp_manager = StateManager(file_path=test_state_file)

        async def mock_runner_weworkremotely(*args, **kwargs):
            return [{
                "title": "Staff Backend Engineer",
                "company": "Stripe",
                "source_board": "WeWorkRemotely",
                "board_url": "https://weworkremotely.com/jobs/101",
                "location": "Remote",
            }]

        async def mock_runner_simplyhired(*args, **kwargs):
            return [{
                "title": "Senior Frontend Developer",
                "company": "Figma",
                "source_board": "SimplyHired",
                "board_url": "https://www.simplyhired.com/job/201",
                "location": "Remote",
            }]

        async def mock_runner_gamesjobsdirect(*args, **kwargs):
            return [{
                "title": "Lead Gameplay Programmer",
                "company": "Epic Games",
                "source_board": "GamesJobsDirect",
                "board_url": "https://www.gamesjobsdirect.com/job/301",
                "location": "Remote",
            }]

        def mock_get_board_runner(board_name):
            mapping = {
                "WeWorkRemotely": mock_runner_weworkremotely,
                "SimplyHired": mock_runner_simplyhired,
                "GamesJobsDirect": mock_runner_gamesjobsdirect,
            }
            return mapping.get(board_name)

        async def mock_process_lead(raw_job, keyword, **kwargs):
            enriched = dict(raw_job)
            comp = str(raw_job.get("company", "")).lower()
            if "stripe" in comp:
                enriched["company_url"] = "https://stripe.com"
                enriched["career_page_url"] = "https://stripe.com/jobs"
                enriched["direct_apply_link"] = "https://jobs.lever.co/stripe/101"
                enriched["verification_status"] = "verified_on_company_site"
            elif "figma" in comp:
                enriched["company_url"] = "https://figma.com"
                enriched["career_page_url"] = "https://figma.com/careers"
                enriched["direct_apply_link"] = "https://jobs.ashbyhq.com/figma/201"
                enriched["verification_status"] = "verified_on_company_site"
            else:
                enriched["company_url"] = "https://epicgames.com"
                enriched["career_page_url"] = "https://epicgames.com/careers"
                enriched["direct_apply_link"] = "https://boards.greenhouse.io/epicgames/jobs/301"
                enriched["verification_status"] = "verified_on_company_site"
            return enriched

        with mock.patch("main.state_manager", temp_manager), \
             mock.patch("discovery.per_job_orchestrator.state_manager", temp_manager), \
             mock.patch("discovery.per_job_orchestrator.get_board_runner", side_effect=mock_get_board_runner), \
             mock.patch("discovery.per_job_orchestrator.process_single_job_lead", side_effect=mock_process_lead):
            await run_orchestrator(
                keyword="Software Engineer",
                location="Remote",
                target_boards=["WeWorkRemotely", "SimplyHired", "GamesJobsDirect"],
                force_reset=True,
            )

        # Verify state persistence
        assert temp_manager.state is not None
        assert temp_manager.state.total_jobs_extracted == 3

        jobs = temp_manager.state.extracted_jobs
        assert all(j.get("direct_apply_link") for j in jobs)
        assert all(j.get("company_url") for j in jobs)
        assert all(j.get("career_page_url") for j in jobs)

        # Export and verify final workbook
        out_excel = export_to_excel(state_data=jobs, output_filename="e2e_verified_leads.xlsx")
        assert out_excel.exists()

        wb = openpyxl.load_workbook(out_excel)
        ws = wb.active
        assert ws.max_row == 4  # 1 header + 3 data rows
        assert ws.cell(row=2, column=1).value == "Staff Backend Engineer"
        assert ws.cell(row=2, column=8).hyperlink.target == "https://jobs.lever.co/stripe/101"


async def main():
    await test_complete_orchestration_pipeline()
    print("\n[SUCCESS] Full 5-Phase End-to-End Orchestration Pipeline verified successfully!")


if __name__ == "__main__":
    asyncio.run(main())
