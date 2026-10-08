"""
Unit and integration test suite for the modular multi-agent architecture:
- ProfileAgent (Stages 1 & 2)
- ScoutAgent (Stage 3)
- MatchAgent (Stages 4 & 5)
- ReportAgent (Stage 6)
- DocAgent (On-Demand)
- Pipeline Orchestrator (pipeline.py)
"""

import pytest
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
    UserProfile,
    JobPosting,
    MatchReport,
    FinalReportPayload,
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


def test_profile_agent_unparseable_input_error_handling():
    """Verify ProfileAgent handles completely empty or unparseable input without raising."""
    out = run_profile_stage(ProfileAgentInput())
    assert isinstance(out, ProfileAgentOutput)
    assert out.parsing_method == "heuristic_fallback"
    assert out.profile.full_name is not None
    assert "empty or unparseable" in out.status_message.lower()
    assert out.recruiter_gap_analysis["readiness_score"] >= 20


def test_profile_agent_with_valid_text():
    """Verify ProfileAgent parses text and extracts skills, roles, and readiness gaps."""
    sample = """
    Elena Rostova
    elena.rostova@techmail.com | +1 (555) 321-9876 | New York, NY | linkedin.com/in/elenarostova
    Principal AI Architect with 9+ years scaling distributed multi-agent systems and PyTorch models.
    Quantified Accomplishments:
    - Reduced model inference cost by 55% using speculative decoding.
    - Led a team of 12 engineers deploying Gemini-powered microservices.
    """
    out = run_profile_stage({"raw_resume_text": sample})
    assert isinstance(out.profile, UserProfile)
    assert out.profile.email == "elena.rostova@techmail.com"
    assert len(out.profile.extracted_skills) > 0
    assert out.recruiter_gap_analysis["readiness_score"] >= 70


def test_scout_agent_missing_keys_and_exclusion_filtering():
    """Verify ScoutAgent handles missing search API keys gracefully and enforces negative keywords."""
    profile = UserProfile(
        headline="AI Platform Engineer",
        target_roles=["AI Platform Engineer"],
        location_preference="Remote",
        negative_keywords=["intern", "entry level"],
    )
    # Test with explicitly enabled channels, omitting Apify token
    inp = ScoutAgentInput(
        profile=profile,
        channels_enabled=["Ashby", "Apify"],  # Apify has no token provided
        max_workers=5,
    )
    out = run_scout_stage(inp)
    assert isinstance(out, ScoutAgentOutput)
    assert out.raw_jobs_found >= 0
    # Apify should be safely contained
    assert "Apify" not in out.failures_by_source or out.failures_by_source.get("Apify") is not None
    # No job should contain "intern"
    for j in out.filtered_jobs:
        assert "intern" not in j.title.lower()


def test_match_agent_scoring_and_recruiter_probability():
    """Verify MatchAgent calculates multi-dimensional fit scores and recruiter probabilities."""
    profile = UserProfile(
        headline="Senior AI Engineer",
        extracted_skills=["Python", "FastAPI", "Docker", "Gemini API"],
        years_of_experience="6+ years",
        location_preference="Remote",
    )
    high_match_job = JobPosting(
        title="Senior AI Engineer",
        company="Autonomous AI Corp",
        location="Remote",
        full_description="Requires Python, FastAPI, Docker, and Gemini API experience.",
        requirements=["Python", "FastAPI", "Docker", "Gemini API"],
        source_url="https://jobs.ashbyhq.com/example/1",
        is_direct_ats=True,
    )
    low_match_job = JobPosting(
        title="Cobol Mainframe Specialist",
        company="OldBank Corp",
        location="On-site",
        full_description="Maintenance of 1980s mainframe applications in COBOL.",
        requirements=["COBOL", "JCL"],
        source_url="https://jobs.example.com/2",
    )

    inp = MatchAgentInput(
        profile=profile,
        candidate_jobs=[high_match_job, low_match_job],
        enable_gemini_rerank=False,
    )
    out = run_match_stage(inp)
    assert isinstance(out, MatchAgentOutput)
    assert len(out.ranked_jobs) == 2
    # First job should be high match
    assert out.ranked_jobs[0].title == "Senior AI Engineer"
    assert out.ranked_jobs[0].fit_score > out.ranked_jobs[1].fit_score

    report = out.match_reports[out.ranked_jobs[0].id]
    assert isinstance(report, MatchReport)
    assert 0.0 <= report.probability_of_recruiter_response <= 1.0
    assert report.match_score >= 85.0


def test_report_agent_final_payload_and_digest():
    """Verify ReportAgent aggregates market insights and produces FinalReportPayload."""
    profile = UserProfile(headline="Staff Backend Engineer")
    job = JobPosting(
        title="Staff Backend Engineer",
        company="CloudScale",
        full_description="Distributed systems in Python and Go.",
        source_url="https://example.com/job",
        fit_score=94,
    )
    report = MatchReport(
        job_id=job.id,
        job_title=job.title,
        company=job.company,
        match_score=94.0,
        probability_of_recruiter_response=0.88,
        alignment_summary="Exceptional alignment with distributed architectures.",
    )
    inp = ReportAgentInput(
        profile=profile,
        ranked_jobs=[job],
        match_reports={job.id: report},
        telemetry={"total_scouted": 40, "channels": {"Ashby": 40}},
    )
    out = run_report_stage(inp)
    assert isinstance(out, ReportAgentOutput)
    assert isinstance(out.payload, FinalReportPayload)
    assert len(out.payload.top_matches) == 1
    assert "Staff Backend Engineer" in out.morning_digest_markdown


def test_doc_agent_tailored_artifacts():
    """Verify DocAgent synthesizes ATS-tailored CV and Cover Letter with high score."""
    profile = UserProfile(
        full_name="Alex Mercer",
        headline="Senior AI Engineer",
        extracted_skills=["Python", "FastAPI", "Gemini API"],
        years_of_experience="6+ years",
    )
    job = JobPosting(
        title="Senior AI Engineer",
        company="DeepMind",
        location="Remote",
        full_description="Build autonomous agents in Python with Gemini API.",
        source_url="https://deepmind.google/careers",
        matched_skills=["Python", "Gemini API"],
    )
    inp = DocAgentInput(user_profile=profile, job_posting=job, language="en")
    out = run_doc_stage(inp)
    assert isinstance(out, DocAgentOutput)
    assert out.cv_markdown is not None
    assert out.cover_letter_markdown is not None
    assert out.ats_compatibility_score is not None
    assert out.ats_compatibility_score >= 60


def test_multi_agent_job_pipeline_composite_execution():
    """Verify the end-to-end MultiAgentJobPipeline executes all stages synchronously."""
    pipeline = MultiAgentJobPipeline(api_key=None)
    profile = UserProfile(
        headline="AI Engineer",
        extracted_skills=["Python", "FastAPI"],
        location_preference="Remote",
    )
    res = pipeline.execute(
        existing_profile=profile,
        channels_enabled=["Ashby"],
        max_workers=4,
    )
    assert "profile_output" in res
    assert "scout_output" in res
    assert "match_output" in res
    assert "report_output" in res
    assert "final_payload" in res
    assert len(res["top_recommendations"]) > 0
    assert res["execution_time_seconds"] > 0
