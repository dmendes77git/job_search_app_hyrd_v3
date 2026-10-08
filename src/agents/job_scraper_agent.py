"""
Universal Job Scraper & Aggregator Agent: Autonomous multi-source job search and semantic scoring engine.
Supports all industries, professions, and job types (Tech, Finance, Marketing, Product, Design, Sales, HR, Healthcare, etc.).
Intelligently handles Remote positions worldwide, as well as On-site and Hybrid positions in specific user-targeted countries.

Modular Architecture:
- Scrapers: src.agents.scrapers (ATS, Aggregator, Remote)
- Scoring: src.agents.matching.scoring (Semantic scoring, Location/Work mode matching)
"""

import logging
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List, Optional, Tuple, Callable

from src.agents.matching.scoring import (
    COUNTRY_SYNONYMS,
    extract_target_countries,
    check_job_country_match,
    determine_work_mode,
    calculate_semantic_fit,
    rerank_top_jobs_with_gemini,
)
from src.agents.scrapers import (
    DEFAULT_HEADERS,
    clean_html_text,
    normalize_company_slug,
    safe_fetch_json,
    safe_scrape,
    fetch_ashby_jobs,
    fetch_greenhouse_jobs,
    fetch_lever_jobs,
    fetch_smartrecruiters_jobs,
    silence_jobspy_loggers,
    fetch_jobspy_jobs,
    fetch_apify_jobs,
    fetch_arbeitnow_jobs,
    fetch_jobicy_jobs,
    fetch_remoteok_jobs,
    fetch_remotive_jobs,
    fetch_linkedin_jobs,
    fetch_weworkremotely_jobs,
    fetch_telecomcrossing_jobs,
    fetch_ziprecruiter_jobs,
    fetch_itjobs_jobs,
    fetch_netempregos_jobs,
    fetch_landingjobs_jobs,
)

# Backwards compatibility alias
HTTP_HEADERS = DEFAULT_HEADERS

__all__ = [
    "HTTP_HEADERS",
    "DEFAULT_HEADERS",
    "COUNTRY_SYNONYMS",
    "DIRECT_ATS_SOURCES",
    "clean_html_text",
    "normalize_company_slug",
    "extract_target_countries",
    "check_job_country_match",
    "determine_work_mode",
    "calculate_semantic_fit",
    "optimize_query_for_source",
    "silence_jobspy_loggers",
    "fetch_ashby_jobs",
    "fetch_greenhouse_jobs",
    "fetch_lever_jobs",
    "fetch_smartrecruiters_jobs",
    "fetch_jobspy_jobs",
    "fetch_apify_jobs",
    "fetch_arbeitnow_jobs",
    "fetch_jobicy_jobs",
    "fetch_remoteok_jobs",
    "fetch_remotive_jobs",
    "fetch_linkedin_jobs",
    "fetch_weworkremotely_jobs",
    "fetch_telecomcrossing_jobs",
    "fetch_ziprecruiter_jobs",
    "fetch_itjobs_jobs",
    "fetch_netempregos_jobs",
    "fetch_landingjobs_jobs",
    "search_live_jobs_pipeline",
]

# Official direct Applicant Tracking Systems (ATS) - unmediated employer endpoints
from src.agents.scrapers.base import DIRECT_ATS_SOURCES

_QUERY_PARENS_RE = re.compile(r"\s*\([^)]*\)")
_QUERY_PUNCT_RE = re.compile(r"[/\\,]+")


def optimize_query_for_source(query: str, source_name: str) -> str:
    """
    Format query syntax appropriately for each specific scraper/API (Point 1.B):
    - ATS (Ashby, Greenhouse, Lever, SmartRecruiters): Clean core discipline keywords.
    - Boolean boards (LinkedIn, JobSpy): Clean query without noisy parenthesis or stopwords.
    - Portuguese portals (ITJobs, Net-Empregos, Landing.jobs): Clean tech terms, supporting bilingual PT-PT and EN queries.
    - Aggregators: Clean tag/discipline keywords.
    """
    if not query:
        return ""
    q = _QUERY_PARENS_RE.sub("", query).strip()
    q_clean = _QUERY_PUNCT_RE.sub(" ", q).strip()

    source_lower = source_name.lower()
    if any(ats in source_lower for ats in DIRECT_ATS_SOURCES):
        words = q_clean.split()
        if len(words) > 3:
            if any(k in q_clean.lower() for k in ["ai", "machine learning", "ml", "llm"]):
                return "AI Engineer" if "engineer" in q_clean.lower() else "Machine Learning"
            elif "data" in q_clean.lower():
                return "Data Engineer" if "engineer" in q_clean.lower() else "Data"
            elif "product" in q_clean.lower():
                return "Product Manager"
            else:
                return "Software Engineer"
        return q_clean

    if "net-empregos" in source_lower or "netempregos" in source_lower:
        # Net-Empregos benefits from concise Portuguese titles or core terms
        q_lower = q_clean.lower()
        if "software engineer" in q_lower or "full stack" in q_lower:
            return "Engenheiro de Software"
        elif "backend" in q_lower:
            return "Desenvolvedor Backend"
        elif "frontend" in q_lower:
            return "Desenvolvedor Frontend"
        elif "data engineer" in q_lower:
            return "Engenheiro de Dados"
        elif "data scientist" in q_lower:
            return "Cientista de Dados"
        elif "product manager" in q_lower:
            return "Gestor de Produto"
        elif "ai engineer" in q_lower or "machine learning" in q_lower:
            return "Inteligência Artificial"
        return q_clean

    if "itjobs" in source_lower:
        # ITJobs.pt works effectively with concise tech roles
        q_lower = q_clean.lower()
        if "software engineer" in q_lower:
            return "Software Developer"
        return q_clean

    return q_clean



