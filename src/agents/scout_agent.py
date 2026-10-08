"""
ScoutAgent (Stage 3): Autonomous Multi-Source Job Searching & Web Scraping.
Leverages the google-antigravity framework and executes parallel harvesting
across up to 17 live ATS, aggregator, and regional job endpoints.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Callable, Dict, List, Optional, Union

try:
    from google.antigravity import Agent, LocalAgentConfig
    from google.antigravity.tools.tool_runner import ToolRunner
except ImportError:
    from google.antigravity.tools.tool_runner import ToolRunner  # type: ignore
    Agent = Any  # type: ignore
    LocalAgentConfig = Any  # type: ignore

from src.schemas import (
    ScoutAgentInput,
    ScoutAgentOutput,
    JobPosting,
    UserProfile,
    WorkModeEnum,
)
from src.tools.search_tools import execute_concurrent_search, search_tools_runner
from src.agents.matching.scoring import (
    extract_target_countries,
    check_job_country_match,
    determine_work_mode,
)
from src.agents.scrapers.base import normalize_company_slug

logger = logging.getLogger("Hyrd.ScoutAgent")

DIRECT_ATS_SOURCES = {"ashby", "greenhouse", "lever", "smartrecruiters"}


class ScoutAgent:
    """Autonomous agent governing Stage 3 Multi-Source Crawling and Filtering."""

    def __init__(self):
        self.tool_runner = search_tools_runner

    def run(
        self,
        input_payload: ScoutAgentInput,
        on_progress: Optional[Callable[[int, str, str], None]] = None,
    ) -> ScoutAgentOutput:
        """Execute Stage 3: Concurrently scrape, deduplicate, and filter job postings."""
        start_time = time.perf_counter()
        profile = input_payload.profile
        profile_dict = profile.to_dict()

        def log(pct: int, agent: str, msg: str):
            if on_progress:
                on_progress(pct, agent, msg)

        log(2, "ScoutAgent", f"Initializing opportunity harvesting for {profile.full_name} ({profile.headline})...")

        # 1. Execute concurrent search across active channels
        raw_postings, telemetry, failures = execute_concurrent_search(
            profile_data=profile_dict,
            channels_enabled=input_payload.channels_enabled,
            max_workers=input_payload.max_workers,
            apify_token=input_payload.apify_api_token,
            on_progress=on_progress,
        )

        total_scraped = len(raw_postings)
        log(80, "ScoutAgent", f"Applying negative keyword exclusions and geographic constraints to {total_scraped} postings...")

        # 2. Extract filtering parameters
        target_loc_str = profile.location_preference or profile.location or "Remote"
        target_countries = extract_target_countries(target_loc_str)
        work_mode_pref = (
            profile.work_mode.value.lower()
            if isinstance(profile.work_mode, WorkModeEnum)
            else str(profile.work_mode).lower()
        )
        is_remote_only = "remote only" in work_mode_pref
        is_onsite_only = "on-site only" in work_mode_pref

        # Extract negative exclusion terms
        negative_keywords: List[str] = [
            n.strip().lower() for n in profile.negative_keywords if n and n.strip()
        ]

        # Extract custom target companies
        target_companies: List[str] = [
            c.strip().lower() for c in profile.target_companies if c and c.strip()
        ]

        # 3. Filtering & Metadata Tagging Loop
        filtered_jobs: List[JobPosting] = []
        seen_keys = set()

        for job in raw_postings:
            title = job.title or ""
            comp = job.company or ""
            desc = job.full_description or ""
            searchable_text = f"{title} {comp} {desc}".lower()

            # Rule A: Negative keyword exclusions
            if negative_keywords and any(nk in searchable_text for nk in negative_keywords):
                continue

            # Rule B: Work mode and geographic filtering
            job_dict_repr = job.to_dict()
            mode_label, is_remote, is_hybrid, is_onsite = determine_work_mode(job_dict_repr)
            job_loc = job.location or ""

            if is_remote_only:
                if not is_remote:
                    continue
            elif is_onsite_only:
                if is_remote:
                    continue
                if target_countries:
                    is_match, _ = check_job_country_match(job_loc, target_countries)
                    if not is_match:
                        continue
            else:
                # Open to remote or hybrid: if on-site/hybrid, must match specified country
                if not is_remote and target_countries:
                    is_match, _ = check_job_country_match(job_loc, target_countries)
                    if not is_match:
                        continue

            # Rule C: Deduplicate by title + company
            dedup_key = f"{title.strip().lower()}_{comp.strip().lower()}"
            if dedup_key in seen_keys:
                continue
            seen_keys.add(dedup_key)

            # Rule D: Direct ATS identification
            is_direct_ats = any(ats in job.source.lower() for ats in DIRECT_ATS_SOURCES)
            job.is_direct_ats = is_direct_ats

            # Rule E: Target company tag
            is_target = False
            if target_companies:
                norm_comp = normalize_company_slug(comp)
                is_target = any(normalize_company_slug(tc) in norm_comp for tc in target_companies)
            job.is_target_company = is_target

            # Set normalized work mode label
            job.job_type = mode_label

            filtered_jobs.append(job)

        elapsed = time.perf_counter() - start_time
        log(100, "ScoutAgent", f"Scouting completed: harvested {total_scraped}, filtered to {len(filtered_jobs)} qualified opportunities.")

        return ScoutAgentOutput(
            raw_jobs_found=total_scraped,
            filtered_jobs=filtered_jobs,
            channel_telemetry=telemetry,
            failures_by_source=failures,
            execution_time_seconds=elapsed,
        )


def run_scout_agent(
    input_data: Union[ScoutAgentInput, Dict[str, Any]],
    on_progress: Optional[Callable[[int, str, str], None]] = None,
) -> ScoutAgentOutput:
    """Functional runner for ScoutAgent to allow isolated stage testing."""
    if isinstance(input_data, dict):
        validated_input = ScoutAgentInput(**input_data)
    else:
        validated_input = input_data

    agent = ScoutAgent()
    return agent.run(validated_input, on_progress=on_progress)
