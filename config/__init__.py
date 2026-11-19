"""
Configuration package for the Autonomous Job-Scraping Agent.
"""

from .settings import settings
from .logging_config import setup_logging, get_logger
from .agent_config import get_orchestrator_config, MASTER_ORCHESTRATOR_SYSTEM_INSTRUCTIONS
from .cli import parse_arguments

__all__ = [
    "settings",
    "setup_logging",
    "get_logger",
    "get_orchestrator_config",
    "MASTER_ORCHESTRATOR_SYSTEM_INSTRUCTIONS",
    "parse_arguments",
]
