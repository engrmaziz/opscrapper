"""
Scrapers package for the Autonomous Multi-Platform Job-Scraping Agent.
"""

from .board_registry import (
    BOARD_METADATA_REGISTRY,
    get_board_metadata,
    get_board_runner,
    list_all_boards,
)
from .standard_boards import is_valid_job

__all__ = [
    "BOARD_METADATA_REGISTRY",
    "get_board_metadata",
    "get_board_runner",
    "list_all_boards",
    "is_valid_job",
]
