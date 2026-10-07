# ⚡ Hyrd — Autonomous Multi-Agent Career Platform
> **Don't just search. Get Hyrd!**

An end-to-end, multi-agent autonomous job search, resume customization, company intelligence, application pipeline, and interview coaching platform built with **Google Antigravity** and **Streamlit**.

> 📖 **Looking for the complete walkthrough?** See the [**User Guide & User Manual (USER_GUIDE.md)**](USER_GUIDE.md) for a front-to-back guide from a candidate's perspective.
> 🚀 **Deploying to Production?** See the [**Production Deployment Guide (DEPLOYMENT.md)**](DEPLOYMENT.md) for Docker and Google Cloud Run instructions.
> 🏛️ **Architecture & Refactoring Specs?** See the [**Architecture Refactoring & Optimization Summary (ARCHITECTURE_REFACTORING_SUMMARY.md)**](ARCHITECTURE_REFACTORING_SUMMARY.md) for full modularization benchmarks, zero-regression test proofs, and component hierarchy.

---

## 🚀 Version 4 Milestones (v4.0.0)

- **🎯 Screen 2: Recommended Roles & Recruiter Gap Analysis**:
  - **Dynamic Role Match Scoring**: Evaluates candidate profile against each recommended role with an expert recruiter score (0–100%) and dynamic qualitative tier badges (*Exceptional Fit*, *Strong Match*, *High Potential*).
  - **Interactive Recruiter Analysis Modal**: Comprehensive recruiter evaluation pop-up revealing candidate strengths and a detailed **100% Match Gap Analysis** outlining exact skills to acquire, experience to emphasize, and certifications to earn.
  - **Selective Role Search Checkboxes**: Candidates can selectively check or uncheck individual Recommended Roles to fine-tune exactly which search vectors are crawled.
  - **Ergonomic 2-Column Review**: Balanced layout positioning Target Employers & Exclusions in the right column and Core Competencies directly below Recommended Roles.
- **📍 Screen 4: Geographic Salary Calibration & Freshness Intelligence**:
  - **Target Location & Countries Compensation Calibration**: Salary Score and Market Benchmark Rank are dynamically calibrated against the candidate's designated geographic market (e.g. US, UK/Europe, Canada, Remote, APAC, LATAM, Middle East) with dynamic location badges.
  - **"Days Since Posted" Freshness Indicator**: Positioned directly after `📍 Location:` on every job card with numeric days count and color-coded tier badges (`🔥 New (<= 3 days)`, `⏱️ Recent (4-14 days)`, `📅 Active (> 14 days)`).
  - **Heterogeneous Date Engine (`date_utils.py`)**: Seamlessly normalizes ISO timestamps, relative durations (*days, weeks, months*), and live ATS feed active statuses.
- **🏛️ High-Throughput Modular Architecture**: Complete decoupling of scrapers (`src/agents/scrapers/`), semantic matching (`src/agents/matching/`), and UI dialogs (`src/components/dialogs/`).
- **⚡ Unified Gemini Gateway (`src/utils/gemini_client.py`)**: Thread-safe client pooling, dynamic multi-tier fallback routing, and exponential backoff retry.
- **🏎️ Sub-Second In-Memory Caching & Pre-Compiled Patterns**: 50+ pre-compiled regex patterns and `@lru_cache` accelerated salary benchmarking and geo-matching.
- **🛡️ 100% Zero-Regression Test Suite (`tests/`)**: Automated baseline unit and integration test coverage across all subsystems with 37/37 passing test suites.

---

## 🚀 Version 3 Milestones (v3.0.0)

- **🐳 Production Containerization & Cloud Run Ready**: Complete production `Dockerfile`, non-root security profile (`appuser`), Docker Compose, Google Cloud Build pipeline (`cloudbuild.yaml`), native health checks (`/_stcore/health`), and one-click deployment scripts.
- **📄 1-Click ATS-Certified PDF & Word (DOCX) Exporter**:
  - **ATS-Compliant PDF Generation**: Uses `fpdf2` with single-column linear layout, standard Helvetica typography, 18mm margins, and UTF-8 safe character translation to ensure 100% parseability by Greenhouse, Ashby, Lever, and Workday.
  - **Executive Word (.docx) Export**: Clean Calibri 11pt formatting with standard heading taxonomy and proper list indentations.
  - **Cover Letter Multi-Format Downloads**: One-click download of tailored cover letters in formal letterhead PDF, executive DOCX, or plain text.
