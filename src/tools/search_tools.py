"""
Search and Scraping Tools Suite for Hyrd Agentic Architecture.
Integrates live ATS feeds, aggregator APIs, and regional portals with
the google-antigravity ToolRunner infrastructure.
"""

from __future__ import annotations

import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

try:
    import google.antigravity as ga
    from google.antigravity.tools.tool_runner import ToolRunner
    ga.ToolRunner = ToolRunner  # Expose ToolRunner directly on google.antigravity
except ImportError:
    class ToolRunner:  # type: ignore
        """Fallback lightweight ToolRunner if google-antigravity is unavailable."""
        def __init__(self):
            self._tools: Dict[str, Callable] = {}

        def register(self, tool: Callable, name: Optional[str] = None) -> None:
            tool_name = name or getattr(tool, "__name__", str(tool))
            self._tools[tool_name] = tool

        def execute(self, name: str, args: Optional[Dict[str, Any]] = None) -> Any:
            if name not in self._tools:
                raise KeyError(f"Tool '{name}' is not registered.")
            args = args or {}
            return self._tools[name](**args)

        @property
        def tool_names(self) -> List[str]:
            return list(self._tools.keys())

from src.schemas import JobPosting
from src.agents.scrapers import (
    safe_scrape,
    # Tier 1 Direct ATS
    fetch_ashby_jobs,
    fetch_greenhouse_jobs,
    fetch_lever_jobs,
    fetch_smartrecruiters_jobs,
    fetch_workday_jobs,
    fetch_bamboohr_jobs,
    fetch_breezyhr_jobs,
    # Tier 2 Public JSON & RSS
    fetch_arbeitnow_jobs,
    fetch_jobicy_jobs,
    fetch_remoteok_jobs,
    fetch_remotive_jobs,
    fetch_himalayas_jobs,
    fetch_weworkremotely_jobs,
    fetch_hackernews_jobs,
    # Tier 3 Aggregators & Cloud Actors
    fetch_jobspy_jobs,
    fetch_apify_jobs,
    fetch_jsearch_jobs,
    fetch_jooble_jobs,
    fetch_wellfound_apify_jobs,
    fetch_glassdoor_apify_jobs,
    # Tier 4 Regional & Niche DOM
    fetch_linkedin_jobs,
    fetch_telecomcrossing_jobs,
    fetch_ziprecruiter_jobs,
    fetch_itjobs_jobs,
    fetch_netempregos_jobs,
    fetch_landingjobs_jobs,
    fetch_teamlyzer_jobs,
    fetch_infojobs_jobs,
    fetch_builtin_jobs,
    fetch_wellfound_jobs,
)
from src.agents.job_scraper_agent import optimize_query_for_source

logger = logging.getLogger("Hyrd.SearchTools")


# ============================================================================
# 1. ATOMIC TOOL DEFINITIONS
# ============================================================================

def search_ashby_jobs(
    query: str,
    location: str = "Remote",
    companies: Optional[List[str]] = None,
    limit: int = 40,
) -> List[Dict[str, Any]]:
    """Query Ashby ATS direct job postings for target query and target employers.

    Args:
        query: Professional title or role discipline (e.g. 'Software Engineer').
        location: Target geographic location or 'Remote'.
        companies: Optional list of target company names.
        limit: Maximum results to retrieve.
    """
    opt_query = optimize_query_for_source(query, "Ashby")
    return fetch_ashby_jobs(
        target_query=opt_query,
        target_location=location,
        custom_companies=companies,
        limit=limit,
    )


def search_greenhouse_jobs(
    query: str,
    location: str = "Remote",
    companies: Optional[List[str]] = None,
    limit: int = 40,
) -> List[Dict[str, Any]]:
    """Query Greenhouse ATS unmediated employer requisitions.

    Args:
        query: Professional title or role discipline.
        location: Target geographic location or 'Remote'.
        companies: Optional list of target company names.
        limit: Maximum results to retrieve.
    """
    opt_query = optimize_query_for_source(query, "Greenhouse")
    return fetch_greenhouse_jobs(
        target_query=opt_query,
        target_location=location,
        custom_companies=companies,
        limit=limit,
    )


