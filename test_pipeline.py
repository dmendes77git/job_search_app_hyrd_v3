"""
CLI Test Runner (test_pipeline.py)
Standalone verification harness for Hyrd Multi-Agent Pipeline.
Verifies that all 5 specialized agents (ProfileAgent, ScoutAgent, MatchAgent,
ReportAgent, DocAgent) communicate and pass typed Pydantic messages correctly.
"""

from __future__ import annotations

import os
import sys
import time
from typing import Dict, Any

# Ensure project root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from src.schemas import (
    UserProfile,
    JobPosting,
    MatchReport,
    FinalReportPayload,
    TailoredDocsRequest,
    TailoredDocsResponse,
    ProfileAgentInput,
    ScoutAgentInput,
    MatchAgentInput,
    ReportAgentInput,
    DocAgentInput,
    WorkModeEnum,
)
from src.pipeline import (
    run_profile_stage,
    run_scout_stage,
    run_match_stage,
    run_report_stage,
    run_doc_stage,
    MultiAgentJobPipeline,
)


def print_banner(text: str) -> None:
    width = 75
    print("\n" + "=" * width)
    print(f" {text}".center(width))
    print("=" * width)


def main() -> int:
    print_banner("⚡ HYRD MULTI-AGENT PIPELINE CLI VERIFICATION HARNESS")
    overall_start = time.perf_counter()

    mock_resume_text = """
    Alex Mercer
    alex.mercer.dev@example.com | +1 (555) 019-2834 | San Francisco, CA | linkedin.com/in/alexmercer
    
    EXECUTIVE SUMMARY:
    Principal AI Systems Architect with 8+ years experience designing autonomous multi-agent swarms,
    resilient LLM applications with Google Gemini API, and high-throughput microservices in Python & FastAPI.
    
    CORE COMPETENCIES:
    - Programming: Python, TypeScript, SQL, Bash
    - AI & LLM Systems: Google GenAI (Gemini), Multi-Agent Orchestration, RAG, Vector Search
    - Cloud & Infrastructure: Docker, Kubernetes, Google Cloud Platform (GCP), CI/CD Automation
    - Frameworks: FastAPI, Streamlit, Pydantic, PostgreSQL
    
    EXPERIENCE HIGHLIGHTS:
    - Architected autonomous multi-agent pipelines serving 300,000+ daily queries with 99.9% availability.
    - Reduced search latency by 65% through optimized vector indexing and caching strategies.
    - Directed distributed engineering squads delivering high-concurrency enterprise services.
    
    EDUCATION:
    - B.S. in Computer Science | University of California, Berkeley
    """

    # ------------------------------------------------------------------------
    # STEP 1: Verify ProfileAgent (Stages 1 & 2)
    # ------------------------------------------------------------------------
    print("\n[Stage 1 & 2] Executing ProfileAgent (Intake & Entity Extraction)...")
    t0 = time.perf_counter()
    p_input = ProfileAgentInput(
        raw_resume_text=mock_resume_text,
        preferred_language="en",
    )
    p_output = run_profile_stage(p_input)
    t_profile = time.perf_counter() - t0

    assert isinstance(p_output.profile, UserProfile), "Profile output must be a UserProfile"
    assert "Alex Mercer" in p_output.profile.full_name or p_output.profile.full_name == "Alex Mercer"
    assert len(p_output.profile.extracted_skills) >= 4, "Should extract at least 4 skills"
    assert p_output.recruiter_gap_analysis["readiness_score"] >= 60, "Recruiter readiness score must be valid"

    print(f"  ✅ ProfileAgent Succeeded ({t_profile:.2f}s)")
    print(f"     • Candidate: {p_output.profile.full_name} | Role: {p_output.profile.headline}")
    print(f"     • Skills Detected ({len(p_output.profile.extracted_skills)}): {', '.join(p_output.profile.extracted_skills[:6])}")
    print(f"     • Recruiter Readiness: {p_output.recruiter_gap_analysis['readiness_score']}% ({p_output.recruiter_gap_analysis['readiness_label']})")
    print(f"     • Parsing Method: {p_output.parsing_method}")

    profile = p_output.profile

    # ------------------------------------------------------------------------
    # STEP 2: Verify ScoutAgent (Stage 3)
    # ------------------------------------------------------------------------
    print("\n[Stage 3] Executing ScoutAgent (Parallel Multi-Channel Harvesting)...")
    t0 = time.perf_counter()
    s_input = ScoutAgentInput(
        profile=profile,
        channels_enabled=["Ashby", "RemoteOK"],  # Target fast live endpoints for verification
        max_workers=8,
        target_job_limit_per_source=25,
    )
    s_output = run_scout_stage(s_input)
    t_scout = time.perf_counter() - t0

    assert isinstance(s_output.filtered_jobs, list), "Filtered jobs must be a list"
    assert len(s_output.filtered_jobs) > 0, "ScoutAgent must harvest at least one opportunity"
    assert all(isinstance(j, JobPosting) for j in s_output.filtered_jobs), "All items must be JobPosting instances"

    print(f"  ✅ ScoutAgent Succeeded ({t_scout:.2f}s)")
    print(f"     • Raw Positions Scraped: {s_output.raw_jobs_found}")
    print(f"     • Qualified Openings After Filtering: {len(s_output.filtered_jobs)}")
    print(f"     • Channel Telemetry: {s_output.channel_telemetry}")

    candidate_jobs = s_output.filtered_jobs

    # ------------------------------------------------------------------------
    # STEP 3: Verify MatchAgent (Stages 4 & 5)
    # ------------------------------------------------------------------------
    print("\n[Stages 4 & 5] Executing MatchAgent (Multi-Dimensional Scoring & Recruiter Callback Probability)...")
    t0 = time.perf_counter()
    m_input = MatchAgentInput(
        profile=profile,
        candidate_jobs=candidate_jobs,
        enable_gemini_rerank=False,  # Offline/deterministic pass for verification speed
    )
    m_output = run_match_stage(m_input)
    t_match = time.perf_counter() - t0

    assert len(m_output.ranked_jobs) == len(candidate_jobs), "Ranked jobs count should match candidate jobs"
    top_job = m_output.ranked_jobs[0]
    assert top_job.id in m_output.match_reports, "Each ranked job must have an associated MatchReport"
    
    top_report = m_output.match_reports[top_job.id]
    assert 0.0 <= top_report.match_score <= 100.0, "Match score must be bounded 0-100"
    assert 0.0 <= top_report.probability_of_recruiter_response <= 1.0, "Probability must be bounded 0.0-1.0"

    print(f"  ✅ MatchAgent Succeeded ({t_match:.2f}s)")
    print(f"     • Evaluated Positions: {m_output.total_evaluated}")
    print(f"     • Average Market Fit: {m_output.average_fit_score}%")
    print(f"     • Top Tier Matches (>=90%): {m_output.top_tier_count}")
    print(f"     • #1 Opportunity: '{top_job.title}' at '{top_job.company}'")
    print(f"       - Fit Score: {top_job.fit_score}% | Recruiter Callback Prob: {int(top_report.probability_of_recruiter_response * 100)}%")
    print(f"       - Matched Skills: {', '.join(top_job.matched_skills[:4]) if top_job.matched_skills else 'Domain alignment'}")
    print(f"       - Missing Gaps: {', '.join(top_job.missing_skills[:3]) if top_job.missing_skills else 'None detected'}")

    # ------------------------------------------------------------------------
    # STEP 4: Verify ReportAgent (Stage 6)
    # ------------------------------------------------------------------------
    print("\n[Stage 6] Executing ReportAgent (Final Payload & Morning Digest)...")
    t0 = time.perf_counter()
    r_input = ReportAgentInput(
        profile=profile,
        ranked_jobs=m_output.ranked_jobs,
        match_reports=m_output.match_reports,
        telemetry={
            "total_scouted": s_output.raw_jobs_found,
            "channels": s_output.channel_telemetry,
        },
    )
    r_output = run_report_stage(r_input)
    t_report = time.perf_counter() - t0

    assert isinstance(r_output.payload, FinalReportPayload), "Payload must be a FinalReportPayload"
    assert len(r_output.payload.top_matches) > 0, "Payload must include top matches"
    assert len(r_output.morning_digest_markdown) > 0, "Morning digest markdown must not be empty"

    print(f"  ✅ ReportAgent Succeeded ({t_report:.2f}s)")
    print(f"     • Report ID: {r_output.payload.report_id}")
    print(f"     • Top Ranked Positions Crated: {len(r_output.payload.top_matches)}")
    print(f"     • Executive Directive: {r_output.payload.executive_takeaway[:80]}...")
    print(f"     • Morning Digest Length: {len(r_output.morning_digest_markdown)} chars")

    # ------------------------------------------------------------------------
    # STEP 5: Verify DocAgent (On-Demand Tailoring)
    # ------------------------------------------------------------------------
    print("\n[On-Demand Trigger] Executing DocAgent (ATS CV & Cover Letter Generation)...")
    t0 = time.perf_counter()
    d_input = DocAgentInput(
        user_profile=profile,
        job_posting=top_job,
        language="en",
    )
    d_output = run_doc_stage(d_input)
    t_doc = time.perf_counter() - t0

    assert isinstance(d_output, TailoredDocsResponse), "Output must be TailoredDocsResponse"
    assert d_output.cv_markdown is not None, "Synthesized CV markdown must exist"
    assert d_output.cover_letter_markdown is not None, "Synthesized Cover Letter markdown must exist"
    assert d_output.ats_compatibility_score is not None and d_output.ats_compatibility_score >= 60

    print(f"  ✅ DocAgent Succeeded ({t_doc:.2f}s)")
    print(f"     • Generated CV Characters: {len(d_output.cv_markdown)}")
    print(f"     • Generated Cover Letter Characters: {len(d_output.cover_letter_markdown)}")
    print(f"     • Objective ATS Score: {d_output.ats_compatibility_score}/100")
    print(f"     • Engine: {d_output.generated_model}")

    # ------------------------------------------------------------------------
    # STEP 6: Verify Composite Pipeline (End-to-End Orchestrator)
    # ------------------------------------------------------------------------
    print("\n[Composite Pipeline] Executing MultiAgentJobPipeline.execute End-to-End...")
    t0 = time.perf_counter()
    pipeline = MultiAgentJobPipeline(api_key=None)
    full_result = pipeline.execute(
        existing_profile=profile,
        channels_enabled=["Ashby"],
        max_workers=4,
    )
    t_pipeline = time.perf_counter() - t0

    assert "final_payload" in full_result
    assert "top_recommendations" in full_result
    assert full_result["execution_time_seconds"] > 0
    print(f"  ✅ MultiAgentJobPipeline Succeeded ({t_pipeline:.2f}s)")
    print(f"     • Returned {len(full_result['top_recommendations'])} top opportunities in full cycle")

    total_time = time.perf_counter() - overall_start
    print_banner(f"🎉 ALL 5 AGENTS & PIPELINE ORCHESTRATOR PASSED VERIFICATION ({total_time:.2f}s)!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