- **🏢 Company Intelligence & Executive Dossier Agent (`src/agents/company_intelligence_agent.py`)**:
  - **Deep-Dive Employer Investigations**: Analyzes business model, funding stage, valuation, and notable venture capital investors (Sequoia, a16z, Accel, YC).
  - **Tech Stack & Architecture**: Identifies core languages, frontend/backend frameworks, database/storage layer, cloud infrastructure, and AI/ML tooling.
  - **Culture & Leadership**: Maps leadership team (CEO, CTO, Head of Talent), remote-first philosophy, release cadence, and employee sentiment with Glassdoor/Blind pros and watch-outs.
  - **Strategic Interview Talking Points**: Generates 3 sharp, insider-level questions grounded in the company's business model to separate the candidate from other applicants.
- **🔭 Autonomous Job Scout & Morning Career Digest (`src/agents/job_scout_agent.py`)**:
  - **Autonomous Background Monitor**: Tracks configured ATS employers (Ashby, Greenhouse, Lever, etc.) and remote boards on a customizable schedule.
  - **Automated Differential Detection**: Isolates newly posted opportunities since the last cycle.
  - **Morning Career Intelligence Digest**: Synthesizes hiring tempo signals, top curated openings with fit scores, and recommended actions.
  - **1-Click Batch Actions**: Auto-add curated matches to the Kanban pipeline or launch one-click ATS resume tailoring.
  - **Email Alert Export**: Formatted markdown newsletter ready to copy or email to the candidate.

---

## 🚀 Previous Milestones: Version 2 (v2.0.0)

- **👥 Multi-User Account Hub & Dedicated Workspace Isolation (Screen 0)**:
  - **Multi-Candidate Platform**: Multiple job seekers can manage their careers on the same application with 100% data isolation.
  - **Dedicated Filesystem Storage**: Each candidate possesses their own directory under `data/users/{user_id}/` holding their detailed profile (`profile.json`) and complete saved state (`workspace.json`).
  - **Zero Cross-Contamination**: Switching candidates instantly flushes active session data to disk and rehydrates the target user's saved jobs, applied jobs, Kanban pipeline stages, interview packs, customized cover letters, and tailored CVs.
  - **LinkedIn-Style Candidate Registry**: Register full professional details (headline, industry, seniority, compensation targets, core competencies, accomplishments, education, certifications, and portfolio links) with optional **1-Click Resume Auto-Fill** powered by the Gemini Resume Parser Agent.
- **⚡ Concurrent Async Scraping Pipeline**: All 14 job search sources now execute concurrently in parallel via `concurrent.futures.ThreadPoolExecutor(max_workers=14)`. Scraping execution time dropped from ~25s down to **4–8 seconds** with live progress telemetry.
- **🏢 "Dream Companies" Dynamic ATS Target Filter**: Candidates can specify target employers (e.g., `Linear, Stripe, Databricks, Figma, OpenAI, Ramp`). The system dynamically normalizes company slugs and directly queries their live Ashby, Greenhouse, Lever, and SmartRecruiters ATS feeds, badging matching roles with **⭐ Target Dream Company** and providing scoring boosts.
- **🚫 Negative Keyword / Exclusion Filter**: Candidates can define exclusion keywords (e.g., `Clearance, Crypto, Staffing Agency, C2C, Unpaid`). Jobs containing any of these terms in their title, employer, or description are automatically filtered out during evaluation.
- **🎯 Built-in ATS Screening & Optimization Engine**:
  - **Interactive ATS Compatibility Scorecard**: Audits tailored CVs in real time with a 0–100% score, letter grade (`A+ (Guaranteed ATS Pass)`), keyword density metrics, and a 5-point parser compliance checklist.
  - **Strict Parser-Safe Formatting**: Single-column linear layout without tables, standard ATS section headings (`PROFESSIONAL SUMMARY`, `CORE COMPETENCIES & TECHNICAL SKILLS`, `PROFESSIONAL EXPERIENCE`, `EDUCATION & CREDENTIALS`), and clean plain-text contact blocks.
  - **Google XYZ Impact Bullets**: Rewrites accomplishments to quantify results (`Accomplished [X] as measured by [Y] by doing [Z]`).
  - **ATS-Certified `.docx` Export**: Generates Word documents using standard Calibri 11pt typography, 0.75" margins, and standard paragraph styles.
  - **ATS-Aligned Cover Letters & Outreach**: Requisition Matching lines (`RE: Application for [Role] (Req Match)`) and Boolean search query alignment for LinkedIn Recruiter and Talent CRMs.

---

## 🏗️ Architecture & 6-Screen Deterministic Flow

The platform is organized as a modular 6-screen deterministic state machine governed by `st.session_state`:

```
[Screen 0: Candidate Account Hub & User Registry]
                    │
                    ▼
[Screen 1: Candidate Intake & Resume Parsing]
                    │
                    ▼
[Screen 2: Profile Review & Competency Calibration]
                    │
                    ▼
[Screen 3: 14-Source Concurrent Async Scraping Engine]
                    │
                    ▼
[Screen 4: Job Dashboard & 4 Agentic Power Tools]
                    │
                    ▼
[Screen 5: Application Pipeline & Kanban Board]
```

