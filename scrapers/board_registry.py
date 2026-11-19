"""
Unified Job Board Registry mapping all 100+ platforms to categorized metadata and scraper runners.
"""

from typing import Any, Callable, Dict, List, Optional
from config.settings import settings

# Import scrapers across all modules
from scrapers.standard_boards import (
    scrape_itch_io,
    scrape_gamesindustry,
    scrape_wwr,
    scrape_remoteok,
    scrape_remotive,
    scrape_builtin,
    scrape_working_nomads,
    scrape_techcareers,
    scrape_jobspresso,
    scrape_justremote,
    scrape_dice,
    scrape_hackernews_hiring,
    scrape_arc_dev,
    scrape_himalayas,
    scrape_skipthedrive,
    scrape_authentic_jobs,
    scrape_pangian,
    scrape_remote_com,
    scrape_dailyremote,
    scrape_4dayweek,
    scrape_nodesk,
)
from scrapers.startup_boards import (
    scrape_wellfound,
    scrape_work_at_a_startup,
    scrape_dynamite_jobs,
    scrape_welcome_to_the_jungle,
    scrape_f6s,
    scrape_startupers,
    scrape_eu_startups,
    scrape_underdog,
    scrape_techstars_jobs,
    scrape_climatebase,
    scrape_climatetechlist,
    scrape_startups_gallery,
    scrape_startupjobs_cz,
    scrape_vcplatform,
    scrape_seedcamp_jobs,
    scrape_berlinstartupjobs,
    scrape_hasjob,
)
from scrapers.ai_data_boards import (
    scrape_ai_jobs_net,
    scrape_datayoshi,
    scrape_deeplearning_ai,
    scrape_aicareers,
    scrape_outerjoin,
    scrape_analytics_jobs,
    scrape_datajobs,
    scrape_datasciencejobs,
    scrape_machinelearningjobs,
    scrape_r_users,
    scrape_kaggle_jobs,
    scrape_huggingface_jobs,
)
from scrapers.specialized_tech_boards import (
    scrape_python_org,
    scrape_golang_projects,
    scrape_rust_jobs,
    scrape_react_careers,
    scrape_vue_jobs,
    scrape_rubyonremote,
    scrape_elixir_jobs,
    scrape_scala_jobs,
    scrape_android_jobs,
    scrape_ios_dev_jobs,
    scrape_cplusplus_jobs,
    scrape_graphql_jobs,
    scrape_pyjobs,
    scrape_remotepython,
    scrape_djangoproject,
    scrape_pythonjobsgithub,
)
from scrapers.web3_boards import (
    scrape_crypto_jobs_list,
    scrape_web3_career,
    scrape_crypto_jobs,
    scrape_use_web3,
    scrape_bankless_jobs,
    scrape_solana_jobs,
    scrape_ethereum_jobs,
    scrape_defi_jobs,
    scrape_blockew,
    scrape_crypto_careers,
)
from scrapers.gaming_design_boards import (
    scrape_hitmarker,
    scrape_work_with_indies,
    scrape_games_jobs_direct,
    scrape_game_devs_of_color,
    scrape_maxibestof,
    scrape_dribbble_jobs,
    scrape_product_hunt_jobs,
    scrape_design_jobs,
    scrape_game_job_hunter,
    scrape_behance_jobs,
    scrape_designhill,
    scrape_uiuxjobsboard,
    scrape_remotegamejobs,
)
from scrapers.devops_cloud_boards import (
    scrape_cybersec_jobs,
    scrape_infosec_jobs,
    scrape_kubernetes_jobs,
    scrape_cloud_jobs,
    scrape_devops_jobs,
    scrape_linux_jobs,
    scrape_sre_jobs,
    scrape_cleared_jobs,
)
from scrapers.regional_global_boards import (
    scrape_onlinejobs_ph,
    scrape_nofluffjobs,
    scrape_jobgether,
    scrape_euro_tech_jobs,
    scrape_work_in_startups,
    scrape_german_tech_jobs,
    scrape_swiss_dev_jobs,
    scrape_uk_dev_jobs,
    scrape_landing_jobs,
    scrape_tokyo_dev,
)
from scrapers.aggregator_boards import (
    scrape_simplyhired,
    scrape_jooble,
    scrape_careerbuilder,
    scrape_arise,
    scrape_flexjobs,
    scrape_themuse,
    scrape_ladders,
    scrape_jobserve,
    scrape_arbeitnow,
    scrape_jobicy,
    scrape_linkedin,
    scrape_indeed,
    scrape_talent,
)
from scrapers.freelance_boards import (
    scrape_upwork,
    scrape_freelancer,
    scrape_guru,
    scrape_problogger,
    scrape_heymarketers,
    scrape_twine,
)

