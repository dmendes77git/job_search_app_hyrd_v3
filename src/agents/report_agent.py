"""
ReportAgent (Stage 6): Opportunity Ranking, Market Intelligence Aggregation,
and Executive Morning Digest Formatting.
Built using the google-antigravity framework with strict Pydantic v2 contracts.
"""

from __future__ import annotations

import logging
import os
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

try:
    from google.antigravity import Agent, LocalAgentConfig
    from google.antigravity.tools.tool_runner import ToolRunner
except ImportError:
    from google.antigravity.tools.tool_runner import ToolRunner  # type: ignore
    Agent = Any  # type: ignore
    LocalAgentConfig = Any  # type: ignore

from src.schemas import (
    ReportAgentInput,
    ReportAgentOutput,
    FinalReportPayload,
    JobPosting,
    MatchReport,
    UserProfile,
)
from src.agents.job_scout_agent import _synthesize_digest_narrative, _format_email_newsletter
from src.utils.gemini_client import generate_gemini_content

logger = logging.getLogger("Hyrd.ReportAgent")


def generate_morning_digest(
    profile: Dict[str, Any],
    scouted_jobs: List[Dict[str, Any]],
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Compile morning briefing from scouted jobs and profile background."""
    narrative = _synthesize_digest_narrative(
        profile=profile,
        featured_jobs=scouted_jobs[:4],
        total_scraped=len(scouted_jobs),
        new_count=len(scouted_jobs),
        target_count=sum(1 for j in scouted_jobs if j.get("is_target_company")),
        api_key=api_key,
    )
    email_md = _format_email_newsletter(
        profile=profile,
        digest_headline=narrative.get("headline", "Your Daily Career Digest"),
        summary=narrative.get("executive_summary", ""),
        market_signals=narrative.get("market_signals", []),
        jobs=scouted_jobs[:5],
        timestamp=datetime.now(timezone.utc).strftime("%b %d, %Y"),
    )
    return {
        "headline": narrative.get("headline", "Your Daily Career Digest"),
        "executive_summary": narrative.get("executive_summary", ""),
        "full_digest_markdown": email_md,
        "action_item": narrative.get("action_plan", "Review top opportunities and apply."),
    }


def synthesize_market_insights(
    jobs: List[JobPosting],
    profile: UserProfile,
) -> Dict[str, Any]:
    """Compute empirical market intelligence metrics across scouted job opportunities."""
    if not jobs:
        return {
            "top_skills_in_demand": [],
            "common_locations": [],
            "average_market_fit": 0.0,
            "direct_ats_ratio": 0.0,
        }

    # Extract all skills demanded
    all_skills: List[str] = []
    locations: List[str] = []
    direct_count = 0

    for j in jobs:
        all_skills.extend(j.matched_skills)
        all_skills.extend(j.requirements)
        if j.location:
            locations.append(j.location.strip())
        if j.is_direct_ats:
            direct_count += 1

    skill_counts = Counter(all_skills).most_common(8)
    loc_counts = Counter(locations).most_common(4)

    avg_fit = sum(j.fit_score for j in jobs) / len(jobs)
    direct_ratio = round(direct_count / len(jobs), 2)

    return {
        "top_skills_in_demand": [s[0] for s in skill_counts],
        "common_locations": [l[0] for l in loc_counts],
        "average_market_fit": round(avg_fit, 1),
        "direct_ats_ratio": direct_ratio,
        "sample_size": len(jobs),
    }


class ReportAgent:
    """Autonomous agent governing Stage 6 Final Reporting & Morning Briefing."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        self.tool_runner = ToolRunner()
        self._register_tools()

    def _register_tools(self) -> None:
        self.tool_runner.register(synthesize_market_insights, "synthesize_market_insights")
        self.tool_runner.register(generate_morning_digest, "generate_morning_digest")

    def run(self, input_payload: ReportAgentInput) -> ReportAgentOutput:
        """Execute Stage 6: Build FinalReportPayload and format executive morning digest."""
        profile = input_payload.profile
        jobs = input_payload.ranked_jobs
        match_reports_map = input_payload.match_reports
        telemetry = input_payload.telemetry or {}

        # 1. Select top recommendations (top 10 opportunities)
        top_recommendations = jobs[:10] if jobs else []

        # 2. Extract detailed MatchReport objects for top recommendations
        detailed_reports: List[MatchReport] = []
        for j in top_recommendations:
            if j.id in match_reports_map:
                detailed_reports.append(match_reports_map[j.id])

        # 3. Market Intelligence Synthesis
        market_intel = synthesize_market_insights(jobs, profile)

        # 4. Generate Executive Morning Digest
        profile_dict = profile.to_dict()
        job_dicts = [j.to_dict() for j in jobs]
        try:
            digest_dict = generate_morning_digest(
                profile=profile_dict,
                scouted_jobs=job_dicts,
                api_key=self.api_key,
            )
            digest_md = digest_dict.get("full_digest_markdown") or digest_dict.get("executive_summary") or ""
            executive_takeaway = digest_dict.get("action_item") or (
                f"Prioritize immediate applications to the top {min(3, len(top_recommendations))} "
                f"direct ATS postings featuring >90% semantic match."
            )
        except Exception as exc:
            logger.warning(f"Morning digest generator exception: {exc}. Using deterministic summary.")
            digest_md = (
                f"# 🎯 Executive Career Digest for {profile.full_name}\n\n"
                f"**Role:** {profile.headline} | **Scouted Positions:** {len(jobs)}\n\n"
                f"## Top Opportunities Identified:\n"
            )
            for j in top_recommendations[:5]:
                digest_md += f"- **{j.title}** at **{j.company}** (Fit: {j.fit_score}% | {j.location})\n"
            executive_takeaway = "Focus on top-tier direct ATS opportunities matching your core competencies."

        # 5. Build FinalReportPayload
        payload = FinalReportPayload(
            candidate_id=profile.candidate_id,
            candidate_name=profile.full_name,
            target_role=profile.headline,
            total_jobs_scouted=telemetry.get("total_scouted", len(jobs)),
            total_jobs_evaluated=len(jobs),
            top_matches=top_recommendations,
            detailed_match_reports=detailed_reports,
            market_intelligence_summary=market_intel,
            search_channels_telemetry=telemetry.get("channels", {}),
            executive_takeaway=executive_takeaway,
        )

        return ReportAgentOutput(
            payload=payload,
            morning_digest_markdown=digest_md,
            top_recommendations=top_recommendations,
        )


def run_report_agent(
    input_data: Union[ReportAgentInput, Dict[str, Any]],
    api_key: Optional[str] = None,
) -> ReportAgentOutput:
    """Functional runner for ReportAgent to allow isolated stage testing."""
    if isinstance(input_data, dict):
        validated_input = ReportAgentInput(**input_data)
    else:
        validated_input = input_data

    agent = ReportAgent(api_key=api_key)
    return agent.run(validated_input)
