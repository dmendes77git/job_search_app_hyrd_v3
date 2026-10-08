"""
Unit test suite for src/schemas.py (Pydantic models and Agent specifications).
"""

import pytest
from src.schemas import (
    UserProfile,
    EducationEntry,
    WorkExperience,
    JobPosting,
    MatchReport,
    FinalReportPayload,
    TailoredDocsRequest,
    TailoredDocsResponse,
    DocumentTypeEnum,
    WorkModeEnum,
    SeniorityLevelEnum,
    ApplicationStatusEnum,
    AGENT_ROLE_SPECS,
)


def test_user_profile_initialization_and_sync():
    """Verify UserProfile field validation, default synchronization, and to_dict."""
    edu = [
        EducationEntry(
            degree="M.Sc. in Computer Science",
            institution="Instituto Superior Técnico",
            graduation_year="2021",
        )
    ]
    profile = UserProfile(
        full_name="Carlos Silva",
        email="carlos.silva@example.pt",
        extracted_skills=["Python", "FastAPI", "Docker", "Gemini API"],
        experience_years=7.5,
        target_roles=["Senior AI Engineer", "Staff Backend Engineer"],
        location_preference="Portugal / Remote",
        education=edu,
        work_mode=WorkModeEnum.REMOTE_ONLY,
    )

    # Check field values
    assert profile.full_name == "Carlos Silva"
    assert profile.experience_years == 7.5
    assert "7+ years" in profile.years_of_experience
    assert profile.extracted_skills == ["Python", "FastAPI", "Docker", "Gemini API"]
    assert profile.core_skills == profile.extracted_skills
    assert profile.location == "Portugal / Remote"
    assert len(profile.education) == 1
    assert profile.education[0].institution == "Instituto Superior Técnico"

    # Verify dict representation for downstream compatibility
    d = profile.to_dict()
    assert isinstance(d, dict)
    assert d["full_name"] == "Carlos Silva"
    assert "core_skills" in d


def test_job_posting_normalization_and_aliases():
    """Verify JobPosting normalization of aliases (job_title, description, url)."""
    job = JobPosting(
        job_title="Lead AI Engineer",
        company="Anthropic",
        location="Remote",
        description="Lead research and multi-agent development.",
        requirements=["Python", "LLMs", "Distributed Systems"],
        salary_range="$220,000 - $300,000",
        url="https://jobs.lever.co/anthropic/123",
        source="Lever",
        is_direct_ats=True,
    )

    assert job.title == "Lead AI Engineer"
    assert job.company == "Anthropic"
    assert job.full_description == "Lead research and multi-agent development."
    assert job.source_url == "https://jobs.lever.co/anthropic/123"
    assert job.is_direct_ats is True
    assert job.application_status == ApplicationStatusEnum.SAVED

    d = job.to_dict()
    assert d["title"] == "Lead AI Engineer"
    assert d["description"] == job.full_description
    assert d["url"] == job.source_url
    assert d["company_size"] == "Scale-up / Enterprise"


def test_match_report_metrics_and_bounds():
    """Verify MatchReport validation bounds for match_score and probability."""
    report = MatchReport(
        job_id="job-uuid-123",
        job_title="Senior AI Engineer",
        company="TechCorp",
        match_score=92.5,
        probability_of_recruiter_response=0.85,
        key_skill_gaps=["Kubernetes"],
        alignment_summary="Exceptional alignment with Gemini API and distributed agent patterns.",
        matching_skills=["Python", "FastAPI", "Docker"],
        dimension_scores={"semantic_fit": 94.0, "seniority_fit": 90.0},
        recruiter_reasoning=["Strong 7+ years track record", "Direct ATS alignment"],
    )

    assert report.match_score == 92.5
    assert report.probability_of_recruiter_response == 0.85
    assert "Kubernetes" in report.key_skill_gaps
    assert report.recommended_action == "Apply Immediately"


def test_match_report_invalid_bounds():
    """Verify MatchReport raises ValidationError when scores exceed bounds."""
    with pytest.raises(Exception):
        MatchReport(
            job_id="1",
            job_title="Test",
            company="Test",
            match_score=150.0,  # Invalid: > 100
            probability_of_recruiter_response=0.5,
            alignment_summary="Exceeds score",
        )

    with pytest.raises(Exception):
        MatchReport(
            job_id="1",
            job_title="Test",
            company="Test",
            match_score=80.0,
            probability_of_recruiter_response=1.5,  # Invalid: > 1.0
            alignment_summary="Exceeds probability",
        )


def test_final_report_payload_aggregation():
    """Verify FinalReportPayload holds sorted job matches and telemetry."""
    job1 = JobPosting(
        title="Job 1",
        company="Corp 1",
        full_description="Desc 1",
        source_url="https://url1",
        fit_score=95,
    )
    job2 = JobPosting(
        title="Job 2",
        company="Corp 2",
        full_description="Desc 2",
        source_url="https://url2",
        fit_score=88,
    )

    payload = FinalReportPayload(
        candidate_id="cand-001",
        candidate_name="Carlos Silva",
        target_role="Senior AI Engineer",
        total_jobs_scouted=150,
        total_jobs_evaluated=60,
        top_matches=[job1, job2],
        search_channels_telemetry={"Ashby": 40, "LinkedIn": 25},
    )

    assert len(payload.top_matches) == 2
    assert payload.top_matches[0].fit_score >= payload.top_matches[1].fit_score
    assert payload.total_jobs_scouted == 150


def test_tailored_docs_request_and_response():
    """Verify TailoredDocsRequest and TailoredDocsResponse models."""
    profile = UserProfile(
        full_name="Alex Mercer",
        extracted_skills=["Python", "FastAPI"],
        target_roles=["Senior AI Engineer"],
    )
    job = JobPosting(
        title="Senior AI Engineer",
        company="OpenAI",
        full_description="Build agent platforms.",
        source_url="https://openai.com/careers/1",
    )

    req = TailoredDocsRequest(
        user_profile=profile,
        job_posting=job,
        language="pt-pt",
        document_types=[DocumentTypeEnum.CV, DocumentTypeEnum.COVER_LETTER],
    )
    assert req.language == "pt-pt"
    assert len(req.document_types) == 2

    res = TailoredDocsResponse(
        job_id=job.id,
        job_title=job.title,
        company=job.company,
        cv_markdown="# Alex Mercer CV\n## EXPERIÊNCIA",
        cover_letter_markdown="Exma. Equipa de Recrutamento...",
        ats_compatibility_score=98,
        language="pt-pt",
    )
    assert res.ats_compatibility_score == 98
    assert "EXPERIÊNCIA" in res.cv_markdown


def test_agent_role_specs_registry():
    """Verify all 5 required agents are formally registered with full specifications."""
    expected_agents = ["ProfileAgent", "ScoutAgent", "MatchAgent", "ReportAgent", "DocAgent"]
    for agent_name in expected_agents:
        assert agent_name in AGENT_ROLE_SPECS
        spec = AGENT_ROLE_SPECS[agent_name]
        assert spec.name == agent_name
        assert len(spec.assigned_tools) > 0
        assert spec.input_schema is not None
        assert spec.output_schema is not None
        assert spec.fallback_strategy is not None