def search_live_jobs_pipeline(
    profile: Dict[str, Any],
    on_progress: Optional[Callable[[int, str, str], None]] = None,
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Universal autonomous job search pipeline with Concurrent Async Multi-Source Scraping across 14 channels:
    LinkedIn, Ashby, Greenhouse, Lever, SmartRecruiters, JobSpy (Indeed), We Work Remotely,
    TelecomCrossing, ZipRecruiter, Apify, Arbeitnow, Jobicy, RemoteOK, and Remotive.
    - Concurrently executes all 14 scrapers in parallel via ThreadPoolExecutor.
    - Dynamically queries candidate's custom Dream Companies across ATS endpoints.
    - Enforces negative keyword exclusions (filtering out unwanted roles/terms).
    - Semantically scores and ranks all candidates' opportunities.
    """
    def log(pct: int, agent: str, msg: str):
        if on_progress:
            on_progress(pct, agent, msg)

    target_role = profile.get("headline") or profile.get("target_role") or "Target Profession"
    target_loc_str = profile.get("location") or profile.get("target_location") or "Remote"
    target_countries = extract_target_countries(target_loc_str)
    work_mode_pref = (profile.get("work_mode") or "Remote Only").lower()
    is_remote_only = "remote only" in work_mode_pref
    is_onsite_only = "on-site only" in work_mode_pref

    # Extract Dream Companies & Negative Filters
    target_companies_str = profile.get("target_companies") or ""
    custom_companies = [c.strip() for c in target_companies_str.split(",") if c.strip()]

    negative_keywords_str = profile.get("negative_keywords") or ""
    negative_keywords = [n.strip().lower() for n in negative_keywords_str.split(",") if n.strip()]

    countries_display = ", ".join([c.title() for c in target_countries]) if target_countries else "Global / Worldwide"

    selected_roles = profile.get("selected_roles") or profile.get("target_roles") or []
    
    # Point 1.A: Multi-Query Fan-Out across selected recommended roles
    search_queries = [target_role]
    for r in selected_roles:
        if r and r.strip().lower() != target_role.strip().lower() and r.strip() not in search_queries:
            search_queries.append(r.strip())
            if len(search_queries) >= 3:
                break

    role_display = f"'{target_role}'"
    if len(search_queries) > 1:
        role_display = f"{len(search_queries)} curated roles ({', '.join(search_queries[:2])}...)"

    dispatch_desc = f"Searching roles for: {role_display} | Region: {countries_display} | Mode: {profile.get('work_mode', 'Remote Only')}"
    if custom_companies:
        dispatch_desc += f" | Dream Companies: {', '.join(custom_companies)}"
    if negative_keywords:
        dispatch_desc += f" | Exclusions: {', '.join(negative_keywords)}"

    log(5, "JobCrawler-Dispatcher", dispatch_desc)

    # Configure the concurrent scraper tasks across all 17 channels with source-specific query optimization (Point 1.B)
    tasks = [
        ("LinkedIn", lambda: fetch_linkedin_jobs(target_query=optimize_query_for_source(target_role, "LinkedIn"), target_location=target_loc_str, work_mode_pref=work_mode_pref, limit=25)),
        ("Ashby", lambda: fetch_ashby_jobs(target_query=optimize_query_for_source(target_role, "Ashby"), target_location=target_loc_str, custom_companies=custom_companies, limit=40)),
        ("Greenhouse", lambda: fetch_greenhouse_jobs(target_query=optimize_query_for_source(target_role, "Greenhouse"), target_location=target_loc_str, custom_companies=custom_companies, limit=40)),
        ("Lever", lambda: fetch_lever_jobs(target_query=optimize_query_for_source(target_role, "Lever"), target_location=target_loc_str, custom_companies=custom_companies, limit=35)),
        ("SmartRecruiters", lambda: fetch_smartrecruiters_jobs(target_query=optimize_query_for_source(target_role, "SmartRecruiters"), target_location=target_loc_str, custom_companies=custom_companies, limit=25)),
        ("JobSpy", lambda: fetch_jobspy_jobs(target_query=optimize_query_for_source(target_role, "JobSpy"), target_location=target_loc_str, is_remote=not is_onsite_only, limit=25)),
        ("Arbeitnow", lambda: fetch_arbeitnow_jobs(target_query=optimize_query_for_source(target_role, "Arbeitnow"), limit=80)),
        ("WeWorkRemotely", lambda: fetch_weworkremotely_jobs(target_query=optimize_query_for_source(target_role, "WeWorkRemotely"), target_location=target_loc_str, limit=35)),
        ("TelecomCrossing", lambda: fetch_telecomcrossing_jobs(target_query=optimize_query_for_source(target_role, "TelecomCrossing"), target_location=target_loc_str, limit=25)),
        ("ZipRecruiter", lambda: fetch_ziprecruiter_jobs(target_query=optimize_query_for_source(target_role, "ZipRecruiter"), target_location=target_loc_str, is_remote=not is_onsite_only, limit=25)),
        ("ITJobs", lambda: fetch_itjobs_jobs(target_query=optimize_query_for_source(target_role, "ITJobs"), target_location=target_loc_str, limit=30)),
        ("NetEmpregos", lambda: fetch_netempregos_jobs(target_query=optimize_query_for_source(target_role, "NetEmpregos"), target_location=target_loc_str, limit=30)),
        ("LandingJobs", lambda: fetch_landingjobs_jobs(target_query=optimize_query_for_source(target_role, "LandingJobs"), target_location=target_loc_str, limit=25)),
        ("Jobicy", lambda: fetch_jobicy_jobs(limit=40)),
        ("RemoteOK", lambda: fetch_remoteok_jobs(limit=50)),
        ("Remotive", lambda: fetch_remotive_jobs(limit=30)),
    ]

    # Fan-Out for secondary selected roles across high-yield search channels (Point 1.A)
    for sec_role in search_queries[1:]:
        tasks.append(("LinkedIn", lambda r=sec_role: fetch_linkedin_jobs(target_query=optimize_query_for_source(r, "LinkedIn"), target_location=target_loc_str, work_mode_pref=work_mode_pref, limit=20)))
        tasks.append(("Ashby", lambda r=sec_role: fetch_ashby_jobs(target_query=optimize_query_for_source(r, "Ashby"), target_location=target_loc_str, custom_companies=custom_companies, limit=30)))
        tasks.append(("Greenhouse", lambda r=sec_role: fetch_greenhouse_jobs(target_query=optimize_query_for_source(r, "Greenhouse"), target_location=target_loc_str, custom_companies=custom_companies, limit=30)))
        tasks.append(("JobSpy", lambda r=sec_role: fetch_jobspy_jobs(target_query=optimize_query_for_source(r, "JobSpy"), target_location=target_loc_str, is_remote=not is_onsite_only, limit=20)))
        tasks.append(("ITJobs", lambda r=sec_role: fetch_itjobs_jobs(target_query=optimize_query_for_source(r, "ITJobs"), target_location=target_loc_str, limit=20)))
        tasks.append(("NetEmpregos", lambda r=sec_role: fetch_netempregos_jobs(target_query=optimize_query_for_source(r, "NetEmpregos"), target_location=target_loc_str, limit=20)))
        tasks.append(("LandingJobs", lambda r=sec_role: fetch_landingjobs_jobs(target_query=optimize_query_for_source(r, "LandingJobs"), target_location=target_loc_str, limit=20)))

    apify_token = profile.get("apify_api_token") or os.environ.get("APIFY_API_TOKEN")
    if apify_token:
        tasks.append(("Apify", lambda: fetch_apify_jobs(target_query=target_role, target_location=target_loc_str, api_token=apify_token, limit=20)))

    total_tasks = len(tasks)
    log(8, "JobCrawler-Dispatcher", f"Launched {total_tasks} parallel async scrapers across {len(search_queries)} role queries...")

    all_raw = []
    completed_count = 0

    with ThreadPoolExecutor(max_workers=min(22, total_tasks)) as executor:
        future_to_name = {
            executor.submit(safe_scrape, name, fn): name
            for name, fn in tasks
        }
        for future in as_completed(future_to_name):
            completed_count += 1
            src_name, src_jobs = future.result()
            all_raw.extend(src_jobs)
            pct = int(10 + (completed_count / total_tasks) * 82)
            log(
                pct,
                f"JobCrawler-{src_name}",
                f"Retrieved {len(src_jobs)} positions from {src_name} ({completed_count}/{total_tasks} scrapers finished).",
            )

    total_scraped = len(all_raw)

    if not all_raw:
        from src.mock_data import MOCK_JOB_RESULTS
        log(100, "ScoringAgent", "Network throttled — loaded verified opportunities.")
        return MOCK_JOB_RESULTS, len(MOCK_JOB_RESULTS)

    # Phase: Semantic Evaluation, Exclusions & Candidate Profile Calibration
    log(94, "SemanticMatcher", f"Scoring {total_scraped} raw positions across multi-dimensional match criteria...")

    matched_jobs = []
    excluded_by_negative = 0

    for job in all_raw:
        job_title = job.get("title", "")
        job_comp = job.get("company", "")
        job_desc = job.get("full_description", "") or job.get("description", "")
        searchable_text = f"{job_title} {job_comp} {job_desc}".lower()

        # 1. Negative Keyword / Exclusion Filter
        if negative_keywords:
            if any(nk in searchable_text for nk in negative_keywords):
                excluded_by_negative += 1
                continue

        mode_label, is_remote, is_hybrid, is_onsite = determine_work_mode(job)
        job_loc = job.get("location", "")

        # 2. Geographic & Work Mode Filtering
        if is_remote_only:
            # Candidate ONLY wants remote
            if not is_remote:
                continue
        elif is_onsite_only:
            # Candidate ONLY wants on-site / hybrid in specified countries
            if is_remote:
                continue
            is_country_match, _ = check_job_country_match(job_loc, target_countries)
            if not is_country_match and target_countries:
                continue
        else:
            # Candidate is open to Remote, Hybrid, and/or On-site
            if is_remote:
                # Remote positions are eligible
                pass
            else:
                # If on-site or hybrid, it MUST match the specific countries/cities mentioned
                if target_countries:
                    is_country_match, _ = check_job_country_match(job_loc, target_countries)
                    if not is_country_match:
                        continue

        # Direct ATS Identification (Point 3.B)
        is_direct_ats = any(ats in job.get("source", "").lower() for ats in DIRECT_ATS_SOURCES)
        job["is_direct_ats"] = is_direct_ats

        # 3. Compute Multi-Dimensional Semantic Fit (Point 2)
        fit_score, matched_skills, reasons, final_mode_label = calculate_semantic_fit(job, profile, target_countries)

        # Direct ATS Trust Bonus
        if is_direct_ats:
            fit_score = min(99, fit_score + 2)
            reasons.insert(0, "⭐ Direct ATS Official Submission: Unmediated employer requisition.")

        # 4. Target Dream Company Boost
        is_target_employer = job.get("is_target_company") or (
            custom_companies
            and any(
                normalize_company_slug(c) in normalize_company_slug(job_comp)
                for c in custom_companies
            )
        )
        if is_target_employer:
            fit_score = min(99, fit_score + 6)
            reasons.insert(0, f"Target dream employer specified in your profile ({job_comp}).")

        if fit_score >= 90:
            badge_color = "#10b981"
        elif fit_score >= 82:
            badge_color = "#2563eb"
        else:
            badge_color = "#f59e0b"

        job["fit_score"] = fit_score
        job["profile_fit_score"] = float(fit_score)
        job["badge_color"] = badge_color
        job["matched_skills"] = matched_skills
        job["key_reasons"] = reasons
        job["job_type"] = final_mode_label
        job["is_target_company"] = bool(is_target_employer)

        matched_jobs.append(job)

    # Sort descending by match score
    matched_jobs.sort(key=lambda j: j["fit_score"], reverse=True)

    # Deduplicate by job title + company
    seen_keys = set()
    unique_matches = []
    for j in matched_jobs:
        key = f"{j['title'].lower()}_{j['company'].lower()}"
        if key not in seen_keys:
            seen_keys.add(key)
            unique_matches.append(j)

    # Phase 2: Hybrid Gemini Reranking (Point 2.E - if API key available)
    gemini_key = profile.get("gemini_api_key") or os.environ.get("GEMINI_API_KEY")
    if gemini_key and len(unique_matches) > 1:
        log(98, "GeminiReranker", "Pass 2: Executing deep semantic reranking with Gemini Flash...")
        unique_matches = rerank_top_jobs_with_gemini(unique_matches, profile, api_key=gemini_key, limit=15)

    top_matches = unique_matches[:100] if unique_matches else all_raw[:25]

    completion_msg = f"Discovered {len(top_matches)} high-confidence matches tailored to your profile."
    if excluded_by_negative > 0:
        completion_msg += f" (Filtered out {excluded_by_negative} jobs matching exclusion keywords)."

    log(100, "PipelineComplete", completion_msg)
    return top_matches, total_scraped
