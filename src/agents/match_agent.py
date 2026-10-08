"""
MatchAgent (Stages 4 & 5): Multi-Dimensional Semantic Fit, Salary Calibration,
and Recruiter Response Estimation.
Built using the google-antigravity framework with strict Pydantic v2 contracts.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional, Tuple, Union

try:
    from google.antigravity import Agent, LocalAgentConfig
    from google.antigravity.tools.tool_runner import ToolRunner
except ImportError:
    from google.antigravity.tools.tool_runner import ToolRunner  # type: ignore
    Agent = Any  # type: ignore
    LocalAgentConfig = Any  # type: ignore

from src.schemas import (
    MatchAgentInput,
    MatchAgentOutput,
    JobPosting,
    MatchReport,
    UserProfile,
    SalaryEvaluation,
    CapabilityMatch,
    LevelingAnalysis,
    GatekeeperAudit,
    ViabilityMetrics,
)
from src.agents.matching.scoring import (
    calculate_semantic_fit,
    calculate_quality_match,
    extract_target_countries,
    calculate_bayesian_callback_probability,
    evaluate_dealbreakers,
    rerank_top_jobs_with_gemini,
)
from src.utils.salary_evaluator import evaluate_job_salary
from src.utils.salary_benchmarks import MARKET_BENCHMARKS, GEOGRAPHIC_SALARY_FACTORS

logger = logging.getLogger("Hyrd.MatchAgent")


# ============================================================================
# STATISTICAL RECRUITER RESPONSE ESTIMATOR
# ============================================================================

def estimate_recruiter_response_probability(
    fit_score: int,
    is_direct_ats: bool,
    missing_skills_count: int,
    is_target_company: bool = False,
) -> float:
    """Calculate statistical probability of recruiter callback (0.0 to 1.0)
    calibrated against institutional hiring response distributions.
    """
    # Baseline probability derived from semantic fit score
    base_prob = (fit_score / 100.0) * 0.85

    # Direct ATS unmediated application bonus (+6%)
    if is_direct_ats:
        base_prob += 0.06

    # Target company cultural alignment bonus (+3%)
    if is_target_company:
        base_prob += 0.03

    # Penalty for missing critical requirements (-2.5% per gap)
    gap_penalty = min(0.25, missing_skills_count * 0.025)
    calibrated_prob = base_prob - gap_penalty

    # Bound within realistic limits [0.08, 0.96]
    return float(round(max(0.08, min(0.96, calibrated_prob)), 3))


# ============================================================================
# MATCH AGENT CLASS & RUNNER
# ============================================================================

class MatchAgent:
    """Autonomous agent governing Stages 4 & 5 Semantic Scoring and Evaluation."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        self.tool_runner = ToolRunner()
        self._register_tools()

    def _register_tools(self) -> None:
        self.tool_runner.register(calculate_semantic_fit, "calculate_semantic_fit")
        self.tool_runner.register(calculate_quality_match, "calculate_quality_match")
        self.tool_runner.register(estimate_recruiter_response_probability, "estimate_probability")
        self.tool_runner.register(calculate_bayesian_callback_probability, "calculate_bayesian_callback_probability")
        self.tool_runner.register(evaluate_dealbreakers, "evaluate_dealbreakers")
        self.tool_runner.register(evaluate_job_salary, "evaluate_job_salary")

    def run(self, input_payload: MatchAgentInput) -> MatchAgentOutput:
        """Execute Stages 4 & 5: Score opportunities, calculate recruiter response probability,
        calibrate compensation, and perform Pass-2 Gemini reranking.
        """
        profile = input_payload.profile
        profile_dict = profile.to_dict()
        target_loc_str = profile.location_preference or profile.location or "Remote"
        target_countries = extract_target_countries(target_loc_str)

        evaluated_jobs: List[JobPosting] = []
        match_reports: Dict[str, MatchReport] = {}

        for job in input_payload.candidate_jobs:
            job_dict = job.to_dict()

            # 1. Compute multi-dimensional semantic fit & decoupled quality match
            fit_score, matched_skills, reasons, final_mode_label = calculate_semantic_fit(
                job=job_dict,
                profile=profile_dict,
                target_countries=target_countries,
            )

            profile_fit_score = float(job_dict.get("profile_fit_score", fit_score))
            interview_likelihood_pct = float(job_dict.get("interview_likelihood_pct", 50.0))
            strategic_quadrant = str(job_dict.get("strategic_quadrant", "QI"))
            recommended_action = str(job_dict.get("recommended_action", "Apply with tailored CV."))
            badge_color = str(job_dict.get("badge_color", "#2563eb"))

            # 2. Extract Skill Gaps
            job_reqs = job.requirements or []
            cand_skills_lower = {s.lower() for s in profile.extracted_skills}
            missing_skills: List[str] = list(job_dict.get("missing_skills", []))
            for r in job_reqs:
                if not any(cs in r.lower() for cs in cand_skills_lower):
                    short_r = r[:40]
                    if short_r not in missing_skills:
                        missing_skills.append(short_r)

            # 3. Recruiter Response Likelihood via Bayesian Callback Model (Feature P2-C)
            bayesian_res = calculate_bayesian_callback_probability(
                fit_score=profile_fit_score,
                days_posted=job_dict.get("days_since_posted", 1),
                source=job_dict.get("source", "direct_ats"),
                is_direct_ats=bool(job_dict.get("is_direct_ats", False)),
                missing_skills_count=len(missing_skills),
                seniority_delta=int(job_dict.get("leveling_delta", 0)),
                is_target_company=bool(job_dict.get("is_target_company", False)),
            )
            prob_response = bayesian_res["probability_of_response"]
            interview_likelihood_pct = bayesian_res["interview_likelihood_pct"]


            # 4. Salary Benchmark Evaluation
            try:
                salary_str = job.salary_range or job_dict.get("salary") or ""
                salary_eval = evaluate_job_salary(
                    job_salary_str=salary_str,
                    job_title=job.title,
                    profile=profile_dict,
                    target_location=target_loc_str,
                    job_location=job.location,
                )
                salary_score = salary_eval.get("score", 75)
            except Exception as exc:
                logger.debug(f"Salary evaluation fallback: {exc}")
                salary_eval = None
                salary_score = 75

            # Update JobPosting model fields
            job.fit_score = int(round(profile_fit_score))
            job.profile_fit_score = profile_fit_score
            job.interview_likelihood_pct = interview_likelihood_pct
            job.strategic_quadrant = strategic_quadrant
            job.badge_color = badge_color
            job.matched_skills = job_dict.get("matched_skills", matched_skills)
            job.missing_skills = missing_skills[:6]
            job.key_reasons = job_dict.get("key_reasons", reasons)
            job.job_type = job_dict.get("job_type", final_mode_label)
            job.salary_score = salary_score
            job.salary_evaluation = salary_eval

            # Generate short role summary if not already present
            if not getattr(job, "short_summary", None):
                desc_for_sum = job.full_description or job.description_text or ""
                if desc_for_sum:
                    from src.utils.job_summarizer import summarize_job_description
                    sum_res = summarize_job_description(
                        desc_for_sum,
                        title=job.title,
                        company=job.company_name or job.company,
                    )
                    job.short_summary = sum_res.get("formatted_markdown", "")

            # 5. Build Granular Sub-Models for MatchReport
            capability_matches = [
                CapabilityMatch(**cm) if isinstance(cm, dict) else cm
                for cm in job_dict.get("capability_matches", [])
            ]
            leveling_analysis = (
                LevelingAnalysis(**job_dict["leveling_analysis"])
                if isinstance(job_dict.get("leveling_analysis"), dict)
                else job_dict.get("leveling_analysis")
            )
            gatekeeper_audit = (
                GatekeeperAudit(**job_dict["gatekeeper_audit"])
                if isinstance(job_dict.get("gatekeeper_audit"), dict)
                else job_dict.get("gatekeeper_audit")
            )
            viability_metrics = (
                ViabilityMetrics(**job_dict["viability_metrics"])
                if isinstance(job_dict.get("viability_metrics"), dict)
                else job_dict.get("viability_metrics")
            )

            # 6. Build MatchReport Model
            alignment_summary = (
                f"Candidate exhibits {profile_fit_score}% profile fit ({strategic_quadrant}) for {job.title} at {job.company}. "
                f"Core strengths include {', '.join(job.matched_skills[:3]) if job.matched_skills else 'functional discipline'}. "
                f"Estimated recruiter callback odds are {interview_likelihood_pct}%. "
                f"{recommended_action}"
            )

            dimension_scores = dict(job_dict.get("dimension_scores", {}))
            if "semantic_fit" not in dimension_scores:
                dimension_scores["semantic_fit"] = float(job.fit_score)
            if "salary_competitiveness" not in dimension_scores:
                dimension_scores["salary_competitiveness"] = float(salary_score)

            report = MatchReport(
                job_id=job.id,
                job_title=job.title,
                company=job.company,
                match_score=float(job.fit_score),
                profile_fit_score=profile_fit_score,
                probability_of_recruiter_response=prob_response,
                interview_likelihood_pct=interview_likelihood_pct,
                strategic_quadrant=strategic_quadrant,
                recommended_action=recommended_action,
                key_skill_gaps=missing_skills[:5],
                alignment_summary=alignment_summary,
                matching_skills=job.matched_skills,
                dimension_scores=dimension_scores,
                capability_matches=capability_matches,
                leveling_analysis=leveling_analysis,
                gatekeeper_audit=gatekeeper_audit,
                viability_metrics=viability_metrics,
                recruiter_reasoning=job.key_reasons[:4],
            )

            match_reports[job.id] = report
            evaluated_jobs.append(job)

        # 7. Sort descending by match score
        evaluated_jobs.sort(key=lambda j: j.fit_score, reverse=True)

        # 8. Pass-2 Gemini Flash Semantic Reranking (if enabled and key present)
        effective_key = self.api_key or profile_dict.get("gemini_api_key") or os.environ.get("GEMINI_API_KEY")
        if input_payload.enable_gemini_rerank and effective_key and len(evaluated_jobs) > 1:
            try:
                dict_list = [j.to_dict() for j in evaluated_jobs[:15]]
                reranked_dicts = rerank_top_jobs_with_gemini(
                    top_jobs=dict_list,
                    profile=profile_dict,
                    api_key=effective_key,
                    limit=15,
                )
                # Map reranked scores back
                rerank_map = {d.get("id"): d.get("fit_score") for d in reranked_dicts if d.get("id")}
                for j in evaluated_jobs:
                    if j.id in rerank_map and rerank_map[j.id]:
                        j.fit_score = int(rerank_map[j.id])
                        j.profile_fit_score = float(j.fit_score)
                        if j.id in match_reports:
                            match_reports[j.id].match_score = float(j.fit_score)
                            match_reports[j.id].profile_fit_score = float(j.fit_score)
                # Re-sort after reranking
                evaluated_jobs.sort(key=lambda j: j.fit_score, reverse=True)
            except Exception as exc:
                logger.warning(f"Pass-2 Gemini reranking failed: {exc}. Retaining deterministic rank order.")

        total_evaluated = len(evaluated_jobs)
        avg_score = (
            sum(j.fit_score for j in evaluated_jobs) / total_evaluated
            if total_evaluated > 0 else 0.0
        )
        top_tier = sum(1 for j in evaluated_jobs if j.fit_score >= 90)

        return MatchAgentOutput(
            ranked_jobs=evaluated_jobs,
            match_reports=match_reports,
            total_evaluated=total_evaluated,
            average_fit_score=round(avg_score, 1),
            top_tier_count=top_tier,
        )


def run_match_agent(
    input_data: Union[MatchAgentInput, Dict[str, Any]],
    api_key: Optional[str] = None,
) -> MatchAgentOutput:
    """Functional runner for MatchAgent to allow isolated stage testing."""
    if isinstance(input_data, dict):
        validated_input = MatchAgentInput(**input_data)
    else:
        validated_input = input_data

    agent = MatchAgent(api_key=api_key)
    return agent.run(validated_input)
