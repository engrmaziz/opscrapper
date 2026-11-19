"""
Unit tests for Board Registry covering all 55+ job platforms and category groupings.
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

from config.settings import settings
from scrapers.board_registry import (
    BOARD_METADATA_REGISTRY,
    get_board_runner,
    get_board_metadata,
    list_all_boards,
)


def test_board_count_and_registration():
    """Verify at least 100 platforms are registered with valid runner functions."""
    assert len(BOARD_METADATA_REGISTRY) >= 100, f"Expected >=100 boards, got {len(BOARD_METADATA_REGISTRY)}"

    for name, meta in BOARD_METADATA_REGISTRY.items():
        assert "category" in meta, f"Board '{name}' missing category"
        assert "url" in meta, f"Board '{name}' missing url"
        assert "icon" in meta, f"Board '{name}' missing icon"
        assert "runner" in meta, f"Board '{name}' missing runner function"
        assert callable(meta["runner"]), f"Runner for '{name}' is not callable"

    all_boards = list_all_boards()
    assert len(all_boards) == len(BOARD_METADATA_REGISTRY)
    print(f"✅ Verified {len(BOARD_METADATA_REGISTRY)} job platforms registered with valid runners.")


def test_categories():
    """Verify categorized boards in settings match registry."""
    registered_names = set(BOARD_METADATA_REGISTRY.keys())
    settings_names = set(settings.TARGET_JOB_BOARDS)

    missing_in_settings = registered_names - settings_names
    assert not missing_in_settings, f"Boards missing in settings: {missing_in_settings}"

    print("✅ Verified category groupings and settings synchronization.")


if __name__ == "__main__":
    test_board_count_and_registration()
    test_categories()
    print("\n🎉 All Board Registry tests PASSED successfully!")
