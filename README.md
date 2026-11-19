# Autonomous Multi-Platform Job-Scraping Agent (v3.0 Enterprise)
## 126 Job Platforms, Sequential Per-Job Direct ATS Enrichment & Real-Time Web UI

![Python Version](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue)
![SDK](https://img.shields.io/badge/SDK-Google%20Antigravity-orange)
![FastAPI](https://img.shields.io/badge/FastAPI-0.141+-009688)
![Platforms](https://img.shields.io/badge/Platforms-126%20Boards-brightgreen)
![Status](https://img.shields.io/badge/status-Production%20Ready-brightgreen)

An enterprise-grade, autonomous multi-platform job intelligence orchestrator with a **126 Job Platform Matrix (126 platforms)**, a **Sequential Per-Job Deep ATS Enrichment Engine**, and a **Real-Time Web Application Dashboard** built with FastAPI and Vanilla JS.

For every job lead across all 126 platforms (up to a configurable limit, default **20 jobs per board**), the agent sequentially traces, verifies, and resolves the 4-link hierarchy:
$$\text{Original Listing URL} \longrightarrow \text{Official Company Website} \longrightarrow \text{Official Company Career Portal} \longrightarrow \text{\textbf{Direct ATS Apply Link (Must)}}$$
and exports all 4 clickable hyperlinks directly into formatted Excel (`.xlsx`) workbooks with high-contrast formatting and color-coded status badges.

---

## 126 Supported Job Platforms Coverage Matrix (126 Total)

| Category | Count | Supported Platforms | Scraper Module |
|---|---|---|---|
| **1. General Tech & Remote** | 20 | WeWorkRemotely, RemoteOK, Remotive, Dice, HackerNews Hiring, BuiltIn, WorkingNomads, Techcareers, Jobspresso, JustRemote, Arc.dev, Himalayas, SkipTheDrive, AuthenticJobs, Pangian, Jobicy, Remote.com, DailyRemote, 4DayWeek, Nodesk | `scrapers/standard_boards.py` |
| **2. Startup & Venture** | 17 | Wellfound, WorkAtAStartup (YC), DynamiteJobs, WelcomeToTheJungle, F6S, Startupers, EUStartups, Underdog, Techstars Jobs, Climatebase, ClimateTechList, Startups.gallery, StartupJobs.cz, VCPlatform, Seedcamp Jobs, BerlinStartupJobs, Hasjob | `scrapers/startup_boards.py` |
| **3. AI & Data Science** | 12 | AI-Jobs.net, DataYoshi, DeepLearningAI, AiCareers, OuterJoin, AnalyticsJobs, DataJobs, DataScienceJobs, MachineLearningJobs, R-users, Kaggle Jobs, HuggingFace Jobs | `scrapers/ai_data_boards.py` |
| **4. Specialized Languages & Frameworks** | 16 | Python.org, GolangProjects, RustJobs, ReactCareers, VueJobs, RubyOnRemote, ElixirJobs, ScalaJobs, AndroidJobs, iOSDevJobs, CPlusPlusJobs, GraphQLJobs, PyJobs, RemotePython, DjangoProject, PythonJobsGithub | `scrapers/specialized_tech_boards.py` |
| **5. Web3 & Blockchain** | 10 | CryptoJobsList, Web3Career, CryptoJobs, UseWeb3, BanklessJobs, SolanaJobs, EthereumJobs, DefiJobs, Blockew, CryptoCareers | `scrapers/web3_boards.py` |
| **6. Gaming & Creative** | 15 | Itch.io, GamesIndustry.biz, GamesJobsDirect, GameDevsOfColor, Hitmarker, WorkWithIndies, GameJobHunter, Maxibestof, Dribbble, ProductHunt, DesignJobs, BehanceJobs, Designhill, UIUXJobsBoard, RemoteGameJobs | `scrapers/gaming_design_boards.py` |
| **7. DevOps, Cloud & Security** | 8 | CyberSecJobs, InfoSecJobs, KubernetesJobs, CloudJobs, DevOpsJobs, LinuxJobs, SREJobs, ClearedJobs | `scrapers/devops_cloud_boards.py` |
| **8. Regional & Global** | 10 | OnlineJobs.ph (APAC), NoFluffJobs (EU), Jobgether (Global), EuroTechJobs (EU), WorkInStartups (UK), GermanTechJobs (DACH), SwissDevJobs (CH), UkDevJobs (UK), Landing.jobs (EU), TokyoDev (APAC) | `scrapers/regional_global_boards.py` |
| **9. Major Aggregators** | 12 | SimplyHired, Jooble, CareerBuilder, Arise, FlexJobs, TheMuse, Ladders, Jobserve, Arbeitnow, LinkedIn, Indeed, Talent.com | `scrapers/aggregator_boards.py` |
| **10. Freelance & Creator Gigs** | 6 | Upwork, Freelancer, Guru, ProBlogger, HeyMarketers, Twine | `scrapers/freelance_boards.py` |

---

## 4-Tier Direct Apply Link & ATS Discovery Architecture

The `discovery/deep_link_matcher.py`, `discovery/career_finder.py`, and `discovery/domain_finder.py` modules guarantee direct apply link resolution:

1. **Tier 1: Outbound Apply Extraction on Original Listing Page**
   - Automatically navigates the platform job posting HTML/Markdown.
   - Detects external apply buttons (`Apply on Company Site`, `Apply Now`, `Job CTA`) and direct outbound ATS redirect links.
2. **Tier 2: Career Portal DOM & JSON-LD Structured Data Matching**
   - Parses the company career page DOM for job title semantic match.
   - Inspects `application/ld+json` (`schema.org/JobPosting`) for `directApply`, `url`, `sameAs`.
   - Extracts embedded ATS `<iframe>` sources (`Greenhouse`, `Lever`, `Ashby`, etc.).
3. **Tier 3: Multi-Engine Targeted ATS Search Query**
   - Dispatches targeted search queries combining company name, exact job title, and ATS domain operators (`greenhouse.io`, `lever.co`, `myworkdayjobs.com`, `ashbyhq.com`, `smartrecruiters.com`, `workable.com`, `bamboohr.com`, `personio.de`, `teamtailor.com`, `jazzhr.com`).
4. **Tier 4: Guaranteed Canonical Career Portal Fallback**
   - If direct application endpoint is gated behind an intranet login, guarantees the exact verified company career portal URL.

---

## Quick Start & Running the Application

### 1. Launch the Web Application UI (Recommended)
```bash
# Using uvicorn:
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# Or via main.py flag:
python main.py --ui
```
Open **[http://127.0.0.1:8000](http://127.0.0.1:8000)** in your browser to access the dashboard.

### 2. Command-Line Interface (CLI) Execution
```bash
# Scrape AI Engineer roles across all 100+ platforms (max 20 jobs/board):
python main.py --keyword "AI Engineer" --location "Remote" --limit 20

# Scrape specific platforms across categories:
python main.py --keyword "Staff Backend" --boards "WeWorkRemotely,RemoteOK,Wellfound,Python.org,CyberSecJobs,HuggingFace Jobs"

# Resume an interrupted session:
python main.py --resume
```

---

## Excel Output Format (.xlsx)

The generated Excel workbook (`data/exports/job_leads.xlsx`) contains:
- **Title**, **Company**, **Location**, **Source Board**, **Extraction Timestamp**
- **4 Clickable Hyperlinks**:
  1. `Open Listing ↗` (Original Board Job Posting)
  2. `Website ↗` (Company Root Domain)
  3. `Career Page ↗` (Company Careers Portal)
  4. `Apply Direct ⚡` (Direct ATS Application URL)
- Color-coded verification status chips (`Verified on Company Site`, `Direct Apply Found`, `Board Extracted`).

---

## Automated Test Suites

Run the full automated test suite to verify 126 platform registrations, scrapers, ATS matchers, domain finders, and Excel exports:

```bash
python tests/test_board_registry.py
python tests/test_deep_link_matcher.py
python tests/test_career_finder.py
python tests/test_domain_finder.py
python tests/test_per_job_orchestrator.py
python tests/test_excel_exporter.py
python tests/test_state_manager.py
python tests/test_standard_boards.py
python tests/test_niche_boards.py
python tests/test_aggregator_boards.py
```
