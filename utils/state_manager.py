"""
State Manager module for tracking job scraping progress, board completions, and extracted leads.
Provides immediate atomic disk persistence, crash-recovery, event subscriptions, and Unicode-safe JSON serialization.
"""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Union
import asyncio
from pydantic import BaseModel, Field
from config.settings import settings
from config.logging_config import get_logger

logger = get_logger("StateManager")


def get_utc_iso_now() -> str:
    """Returns current UTC timestamp in ISO 8601 string format with Z suffix."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class JobRecord(BaseModel):
    """Structured data record for an extracted job posting."""

    title: str = Field(..., description="Job title / role")
    company: str = Field(..., description="Hiring company or organization")
    source_board: str = Field(..., description="Job board where listing was discovered")
    location: Optional[str] = Field(default="Remote", description="Job location or Remote")
    board_url: Optional[str] = Field(default=None, description="Listing URL on the job board")
    company_url: Optional[str] = Field(default=None, description="Company homepage URL")
    career_page_url: Optional[str] = Field(default=None, description="Company direct career portal / ATS")
    direct_apply_link: Optional[str] = Field(default=None, description="Direct link to apply on company ATS")
    salary: Optional[str] = Field(default=None, description="Salary or compensation details")
    date_posted: Optional[str] = Field(default=None, description="Posting date")
    verification_status: Optional[str] = Field(default="board_extracted", description="Enrichment & verification status")
    extracted_at: str = Field(
        default_factory=get_utc_iso_now,
        description="Timestamp when lead was extracted",
    )


class ScrapeState(BaseModel):
    """Complete schema for tracking persistent session state."""

    session_id: str = Field(..., description="Unique scrape session ID")
    keyword: str = Field(..., description="Target search role / keyword")
    location: str = Field(default="Remote", description="Target search location")
    created_at: str = Field(default_factory=get_utc_iso_now)
    updated_at: str = Field(default_factory=get_utc_iso_now)
    status: str = Field(default="initialized", description="Current session status")
    target_boards: List[str] = Field(default_factory=list, description="All target job boards")
    job_boards_completed: List[str] = Field(default_factory=list, description="Completed boards")
    job_boards_pending: List[str] = Field(default_factory=list, description="Pending boards")
    current_job_board: Optional[str] = Field(default=None, description="Currently scraping board")
    extracted_jobs: List[Dict[str, Any]] = Field(default_factory=list, description="Extracted job leads")
    total_jobs_extracted: int = Field(default=0, description="Total count of extracted jobs")
    board_stats: Dict[str, Dict[str, Any]] = Field(default_factory=dict, description="Per-board statistics")
    last_error: Optional[str] = Field(default=None, description="Last recorded error if any")


class StateManager:
    """Manages persistent scrape state on disk with immediate atomic writes and real-time event broadcasting."""

    def __init__(self, file_path: Optional[Path] = None) -> None:
        self.file_path: Path = file_path or settings.STATE_FILE_PATH
        self._state: Optional[ScrapeState] = None
        self._seen_job_keys: Set[str] = set()
        self._listeners: List[Callable[[str, Dict[str, Any]], Any]] = []

        # Ensure parent directory exists
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

    @property
    def state(self) -> Optional[ScrapeState]:
        """Returns the active ScrapeState instance."""
        return self._state

    def add_listener(self, listener: Callable[[str, Dict[str, Any]], Any]) -> None:
        """Subscribes an event listener (for SSE / WebSockets) to state changes."""
        if listener not in self._listeners:
            self._listeners.append(listener)

    def remove_listener(self, listener: Callable[[str, Dict[str, Any]], Any]) -> None:
        """Unsubscribes an event listener."""
        if listener in self._listeners:
            self._listeners.remove(listener)

    def emit_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Broadcasts an event to all subscribed listeners."""
        for listener in list(self._listeners):
            try:
                res = listener(event_type, data)
                if asyncio.iscoroutine(res):
                    try:
                        loop = asyncio.get_running_loop()
                        loop.create_task(res)
                    except RuntimeError:
                        pass
            except Exception as e:
                logger.debug(f"Listener notification error: {e}")

    def initialize_state(
        self,
        keyword: str,
        location: str = "Remote",
        target_boards: Optional[List[str]] = None,
        force_reset: bool = False,
    ) -> Dict[str, Any]:
        """Initializes a new scrape session or loads existing state if matching and not forced.

        Args:
            keyword: Target search keyword.
            location: Target location.
            target_boards: List of target job board names.
            force_reset: If True, overwrites existing state on disk.

        Returns:
            Dict containing the active state data.
        """
        boards = list(target_boards or settings.TARGET_JOB_BOARDS)

        # Check if an existing state can be loaded without force_reset
        if not force_reset and self.file_path.exists():
            existing = self.load_previous_state()
            if existing and existing.keyword.lower() == keyword.lower():
                logger.info(
                    f"Found existing state for '{keyword}'. Resuming session '{existing.session_id}' "
                    f"({len(existing.job_boards_completed)}/{len(existing.target_boards)} boards completed)."
                )
                self._state = existing
                self._rebuild_seen_job_keys()
                self.emit_event("session_resumed", self._state.model_dump())
                return self._state.model_dump()

        session_id = f"scrape_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        now = get_utc_iso_now()

        # Initialize board stats
        board_stats: Dict[str, Dict[str, Any]] = {
            board: {"status": "pending", "jobs_found": 0, "completed_at": None, "error": None}
            for board in boards
        }

        self._state = ScrapeState(
            session_id=session_id,
            keyword=keyword,
            location=location,
            created_at=now,
            updated_at=now,
            status="running",
            target_boards=boards,
            job_boards_completed=[],
            job_boards_pending=list(boards),
            current_job_board=boards[0] if boards else None,
            extracted_jobs=[],
            total_jobs_extracted=0,
            board_stats=board_stats,
            last_error=None,
        )
        self._seen_job_keys.clear()
        self._save_to_disk()
        logger.info(f"Initialized fresh scrape state for keyword '{keyword}' across {len(boards)} boards.")
        self.emit_event("session_started", self._state.model_dump())
        return self._state.model_dump()

    def load_previous_state(self) -> Optional[ScrapeState]:
        """Loads and parses the existing state file from disk.

        Returns:
            ScrapeState instance if file exists and is valid, else None.
        """
        if not self.file_path.exists():
            return None

        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._state = ScrapeState(**data)
            self._rebuild_seen_job_keys()
            logger.info(
                f"Successfully loaded previous state: Session '{self._state.session_id}', "
                f"Status '{self._state.status}', Jobs collected: {self._state.total_jobs_extracted}."
            )
            return self._state
        except (json.JSONDecodeError, ValueError, Exception) as e:
            logger.warning(f"Could not load state from {self.file_path}: {e}")
            return None

    def has_resumable_state(self, keyword: Optional[str] = None) -> bool:
        """Checks if a valid, uncompleted scrape state exists on disk."""
        prev = self.load_previous_state()
        if not prev:
            return False
        if prev.status == "completed":
            return False
        if keyword and prev.keyword.lower() != keyword.lower():
            return False
        return len(prev.job_boards_pending) > 0 or prev.status in ["running", "paused", "initialized"]

    def set_current_board(self, board_name: str) -> None:
        """Sets the currently active job board and persists to disk."""
        if not self._state:
            raise RuntimeError("StateManager is not initialized. Call initialize_state() first.")

        self._state.current_job_board = board_name
        self._state.updated_at = get_utc_iso_now()
        if board_name in self._state.board_stats:
            self._state.board_stats[board_name]["status"] = "in_progress"
        self._save_to_disk()
        logger.info(f"State updated: Current active board set to '{board_name}'.")
        self.emit_event("board_active", {"board": board_name, "status": "in_progress"})

    def update_board_status(
        self,
        board_name: str,
        status: str = "completed",
        error: Optional[str] = None,
        jobs_found: Optional[int] = None,
    ) -> None:
        """Updates status of a specific job board and persists immediately to disk."""
        if not self._state:
            raise RuntimeError("StateManager is not initialized. Call initialize_state() first.")

        now = get_utc_iso_now()
        self._state.updated_at = now

        if board_name not in self._state.board_stats:
            self._state.board_stats[board_name] = {}

        stats = self._state.board_stats[board_name]
        stats["status"] = status
        stats["error"] = error
        if jobs_found is not None:
            stats["jobs_found"] = jobs_found
        if status in ["completed", "skipped", "failed", "blocked"]:
            stats["completed_at"] = now

        if status == "completed":
            if board_name not in self._state.job_boards_completed:
                self._state.job_boards_completed.append(board_name)
            if board_name in self._state.job_boards_pending:
                self._state.job_boards_pending.remove(board_name)

        if error:
            self._state.last_error = f"Board '{board_name}': {error}"

        # Determine next pending board
        next_board = self.get_next_pending_board()
        self._state.current_job_board = next_board

        # Check if all boards are done
        if not self._state.job_boards_pending:
            self._state.status = "completed"
            logger.info("All target job boards have been completed!")

        self._save_to_disk()
        logger.info(
            f"State updated: Board '{board_name}' status set to '{status}'. "
            f"Remaining pending boards: {len(self._state.job_boards_pending)}."
        )
        self.emit_event(
            "board_updated",
            {
                "board": board_name,
                "status": status,
                "jobs_found": stats.get("jobs_found", 0),
                "error": error,
                "completed_count": len(self._state.job_boards_completed),
                "total_boards": len(self._state.target_boards),
            },
        )

    def is_board_completed(self, board_name: str) -> bool:
        """Checks if a job board has already been completed in state."""
        if not self._state:
            return False
        return board_name in self._state.job_boards_completed

    def get_next_pending_board(self) -> Optional[str]:
        """Returns the next job board pending execution, or None if all are completed."""
        if not self._state:
            return None
        return self._state.job_boards_pending[0] if self._state.job_boards_pending else None

    def add_extracted_job(self, job: Union[Dict[str, Any], JobRecord]) -> bool:
        """Adds an extracted job record to state with immediate disk persistence and deduplication.

        Args:
            job: Dict or JobRecord containing job attributes.

        Returns:
            True if job was added, False if duplicate skipped.
        """
        if not self._state:
            raise RuntimeError("StateManager is not initialized. Call initialize_state() first.")

        job_dict = job.model_dump() if isinstance(job, JobRecord) else dict(job)

        # Standardize required fields
        title = str(job_dict.get("title", "")).strip()
        company = str(job_dict.get("company", "")).strip()
        source_board = str(job_dict.get("source_board", "") or job_dict.get("board_source", "")).strip()

        if not title or not company:
            logger.warning(f"Skipping invalid job lead with missing title or company: {job_dict}")
            return False

        # Generate unique deduplication key
        dedup_key = self._generate_dedup_key(title, company, source_board, job_dict.get("board_url") or job_dict.get("listing_url"))
        if dedup_key in self._seen_job_keys:
            logger.debug(f"Skipping duplicate job lead: '{title}' at '{company}' from {source_board}")
            return False

        # Ensure timestamp & default fields
        if not job_dict.get("extracted_at"):
            job_dict["extracted_at"] = get_utc_iso_now()
        if not job_dict.get("source_board"):
            job_dict["source_board"] = source_board
        if not job_dict.get("board_source"):
            job_dict["board_source"] = source_board
        if not job_dict.get("board_url") and job_dict.get("listing_url"):
            job_dict["board_url"] = job_dict.get("listing_url")
        if not job_dict.get("listing_url") and job_dict.get("board_url"):
            job_dict["listing_url"] = job_dict.get("board_url")
        if not job_dict.get("verification_status"):
            job_dict["verification_status"] = "board_extracted"

        self._seen_job_keys.add(dedup_key)
        self._state.extracted_jobs.append(job_dict)
        self._state.total_jobs_extracted = len(self._state.extracted_jobs)
        self._state.updated_at = get_utc_iso_now()

        # Update per-board count
        if source_board and source_board in self._state.board_stats:
            current_count = self._state.board_stats[source_board].get("jobs_found", 0)
            self._state.board_stats[source_board]["jobs_found"] = current_count + 1

        # Immediate persistent write to disk
        self._save_to_disk()
        logger.debug(f"Saved job lead #{self._state.total_jobs_extracted}: '{title}' at '{company}' [{source_board}]")
        self.emit_event(
            "job_added",
            {
                "index": len(self._state.extracted_jobs) - 1,
                "job": job_dict,
                "total_jobs": self._state.total_jobs_extracted,
            },
        )
        return True

    def update_job_lead(self, index: int, updates: Dict[str, Any]) -> bool:
        """Updates fields of a specific job lead by index and persists immediately.

        Args:
            index: Job index in extracted_jobs.
            updates: Dictionary of fields to update.

        Returns:
            True if updated, False otherwise.
        """
        if not self._state or index < 0 or index >= len(self._state.extracted_jobs):
            return False

        job = self._state.extracted_jobs[index]
        job.update(updates)
        self._state.updated_at = get_utc_iso_now()
        self._save_to_disk()

        self.emit_event("job_updated", {"index": index, "job": job})
        return True

    def update_job_field(self, index: int, field_name: str, value: Any) -> bool:
        """Updates a single field on an extracted job by index."""
        return self.update_job_lead(index, {field_name: value})

    def update_jobs_company_url(self, company_name: str, company_url: str) -> int:
        """Updates the company_url for all extracted jobs matching the given company name."""
        if not self._state:
            return 0

        target = company_name.lower().strip()
        updated_count = 0

        for idx, job in enumerate(self._state.extracted_jobs):
            if job.get("company", "").lower().strip() == target:
                job["company_url"] = company_url
                if not job.get("verification_status") or job.get("verification_status") == "board_extracted":
                    job["verification_status"] = "domain_discovered"
                updated_count += 1
                self.emit_event("job_updated", {"index": idx, "job": job})

        if updated_count > 0:
            self._state.updated_at = get_utc_iso_now()
            self._save_to_disk()
            logger.info(f"Updated company_url='{company_url}' across {updated_count} jobs for company '{company_name}'.")

        return updated_count

    def update_jobs_career_page_url(self, company_url: str, career_page_url: str) -> int:
        """Updates the career_page_url for all extracted jobs matching the given company_url."""
        if not self._state or not company_url:
            return 0

        target = company_url.rstrip("/").lower()
        updated_count = 0

        for idx, job in enumerate(self._state.extracted_jobs):
            job_comp_url = str(job.get("company_url", "")).rstrip("/").lower()
            if job_comp_url == target:
                job["career_page_url"] = career_page_url
                if job.get("verification_status") in ["board_extracted", "domain_discovered"]:
                    job["verification_status"] = "career_page_found"
                updated_count += 1
                self.emit_event("job_updated", {"index": idx, "job": job})

        if updated_count > 0:
            self._state.updated_at = get_utc_iso_now()
            self._save_to_disk()
            logger.info(f"Updated career_page_url='{career_page_url}' across {updated_count} jobs.")

        return updated_count

    def update_job_direct_link(
        self,
        job_index: Optional[int] = None,
        direct_link: Optional[str] = None,
        verification_status: str = "verified_on_company_site",
        title: Optional[str] = None,
        company: Optional[str] = None,
    ) -> bool:
        """Updates direct ATS application link and verification status for a specific job lead."""
        if not self._state:
            return False

        if job_index is not None and 0 <= job_index < len(self._state.extracted_jobs):
            job = self._state.extracted_jobs[job_index]
            job["direct_apply_link"] = direct_link
            job["verification_status"] = verification_status
            self._state.updated_at = get_utc_iso_now()
            self._save_to_disk()
            self.emit_event("job_updated", {"index": job_index, "job": job})
            return True

        if title or company:
            target_t = str(title or "").lower().strip()
            target_c = str(company or "").lower().strip()
            for idx, job in enumerate(self._state.extracted_jobs):
                j_title = str(job.get("title", "")).lower().strip()
                j_comp = str(job.get("company", "")).lower().strip()
                if (not target_t or target_t in j_title or j_title in target_t) and (not target_c or target_c in j_comp or j_comp in target_c):
                    job["direct_apply_link"] = direct_link
                    job["verification_status"] = verification_status
                    self._state.updated_at = get_utc_iso_now()
                    self._save_to_disk()
                    self.emit_event("job_updated", {"index": idx, "job": job})
                    return True

        return False

    def get_summary(self) -> Dict[str, Any]:
        """Returns a high-level summary dict of the current scraping progress."""
        if not self._state:
            return {
                "status": "uninitialized",
                "session_id": None,
                "keyword": None,
                "location": None,
                "total_jobs_extracted": 0,
                "completed_boards_count": 0,
                "total_boards": 0,
                "completed_boards": [],
                "pending_boards": [],
                "current_board": None,
                "last_error": None,
            }

        return {
            "status": self._state.status,
            "session_id": self._state.session_id,
            "keyword": self._state.keyword,
            "location": self._state.location,
            "total_jobs_extracted": self._state.total_jobs_extracted,
            "completed_boards_count": len(self._state.job_boards_completed),
            "total_boards": len(self._state.target_boards),
            "completed_boards": list(self._state.job_boards_completed),
            "pending_boards": list(self._state.job_boards_pending),
            "current_board": self._state.current_job_board,
            "board_stats": dict(self._state.board_stats),
            "last_error": self._state.last_error,
            "updated_at": self._state.updated_at,
        }

    def clear_state(self) -> None:
        """Deletes the state file from disk and resets in-memory tracking."""
        if self.file_path.exists():
            try:
                self.file_path.unlink()
                logger.info(f"State file {self.file_path} deleted from disk.")
            except Exception as e:
                logger.warning(f"Failed to delete state file {self.file_path}: {e}")

        self._state = None
        self._seen_job_keys.clear()
        self.emit_event("session_cleared", {})

    def _save_to_disk(self) -> None:
        """Performs atomic disk write using a temporary sibling file."""
        if not self._state:
            return

        temp_path = self.file_path.with_suffix(".tmp")
        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                f.write(self._state.model_dump_json(indent=2))
            temp_path.replace(self.file_path)
        except Exception as e:
            logger.error(f"Failed to atomically persist state to {self.file_path}: {e}", exc_info=True)

    def _rebuild_seen_job_keys(self) -> None:
        """Reconstructs the deduplication set from existing extracted jobs."""
        self._seen_job_keys.clear()
        if not self._state:
            return

        for job in self._state.extracted_jobs:
            title = job.get("title", "")
            company = job.get("company", "")
            board = job.get("source_board", "") or job.get("board_source", "")
            url = job.get("board_url") or job.get("listing_url")
            key = self._generate_dedup_key(title, company, board, url)
            self._seen_job_keys.add(key)

    @staticmethod
    def _generate_dedup_key(title: str, company: str, board: str, url: Optional[str] = None) -> str:
        """Generates a canonical hashable key for a job posting."""
        clean_title = "".join(c for c in title.lower() if c.isalnum())
        clean_company = "".join(c for c in company.lower() if c.isalnum())
        clean_board = "".join(c for c in board.lower() if c.isalnum())
        clean_url = str(url).strip().lower() if url else ""
        return f"{clean_title}::{clean_company}::{clean_board}::{clean_url}"


state_manager = StateManager()