BOARD_METADATA_REGISTRY: Dict[str, Dict[str, Any]] = {
    # =========================================================================
    # 1. General Tech & Remote (15 Platforms)
    # =========================================================================
    "WeWorkRemotely": {
        "category": "General Tech & Remote",
        "url": "https://weworkremotely.com/",
        "icon": "🌍",
        "runner": scrape_wwr,
    },
    "RemoteOK": {
        "category": "General Tech & Remote",
        "url": "https://remoteok.com/",
        "icon": "🚀",
        "runner": scrape_remoteok,
    },
    "Remotive": {
        "category": "General Tech & Remote",
        "url": "https://remotive.com/",
        "icon": "✨",
        "runner": scrape_remotive,
    },
    "Dice": {
        "category": "General Tech & Remote",
        "url": "https://www.dice.com/jobs",
        "icon": "🎲",
        "runner": scrape_dice,
    },
    "HackerNews Hiring": {
        "category": "General Tech & Remote",
        "url": "https://news.ycombinator.com/",
        "icon": "📰",
        "runner": scrape_hackernews_hiring,
    },
    "BuiltIn": {
        "category": "General Tech & Remote",
        "url": "https://builtin.com/",
        "icon": "🏢",
        "runner": scrape_builtin,
    },
    "WorkingNomads": {
        "category": "General Tech & Remote",
        "url": "https://www.workingnomads.com/",
        "icon": "🏖️",
        "runner": scrape_working_nomads,
    },
    "Techcareers": {
        "category": "General Tech & Remote",
        "url": "https://www.techcareers.com/",
        "icon": "💻",
        "runner": scrape_techcareers,
    },
    "Jobspresso": {
        "category": "General Tech & Remote",
        "url": "https://jobspresso.co/",
        "icon": "☕",
        "runner": scrape_jobspresso,
    },
    "JustRemote": {
        "category": "General Tech & Remote",
        "url": "https://justremote.co/",
        "icon": "🎯",
        "runner": scrape_justremote,
    },
    "Arc.dev": {
        "category": "General Tech & Remote",
        "url": "https://arc.dev/remote-jobs",
        "icon": "⚡",
        "runner": scrape_arc_dev,
    },
    "Himalayas": {
        "category": "General Tech & Remote",
        "url": "https://himalayas.app/jobs",
        "icon": "🏔️",
        "runner": scrape_himalayas,
    },
    "SkipTheDrive": {
        "category": "General Tech & Remote",
        "url": "https://www.skipthedrive.com/",
        "icon": "🚗",
        "runner": scrape_skipthedrive,
    },
    "AuthenticJobs": {
        "category": "General Tech & Remote",
        "url": "https://authenticjobs.com/",
        "icon": "💎",
        "runner": scrape_authentic_jobs,
    },
    "Pangian": {
        "category": "General Tech & Remote",
        "url": "https://pangian.com/job-travel-remote-work/",
        "icon": "🌐",
        "runner": scrape_pangian,
    },
    "Jobicy": {
        "category": "General Tech & Remote",
        "url": "https://jobicy.com/",
        "icon": "🌍",
        "runner": scrape_jobicy,
    },
    "Remote.com": {
        "category": "General Tech & Remote",
        "url": "https://remote.com/jobs",
        "icon": "🌐",
        "runner": scrape_remote_com,
    },
    "DailyRemote": {
        "category": "General Tech & Remote",
        "url": "https://dailyremote.com/remote-jobs",
        "icon": "🌍",
        "runner": scrape_dailyremote,
    },
    "4DayWeek": {
        "category": "General Tech & Remote",
        "url": "https://4dayweek.io/remote-jobs",
        "icon": "⏳",
        "runner": scrape_4dayweek,
    },
    "Nodesk": {
        "category": "General Tech & Remote",
        "url": "https://nodesk.co/remote-jobs/",
        "icon": "🌐",
        "runner": scrape_nodesk,
    },

    # =========================================================================
    # 2. Startup & Venture (15 Platforms)
    # =========================================================================
    "Wellfound": {
        "category": "Startup & Venture",
        "url": "https://wellfound.com/",
        "icon": "✌️",
        "runner": scrape_wellfound,
    },
    "WorkAtAStartup": {
        "category": "Startup & Venture",
        "url": "https://www.workatastartup.com/",
        "icon": "🚀",
        "runner": scrape_work_at_a_startup,
    },
    "DynamiteJobs": {
        "category": "Startup & Venture",
        "url": "https://dynamitejobs.com/",
        "icon": "🧨",
        "runner": scrape_dynamite_jobs,
    },
    "WelcomeToTheJungle": {
        "category": "Startup & Venture",
        "url": "https://www.welcometothejungle.com/",
        "icon": "🌴",
        "runner": scrape_welcome_to_the_jungle,
    },
    "F6S": {
        "category": "Startup & Venture",
        "url": "https://www.f6s.com/jobs",
        "icon": "🌐",
        "runner": scrape_f6s,
    },
    "Startupers": {
        "category": "Startup & Venture",
        "url": "https://www.startupers.com/",
        "icon": "💡",
        "runner": scrape_startupers,
    },
    "EUSTartups": {
        "category": "Startup & Venture",
        "url": "https://www.eu-startups.com/jobs/",
        "icon": "🇪🇺",
        "runner": scrape_eu_startups,
    },
    "Underdog": {
        "category": "Startup & Venture",
        "url": "https://underdog.io/",
        "icon": "🐕",
        "runner": scrape_underdog,
    },
    "Techstars Jobs": {
        "category": "Startup & Venture",
        "url": "https://jobs.techstars.com/",
        "icon": "🌟",
        "runner": scrape_techstars_jobs,
    },
    "Climatebase": {
        "category": "Startup & Venture",
        "url": "https://climatebase.org/jobs",
        "icon": "🌱",
        "runner": scrape_climatebase,
    },
    "ClimateTechList": {
        "category": "Startup & Venture",
        "url": "https://www.climatetechlist.com/",
        "icon": "🌿",
        "runner": scrape_climatetechlist,
    },
    "Startups.gallery": {
        "category": "Startup & Venture",
        "url": "https://startups.gallery/",
        "icon": "🖼️",
        "runner": scrape_startups_gallery,
    },
    "StartupJobs.cz": {
        "category": "Startup & Venture",
        "url": "https://www.startupjobs.com/",
        "icon": "🚀",
        "runner": scrape_startupjobs_cz,
    },
    "VCPlatform": {
        "category": "Startup & Venture",
        "url": "https://jobs.vcplatform.com/",
        "icon": "💼",
        "runner": scrape_vcplatform,
    },
    "Seedcamp Jobs": {
        "category": "Startup & Venture",
        "url": "https://jobs.seedcamp.com/",
        "icon": "🌱",
        "runner": scrape_seedcamp_jobs,
    },
    "BerlinStartupJobs": {
        "category": "Startup & Venture",
        "url": "https://berlinstartupjobs.com/engineering/",
        "icon": "🚀",
        "runner": scrape_berlinstartupjobs,
    },
    "Hasjob": {
        "category": "Startup & Venture",
        "url": "https://hasjob.co/",
        "icon": "⚡",
        "runner": scrape_hasjob,
    },

    # =========================================================================
    # 3. AI & Data Science (12 Platforms)
    # =========================================================================
    "AI-Jobs.net": {
        "category": "AI & Data Science",
        "url": "https://ai-jobs.net/",
        "icon": "🧠",
        "runner": scrape_ai_jobs_net,
    },
    "DataYoshi": {
        "category": "AI & Data Science",
        "url": "https://www.datayoshi.com/",
        "icon": "📊",
        "runner": scrape_datayoshi,
    },
    "DeepLearningAI": {
        "category": "AI & Data Science",
        "url": "https://jobs.deeplearning.ai/",
        "icon": "🤖",
        "runner": scrape_deeplearning_ai,
    },
    "AiCareers": {
        "category": "AI & Data Science",
        "url": "https://aicareers.com/",
        "icon": "💡",
        "runner": scrape_aicareers,
    },
    "OuterJoin": {
        "category": "AI & Data Science",
        "url": "https://outerjoin.us/",
        "icon": "🔗",
        "runner": scrape_outerjoin,
    },
    "AnalyticsJobs": {
        "category": "AI & Data Science",
        "url": "https://analyticsjobs.co/",
        "icon": "📈",
        "runner": scrape_analytics_jobs,
    },
    "DataJobs": {
        "category": "AI & Data Science",
        "url": "https://datajobs.com/",
        "icon": "📊",
        "runner": scrape_datajobs,
    },
    "DataScienceJobs": {
        "category": "AI & Data Science",
        "url": "https://datasciencejobs.com/",
        "icon": "🔬",
        "runner": scrape_datasciencejobs,
    },
    "MachineLearningJobs": {
        "category": "AI & Data Science",
        "url": "https://machinelearningjobs.io/",
        "icon": "🤖",
        "runner": scrape_machinelearningjobs,
    },
    "R-users": {
        "category": "AI & Data Science",
        "url": "https://www.r-users.com/",
        "icon": "📊",
        "runner": scrape_r_users,
    },
    "Kaggle Jobs": {
        "category": "AI & Data Science",
        "url": "https://www.kaggle.com/jobs",
        "icon": "🏆",
        "runner": scrape_kaggle_jobs,
    },
    "HuggingFace Jobs": {
        "category": "AI & Data Science",
        "url": "https://huggingface.co/jobs",
        "icon": "🤗",
        "runner": scrape_huggingface_jobs,
    },

    # =========================================================================
    # 4. Languages & Frameworks (12 Platforms)
    # =========================================================================
    "Python.org": {
        "category": "Languages & Frameworks",
        "url": "https://www.python.org/jobs/",
        "icon": "🐍",
        "runner": scrape_python_org,
    },
    "GolangProjects": {
        "category": "Languages & Frameworks",
        "url": "https://golangprojects.com/",
        "icon": "🐹",
        "runner": scrape_golang_projects,
    },
    "RustJobs": {
        "category": "Languages & Frameworks",
        "url": "https://rustjobs.dev/",
        "icon": "🦀",
        "runner": scrape_rust_jobs,
    },
    "ReactCareers": {
        "category": "Languages & Frameworks",
        "url": "https://reactcareers.com/",
        "icon": "⚛️",
        "runner": scrape_react_careers,
    },
    "VueJobs": {
        "category": "Languages & Frameworks",
        "url": "https://vuejobs.com/",
        "icon": "💚",
        "runner": scrape_vue_jobs,
    },
    "RubyOnRemote": {
        "category": "Languages & Frameworks",
        "url": "https://rubyonremote.com/",
        "icon": "💎",
        "runner": scrape_rubyonremote,
    },
    "ElixirJobs": {
        "category": "Languages & Frameworks",
        "url": "https://elixirjobs.net/",
        "icon": "💧",
        "runner": scrape_elixir_jobs,
    },
    "ScalaJobs": {
        "category": "Languages & Frameworks",
        "url": "https://scalajobs.com/",
        "icon": "🔴",
        "runner": scrape_scala_jobs,
    },
    "AndroidJobs": {
        "category": "Languages & Frameworks",
        "url": "https://androidjobs.io/",
        "icon": "🤖",
        "runner": scrape_android_jobs,
    },
    "iOSDevJobs": {
        "category": "Languages & Frameworks",
        "url": "https://iosdevjobs.com/",
        "icon": "🍏",
        "runner": scrape_ios_dev_jobs,
    },
    "CPlusPlusJobs": {
        "category": "Languages & Frameworks",
        "url": "https://cplusplusjobs.com/",
        "icon": "⚡",
        "runner": scrape_cplusplus_jobs,
    },
    "GraphQLJobs": {
        "category": "Languages & Frameworks",
        "url": "https://graphql.jobs/",
        "icon": "🕸️",
        "runner": scrape_graphql_jobs,
    },
    "PyJobs": {
        "category": "Languages & Frameworks",
        "url": "https://www.pyjobs.com/",
        "icon": "🐍",
        "runner": scrape_pyjobs,
    },
    "RemotePython": {
        "category": "Languages & Frameworks",
        "url": "https://www.remotepython.com/jobs/",
        "icon": "🐍",
        "runner": scrape_remotepython,
    },
    "DjangoProject": {
        "category": "Languages & Frameworks",
        "url": "https://www.djangoproject.com/community/jobs/",
        "icon": "🎸",
        "runner": scrape_djangoproject,
    },
    "PythonJobsGithub": {
        "category": "Languages & Frameworks",
        "url": "https://pythonjobs.github.io/",
        "icon": "🐍",
        "runner": scrape_pythonjobsgithub,
    },

    # =========================================================================
    # 5. Web3 & Blockchain (10 Platforms)
    # =========================================================================
    "CryptoJobsList": {
        "category": "Web3 & Blockchain",
        "url": "https://cryptojobslist.com/",
        "icon": "🪙",
        "runner": scrape_crypto_jobs_list,
    },
    "Web3Career": {
        "category": "Web3 & Blockchain",
        "url": "https://web3.career/",
        "icon": "🌐",
        "runner": scrape_web3_career,
    },
    "CryptoJobs": {
        "category": "Web3 & Blockchain",
        "url": "https://cryptojobs.com/",
        "icon": "⚡",
        "runner": scrape_crypto_jobs,
    },
    "UseWeb3": {
        "category": "Web3 & Blockchain",
        "url": "https://useweb3.xyz/jobs",
        "icon": "⛓️",
        "runner": scrape_use_web3,
    },
    "BanklessJobs": {
        "category": "Web3 & Blockchain",
        "url": "https://pallet.xyz/list/bankless/jobs",
        "icon": "🏴",
        "runner": scrape_bankless_jobs,
    },
    "SolanaJobs": {
        "category": "Web3 & Blockchain",
        "url": "https://jobs.solana.com/",
        "icon": "🟣",
        "runner": scrape_solana_jobs,
    },
    "EthereumJobs": {
        "category": "Web3 & Blockchain",
        "url": "https://pallet.xyz/list/ethereum/jobs",
        "icon": "🔷",
        "runner": scrape_ethereum_jobs,
    },
    "DefiJobs": {
        "category": "Web3 & Blockchain",
        "url": "https://defijobs.io/",
        "icon": "💰",
        "runner": scrape_defi_jobs,
    },
    "Blockew": {
        "category": "Web3 & Blockchain",
        "url": "https://blockew.com/",
        "icon": "🧱",
        "runner": scrape_blockew,
    },
    "CryptoCareers": {
        "category": "Web3 & Blockchain",
        "url": "https://cryptocareers.com/",
        "icon": "🪙",
        "runner": scrape_crypto_careers,
    },

    # =========================================================================
    # 6. Gaming & Creative (12 Platforms)
    # =========================================================================
    "Itch.io": {
        "category": "Gaming & Creative",
        "url": "https://itch.io/jobs",
        "icon": "🕹️",
        "runner": scrape_itch_io,
    },
    "GamesIndustry.biz": {
        "category": "Gaming & Creative",
        "url": "https://jobs.gamesindustry.biz/",
        "icon": "🎮",
        "runner": scrape_gamesindustry,
    },
    "GamesJobsDirect": {
        "category": "Gaming & Creative",
        "url": "https://www.gamesjobsdirect.com/",
        "icon": "🎯",
        "runner": scrape_games_jobs_direct,
    },
    "GameDevsOfColor": {
        "category": "Gaming & Creative",
        "url": "https://www.gamedevsofcolor.org/jobs",
        "icon": "🎨",
        "runner": scrape_game_devs_of_color,
    },
    "Hitmarker": {
        "category": "Gaming & Creative",
        "url": "https://hitmarker.net/",
        "icon": "🎮",
        "runner": scrape_hitmarker,
    },
    "WorkWithIndies": {
        "category": "Gaming & Creative",
        "url": "https://www.workwithindies.com/",
        "icon": "🕹️",
        "runner": scrape_work_with_indies,
    },
    "GameJobHunter": {
        "category": "Gaming & Creative",
        "url": "https://gamejobhunter.com/job-postings/",
        "icon": "🎯",
        "runner": scrape_game_job_hunter,
    },
    "Maxibestof": {
        "category": "Gaming & Creative",
        "url": "https://maxibestof.one/jobs",
        "icon": "🎨",
        "runner": scrape_maxibestof,
    },
    "Dribbble": {
        "category": "Gaming & Creative",
        "url": "https://dribbble.com/jobs",
        "icon": "🏀",
        "runner": scrape_dribbble_jobs,
    },
    "ProductHunt": {
        "category": "Gaming & Creative",
        "url": "https://www.producthunt.com/jobs",
        "icon": "🐱",
        "runner": scrape_product_hunt_jobs,
    },
    "DesignJobs": {
        "category": "Gaming & Creative",
        "url": "https://designjobs.co/",
        "icon": "✨",
        "runner": scrape_design_jobs,
    },
    "BehanceJobs": {
        "category": "Gaming & Creative",
        "url": "https://www.behance.net/joblist",
        "icon": "🎨",
        "runner": scrape_behance_jobs,
    },
    "Designhill": {
        "category": "Gaming & Creative",
        "url": "https://www.designhill.com/design-contests",
        "icon": "🎨",
        "runner": scrape_designhill,
    },
    "UIUXJobsBoard": {
        "category": "Gaming & Creative",
        "url": "https://uiuxjobsboard.com/",
        "icon": "🎨",
        "runner": scrape_uiuxjobsboard,
    },
    "RemoteGameJobs": {
        "category": "Gaming & Creative",
        "url": "https://remotegamejobs.com/",
        "icon": "🎮",
        "runner": scrape_remotegamejobs,
    },

    # =========================================================================
    # 7. DevOps, Cloud & Security (8 Platforms)
    # =========================================================================
    "CyberSecJobs": {
        "category": "DevOps, Cloud & Security",
        "url": "https://cybersecjobs.com/",
        "icon": "🔒",
        "runner": scrape_cybersec_jobs,
    },
    "InfoSecJobs": {
        "category": "DevOps, Cloud & Security",
        "url": "https://infosec-jobs.com/",
        "icon": "🛡️",
        "runner": scrape_infosec_jobs,
    },
    "KubernetesJobs": {
        "category": "DevOps, Cloud & Security",
        "url": "https://kubernetesjobs.com/",
        "icon": "☸️",
        "runner": scrape_kubernetes_jobs,
    },
    "CloudJobs": {
        "category": "DevOps, Cloud & Security",
        "url": "https://cloudjobs.io/",
        "icon": "☁️",
        "runner": scrape_cloud_jobs,
    },
    "DevOpsJobs": {
        "category": "DevOps, Cloud & Security",
        "url": "https://devopsjobs.io/",
        "icon": "⚙️",
        "runner": scrape_devops_jobs,
    },
    "LinuxJobs": {
        "category": "DevOps, Cloud & Security",
        "url": "https://linuxjobs.io/",
        "icon": "🐧",
        "runner": scrape_linux_jobs,
    },
    "SREJobs": {
        "category": "DevOps, Cloud & Security",
        "url": "https://srejobs.io/",
        "icon": "🚨",
        "runner": scrape_sre_jobs,
    },
    "ClearedJobs": {
        "category": "DevOps, Cloud & Security",
        "url": "https://clearedjobs.net/",
        "icon": "🎖️",
        "runner": scrape_cleared_jobs,
    },

    # =========================================================================
    # 8. Regional & Global (10 Platforms)
    # =========================================================================
    "OnlineJobs.ph": {
        "category": "Regional & Global",
        "url": "https://www.onlinejobs.ph/",
        "icon": "🇵🇭",
        "runner": scrape_onlinejobs_ph,
    },
    "NoFluffJobs": {
        "category": "Regional & Global",
        "url": "https://nofluffjobs.com/",
        "icon": "🇪🇺",
        "runner": scrape_nofluffjobs,
    },
    "Jobgether": {
        "category": "Regional & Global",
        "url": "https://jobgether.com/",
        "icon": "🌍",
        "runner": scrape_jobgether,
    },
    "EuroTechJobs": {
        "category": "Regional & Global",
        "url": "https://www.eurotechjobs.com/",
        "icon": "🇪🇺",
        "runner": scrape_euro_tech_jobs,
    },
    "WorkInStartups": {
        "category": "Regional & Global",
        "url": "https://workinstartups.com/",
        "icon": "🇬🇧",
        "runner": scrape_work_in_startups,
    },
    "GermanTechJobs": {
        "category": "Regional & Global",
        "url": "https://germantechjobs.de/",
        "icon": "🇩🇪",
        "runner": scrape_german_tech_jobs,
    },
    "SwissDevJobs": {
        "category": "Regional & Global",
        "url": "https://swissdevjobs.ch/",
        "icon": "🇨🇭",
        "runner": scrape_swiss_dev_jobs,
    },
    "UkDevJobs": {
        "category": "Regional & Global",
        "url": "https://ukdevjobs.co.uk/",
        "icon": "🇬🇧",
        "runner": scrape_uk_dev_jobs,
    },
    "Landing.jobs": {
        "category": "Regional & Global",
        "url": "https://landing.jobs/",
        "icon": "🛬",
        "runner": scrape_landing_jobs,
    },
    "TokyoDev": {
        "category": "Regional & Global",
        "url": "https://www.tokyodev.com/jobs",
        "icon": "🗾",
        "runner": scrape_tokyo_dev,
    },

    # =========================================================================
    # 9. Major Aggregators (8 Platforms)
    # =========================================================================
    "SimplyHired": {
        "category": "Major Aggregators",
        "url": "https://www.simplyhired.com/",
        "icon": "🔍",
        "runner": scrape_simplyhired,
    },
    "Jooble": {
        "category": "Major Aggregators",
        "url": "https://jooble.org/",
        "icon": "💼",
        "runner": scrape_jooble,
    },
    "CareerBuilder": {
        "category": "Major Aggregators",
        "url": "https://www.careerbuilder.com/",
        "icon": "📁",
        "runner": scrape_careerbuilder,
    },
    "Arise": {
        "category": "Major Aggregators",
        "url": "https://www.ariseworkfromhome.com/",
        "icon": "🏠",
        "runner": scrape_arise,
    },
    "FlexJobs": {
        "category": "Major Aggregators",
        "url": "https://www.flexjobs.com/",
        "icon": "🌟",
        "runner": scrape_flexjobs,
    },
    "TheMuse": {
        "category": "Major Aggregators",
        "url": "https://www.themuse.com/jobs",
        "icon": "🏛️",
        "runner": scrape_themuse,
    },
    "Ladders": {
        "category": "Major Aggregators",
        "url": "https://www.theladders.com/jobs",
        "icon": "🪜",
        "runner": scrape_ladders,
    },
    "Jobserve": {
        "category": "Major Aggregators",
        "url": "https://www.jobserve.com/",
        "icon": "🏢",
        "runner": scrape_jobserve,
    },
    "Arbeitnow": {
        "category": "Major Aggregators",
        "url": "https://www.arbeitnow.com/",
        "icon": "🌐",
        "runner": scrape_arbeitnow,
    },
    "LinkedIn": {
        "category": "Major Aggregators",
        "url": "https://www.linkedin.com/jobs",
        "icon": "💼",
        "runner": scrape_linkedin,
    },
    "Indeed": {
        "category": "Major Aggregators",
        "url": "https://www.indeed.com/",
        "icon": "🔎",
        "runner": scrape_indeed,
    },
    "Talent.com": {
        "category": "Major Aggregators",
        "url": "https://www.talent.com/",
        "icon": "🌐",
        "runner": scrape_talent,
    },

    # =========================================================================
    # 10. Freelance & Creator Gigs (4 Platforms)
    # =========================================================================
    "Upwork": {
        "category": "Freelance & Creator Gigs",
        "url": "https://www.upwork.com/",
        "icon": "💼",
        "runner": scrape_upwork,
    },
    "Freelancer": {
        "category": "Freelance & Creator Gigs",
        "url": "https://www.freelancer.com/",
        "icon": "🌐",
        "runner": scrape_freelancer,
    },
    "Guru": {
        "category": "Freelance & Creator Gigs",
        "url": "https://www.guru.com/",
        "icon": "💼",
        "runner": scrape_guru,
    },
    "ProBlogger": {
        "category": "Freelance & Creator Gigs",
        "url": "https://problogger.com/jobs/",
        "icon": "✍️",
        "runner": scrape_problogger,
    },
    "HeyMarketers": {
        "category": "Freelance & Creator Gigs",
        "url": "https://heymarketers.com/jobs/",
        "icon": "📢",
        "runner": scrape_heymarketers,
    },
    "Twine": {
        "category": "Freelance & Creator Gigs",
        "url": "https://www.twine.net/jobs",
        "icon": "🧶",
        "runner": scrape_twine,
    },
}


def get_board_metadata(board_name: str) -> Optional[Dict[str, Any]]:
    """Returns metadata for a specific board name."""
    return BOARD_METADATA_REGISTRY.get(board_name)


def get_board_runner(board_name: str) -> Optional[Callable[..., Any]]:
    """Returns the scraper function runner for a given board name."""
    meta = BOARD_METADATA_REGISTRY.get(board_name)
    return meta.get("runner") if meta else None


def list_all_boards() -> List[Dict[str, Any]]:
    """Returns a list of all registered boards with metadata for UI and API."""
    return [
        {
            "name": name,
            "category": meta["category"],
            "url": meta["url"],
            "icon": meta["icon"],
        }
        for name, meta in BOARD_METADATA_REGISTRY.items()
    ]