### Screen Breakdown:
0. **Screen 0: Candidate Account Hub & User Registry (`src/views/screen0_registry.py`)**
   - Candidate Workspace Switcher: Browse registered profiles, view workspace statistics, switch active workspace with 1 click, or delete accounts.
   - Comprehensive LinkedIn-Style Candidate Registration: Contact details, professional headline, avatar theme, seniority, target roles, desired salary, dream companies, negative keywords, competencies, and work history.
   - 1-Click Resume Auto-Fill: Upload an existing resume (`.pdf`, `.docx`, `.txt`) to auto-populate the registration form via Gemini.
   - Active Profile Editor: In-place editing of profile attributes and search parameters.
1. **Screen 1: User Input Form (`src/views/screen1_input.py`)**
   - Active workspace integration: Auto-populated with the active candidate's criteria.
   - File upload supporting **`.pdf`**, **`.docx`**, and **`.txt`** with Gemini resume parsing.
   - Intelligent auto-fill for Candidate Name, Seniority Level, and Core Competencies.
   - Dynamic Target Role selector (extracted query dropdown + manual custom input).
   - Location, Work Mode (*Remote Only, Hybrid, On-site, Open to All*), and Minimum Salary preferences.
   - **Target Dream Companies**: Optional comma-separated list of priority employers.
   - **Negative Keywords**: Optional comma-separated exclusion keywords.
2. **Screen 2: Profile Review & Role Calibration (`src/views/screen2_review.py`)**
   - Synthesized candidate summary, verified competencies, experience highlights, target ATS employers, and exclusion filters.
   - **Recommended Roles**: Dynamically classified roles with recruiter **Role Match Scores** (0-100%) and qualitative tier badges (*Exceptional Fit*, *Strong Match*, *High Potential*).
   - **Recruiter Analysis & 100% Match Gap Analysis Modal**: Explains fit rationale and provides step-by-step guidance on skills, experience, and certifications needed to hit 100% match.
   - **Selective Search Checkboxes**: Check or uncheck recommended roles to control which queries are crawled.
3. **Screen 3: Concurrent Multi-Source Scraping Stream (`src/views/screen3_loading.py`)**
   - Real-time animated telemetry tracking concurrent crawlers across **14 live job sources** executed in parallel.
   - Profile-driven semantic matching, exclusion rejection, and deduplication.
4. **Screen 4: Job Dashboard (`src/views/screen4_dashboard.py`)**
   - Ranked job opportunities with calibrated Match Score badges and **⭐ Target Dream Company** indicators.
   - **Days Since Posted Indicator**: Positioned right after Location with elapsed day count and freshness tier badges (`🔥 New`, `⏱️ Recent`, `📅 Active`).
   - **Geographic Salary Evaluator**: Numerical score (0-100) and market rank calibrated to the candidate's designated **Target Location & Countries** from Screen 1.
   - **The 4 Agentic Power Tools on Every Job Card**:
     - 📄 **Tailored CV (ATS-Optimized)**: Custom CV tailored for the specific employer with an interactive ATS Compatibility Scorecard, 5-point parser audit, keyword density metrics, and ATS-certified Word (`.docx`) download.
     - ✉️ **Tailored Cover Letter (ATS-Aligned)**: Targeted cover letter featuring an explicit Requisition Match line and keyword mirroring with text download.
     - 🎤 **AI Interview Prep Pack**: 7-tab prep suite (Briefing, 5 Tech Q&A, 4 STAR stories, Gap handling, Reverse questions, 15-min cheat sheet, `.docx` & `.txt` downloads).
     - 📬 **Recruiter Outreach Drafter (Boolean Match)**: 5-part cold outreach campaign optimized for recruiter talent searches and InMails (LinkedIn $\le 300$-char note with counter, Hiring Manager email, InMail, Referral request, Thank You note, `.docx` download).
5. **Screen 5: Application Pipeline & Kanban Tracker (`src/views/screen5_pipeline.py`)**
   - 5-stage visual Kanban board (*Saved ➔ Applied ➔ Interviewing ➔ Offer Received ➔ Archived*).
   - Drag-and-drop / select stage mover, notes dialog, custom application logger, and JSON export.

---

## 🌐 The 14-Source Scraping Engine

