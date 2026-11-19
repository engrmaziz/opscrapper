import json
from pathlib import Path
import sys

# Add project root to sys.path for direct script execution
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import settings
from config.cli import parse_arguments
from utils.state_manager import StateManager, JobRecord


def test_cli_parser_defaults():
    """Validates CLI argument parsing defaults."""
    args = parse_arguments(["--keyword", "UI/UX Designer", "--location", "UK"])
    assert args.keyword == "UI/UX Designer"
    assert args.location == "UK"
    assert args.resume is False


def test_cli_parser_resume():
    """Validates CLI argument parsing with --resume flag."""
    args = parse_arguments(["--resume"])
    assert args.resume is True


def test_state_manager_lifecycle(tmp_path: Path):
    """Tests the full lifecycle of StateManager including atomic writes, deduplication, and crash recovery."""
    test_state_file = tmp_path / "test_scrape_state.json"
    manager = StateManager(file_path=test_state_file)

    # 1. Initialize State
    state = manager.initialize_state(
        keyword="UI/UX Designer",
        location="Remote",
        target_boards=["LinkedIn", "Indeed", "Wellfound"],
    )
    assert state["keyword"] == "UI/UX Designer"
    assert state["status"] == "running"
    assert len(state["job_boards_pending"]) == 3
    assert state["current_job_board"] == "LinkedIn"
    assert test_state_file.exists()

    # 2. Add Job with Unicode Characters
    job1 = {
        "title": "Lead UI/UX Designer 🎨 (München / Zürich)",
        "company": "Designify GmbH & Co.",
        "source_board": "LinkedIn",
        "location": "München, Germany",
        "board_url": "https://linkedin.com/jobs/view/12345",
        "salary": "€95,000 - €120,000",
    }
    added1 = manager.add_extracted_job(job1)
    assert added1 is True
    assert manager.state.total_jobs_extracted == 1

    # Verify JSON file has proper Unicode decoding
    with open(test_state_file, "r", encoding="utf-8") as f:
        saved_data = json.load(f)
    assert saved_data["extracted_jobs"][0]["title"] == "Lead UI/UX Designer 🎨 (München / Zürich)"

    # 3. Deduplication Check
    added_duplicate = manager.add_extracted_job(job1)
    assert added_duplicate is False
    assert manager.state.total_jobs_extracted == 1

    # 4. Add Second Job
    job2 = JobRecord(
        title="Senior Product Designer",
        company="TechCorp Inc",
        source_board="LinkedIn",
        location="Remote",
    )
    added2 = manager.add_extracted_job(job2)
    assert added2 is True
    assert manager.state.total_jobs_extracted == 2

    # 5. Complete First Board
    manager.update_board_status(
        board_name="LinkedIn",
        status="completed",
        jobs_found=2,
    )
    assert "LinkedIn" in manager.state.job_boards_completed
    assert "LinkedIn" not in manager.state.job_boards_pending
    assert manager.state.current_job_board == "Indeed"

    # 6. Simulate Crash & Reload (Crash Recovery)
    reloaded_manager = StateManager(file_path=test_state_file)
    recovered_state = reloaded_manager.load_previous_state()
    assert recovered_state is not None
    assert recovered_state.keyword == "UI/UX Designer"
    assert recovered_state.total_jobs_extracted == 2
    assert recovered_state.job_boards_completed == ["LinkedIn"]
    assert recovered_state.current_job_board == "Indeed"
    assert len(recovered_state.job_boards_pending) == 2

    # 7. Complete Remaining Boards
    reloaded_manager.update_board_status("Indeed", "completed", jobs_found=0)
    reloaded_manager.update_board_status("Wellfound", "completed", jobs_found=1)
    assert reloaded_manager.state.status == "completed"
    assert len(reloaded_manager.state.job_boards_pending) == 0

    print("\n[SUCCESS] All StateManager & CLI tests passed successfully!")


if __name__ == "__main__":
    import tempfile

    with tempfile.TemporaryDirectory() as tmp_dir:
        test_cli_parser_defaults()
        test_cli_parser_resume()
        test_state_manager_lifecycle(Path(tmp_dir))
