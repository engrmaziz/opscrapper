"""
Agent tool wrappers for StateManager operations (recording leads, updating board progress, querying state).
"""

from typing import Any, Dict, List, Optional
from .base import BaseAgentTool, registry
from utils.state_manager import state_manager, JobRecord


class AddExtractedJobTool(BaseAgentTool):
    """Tool allowing the agent to save an extracted job lead with immediate disk persistence."""

    name = "add_extracted_job"
    description = (
        "Records an extracted job listing into persistent state on disk. "
        "Deduplicates automatically and updates session telemetry."
    )

    async def execute(
        self,
        title: str,
        company: str,
        source_board: str,
        location: str = "Remote",
        board_url: Optional[str] = None,
        company_url: Optional[str] = None,
        career_page_url: Optional[str] = None,
        direct_apply_link: Optional[str] = None,
        salary: Optional[str] = None,
        date_posted: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Executes job lead insertion into state."""
        job_record = JobRecord(
            title=title,
            company=company,
            source_board=source_board,
            location=location,
            board_url=board_url,
            company_url=company_url,
            career_page_url=career_page_url,
            direct_apply_link=direct_apply_link,
            salary=salary,
            date_posted=date_posted,
        )
        added = state_manager.add_extracted_job(job_record)
        return {
            "success": added,
            "status": "added" if added else "skipped_duplicate",
            "total_jobs": state_manager.state.total_jobs_extracted if state_manager.state else 0,
            "job": job_record.model_dump(),
        }


class UpdateBoardStatusTool(BaseAgentTool):
    """Tool allowing the agent to mark a job board as completed, skipped, or failed."""

    name = "update_board_status"
    description = (
        "Updates the progress status of a specific job board (e.g., 'completed', 'in_progress', 'failed'). "
        "Advances the pending queue and saves to disk."
    )

    async def execute(
        self,
        board_name: str,
        status: str = "completed",
        jobs_found: Optional[int] = None,
        error: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Executes board status update."""
        state_manager.update_board_status(
            board_name=board_name,
            status=status,
            error=error,
            jobs_found=jobs_found,
        )
        return {
            "success": True,
            "board_name": board_name,
            "status": status,
            "summary": state_manager.get_summary(),
        }


class GetScrapeStateTool(BaseAgentTool):
    """Tool allowing the agent to inspect the current session state and remaining pending boards."""

    name = "get_scrape_state"
    description = "Retrieves the active session state summary, completed boards, and remaining pending boards."

    async def execute(self) -> Dict[str, Any]:
        """Returns the current state summary."""
        return state_manager.get_summary()


# Register state tools into the global registry
registry.register(AddExtractedJobTool())
registry.register(UpdateBoardStatusTool())
registry.register(GetScrapeStateTool())
