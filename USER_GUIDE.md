# 📖 Hyrd — Comprehensive User Guide & Manual
> **Don't just search. Get Hyrd!**

Welcome to **Hyrd**, an autonomous multi-agent career acceleration, job search, company intelligence, application tracking, and interview coaching platform powered by **Google Antigravity**.

This guide provides a comprehensive, front-to-back walkthrough of the application from a candidate’s perspective, explaining every screen, tool, setting, and automated agent in detail.

---

## 📑 Table of Contents

1. [System Overview & Architecture](#-system-overview--architecture)
2. [Prerequisites & Quick Start](#-prerequisites--quick-start)
3. [Global Navigation & Settings Sidebar](#-global-navigation--settings-sidebar)
4. [Screen 0: Candidate Account Hub & User Registry](#-screen-0-candidate-account-hub--user-registry)
5. [Screen 1: Candidate Profile Intake & Search Preferences](#-screen-1-candidate-profile-intake--search-preferences)
6. [Screen 2: Profile Review & Competency Calibration](#-screen-2-profile-review--competency-calibration)
7. [Screen 3: Agentic Search & The 14-Source Scraping Engine](#-screen-3-agentic-search--the-14-source-scraping-engine)
8. [Screen 4: Job Dashboard & Opportunity Evaluation](#-screen-4-job-dashboard--opportunity-evaluation)
   - [Salary Evaluator & Market Benchmarking](#salary-evaluator--market-benchmarking)
   - [The 4 Agentic Power Tools](#the-4-agentic-power-tools)
9. [Screen 5: Application Pipeline & Kanban Tracker](#-screen-5-application-pipeline--kanban-tracker)
10. [Exporting Documents & Application Artifacts](#-exporting-documents--application-artifacts)
11. [Troubleshooting & Frequently Asked Questions](#-troubleshooting--frequently-asked-questions)

---

## 🌟 System Overview & Architecture

Unlike traditional static job boards, **Agentic AI Job Search** employs a multi-agent architecture where specialized AI agents collaborate across a 6-step deterministic state machine with isolated multi-user workspaces:

```
[Screen 0: Candidate Account Hub & User Registry]
                     │
                     ▼
[Screen 1: Candidate Intake & Resume Parser]
                     │
                     ▼
[Screen 2: Profile Review & Calibration]
                     │
                     ▼
[Screen 3: 14-Source Autonomous Crawler & Matcher]
                     │
                     ▼
[Screen 4: Job Dashboard & 4 Power Tools]
                     │
                     ▼
[Screen 5: Application Kanban & Pipeline Tracker]
```

### Specialized Agents & Systems:
- **User Manager & Workspace Isolation (`user_manager.py`)**: Manages isolated multi-user workspaces (`data/users/{user_id}/`). Persists full candidate career profiles, tailored CVs, cover letters, prep packs, outreach messages, and Kanban stages with zero cross-contamination.
- **Resume Parser Agent (`resume_parser_agent.py`)**: Ingests uploaded resumes in `.pdf`, `.docx`, or text formats, extracts structured competencies, career history, and target roles via Google Gemini with Pydantic schemas. Supports 1-click auto-fill during profile registration.
- **Job Scraper & Crawler Agent (`job_scraper_agent.py`)**: Concurrently crawls **14 live job sources** across major networks, applicant tracking systems (ATS), and scrapers.
- **Semantic Matcher & Scoring Agent**: Evaluates roles using a three-tier scoring model (Title & Seniority, Skill Overlap, Location/Work Mode) to produce calibrated fit scores (0–100%).
- **Salary Benchmark Evaluator (`salary_evaluator.py`)**: Analyzes compensation against market baselines and candidate seniority, generating a numerical Salary Score and market rank (*Above Market*, *Within Market Standard*, *Below Market*).
- **Application Tailoring Agent (`application_agent.py`)**: Dynamically tailors customized CVs and high-conversion cover letters specifically targeted to each employer.
- **AI Interview Prep Agent (`interview_prep_agent.py`)**: Generates role-specific 6-part interview master packs (Executive Briefing, 5 Technical Q&As, 4 STAR behavioral scenarios, skill gap handling, and a 15-minute cheat sheet).
- **Recruiter Cold Outreach Drafter (`outreach_agent.py`)**: Formulates multi-channel outreach campaigns including strict $\le 300$-character LinkedIn notes, direct hiring manager emails, recruiter InMails, referral requests, and thank-you notes.

---

## 🚀 Prerequisites & Quick Start

### 1. Requirements
- **Python**: Version 3.10, 3.11, 3.12, 3.13, or 3.14.
- **Google Gemini API Key** *(Optional but recommended)*: Activates live Gemini reasoning (`gemini-3.8-flash`, `gemini-2.5-flash`). If omitted, the application runs in high-fidelity offline fallback mode.
- **Apify API Token** *(Optional)*: Enables cloud Apify web actors for extended datasets.

### 2. Local Installation
```bash
# Clone the repository
git clone https://github.com/dmendes77git/agentic-ai-job-search.git
cd agentic-ai-job-search

# Create and activate virtual environment (Windows PowerShell)
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install required dependencies
pip install -r requirements.txt

# Run the Streamlit application
streamlit run app.py
```

---

## 🎛️ Global Navigation & Settings Sidebar

The left sidebar gives you full control over candidate workspace management, application state, AI models, and cloud credentials:

1. **Active Candidate Workspace Card**: Displays the current candidate's avatar, initials, full name, and professional headline.
2. **👥 Switch Candidate / Hub Button**: 1-click shortcut that automatically flushes the active session to disk and opens Screen 0 (Candidate Hub).
3. **Current State & Progress Indicator**: Displays which step is active (`Screen 0` to `Screen 5`).
4. **⚡ Quick Jump Navigation**: Allows instant switching between any screen without losing your session data.
5. **🔄 Reset Current Search**: Clears current search results while keeping this user's profile and pipeline completely intact.
6. **🔑 Gemini API Settings**:
   - **Gemini API Key input**: Paste your key securely (`AIzaSy...`).
   - **Model Strategy**: Choose between `Auto (Dynamic Discovery & Smart Cascade)` or select specific models (`gemini-3.8-flash`, `gemini-2.5-flash`, `gemini-2.0-flash`).
   - **🔍 Test Key button**: Validates the key directly against Google's endpoint and lists authorized models.
7. **☁️ Apify Cloud Scraper Settings**:
   - Optional API token input to run cloud web scraping actors.
   - When left blank, the app relies on **JobSpy** (Indeed, ZipRecruiter) and direct public ATS endpoints (Ashby, Greenhouse, Lever, SmartRecruiters).
8. **🛠️ Session State Inspector**: A JSON viewer for inspecting session variables in real time.

---

## 👤 Screen 0: Candidate Account Hub & User Registry

Positioned as the gateway before Screen 1, **Screen 0** delivers multi-user candidate management, allowing multiple job seekers to utilize the application on the same machine with **100% data isolation**.

### 1. Dedicated Workspace Architecture
Each candidate is assigned a unique account ID and an isolated directory on disk:
- `data/users/registry.json`: Global account index storing candidate metadata, headlines, avatar colors, and the active user pointer.
- `data/users/{user_id}/profile.json`: Full LinkedIn-style career record, including contact info, executive summary, target roles, dream employers, negative exclusion keywords, core competencies, work accomplishments, education, certifications, and portfolio links.
- `data/users/{user_id}/workspace.json`: Complete user workspace containing:
  - 📋 **Application Pipeline**: All Kanban application cards, custom notes, and interview stages.
  - ⭐ **Saved Jobs**: Candidate-specific bookmarked opportunities.
  - 🚀 **Applied Jobs**: In-app application tracker history.
  - 📄 **Customized CVs**: All ATS-tailored resume variants generated for specific employers.
  - ✉️ **Customized Cover Letters**: All employer-specific cover letters.
  - 🎤 **Interview Prep Packs**: Generated STAR interview preparation guides and cheat sheets.
  - 📬 **Outreach Campaigns**: Multi-channel cold recruiter outreach sequences.
  - 🔍 **Discovered Jobs**: Scraped job listings matched specifically to this candidate.

### 2. Tab 1: 👥 Switch Candidate Workspace
- **Candidate Account Cards**: Displays each registered job seeker with their avatar initials, color theme, headline, location, and key metrics (*Saved Jobs*, *Pipeline Apps*, *Tailored CVs*).
- **🚀 Enter Workspace**: Instantly loads the candidate's complete profile and workspace into session state.
- **📋 Open Kanban**: Directly jumps into the candidate's active application pipeline.
- **👁️ View Details**: Expands the candidate's executive summary, target employers, exclusion keywords, and top competencies.
- **🗑️ Delete Candidate**: Permanently purges the candidate profile and workspace folder with automatic fallback to another candidate.

### 3. Tab 2: ➕ Register New Candidate (LinkedIn-Style Intake)
A comprehensive registration form modeled after LinkedIn's complete profile schema:
- **1-Click Resume Auto-Fill**: Upload an existing resume (`.pdf`, `.docx`, `.txt`) and click *"⚡ Auto-Fill Details with Gemini Resume Parser"*. Gemini extracts and automatically populates all form sections (including personal LinkedIn address).
- **Section 1: Personal & Contact Identity**:
  - Full Name, Email Address, Phone Number, Current Location.
  - **Personal LinkedIn Address**: Directly integrated into Section 1.
  - **🔍 AI LinkedIn Profile Auditor Agent**: A dedicated button (`🔍 Analyze LinkedIn Profile with AI Agent`) that audits the candidate's LinkedIn URL and career background:
    - *Overall Optimization Rating (0–100)* & Letter Grade (e.g. `A+`, `A`, `B+`).
    - *5-Pillar Score Cards*: Headline Searchability, About Bio Value Proposition, Core Skills Fit, Experience Quantification, and URL Slug Hygiene.
    - *💡 3 High-Impact Headline Alternatives*: Ready-to-use formulas with 1-click *"👉 Apply to Form"* buttons.
    - *📝 Rewritten Executive About Bio*: Complete 3-section narrative with 1-click *"👉 Apply to Form"* button.
    - *🏷️ Missing Recruiter Keywords*: Crucial terms to add to boost LinkedIn Recruiter and Talent CRM search visibility.
    - *📋 Actionable Profile Plan*: Specific guidance on custom vanity URL slugs, featured sections, and metrics.
  - **Avatar Color**: Dropdown displaying actual color names and emojis (`🔵 Royal Blue`, `🟣 Electric Purple`, `🟢 Emerald Green`, `🟠 Warm Amber`, `🔴 Crimson Red`, `🩵 Ocean Cyan`, `🔷 Deep Indigo`, `🌺 Rose Magenta`, `🌐 Sky Blue`, `⚫ Slate Charcoal`) with an active live circular swatch preview.
- **Section 2: Professional Summary & Bio**: Professional headline and executive summary (About me).
- **Section 3: Career Seniority & Current Experience**: Seniority tier (*Junior, Mid-Level, Senior, Staff/Principal, Director, Executive*), years of experience, and current/most recent employer.
- **Section 4: Work Mode & Compensation Target**: Work mode (*Remote Only, Hybrid, On-site, Open to All*) and minimum desired salary.
- **Section 5: Strategic Target & Exclusion Filters**:
  - *Target Dream Companies*: Priority employers whose live ATS endpoints (Ashby, Greenhouse, Lever, SmartRecruiters) will be actively crawled.
  - *Negative Exclusion Keywords*: Terms to automatically filter out unwanted roles.
- **Section 6: Core Competencies & Skills**: Tag-based list of technical skills, frameworks, and methodologies.
- **Section 7: Work History & Accomplishments**: Quantified accomplishment bullet points following the Google XYZ formula.
- **Section 8: Additional Portfolio & Code Links**: GitHub profile URL and personal portfolio website.

### 4. Tab 3: ✏️ Edit Active Profile Details
Allows active candidates to quickly update their headline, target roles, personal LinkedIn address, remote preference, minimum compensation, dream employers, negative keywords, or core competencies without re-registering. Also includes the **🔍 Analyze LinkedIn Profile with AI Agent** tool with 1-click apply buttons to update the active candidate's live profile.

---

## 📝 Screen 1: Candidate Profile Intake & Search Preferences

The intake screen automatically inherits all parameters from the active candidate's profile:

### 1. Resume Intake Options
- **📂 Upload Document**: Drag and drop your existing resume as a **`.pdf`**, **`.docx`**, or **`.txt`** file. The system extracts raw text and passes it to the Resume Parser Agent.
- **📋 Paste Raw Resume**: Directly paste plain text or Markdown into the text area.
- **⚡ Load Sample Resume**: 1-click button that loads a pre-configured Senior AI/Software Architect profile (`Alex Mercer`) for rapid testing.

### 2. Intelligent Auto-Filling
Once a resume is uploaded or parsed:
- **Candidate Name**: Automatically extracted from the resume profile.
- **Experience Level**: Automatically classified (e.g., *Senior (8+ years)*, *Staff / Principal (12+ years)*).
- **Primary Competency Focus**: Automatically extracted from core skills and formatted as selectable tags.

### 3. Search Preferences & Advanced Target Filters
- **Target Role**:
  - Select from a dynamic dropdown of extracted job query variations (e.g., *Staff AI Systems Architect*, *Principal Machine Learning Engineer*).
  - Or enter your desired target role title manually in the text field.
- **Target Location & Countries** *(Mandatory)*: Enter your desired geographic location (e.g., `Remote`, `United Kingdom`, `Germany`, `San Francisco`, `New York`, `Worldwide`). On-site and hybrid roles strictly match your designated locations.
- **Work Mode Preference**:
  - `Remote Only` (Default)
  - `Hybrid Preferred (Remote + Hybrid in Target Countries)`
  - `Open to On-site (Remote, Hybrid & On-site in Target Countries)`
  - `On-site Only (Target Countries)`
  - `No Preference`
- **Desired Minimum Salary** *(Optional)*: Enter your target compensation threshold (e.g., `$150,000`).
- **🏢 Target Dream Companies** *(Optional - v2 New)*: Enter priority employers separated by commas (e.g., `Linear, Stripe, Databricks, Figma, OpenAI, Ramp`). The system dynamically normalizes company names and directly queries their live Ashby, Greenhouse, Lever, and SmartRecruiters ATS job feeds.
- **🚫 Negative Keywords / Exclusions** *(Optional - v2 New)*: Enter comma-separated terms to exclude (e.g., `Clearance, Crypto, Staffing Agency, C2C, Unpaid`). Any job containing these words in the title, company name, or description will be filtered out automatically.

Click **"🤖 Parse Resume with Agent & Review Profile →"** to proceed.

---

## 🔍 Screen 2: Profile Review & Competency Calibration

Screen 2 presents the structured output extracted by the AI agent before initiating the live web crawl, organized in an ergonomic 2-column layout:

1. **Executive Candidate Card**:
   - Verified Candidate Name, Classified Seniority Tier, and Target Role.
   - Comprehensive Professional Summary synthesizing years of experience, core domains, and leadership achievements.

2. **Left Column — Recommended Roles & Core Competencies**:
   - **Recommended Roles**: Prioritized target role queries extracted from your profile and industry demand.
   - **Selection Checkboxes**: Check or uncheck individual recommended roles so the agentic crawler targets only the exact queries you desire.
   - **Role Match Score (0–100%)**: Evaluates how well your profile and experience align with each proposed position.
   - **Dynamic Qualitative Tiers**: Visual badges formatted alongside the match score:
     - `🟢 Exceptional Fit (90-100%)`
     - `🔵 Strong Match (80-89%)`
     - `🟡 High Potential (70-79%)`
   - **Recruiter Analysis Pop-up Window**: Clicking **"Recruiter Analysis"** opens an interactive modal with:
     - Recruiter evaluation overview detailing profile alignment.
     - **100% Match Gap Analysis**: Specific actionable recommendations on:
       - ⚡ **Skills to Acquire / Deepen**: Frameworks or technical proficiencies to master.
       - 📈 **Experience to Emphasize**: Project scale, team leadership, or metrics to highlight.
       - 📜 **Certifications & Credentials**: High-impact industry certifications to earn.
   - **Core Competencies & Skills**: Positioned directly below Recommended Roles, showing technical proficiencies, frameworks, methodologies, and leadership skills.

3. **Right Column — Experience Highlights & Filters**:
   - **Key Experience Highlights**: Quantifiable achievements and metrics extracted from your career history.
   - **Target Employers & Exclusion Filters**: Positioned below Experience Highlights with green badges for active Target ATS Companies and red badges for negative Exclusion Keywords.

4. **Navigation**:
   - **← Back to Edit Input**: Return to Screen 1 to make changes.
   - **🚀 Confirm & Launch Agentic Search**: Triggers the concurrent async scraping and matching pipeline for the selected recommended roles.

---

## ⚡ Screen 3: Agentic Search & The 14-Source Concurrent Scraping Engine

Screen 3 is an interactive search engine that executes parallel scraping, filters opportunities by your criteria, and scores each position.

### Concurrent Async Architecture (v2 New)
In Version 2, all 14 scrapers execute concurrently via `concurrent.futures.ThreadPoolExecutor(max_workers=14)`. Instead of waiting sequentially across 14 networks (which previously took 25+ seconds), all scrapers run in parallel, retrieving 350+ live opportunities in **4 to 8 seconds**.

### Live Telemetry & Progress Stream
- Real-time progress bar (0% to 100%) dynamically incrementing as each scraper finishes.
- Animated terminal-style execution log detailing each crawler’s actions, timestamp, retrieved counts, and status.

### The 14-Source Multi-Agent Scraping Engine

The platform aggregates opportunities across 14 distinct global sources:

| # | Source | Domain & Focus | Work Modes & Coverage | Integration & Scraping Method |
|---|---|---|---|---|
| **1** | **We Work Remotely** | Curated remote roles (Tech, Product, Design, Sales, Support, Finance) | **100% Remote** (Worldwide & Regional) | Official RSS Feed parser (`/remote-jobs.rss`) extracting clean descriptions and application URLs |
| **2** | **TelecomCareers (via TelecomCrossing)** | Telecommunications, Wireless, 5G, Satellite, RF, and Network Infrastructure | **On-site, Hybrid & Remote** | Live HTML parser and job card extractor (`/jobs/`) with direct listing links (`/job/id-...`) |
| **3** | **ZipRecruiter** | Comprehensive job market across all industries and professions | **On-site, Hybrid & Remote** | Dual-layer scraper (`python-jobspy` with syndicated partner network resilience) |
| **4** | **Ashby** | High-growth scale-ups (Linear, Retool, Ramp, Perplexity AI, Synthesia, Sentry, ElevenLabs, Vanta, Cursor...) | **Remote, Hybrid & On-site** | Direct Public Board API (`api.ashbyhq.com/posting-api/job-board/{org}`) + Dynamic Dream Company Slugs |
| **5** | **Greenhouse** | Major tech leaders (Stripe, Airbnb, Databricks, GitLab, Pinterest, Canonical, Elastic, Dropbox...) | **Remote, Hybrid & On-site** | Official Public Board API (`boards-api.greenhouse.io/v1/boards/{company}/jobs`) + Dynamic Dream Company Slugs |
| **6** | **Lever** | Top enterprise innovators (Spotify, Netflix, Eventbrite, Atlassian, Shopify, Carta...) | **Remote, Hybrid & On-site** | Official Postings API (`api.lever.co/v0/postings/{company}`) + Dynamic Dream Company Slugs |
| **7** | **SmartRecruiters** | Global institutions & enterprises (CERN, Informa, Colt Technology, Blizzard, Siemens...) | **Remote, Hybrid & On-site** | Official Public API (`api.smartrecruiters.com/v1/companies/{company}/postings`) + Dynamic Dream Company Slugs |
| **8** | **JobSpy** | Open-source multi-board scraper library | **Indeed, ZipRecruiter, Google Jobs** | Python library (`python-jobspy`) executing direct scraping without rate limits |
| **9** | **Apify** | Cloud Web Actor platform | **LinkedIn & Multi-Board Cloud Datasets** | Native `apify-client` integration configured via sidebar API token |
| **10** | **LinkedIn Jobs** | Global professional network across all industries | **Remote, Hybrid & On-site Worldwide** | Public guest search query endpoint with keyword, location, and `f_WT` filters |
| **11** | **Arbeitnow** | European & global business roles (Tech, Marketing, Finance, HR, Sales) | **On-site, Hybrid & Remote in EU & Global** | REST API (`/api/job-board-api`) |
| **12** | **Jobicy** | Remote jobs across diverse business sectors | **Remote** (Global & Regional) | REST API v2 (`/api/v2/remote-jobs`) |
| **13** | **RemoteOK** | Remote tech and digital roles with posted salaries | **Remote** (Worldwide) | Direct feed API (`/api`) with structured compensation data |
| **14** | **Remotive** | Curated remote engineering, product, and business positions | **Remote** (Global & Regional) | REST API (`/api/remote-jobs`) |

### How Semantic Fit Scoring & Pre-Filtering Works
Each scraped posting is evaluated by the **Semantic Matcher**:
1. **Negative Keyword Rejection (v2 New)**: Before scoring, any opportunity containing any of your specified negative keywords in its title, company, or description is automatically excluded.
2. **Title & Seniority Alignment (0–45 pts)**: Matches target role keywords, seniority tokens (*Senior, Staff, Principal, Lead, Director*), and career trajectory.
3. **Core Competency Overlap (0–35 pts)**: Compares required technologies and competencies against your verified CV skills.
4. **Location & Work-Mode Fit (0–20 pts)**: Validates remote eligibility or matches on-site/hybrid positions against your target country/city.
5. **Dream Company Priority Boost (v2 New)**: Positions from your target dream employers receive an automatic +6 fit score boost and special justification tags.
- **Fit Badges**:
  - 🟢 **90% - 100%**: Exceptional Match
  - 🔵 **82% - 89%**: High Match
  - 🟡 **72% - 81%**: Moderate Match

---

## 📊 Screen 4: Job Dashboard & Opportunity Evaluation

Screen 4 displays your ranked opportunities with filtering tools and application utilities:

### 1. Executive Metric KPIs
- **Total Openings Scraped**: Live count of positions crawled across all 14 sources concurrently (typically 350+).
- **High-Fit Matches**: Number of roles meeting an 80%+ threshold.
- **Top Match Score**: Highest calibrated fit score.

### 2. Search & Filter Bar
- **Keyword Search**: Filter dynamically across job titles, company names, or required skills.
- **Minimum Fit Score Slider**: Adjust threshold (e.g., 75% to 95%).
- **Work Mode Filter**: Toggle between *All*, *Remote Only*, *Hybrid*, or *On-site*.

### 3. Job Badges & Freshness Indicators
- **⭐ Target Dream Company**: Highlighted green badge identifying positions from companies specified in your custom target employer list.
- **Network Source Badge**: Visual badge distinguishing source origins (LinkedIn, Ashby, Greenhouse, Lever, SmartRecruiters, JobSpy, etc.).
- **📅 Days Since Posted Indicator**: Positioned directly below `📍 Location:`, displaying the numeric elapsed days since the position was posted, accompanied by color-coded freshness badges:
  - `🔥 New (<= 3 days)`: Just published opportunities.
  - `⏱️ Recent (4–14 days)`: Actively recruiting roles within the standard hiring window.
  - `📅 Active (> 14 days)`: Standing opportunities or extended requisition searches.
  - Normalizes heterogeneous source formats including ISO timestamps (`2026-10-02`), relative durations (*3 days ago, 2 weeks ago, 1 month ago*), and ATS active feeds (*Active on ZipRecruiter, Active on Ashby*).

### 4. Geographic Salary Evaluator & Market Benchmarking
Every job card features an automated salary assessment calibrated to the candidate's **Target Location & Countries** defined in Screen 1:
- **Numerical Salary Score (0–100)**: Evaluates proposed compensation against candidate seniority and regional purchasing power standards (US, UK/Europe, Canada, Worldwide Remote, APAC, LATAM, etc.).
- **Market Benchmark Rank**:
  - `🟢 Above Market`: Exceeds prevailing geographic industry baselines.
  - `🔵 Within Market Standard`: Aligns with standard compensation bands for the region.
  - `🟡 Below Market`: Below typical market benchmarks.
- **Regional Location Badge**: Explicit badge displaying which market benchmark was applied (e.g. `📍 London / UK Benchmark`, `📍 San Francisco Benchmark`, `📍 Remote Benchmark`).

### 4. The 4 Agentic Power Tools on Every Job Card
Each job card provides a 2x2 action button grid:

```
┌───────────────────────────────┬───────────────────────────────┐
│     📄 Tailored CV            │     ✉️ Cover Letter           │
├───────────────────────────────┼───────────────────────────────┤
│     🎤 Prep Pack              │     📬 Outreach Drafter       │
└───────────────────────────────┴───────────────────────────────┘
```

#### Tool 1: 📄 ATS-Optimized Tailored CV Generator & Screening Audit
- Click to open the **ATS-Optimized Tailored CV Dialog**.
- The Application Agent dynamically tailors your CV to pass automated Applicant Tracking Systems (ATS) including **Greenhouse, Ashby, Lever, Workday, SmartRecruiters, and Taleo**.
- **The 3 Inspection & Optimization Tabs**:
  1. `👁️ Formatted Preview`: Rendered view of your tailored CV.
  2. `🎯 ATS Screening Audit ({score}%)`:
     - **ATS Match Score (0–100%)**: Composite parseability and keyword alignment rating.
     - **Letter Grade**: e.g., `A+ (Guaranteed ATS Pass)`.
     - **5-Point ATS Parser Compliance Checklist**:
       - ✅ *Single-Column Parser-Safe Layout*: Guarantees 100% linear text flow without tables, floating columns, or multi-grid boxes that crash ATS text extraction engines.
       - ✅ *Standard ATS Section Headings*: Uses standard uppercase headers (`PROFESSIONAL SUMMARY`, `CORE COMPETENCIES & TECHNICAL SKILLS`, `PROFESSIONAL EXPERIENCE`, `EDUCATION & CREDENTIALS`).
       - ✅ *Contact Data Parser Integrity*: Standard un-nested contact line (`Location • Phone • Email • LinkedIn • GitHub`).
       - ✅ *High-Density Keyword Alignment*: Compares job description competencies against your CV with density percentage and matched badges.
       - ✅ *Action Verbs & Quantified Metrics (XYZ Formula)*: Ensures bullet points follow the Google formula (`Accomplished [X] as measured by [Y] by doing [Z]`).
     - **Keyword Pills**: Displays green matched keyword pills (`✓ Python`, `✓ Docker`) and suggested bonus keywords (`+ Kubernetes`) to boost search ranking.
  3. `✏️ Edit & Customize`: Live text editor. When you modify and save bullet points, the ATS Screening Audit instantly recalculates your score and checklist.
- **ATS Export Compliance**:
  - 📥 **Download ATS-Certified CV (`.docx`)**: Exports in clean single-column format using standard **Calibri 11pt typography, 0.75-inch margins, and standard paragraph styles** to prevent OCR or text extraction errors.
  - 🔄 Re-run Agent to regenerate fresh variations.

#### Tool 2: ✉️ ATS-Aligned Cover Letter Generator
- Generates a targeted, 3-to-4 paragraph cover letter addressing the hiring team directly.
- **ATS Requisition Match**: Includes a prominent subject line formatted for ATS keyword scrapers and recruiter inbox search:
  `RE: Application for [Job Title] (Requisition Match) — [Target Company]`
- **Features**:
  - Markdown preview and live editor.
  - Mirrored hard and functional skills matching job requirements.
  - 📥 **Download Cover Letter (`.txt`)**: Clean ASCII text format for seamless copy-pasting into ATS text fields.

#### Tool 3: 🎤 AI Interview Preparation Pack
- Launches the **AI Interview Preparation Pack Dialog** with 7 structured tabs:
  1. `📑 Briefing`: Target company mission, market positioning, and hiring team expectations.
  2. `💻 Technical (5)`: 5 deep-dive technical questions tailored to the position with benchmark model answers.
  3. `🌟 STAR Scenarios (4)`: 4 behavioral scenarios mapped directly to your CV (*Situation, Task, Action, Result*).
  4. `🛡️ Skill Gaps`: Objection handling strategies to turn missing niche tools into learning strengths.
  5. `❓ Reverse Questions`: High-impact questions categorized by interviewer role (*Hiring Manager, Peer Team, Executive*).
  6. `⚡ 15-Min Cheat Sheet`: Rapid pre-call review with elevator pitch, 3 signature metrics, and 5 keywords.
  7. `✏️ Full Pack & Edit`: Full markdown editor.
- **Downloads**:
  - 📥 **Download Prep Guide (`.docx`)**: Complete Word document.
  - 📥 **Download Cheat Sheet (`.txt`)**: Quick text file for reference during calls.

#### Tool 4: 📬 Recruiter Cold Outreach & Talent Search Drafter
- Formulated with target job title tokens, exact requisition keywords, and Boolean search terms used by recruiters on LinkedIn Recruiter and ATS Talent CRMs.
- Opens the **Recruiter Outreach Dialog** with 5 multi-channel messages:
  1. `🔗 LinkedIn Note (<300 char)`: Strict $\le 300$-character connection note with a real-time character budget counter.
  2. `👔 Hiring Manager Email`: Concise 100–140 word cold email focused on problem solving and proposing a 10-minute discovery chat.
  3. `🎯 Recruiter InMail`: Direct requisition alignment, key skills, and timeline inquiry.
  4. `🤝 Referral / Insider Chat`: Low-pressure message to team members or alumni asking for culture advice.
  5. `🙏 Post-Interview Thank You`: Follow-up note sent within 24 hours of an interview.
- **Customization Options**:
  - Set Recruiter Name, Title, Custom Personal Hook, and Tone (*Direct & Value-Focused*, *Professional & Authoritative*, *Warm & Conversational*).
- **Downloads**:
  - 📥 **Download Campaign (`.docx`)** & 📥 **Download Text Pack (`.txt`)**.

---

## 📋 Screen 5: Application Pipeline & Kanban Tracker

Screen 5 is a visual application management board for tracking jobs across their entire lifecycle:

### 1. The 5 Pipeline Stages
- **📌 Saved**: Bookmarked roles undergoing research or outreach drafting.
- **📤 Applied**: Positions where your tailored CV and cover letter have been submitted.
- **🎤 Interviewing**: Active interview cycles (screening, technical rounds, executive panel).
- **🎉 Offer Received**: Positions where you have received a formal compensation offer.
- **📁 Archived & Inactive**: Closed, rejected, or paused applications (stored in a collapsible tray).

### 2. Kanban Board Actions
- **Stage Mover**: Quick dropdown on every card to advance a role from stage to stage (e.g., *Saved ➔ Applied ➔ Interviewing*).
- **Direct Asset Access**: Every card includes direct buttons for **📄 Tailored CV**, **✉️ Cover Letter**, **🎤 Prep Pack**, and **📬 Outreach**.
- **📝 Notes & Details Dialog**: Log recruiter names, interview dates, submission links, and custom notes.
- **➕ Add Custom Application**: Log jobs found outside the app (e.g. from direct referrals, executive search, or company career portals).
- **📥 Export Pipeline (JSON)**: Download your entire pipeline, stage history, and notes as a portable JSON file.

---

## 💾 Exporting Documents & Application Artifacts

All generated materials are available for export in standard desktop formats:

| Document | Format | Generated By | Features & ATS Compliance |
|---|---|---|---|
| **ATS Tailored CV** | `.docx` | Application Agent | 100% ATS-certified (single-column, Calibri 11pt, 0.75" margins, standard headers, no tables) |
| **Cover Letter** | `.txt` | Application Agent | Requisition-matched (`RE: Application for [Role] (Req Match)`), mirrored keywords, plain ASCII |
| **Interview Prep Guide** | `.docx` | Interview Prep Agent | Full 6-section guide with callouts and styled tables |
| **15-Min Cheat Sheet** | `.txt` | Interview Prep Agent | Compact text summary for pre-call review |
| **Outreach Campaign** | `.docx` | Outreach Agent | Formatted Word pack containing all 5 outreach messages |
| **Outreach Messages** | `.txt` | Outreach Agent | Ready-to-copy plain text formatted for LinkedIn & email |
| **Pipeline State** | `.json` | Pipeline Manager | Complete application pipeline data export |

---

## ❓ Troubleshooting & Frequently Asked Questions

### 1. Why are some jobs showing "Market Benchmark" for salary?
Some job postings (especially outside the US) do not publish explicit salary ranges. In those instances, our **Salary Evaluator** analyzes the title, seniority, and location to estimate a realistic market benchmark band.

### 2. Can I use the app without a Google Gemini API key?
**Yes.** The platform includes deterministic fallback engines for resume parsing, semantic scoring, tailored CV generation, interview prep, and outreach drafting. Adding a Gemini key enables dynamic AI reasoning.

### 3. How does the app prevent rate limiting on job scrapers?
The crawler uses a multi-tier approach:
- Direct public JSON/REST endpoints (Arbeitnow, Jobicy, RemoteOK, Remotive, Ashby, Greenhouse, Lever, SmartRecruiters).
- Official RSS XML feeds (We Work Remotely).
- `python-jobspy` for direct scraping without API keys.
- Automatic exception handling ensures that if any single source experiences network latency, the remaining 13 sources continue unaffected.

### 4. What is the Apify integration used for?
Apify allows you to run cloud-hosted web actors (e.g., specialized LinkedIn or Indeed crawlers). If you do not have an Apify token, leave the field blank; the app will use its built-in direct scrapers.

### 5. Where is my application data stored?
All session data, saved jobs, pipeline stages, custom notes, and generated documents are stored locally in your browser's session state (`st.session_state`). You can export your data at any time via the **📥 Export Pipeline (JSON)** button on Screen 5.

---

*Hyrd — Don't just search. Get Hyrd!*
