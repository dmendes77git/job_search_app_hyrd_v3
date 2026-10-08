"""
Hyrd Multi-Agent Pipeline Orchestrator.
Coordinates the end-to-end autonomous lifecycle across all 5 specialized agents:
ProfileAgent -> ScoutAgent -> MatchAgent -> ReportAgent -> DocAgent.
Exposes isolated runner functions for granular stage testing.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from src.schemas import (
    ProfileAgentInput,
    ProfileAgentOutput,
    ScoutAgentInput,
    ScoutAgentOutput,
    MatchAgentInput,
    MatchAgentOutput,
    ReportAgentInput,
    ReportAgentOutput,
    DocAgentInput,
    DocAgentOutput,
    TailoredDocsRequest,
    TailoredDocsResponse,
    UserProfile,
    JobPosting,
    MatchReport,
    FinalReportPayload,
)
from src.agents.profile_agent import run_profile_agent, ProfileAgent
from src.agents.scout_agent import run_scout_agent, ScoutAgent
from src.agents.match_agent import run_match_agent, MatchAgent
from src.agents.report_agent import run_report_agent, ReportAgent
from src.agents.doc_agent import run_doc_agent, DocAgent

logger = logging.getLogger("Hyrd.Pipeline")


# ============================================================================
# ISOLATED STAGE RUNNERS (FOR GRANULAR COMPONENT TESTING)
# ============================================================================

def run_profile_stage(
    input_data: Union[ProfileAgentInput, Dict[str, Any]],
    api_key: Optional[str] = None,
) -> ProfileAgentOutput:
    """Execute Stages 1 & 2 (Candidate Intake, Resume Extraction & Calibration)."""
    return run_profile_agent(input_data, api_key=api_key)


def run_scout_stage(
    input_data: Union[ScoutAgentInput, Dict[str, Any]],
    on_progress: Optional[Callable[[int, str, str], None]] = None,
) -> ScoutAgentOutput:
    """Execute Stage 3 (Parallel Scraping & Opportunity Harvesting)."""
    return run_scout_agent(input_data, on_progress=on_progress)


def run_match_stage(
    input_data: Union[MatchAgentInput, Dict[str, Any]],
    api_key: Optional[str] = None,
) -> MatchAgentOutput:
    """Execute Stages 4 & 5 (Semantic Scoring, Recruiter Likelihood & Salary Calibration)."""
    return run_match_agent(input_data, api_key=api_key)


def run_report_stage(
    input_data: Union[ReportAgentInput, Dict[str, Any]],
    api_key: Optional[str] = None,
) -> ReportAgentOutput:
    """Execute Stage 6 (Final Opportunity Ranking & Executive Briefing)."""
    return run_report_agent(input_data, api_key=api_key)


def run_doc_stage(
    input_data: Union[DocAgentInput, TailoredDocsRequest, Dict[str, Any]],
    api_key: Optional[str] = None,
) -> DocAgentOutput:
    """Execute On-Demand Document Tailoring (ATS CV, Cover Letter)."""
    return run_doc_agent(input_data, api_key=api_key)


# ============================================================================
# COMPOSITE MULTI-AGENT PIPELINE ORCHESTRATOR
# ============================================================================

class MultiAgentJobPipeline:
    """Full-lifecycle multi-agent pipeline orchestrating end-to-end career acceleration."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        self.profile_agent = ProfileAgent(api_key=self.api_key)
        self.scout_agent = ScoutAgent()
        self.match_agent = MatchAgent(api_key=self.api_key)
        self.report_agent = ReportAgent(api_key=self.api_key)
        self.doc_agent = DocAgent(api_key=self.api_key)

    def execute(
        self,
        raw_resume: Optional[Union[str, bytes]] = None,
        file_type: str = "pdf",
        existing_profile: Optional[UserProfile] = None,
        channels_enabled: Optional[List[str]] = None,
        apify_token: Optional[str] = None,
        max_workers: int = 22,
        on_progress: Optional[Callable[[int, str, str], None]] = None,
    ) -> Dict[str, Any]:
        """Execute the coordinated 6-stage autonomous career pipeline."""
        start_time = time.perf_counter()

        def log(pct: int, agent: str, msg: str):
            if on_progress:
                on_progress(pct, agent, msg)

        # Stage 1 & 2: Candidate Intake & Profile Calibration
        if existing_profile:
            profile = existing_profile
            log(10, "Pipeline", f"Using verified existing workspace for {profile.full_name}.")
            profile_out = ProfileAgentOutput(
                profile=profile,
                parsing_method="existing_workspace",
                parsing_latency_ms=0.0,
                recruiter_gap_analysis={},
                recommended_roles=profile.target_roles,
                status_message="Loaded active candidate workspace.",
            )
        else:
            log(5, "ProfileAgent", "Initiating candidate intake and structured parsing...")
            raw_text = raw_resume if isinstance(raw_resume, str) else None
            raw_bytes = raw_resume if isinstance(raw_resume, bytes) else None

            profile_input = ProfileAgentInput(
                raw_resume_text=raw_text,
                raw_resume_bytes=raw_bytes,
                file_type=file_type,
            )
            profile_out = self.profile_agent.run(profile_input)
            profile = profile_out.profile
            log(15, "ProfileAgent", f"Profile established for {profile.full_name} ({profile.headline}).")

        # Stage 3: Multi-Source Opportunity Harvesting
        log(20, "ScoutAgent", f"Launching crawler swarm across active channels for '{profile.headline}'...")
        scout_input = ScoutAgentInput(
            profile=profile,
            channels_enabled=channels_enabled,
            max_workers=max_workers,
            apify_api_token=apify_token,
        )
        scout_out = self.scout_agent.run(scout_input, on_progress=on_progress)
        log(75, "ScoutAgent", f"Scouting completed: harvested {scout_out.raw_jobs_found} positions.")

        # Stages 4 & 5: Semantic Match Scoring & Salary Calibration
        log(80, "MatchAgent", f"Scoring {len(scout_out.filtered_jobs)} opportunities against competencies...")
        match_input = MatchAgentInput(
            profile=profile,
            candidate_jobs=scout_out.filtered_jobs,
            enable_gemini_rerank=bool(self.api_key),
        )
        match_out = self.match_agent.run(match_input)
        log(92, "MatchAgent", f"Evaluated {match_out.total_evaluated} jobs (Avg Fit: {match_out.average_fit_score}%).")

        # Stage 6: Final Reporting & Executive Intelligence
        log(95, "ReportAgent", "Synthesizing executive market intelligence and morning digest...")
        report_input = ReportAgentInput(
            profile=profile,
            ranked_jobs=match_out.ranked_jobs,
            match_reports=match_out.match_reports,
            telemetry={
                "total_scouted": scout_out.raw_jobs_found,
                "channels": scout_out.channel_telemetry,
                "failures": scout_out.failures_by_source,
            },
        )
        report_out = self.report_agent.run(report_input)

        total_elapsed = time.perf_counter() - start_time
        log(100, "Pipeline", f"Multi-agent cycle completed in {total_elapsed:.1f}s.")

        return {
            "profile_output": profile_out,
            "scout_output": scout_out,
            "match_output": match_out,
            "report_output": report_out,
            "final_payload": report_out.payload,
            "morning_digest": report_out.morning_digest_markdown,
            "top_recommendations": report_out.top_recommendations,
            "execution_time_seconds": total_elapsed,
        }


def run_full_pipeline(
    raw_resume: Optional[Union[str, bytes]] = None,
    file_type: str = "pdf",
    existing_profile: Optional[UserProfile] = None,
    channels_enabled: Optional[List[str]] = None,
    apify_token: Optional[str] = None,
    api_key: Optional[str] = None,
    on_progress: Optional[Callable[[int, str, str], None]] = None,
) -> Dict[str, Any]:
    """Execute the complete multi-agent pipeline as a standalone entry point."""
    pipeline = MultiAgentJobPipeline(api_key=api_key)
    return pipeline.execute(
        raw_resume=raw_resume,
        file_type=file_type,
        existing_profile=existing_profile,
        channels_enabled=channels_enabled,
        apify_token=apify_token,
        on_progress=on_progress,
    )