| # | Source | Type / Focus | Integration Method |
|---|---|---|---|
| 1 | **We Work Remotely** | Global Remote Jobs | Official RSS feed parser (`/remote-jobs.rss`) |
| 2 | **TelecomCareers (TelecomCrossing)** | Telecommunications & Network Engineering | HTML parser and job card extractor (`/jobs/`) |
| 3 | **ZipRecruiter** | Broad Multi-Sector Job Network | Dual-layer scraper (`python-jobspy` + syndicated partner network) |
| 4 | **Ashby** | Modern Tech Scale-ups (Linear, Retool, Ramp, Perplexity AI...) | Direct Public Board API (`api.ashbyhq.com`) + Custom Target Slugs |
| 5 | **Greenhouse** | Enterprise Tech Leaders (Stripe, Airbnb, Databricks, GitLab...) | Public Board API (`boards-api.greenhouse.io`) + Custom Target Slugs |
| 6 | **Lever** | Top Innovators (Spotify, Netflix, Eventbrite, Atlassian...) | Public Postings API (`api.lever.co`) + Custom Target Slugs |
| 7 | **SmartRecruiters** | Global Enterprises & Institutions (CERN, Informa, Colt...) | Public Postings API (`api.smartrecruiters.com`) + Custom Target Slugs |
| 8 | **JobSpy** | Direct Multi-Board Scraper | Python library (`python-jobspy`) for Indeed |
| 9 | **Apify** | Cloud Web Scraping Actors | Native `apify-client` integration (optional sidebar token) |
| 10 | **LinkedIn Jobs** | Worldwide Professional Network | Public guest search query endpoint |
| 11 | **Arbeitnow** | European & Global Business Roles | REST API (`/api/job-board-api`) |
| 12 | **Jobicy** | Remote Cross-Discipline | REST API v2 (`/api/v2/remote-jobs`) |
| 13 | **RemoteOK** | Remote Tech & Business Roles | Direct feed API (`/api`) with compensation data |
| 14 | **Remotive** | Curated Remote Positions | REST API (`/api/remote-jobs`) |

---

## 🚀 How to Run the App Locally

### 1. Clone & Setup
```bash
git clone https://github.com/dmendes77git/agentic-ai-job-search-v4.git
cd agentic-ai-job-search-v4

# Create and activate virtual environment (Windows PowerShell)
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Launch Streamlit
```bash
streamlit run app.py
```
Streamlit will print the local server URL (typically `http://localhost:8501`) and automatically open it in your default browser.

---

## 📁 Repository Structure

```
agentic-job-search/
├── app.py                            # Streamlit entry point, router & sidebar controls
├── requirements.txt                  # Python dependencies
├── README.md                         # Project overview and run guide
├── USER_GUIDE.md                     # Comprehensive User Manual & Walkthrough
├── data/
│   └── users/                        # Persistent multi-user filesystem isolation
│       ├── registry.json             # Global account registry & active user pointer
│       └── {user_id}/                # Per-candidate dedicated workspace directory
│           ├── profile.json          # Full LinkedIn-style candidate profile
│           └── workspace.json        # Isolated Kanban, tailored CVs, prep packs & saved jobs
├── src/
│   ├── state.py                      # State machine, screen definitions & session defaults
│   ├── mock_data.py                  # Seed sample resumes, mock profiles & benchmark jobs
│   ├── agents/
│   │   ├── resume_parser_agent.py    # Gemini resume parser with Pydantic structured output
│   │   ├── job_scraper_agent.py      # 14-source scraping engine & semantic matcher
│   │   ├── application_agent.py      # Tailored CV and Cover Letter generator + docx export
│   │   ├── interview_prep_agent.py   # 6-part interview master pack generator + docx export
│   │   └── outreach_agent.py         # 5-message recruiter outreach drafter + docx export
│   ├── components/
│   │   ├── stepper.py                # Visual 6-step progress header (Screen 0 through 5)
│   │   └── application_dialogs.py    # Modal dialogs for CV, Cover Letter, Prep Pack & Outreach
│   ├── utils/
│   │   ├── user_manager.py           # Multi-user isolation, registry & workspace persistence
│   │   ├── ats_optimizer.py          # ATS compliance scoring, formatting & keyword auditing
│   │   ├── pipeline_manager.py       # Kanban pipeline persistence & lifecycle transitions
│   │   └── salary_evaluator.py       # Compensation benchmarking & market score
│   └── views/
│       ├── screen0_registry.py       # Screen 0: Candidate Account Hub & LinkedIn Registry
│       ├── screen1_input.py          # Screen 1: Document upload, autofill & preferences
│       ├── screen2_review.py         # Screen 2: Candidate profile card & competency tags
│       ├── screen3_loading.py        # Screen 3: Live telemetry progress & 14-source crawl
│       ├── screen4_dashboard.py      # Screen 4: Ranked job matches, salary scores & 4 tools
│       └── screen5_pipeline.py       # Screen 5: Application Kanban board & external tracking
```

---

## 📄 License
MIT License. Built with Google Antigravity.
