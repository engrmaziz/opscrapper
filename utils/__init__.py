"""
Utilities package for the Autonomous Job-Scraping Agent.
"""

from .state_manager import StateManager, state_manager, JobRecord, ScrapeState
from .excel_exporter import export_to_excel

__all__ = [
    "StateManager",
    "state_manager",
    "JobRecord",
    "ScrapeState",
    "export_to_excel",
]