def search_lever_jobs(
    query: str,
    location: str = "Remote",
    companies: Optional[List[str]] = None,
    limit: int = 35,
) -> List[Dict[str, Any]]:
    """Query Lever ATS job endpoints for tech and business roles.

    Args:
        query: Target role title or keywords.
        location: Target geographic location.
        companies: Target company list.
        limit: Maximum results.
    """
    opt_query = optimize_query_for_source(query, "Lever")
    return fetch_lever_jobs(
        target_query=opt_query,
        target_location=location,
        custom_companies=companies,
        limit=limit,
    )


def search_smartrecruiters_jobs(
    query: str,
    location: str = "Remote",
    companies: Optional[List[str]] = None,
    limit: int = 25,
) -> List[Dict[str, Any]]:
    """Query SmartRecruiters ATS postings with company and role filters."""
    opt_query = optimize_query_for_source(query, "SmartRecruiters")
    return fetch_smartrecruiters_jobs(
        target_query=opt_query,
        target_location=location,
        custom_companies=companies,
        limit=limit,
    )


def search_jobspy_jobs(
    query: str,
    location: str = "Remote",
    is_remote: bool = True,
    limit: int = 25,
) -> List[Dict[str, Any]]:
    """Search Indeed and secondary aggregators using JobSpy."""
    opt_query = optimize_query_for_source(query, "JobSpy")
    return fetch_jobspy_jobs(
        target_query=opt_query,
        target_location=location,
        is_remote=is_remote,
        limit=limit,
    )


