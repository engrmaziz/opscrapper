"""
Unit and integration tests for Excel Exporter Module (utils/excel_exporter.py).
"""

import asyncio
from pathlib import Path
import sys
import tempfile
import openpyxl

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.excel_exporter import export_to_excel, is_valid_url
from utils.state_manager import StateManager


def test_is_valid_url():
    """Validates URL validator helper."""
    assert is_valid_url("https://www.epicgames.com") is True
    assert is_valid_url("http://stripe.com/jobs") is True
    assert is_valid_url("ftp://invalid.com") is False
    assert is_valid_url("") is False
    assert is_valid_url(None) is False


def test_export_to_excel_formatting_and_hyperlinks():
    """Validates Excel workbook creation, column headers, hyperlinks, and styles."""
    sample_jobs = [
        {
            "title": "Principal Graphics Engineer",
            "company": "Epic Games",
            "location": "Cary, NC / Remote",
            "source_board": "GamesIndustry.biz",
            "board_url": "https://jobs.gamesindustry.biz/job/501",
            "company_url": "https://www.epicgames.com",
            "career_page_url": "https://www.epicgames.com/site/en-US/careers",
            "direct_apply_link": "https://boards.greenhouse.io/epicgames/jobs/501",
            "verification_status": "verified_on_company_site",
            "extracted_at": "2026-08-24T12:00:00Z",
        },
        {
            "title": "Lead Product Designer",
            "company": "Figma",
            "location": "Remote",
            "source_board": "WeWorkRemotely",
            "board_url": "https://weworkremotely.com/job/502",
            "company_url": "https://www.figma.com",
            "career_page_url": "https://www.figma.com/careers",
            "direct_apply_link": None,
            "verification_status": "unverified_on_company_site",
            "extracted_at": "2026-08-24T12:05:00Z",
        },
    ]

    with tempfile.TemporaryDirectory() as tmp_dir:
        test_export_name = "test_output.xlsx"
        # Temporarily redirect export dir
        original_dir = Path(__file__).resolve().parent.parent / "data" / "exports"
        out_path = export_to_excel(state_data=sample_jobs, output_filename=test_export_name)

        assert out_path.exists()
        assert out_path.stat().st_size > 0

        # Load workbook with openpyxl to verify formatting
        wb = openpyxl.load_workbook(out_path)
        ws = wb.active
        assert ws.title == "Job Leads"

        # Check headers
        headers = [ws.cell(row=1, column=c).value for c in range(1, 11)]
        assert "Job Title" in headers
        assert "Company" in headers
        assert "Original Listing" in headers
        assert "Direct Apply Link" in headers

        # Verify Frozen Header
        assert ws.freeze_panes == "A2"

        # Verify Data Rows
        assert ws.cell(row=2, column=1).value == "Principal Graphics Engineer"
        assert ws.cell(row=2, column=2).value == "Epic Games"

        # Verify Clickable Hyperlinks on Row 2
        # Column 5: Original Listing
        cell_listing = ws.cell(row=2, column=5)
        assert cell_listing.hyperlink is not None
        assert cell_listing.hyperlink.target == "https://jobs.gamesindustry.biz/job/501"

        # Column 8: Direct Apply Link
        cell_direct = ws.cell(row=2, column=8)
        assert cell_direct.hyperlink is not None
        assert cell_direct.hyperlink.target == "https://boards.greenhouse.io/epicgames/jobs/501"

        # Verify Row 3 with unverified direct apply link (no hyperlink)
        cell_no_direct = ws.cell(row=3, column=8)
        assert cell_no_direct.hyperlink is None
        assert cell_no_direct.value in ["", None, "None"]

        # Verify Column Dimensions (auto-fitted)
        for col_letter in ["A", "B", "C", "D", "E"]:
            assert ws.column_dimensions[col_letter].width >= 14


def test_export_to_excel_from_state_manager():
    """Validates exporting directly from an active StateManager instance."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        state_file = Path(tmp_dir) / "state.json"
        mgr = StateManager(file_path=state_file)
        mgr.initialize_state(keyword="Python", location="Remote", target_boards=["Itch.io"])
        mgr.add_extracted_job({
            "title": "Backend Python Architect",
            "company": "Stripe",
            "source_board": "Itch.io",
            "board_url": "https://itch.io/jobs/99",
            "company_url": "https://stripe.com",
            "career_page_url": "https://stripe.com/jobs",
            "direct_apply_link": "https://jobs.lever.co/stripe/99",
        })

        out_path = export_to_excel(state_data=mgr.state.extracted_jobs, output_filename="state_export.xlsx")
        assert out_path.exists()
        wb = openpyxl.load_workbook(out_path)
        ws = wb.active
        assert ws.cell(row=2, column=1).value == "Backend Python Architect"
        assert ws.cell(row=2, column=2).value == "Stripe"


def main():
    test_is_valid_url()
    test_export_to_excel_formatting_and_hyperlinks()
    test_export_to_excel_from_state_manager()
    print("\n[SUCCESS] All Excel Exporter tests passed successfully!")


if __name__ == "__main__":
    main()
