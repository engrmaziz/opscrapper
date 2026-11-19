"""
Global project settings and environment configuration.
"""

from pathlib import Path
import os
from typing import Dict, List, Optional
from dotenv import load_dotenv

# Base Project Root
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env if present
ENV_PATH = BASE_DIR / ".env"
if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)
else:
    load_dotenv()


class Settings:
    """Project-wide settings container."""

    # Project metadata
    PROJECT_NAME: str = "Autonomous Job Scraper Agent"
    VERSION: str = "3.0.0"
    PART: str = "Expanded 100+ Job Platform Matrix with Per-Job Direct ATS Enrichment & Web UI"

    # Environment
    ENV: str = os.getenv("ANTIGRAVITY_ENV", "development")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()
    CAREER_NAVIGATION_TIMEOUT: float = float(os.getenv("CAREER_NAVIGATION_TIMEOUT", "15.0"))
    DEEP_LINK_RATE_LIMIT_DELAY: float = float(os.getenv("DEEP_LINK_RATE_LIMIT_DELAY", "1.5"))
    DEFAULT_EXCEL_FILENAME: str = os.getenv("DEFAULT_EXCEL_FILENAME", "job_leads.xlsx")
    MAX_JOBS_PER_BOARD: int = int(os.getenv("MAX_JOBS_PER_BOARD", "20"))

    # Web Server Settings
    WEB_HOST: str = os.getenv("WEB_HOST", "0.0.0.0")
    WEB_PORT: int = int(os.getenv("WEB_PORT", "8060"))
    AUTH_KEY: str = os.getenv("AUTH_KEY", "orangepie@1978")

    # Paths
    BASE_DIR: Path = BASE_DIR
    CONFIG_DIR: Path = BASE_DIR / "config"
    TOOLS_DIR: Path = BASE_DIR / "tools"
    SCRAPERS_DIR: Path = BASE_DIR / "scrapers"
    DISCOVERY_DIR: Path = BASE_DIR / "discovery"
    UTILS_DIR: Path = BASE_DIR / "utils"
    DATA_DIR: Path = BASE_DIR / "data"
    RAW_DATA_DIR: Path = BASE_DIR / "data" / "raw"
    EXPORTS_DATA_DIR: Path = BASE_DIR / "data" / "exports"
    LOGS_DIR: Path = BASE_DIR / "logs"
    APP_DIR: Path = BASE_DIR / "app"
    STATIC_DIR: Path = BASE_DIR / "app" / "static"
    STATE_FILE_PATH: Path = BASE_DIR / "data" / "scrape_state.json"

    # Categorized 100+ Target Job Platforms Matrix
    CATEGORIZED_BOARDS: Dict[str, List[str]] = {
        "General Tech & Remote": [
            "WeWorkRemotely",
            "RemoteOK",
            "Remotive",
            "Dice",
            "HackerNews Hiring",
            "BuiltIn",
            "WorkingNomads",
            "Techcareers",
            "Jobspresso",
            "JustRemote",
            "Arc.dev",
            "Himalayas",
            "SkipTheDrive",
            "AuthenticJobs",
            "Pangian",
            "Jobicy",
            "Remote.com",
            "DailyRemote",
            "4DayWeek",
            "Nodesk",
        ],
        "Startup & Venture": [
            "Wellfound",
            "WorkAtAStartup",
            "DynamiteJobs",
            "WelcomeToTheJungle",
            "F6S",
            "Startupers",
            "EUSTartups",
            "Underdog",
            "Techstars Jobs",
            "Climatebase",
            "ClimateTechList",
            "Startups.gallery",
            "StartupJobs.cz",
            "VCPlatform",
            "Seedcamp Jobs",
            "BerlinStartupJobs",
            "Hasjob",
        ],
        "AI & Data Science": [
            "AI-Jobs.net",
            "DataYoshi",
            "DeepLearningAI",
            "AiCareers",
            "OuterJoin",
            "AnalyticsJobs",
            "DataJobs",
            "DataScienceJobs",
            "MachineLearningJobs",
            "R-users",
            "Kaggle Jobs",
            "HuggingFace Jobs",
        ],
        "Languages & Frameworks": [
            "Python.org",
            "GolangProjects",
            "RustJobs",
            "ReactCareers",
            "VueJobs",
            "RubyOnRemote",
            "ElixirJobs",
            "ScalaJobs",
            "AndroidJobs",
            "iOSDevJobs",
            "CPlusPlusJobs",
            "GraphQLJobs",
            "PyJobs",
            "RemotePython",
            "DjangoProject",
            "PythonJobsGithub",
        ],
        "Web3 & Blockchain": [
            "CryptoJobsList",
            "Web3Career",
            "CryptoJobs",
            "UseWeb3",
            "BanklessJobs",
            "SolanaJobs",
            "EthereumJobs",
            "DefiJobs",
            "Blockew",
            "CryptoCareers",
        ],
        "Gaming & Creative": [
            "Itch.io",
            "GamesIndustry.biz",
            "GamesJobsDirect",
            "GameDevsOfColor",
            "Hitmarker",
            "WorkWithIndies",
            "GameJobHunter",
            "Maxibestof",
            "Dribbble",
            "ProductHunt",
            "DesignJobs",
            "BehanceJobs",
            "Designhill",
            "UIUXJobsBoard",
            "RemoteGameJobs",
        ],
        "DevOps, Cloud & Security": [
            "CyberSecJobs",
            "InfoSecJobs",
            "KubernetesJobs",
            "CloudJobs",
            "DevOpsJobs",
            "LinuxJobs",
            "SREJobs",
            "ClearedJobs",
        ],
        "Regional & Global": [
            "OnlineJobs.ph",
            "NoFluffJobs",
            "Jobgether",
            "EuroTechJobs",
            "WorkInStartups",
            "GermanTechJobs",
            "SwissDevJobs",
            "UkDevJobs",
            "Landing.jobs",
            "TokyoDev",
        ],
        "Major Aggregators": [
            "SimplyHired",
            "Jooble",
            "CareerBuilder",
            "Arise",
            "FlexJobs",
            "TheMuse",
            "Ladders",
            "Jobserve",
            "Arbeitnow",
            "LinkedIn",
            "Indeed",
            "Talent.com",
        ],
        "Freelance & Creator Gigs": [
            "Upwork",
            "Freelancer",
            "Guru",
            "ProBlogger",
            "HeyMarketers",
            "Twine",
        ],
    }

    # Flattened full list of 100+ target boards
    TARGET_JOB_BOARDS: List[str] = [
        board for boards in CATEGORIZED_BOARDS.values() for board in boards
    ]

    # Search Defaults
    DEFAULT_KEYWORD: str = os.getenv("DEFAULT_JOB_KEYWORD", "AI Engineer")
    DEFAULT_LOCATION: str = os.getenv("DEFAULT_LOCATION", "Remote")

    # Anti-Bot & Web Navigation Settings
    STEALTH_HEADLESS: bool = os.getenv("STEALTH_HEADLESS", "true").lower() == "true"
    DEFAULT_PAGE_TIMEOUT: int = int(os.getenv("DEFAULT_PAGE_TIMEOUT", "30"))
    MAX_RETRIES_PER_BOARD: int = int(os.getenv("MAX_RETRIES_PER_BOARD", "3"))
    MANAGED_SCRAPER_API_KEY: Optional[str] = os.getenv("MANAGED_SCRAPER_API_KEY", None)
    MANAGED_SCRAPER_SERVICE: Optional[str] = os.getenv("MANAGED_SCRAPER_SERVICE", None)
    DEFAULT_USER_AGENT: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    )

    def ensure_directories(self) -> None:
        """Create necessary project data, utils, tools, logs, and app directories if they do not exist."""
        for directory in [
            self.DATA_DIR,
            self.RAW_DATA_DIR,
            self.EXPORTS_DATA_DIR,
            self.LOGS_DIR,
            self.TOOLS_DIR,
            self.SCRAPERS_DIR,
            self.DISCOVERY_DIR,
            self.UTILS_DIR,
            self.CONFIG_DIR,
            self.APP_DIR,
            self.STATIC_DIR,
        ]:
            directory.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_directories()