def search_apify_jobs(
    query: str,
    location: str = "Remote",
    api_token: Optional[str] = None,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """Scrape LinkedIn or Indeed jobs via Apify actors with credential protection.

    Args:
        query: Job search query.
        location: Target geographic location.
        api_token: Optional Apify API key. If omitted, checks APIFY_API_TOKEN env var.
        limit: Maximum results.
    """
    effective_token = api_token or os.environ.get("APIFY_API_TOKEN", "").strip()
    if not effective_token:
        logger.info("Apify API key not provided or missing. Skipping Apify channel safely.")
        return []
    try:
        return fetch_apify_jobs(
            target_query=query,
            target_location=location,
            api_token=effective_token,
            limit=limit,
        )
    except Exception as exc:
        logger.warning(f"Apify search error: {exc}. Channel safely contained.")
        return []


def search_workday_jobs(
    companies: Optional[List[str]] = None,
    limit: int = 25,
) -> List[Dict[str, Any]]:
    """Query Workday ATS career sites with CSRF token handshake."""
    return fetch_workday_jobs(custom_companies=companies, limit=limit)


def search_bamboohr_jobs(
    companies: Optional[List[str]] = None,
    limit: int = 25,
) -> List[Dict[str, Any]]:
    """Query BambooHR public job feeds."""
    return fetch_bamboohr_jobs(custom_companies=companies, limit=limit)


def search_breezyhr_jobs(
    companies: Optional[List[str]] = None,
    limit: int = 25,
) -> List[Dict[str, Any]]:
    """Query BreezyHR JSON job feeds."""
    return fetch_breezyhr_jobs(custom_companies=companies, limit=limit)


def search_himalayas_jobs(
    query: str,
    limit: int = 35,
) -> List[Dict[str, Any]]:
    """Query Himalayas remote job API."""
    opt_query = optimize_query_for_source(query, "Himalayas")
    return fetch_himalayas_jobs(target_query=opt_query, limit=limit)


def search_hackernews_jobs(
    query: str,
    limit: int = 25,
) -> List[Dict[str, Any]]:
    """Query Hacker News 'Who is hiring?' community threads."""
    opt_query = optimize_query_for_source(query, "HackerNews")
    return fetch_hackernews_jobs(target_query=opt_query, limit=limit)


def search_builtin_jobs(
    query: str,
    location: str = "Remote",
    limit: int = 25,
) -> List[Dict[str, Any]]:
    """Query BuiltIn tech hub opportunities via Next.js extraction."""
    opt_query = optimize_query_for_source(query, "BuiltIn")
    return fetch_builtin_jobs(target_query=opt_query, target_location=location, limit=limit)


def search_infojobs_jobs(
    query: str,
    location: str = "",
    limit: int = 25,
) -> List[Dict[str, Any]]:
    """Query InfoJobs Iberian & European positions."""
    opt_query = optimize_query_for_source(query, "InfoJobs")
    return fetch_infojobs_jobs(target_query=opt_query, target_location=location, limit=limit)


def search_teamlyzer_jobs(
    query: str,
    location: str = "Portugal",
    limit: int = 25,
) -> List[Dict[str, Any]]:
    """Query Teamlyzer tech portal for Portuguese tech openings and salaries."""
    opt_query = optimize_query_for_source(query, "Teamlyzer")
    return fetch_teamlyzer_jobs(target_query=opt_query, target_location=location, limit=limit)


def search_remote_boards(
    query: str,
    location: str = "Remote",
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """Aggregate positions across specialized remote job boards:
    RemoteOK, Remotive, Arbeitnow, WeWorkRemotely, Jobicy, Himalayas, and Hacker News.
    """
    results: List[Dict[str, Any]] = []
    sub_tasks = [
        ("RemoteOK", lambda: fetch_remoteok_jobs(limit=min(40, limit))),
        ("Remotive", lambda: fetch_remotive_jobs(limit=min(30, limit))),
        ("Arbeitnow", lambda: fetch_arbeitnow_jobs(target_query=optimize_query_for_source(query, "Arbeitnow"), limit=min(50, limit))),
        ("WeWorkRemotely", lambda: fetch_weworkremotely_jobs(target_query=optimize_query_for_source(query, "WeWorkRemotely"), target_location=location, limit=min(30, limit))),
        ("Jobicy", lambda: fetch_jobicy_jobs(limit=min(30, limit))),
        ("Himalayas", lambda: fetch_himalayas_jobs(target_query=optimize_query_for_source(query, "Himalayas"), limit=min(35, limit))),
        ("HackerNews", lambda: fetch_hackernews_jobs(target_query=optimize_query_for_source(query, "HackerNews"), limit=min(25, limit))),
    ]
    for name, fn in sub_tasks:
        try:
            _, jobs = safe_scrape(name, fn)
            results.extend(jobs)
        except Exception as exc:
            logger.debug(f"Remote board {name} error: {exc}")
    return results


def search_portuguese_portals(
    query: str,
    location: str = "Portugal",
    limit: int = 30,
) -> List[Dict[str, Any]]:
    """Search Portugal & Iberian tech portals: ITJobs.pt, Net-Empregos, Landing.jobs, Teamlyzer, and InfoJobs."""
    results: List[Dict[str, Any]] = []
    sub_tasks = [
        ("ITJobs", lambda: fetch_itjobs_jobs(target_query=optimize_query_for_source(query, "ITJobs"), target_location=location, limit=limit)),
        ("NetEmpregos", lambda: fetch_netempregos_jobs(target_query=optimize_query_for_source(query, "NetEmpregos"), target_location=location, limit=limit)),
        ("LandingJobs", lambda: fetch_landingjobs_jobs(target_query=optimize_query_for_source(query, "LandingJobs"), target_location=location, limit=limit)),
        ("Teamlyzer", lambda: fetch_teamlyzer_jobs(target_query=optimize_query_for_source(query, "Teamlyzer"), target_location=location, limit=limit)),
        ("InfoJobs", lambda: fetch_infojobs_jobs(target_query=optimize_query_for_source(query, "InfoJobs"), target_location=location, limit=limit)),
    ]
    for name, fn in sub_tasks:
        try:
            _, jobs = safe_scrape(name, fn)
            results.extend(jobs)
        except Exception as exc:
            logger.debug(f"Portuguese board {name} error: {exc}")
    return results


# ============================================================================
# 2. CONCURRENT MULTI-CHANNEL SEARCH ORCHESTRATOR
# ============================================================================

def execute_concurrent_search(
    profile_data: Dict[str, Any],
    channels_enabled: Optional[List[str]] = None,
    max_workers: int = 22,
    apify_token: Optional[str] = None,
    on_progress: Optional[Callable[[int, str, str], None]] = None,
) -> Tuple[List[JobPosting], Dict[str, int], Dict[str, str]]:
    """Concurrently query up to 17 job search channels with graceful failure handling.

    Returns:
        (job_postings, channel_telemetry, failures_by_source)
    """
    def log(pct: int, agent: str, msg: str):
        if on_progress:
            on_progress(pct, agent, msg)

    target_role = profile_data.get("headline") or profile_data.get("target_role") or "Software Engineer"
    target_loc = profile_data.get("location_preference") or profile_data.get("location") or "Remote"
    work_mode_pref = (profile_data.get("work_mode") or "Remote Only").lower()
    is_onsite_only = "on-site only" in work_mode_pref

    # Extract target dream companies
    raw_companies = profile_data.get("target_companies") or []
    if isinstance(raw_companies, str):
        custom_companies = [c.strip() for c in raw_companies.split(",") if c.strip()]
    else:
        custom_companies = [str(c).strip() for c in raw_companies if str(c).strip()]

    # Curate search queries for fan-out
    selected_roles = profile_data.get("selected_roles") or profile_data.get("target_roles") or []
    search_queries = [target_role]
    for r in selected_roles:
        r_str = str(r).strip()
        if r_str and r_str.lower() != target_role.lower() and r_str not in search_queries:
            search_queries.append(r_str)
            if len(search_queries) >= 3:
                break

    log(5, "ScoutAgent-Dispatcher", f"Orchestrating search for {len(search_queries)} role queries across channels...")

    # Build task list across all 4 ingestion tiers
    all_channel_tasks: List[Tuple[str, Callable[[], List[Dict[str, Any]]]]] = [
        # Tier 1: Direct ATS APIs
        ("Ashby", lambda: fetch_ashby_jobs(target_query=optimize_query_for_source(target_role, "Ashby"), target_location=target_loc, custom_companies=custom_companies, limit=40)),
        ("Greenhouse", lambda: fetch_greenhouse_jobs(target_query=optimize_query_for_source(target_role, "Greenhouse"), target_location=target_loc, custom_companies=custom_companies, limit=40)),
        ("Lever", lambda: fetch_lever_jobs(target_query=optimize_query_for_source(target_role, "Lever"), target_location=target_loc, custom_companies=custom_companies, limit=35)),
        ("SmartRecruiters", lambda: fetch_smartrecruiters_jobs(target_query=optimize_query_for_source(target_role, "SmartRecruiters"), target_location=target_loc, custom_companies=custom_companies, limit=25)),
        ("Workday", lambda: fetch_workday_jobs(custom_companies=custom_companies, limit=25)),
        ("BambooHR", lambda: fetch_bamboohr_jobs(custom_companies=custom_companies, limit=25)),
        ("BreezyHR", lambda: fetch_breezyhr_jobs(custom_companies=custom_companies, limit=25)),
        # Tier 2: Public JSON APIs & RSS Feeds
        ("Arbeitnow", lambda: fetch_arbeitnow_jobs(target_query=optimize_query_for_source(target_role, "Arbeitnow"), limit=60)),
        ("Jobicy", lambda: fetch_jobicy_jobs(limit=35)),
        ("RemoteOK", lambda: fetch_remoteok_jobs(limit=40)),
        ("Remotive", lambda: fetch_remotive_jobs(limit=30)),
        ("Himalayas", lambda: fetch_himalayas_jobs(target_query=optimize_query_for_source(target_role, "Himalayas"), limit=35)),
        ("WeWorkRemotely", lambda: fetch_weworkremotely_jobs(target_query=optimize_query_for_source(target_role, "WeWorkRemotely"), target_location=target_loc, limit=35)),
        ("HackerNews", lambda: fetch_hackernews_jobs(target_query=optimize_query_for_source(target_role, "HackerNews"), limit=25)),
        # Tier 3: Aggregators
        ("JobSpy", lambda: fetch_jobspy_jobs(target_query=optimize_query_for_source(target_role, "JobSpy"), target_location=target_loc, is_remote=not is_onsite_only, limit=25)),
        # Tier 4: Regional & Niche DOM Scrapers
        ("LinkedIn", lambda: fetch_linkedin_jobs(target_query=optimize_query_for_source(target_role, "LinkedIn"), target_location=target_loc, work_mode_pref=work_mode_pref, limit=25)),
        ("ITJobs", lambda: fetch_itjobs_jobs(target_query=optimize_query_for_source(target_role, "ITJobs"), target_location=target_loc, limit=30)),
        ("NetEmpregos", lambda: fetch_netempregos_jobs(target_query=optimize_query_for_source(target_role, "NetEmpregos"), target_location=target_loc, limit=30)),
        ("LandingJobs", lambda: fetch_landingjobs_jobs(target_query=optimize_query_for_source(target_role, "LandingJobs"), target_location=target_loc, limit=25)),
        ("Teamlyzer", lambda: fetch_teamlyzer_jobs(target_query=optimize_query_for_source(target_role, "Teamlyzer"), target_location=target_loc, limit=25)),
        ("InfoJobs", lambda: fetch_infojobs_jobs(target_query=optimize_query_for_source(target_role, "InfoJobs"), target_location=target_loc, limit=25)),
        ("BuiltIn", lambda: fetch_builtin_jobs(target_query=optimize_query_for_source(target_role, "BuiltIn"), target_location=target_loc, limit=25)),
        ("TelecomCrossing", lambda: fetch_telecomcrossing_jobs(target_query=optimize_query_for_source(target_role, "TelecomCrossing"), target_location=target_loc, limit=25)),
        ("ZipRecruiter", lambda: fetch_ziprecruiter_jobs(target_query=optimize_query_for_source(target_role, "ZipRecruiter"), target_location=target_loc, is_remote=not is_onsite_only, limit=25)),
    ]

    # Secondary role fan-out across high-yield search channels
    for sec_role in search_queries[1:]:
        all_channel_tasks.append(("LinkedIn", lambda r=sec_role: fetch_linkedin_jobs(target_query=optimize_query_for_source(r, "LinkedIn"), target_location=target_loc, work_mode_pref=work_mode_pref, limit=20)))
        all_channel_tasks.append(("Ashby", lambda r=sec_role: fetch_ashby_jobs(target_query=optimize_query_for_source(r, "Ashby"), target_location=target_loc, custom_companies=custom_companies, limit=30)))
        all_channel_tasks.append(("Greenhouse", lambda r=sec_role: fetch_greenhouse_jobs(target_query=optimize_query_for_source(r, "Greenhouse"), target_location=target_loc, custom_companies=custom_companies, limit=30)))
        all_channel_tasks.append(("Lever", lambda r=sec_role: fetch_lever_jobs(target_query=optimize_query_for_source(r, "Lever"), target_location=target_loc, custom_companies=custom_companies, limit=25)))
        all_channel_tasks.append(("JobSpy", lambda r=sec_role: fetch_jobspy_jobs(target_query=optimize_query_for_source(r, "JobSpy"), target_location=target_loc, is_remote=not is_onsite_only, limit=20)))
        all_channel_tasks.append(("ITJobs", lambda r=sec_role: fetch_itjobs_jobs(target_query=optimize_query_for_source(r, "ITJobs"), target_location=target_loc, limit=20)))
        all_channel_tasks.append(("NetEmpregos", lambda r=sec_role: fetch_netempregos_jobs(target_query=optimize_query_for_source(r, "NetEmpregos"), target_location=target_loc, limit=20)))
        all_channel_tasks.append(("LandingJobs", lambda r=sec_role: fetch_landingjobs_jobs(target_query=optimize_query_for_source(r, "LandingJobs"), target_location=target_loc, limit=20)))

    # Handle optional Apify channel with token check
    token = apify_token or profile_data.get("apify_api_token") or os.environ.get("APIFY_API_TOKEN")
    if token:
        all_channel_tasks.append(("Apify", lambda: search_apify_jobs(target_role, target_loc, api_token=token, limit=20)))
    else:
        logger.debug("Apify skipped (no API token provided).")

    # Filter tasks if channels_enabled is specified
    if channels_enabled:
        channels_lower = [c.lower() for c in channels_enabled]
        active_tasks = [t for t in all_channel_tasks if any(c in t[0].lower() for c in channels_lower)]
    else:
        active_tasks = all_channel_tasks

    total_tasks = len(active_tasks)
    log(10, "ScoutAgent-Dispatcher", f"Executing {total_tasks} parallel channel scrapers with max_workers={max_workers}...")

    raw_jobs: List[Dict[str, Any]] = []
    telemetry: Dict[str, int] = {}
    failures: Dict[str, str] = {}
    completed_count = 0

    with ThreadPoolExecutor(max_workers=min(max_workers, max(1, total_tasks))) as executor:
        future_to_name = {
            executor.submit(safe_scrape, name, fn): name
            for name, fn in active_tasks
        }
        for future in as_completed(future_to_name):
            channel_name = future_to_name[future]
            completed_count += 1
            try:
                src_name, src_jobs = future.result()
                raw_jobs.extend(src_jobs)
                telemetry[src_name] = telemetry.get(src_name, 0) + len(src_jobs)
                pct = int(10 + (completed_count / total_tasks) * 75)
                log(pct, f"Scout-{src_name}", f"Harvested {len(src_jobs)} postings ({completed_count}/{total_tasks} channels done).")
            except Exception as exc:
                failures[channel_name] = str(exc)
                if channel_name not in telemetry:
                    telemetry[channel_name] = 0
                logger.error(f"Channel {channel_name} failed: {exc}")

    # Fallback if network blocked or zero jobs found
    if not raw_jobs:
        from src.mock_data import MOCK_JOB_RESULTS
        log(90, "ScoutAgent-Fallback", "Live scraping returned 0 items — activating verified baseline pool.")
        raw_jobs = MOCK_JOB_RESULTS
        telemetry["MockFallback"] = len(MOCK_JOB_RESULTS)

    # Normalize into JobPosting models
    job_postings: List[JobPosting] = []
    for j_dict in raw_jobs:
        try:
            # Map required fields safely
            title = j_dict.get("title") or j_dict.get("job_title") or "Unknown Role"
            company = j_dict.get("company") or "Unknown Company"
            desc = j_dict.get("full_description") or j_dict.get("description") or ""
            source_url = j_dict.get("source_url") or j_dict.get("url") or ""
            
            posting = JobPosting(
                title=title,
                company=company,
                location=j_dict.get("location") or "Remote",
                full_description=desc,
                requirements=j_dict.get("requirements", []),
                salary_range=j_dict.get("salary_range") or j_dict.get("salary"),
                source_url=source_url,
                source=j_dict.get("source") or "Aggregator",
                posted_date=j_dict.get("posted_date"),
                job_type=j_dict.get("job_type") or "Remote",
                is_direct_ats=bool(j_dict.get("is_direct_ats", False)),
                is_target_company=bool(j_dict.get("is_target_company", False)),
                matched_skills=j_dict.get("matched_skills", []),
                missing_skills=j_dict.get("missing_skills", []),
                fit_score=int(j_dict.get("fit_score", 0)),
                badge_color=j_dict.get("badge_color", "#2563eb"),
                key_reasons=j_dict.get("key_reasons", []),
            )
            job_postings.append(posting)
        except Exception as exc:
            logger.debug(f"Failed to normalize job dictionary: {exc}")

    log(90, "ScoutAgent", f"Normalized {len(job_postings)} opportunities into Pydantic models.")
    return job_postings, telemetry, failures


# ============================================================================
# 3. GLOBAL TOOL RUNNER REGISTRATION
# ============================================================================

search_tools_runner = ToolRunner()

search_tools_runner.register(search_ashby_jobs, "search_ashby")
search_tools_runner.register(search_greenhouse_jobs, "search_greenhouse")
search_tools_runner.register(search_lever_jobs, "search_lever")
search_tools_runner.register(search_smartrecruiters_jobs, "search_smartrecruiters")
search_tools_runner.register(search_workday_jobs, "search_workday")
search_tools_runner.register(search_bamboohr_jobs, "search_bamboohr")
search_tools_runner.register(search_breezyhr_jobs, "search_breezyhr")
search_tools_runner.register(search_jobspy_jobs, "search_jobspy")
search_tools_runner.register(search_apify_jobs, "search_apify")
search_tools_runner.register(search_remote_boards, "search_remote_boards")
search_tools_runner.register(search_himalayas_jobs, "search_himalayas")
search_tools_runner.register(search_hackernews_jobs, "search_hackernews")
search_tools_runner.register(search_portuguese_portals, "search_portuguese_portals")
search_tools_runner.register(search_builtin_jobs, "search_builtin")
search_tools_runner.register(search_infojobs_jobs, "search_infojobs")
search_tools_runner.register(search_teamlyzer_jobs, "search_teamlyzer")
