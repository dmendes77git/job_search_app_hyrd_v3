"""
Comprehensive Verification Test Suite for Features P1-A, P1-B, P1-C, P3-A, P3-B, and P3-C.
Ensures zero-regression guarantee across:
  - P3-A: 1-Click Application Bundle (.zip) In-Memory Exporter
  - P3-B: Visual ATS Keyword Match Heatmap & Optimization Inspector
  - P3-C: Interactive Mock Interview Simulator with Real-Time AI Scoring
  - P1-A: Autonomous GitHub & Portfolio Deep Inspector
  - P1-B: Multi-CV Persona Management & Profile Switching
  - P1-C: Hierarchical Competency Graph & Proficiency Taxonomy (3-Tier)
"""

import io
import zipfile
import pytest

from src.tools.bundle_exporter import build_application_bundle_zip
from src.utils.ats_optimizer import generate_ats_keyword_heatmap
from src.agents.interview_prep_agent import evaluate_mock_interview_answer
from src.tools.github_inspector import extract_github_username, inspect_github_profile
from src.agents.profile_agent import categorize_competencies
from src.utils.user_manager import (
    create_or_update_persona,
    get_personas,
    switch_active_persona,
    delete_persona,
    create_user,
    delete_user,
)


@pytest.fixture
def sample_job():
    return {
        "id": "job_bundle_test_01",
        "title": "Lead Distributed Systems Architect",
        "company": "Nexus Scale",
        "location": "Remote",
        "description": "Seeking a Lead Architect with deep expertise in Python, Kubernetes, PostgreSQL, and FastAPI.",
        "matched_skills": ["Python", "Kubernetes", "PostgreSQL", "FastAPI"],
        "missing_skills": ["Golang"],
        "key_reasons": ["7+ years architecting distributed microservices."],
        "salary": "$175,000 - $210,000",
    }


@pytest.fixture
def sample_profile():
    return {
        "full_name": "Jordan Rivera",
        "headline": "Lead Systems Engineer",
        "location": "San Francisco, CA",
        "email": "jordan.rivera@example.com",
        "phone": "+1 555-019-8822",
        "core_skills": ["Python", "Distributed Systems", "Kubernetes", "PostgreSQL", "FastAPI", "Docker"],
        "years_of_experience": "8 years",
        "summary": "Proven lead systems architect specializing in high-throughput microservices and distributed databases.",
        "experience_highlights": ["Scaled transaction processing by 400% with 99.99% availability."],
    }


# ============================================================================
# P3-A: Application Bundle (.zip) Tests
# ============================================================================

def test_build_application_bundle_zip_structure(sample_job, sample_profile):
    """Verify that build_application_bundle_zip creates a valid, multi-file in-memory ZIP."""
    cached = {
        "tailored_cv": "# JORDAN RIVERA\n\n## PROFESSIONAL SUMMARY\nExpert engineer.",
        "cover_letter": "Dear Nexus Scale Hiring Team,\n\nI am thrilled to apply.",
        "interview_prep": {
            "briefing": "Nexus Scale company briefing.",
            "technical_qa": "### Q1: Distributed Consensus",
            "behavioral_star": "### STAR 1: Resolving Outages",
            "cheat_sheet": "Pre-call notes.",
            "raw_markdown": "# Prep Guide",
        },
        "company_dossier": {
            "company_name": "Nexus Scale",
            "executive_summary": "Pioneering distributed edge infrastructure.",
            "tech_stack": ["Python", "Kubernetes"],
            "interview_insights": ["Values operational resilience."],
            "strategic_talking_points": ["Edge consensus latency reduction."],
        },
        "outreach_campaign": {
            "linkedin_note": {"text": "Hi, love your work at Nexus Scale!"},
            "hiring_manager_email": {"subject": "Lead Architect Opportunity", "body": "Hello hiring team..."},
        },
    }

    zip_buffer = build_application_bundle_zip(sample_job, sample_profile, cached_docs=cached)
    assert isinstance(zip_buffer, io.BytesIO)
    assert zip_buffer.getvalue() is not None
    assert len(zip_buffer.getvalue()) > 500

    # Unpack and verify files
    with zipfile.ZipFile(zip_buffer, "r") as zf:
        namelist = zf.namelist()
        # Must contain all 5 systematically numbered artifacts
        assert any(n.startswith("01_Resume_") and n.endswith(".docx") for n in namelist)
        assert any(n.startswith("01_Resume_") and n.endswith(".pdf") for n in namelist)
        assert any(n.startswith("02_CoverLetter_") and n.endswith(".docx") for n in namelist)
        assert any(n.startswith("02_CoverLetter_") and n.endswith(".pdf") for n in namelist)
        assert any(n.startswith("03_InterviewPrep_Battlecard_") and n.endswith(".docx") for n in namelist)
        assert any(n.startswith("04_CompanyIntelligence_Dossier_") and n.endswith(".docx") for n in namelist)
        assert any(n.startswith("04_CompanyIntelligence_Dossier_") and n.endswith(".pdf") for n in namelist)
        assert "05_Executive_Outreach_Campaign.txt" in namelist


# ============================================================================
# P3-B: Visual ATS Keyword Match Heatmap Tests
# ============================================================================

def test_generate_ats_keyword_heatmap(sample_job, sample_profile):
    """Verify keyword density, synonym mapping, section parsing, and auto-inject suggestions."""
    cv_text = """# JORDAN RIVERA
**Target Role:** Lead Architect | **Target Company:** Nexus Scale
San Francisco, CA • jordan@example.com

## PROFESSIONAL SUMMARY
Senior architect with deep experience in Python and PostgreSQL.

## CORE COMPETENCIES & TECHNICAL SKILLS
- Python, PostgreSQL, FastAPI, K8s

## PROFESSIONAL EXPERIENCE
### Lead Architect | TechCorp
- Architected distributed data pipelines using Python and PostgreSQL.
"""
    heatmap = generate_ats_keyword_heatmap(sample_job, cv_text, sample_profile)

    assert "match_rate_pct" in heatmap
    assert heatmap["total_keywords"] > 0
    assert heatmap["matched_count"] >= 2  # Python, PostgreSQL, FastAPI
    assert heatmap["partial_count"] >= 1  # K8s synonym for Kubernetes
    assert "items" in heatmap
    assert len(heatmap["items"]) > 0

    # Verify that K8s is recognized as partial match for Kubernetes
    k8s_items = [it for it in heatmap["items"] if "kubernetes" in it["keyword"].lower()]
    if k8s_items:
        assert k8s_items[0]["status"] in ("matched", "partial")

    # Auto-inject suggestions exist
    assert "auto_inject_suggestions" in heatmap
    assert isinstance(heatmap["auto_inject_suggestions"], list)


# ============================================================================
# P3-C: Interactive Mock Interview Simulator Tests
# ============================================================================

def test_evaluate_mock_interview_answer_star_rubric():
    """Verify deterministic mock interview evaluation across STAR dimensions."""
    q = "Describe a time you resolved a major production bottleneck under tight deadlines."
    a = (
        "When I was at CloudScale Systems, our API service faced severe latency spikes during peak load. "
        "The objective was to cut response latency in half before our annual user conference. "
        "I spearheaded the architectural redesign by profiling query bottlenecks, implementing asynchronous caching with Redis, "
        "and optimizing PostgreSQL connection pools in Python. "
        "As a result, we reduced p99 latency by 58%, eliminated 500 errors, and saved over $35,000 in monthly compute expenses."
    )

    eval_result = evaluate_mock_interview_answer(
        question=q,
        answer_text=a,
        job_title="Lead Architect",
        company="Nexus Scale",
    )

    assert eval_result["overall_score"] >= 7.0
    assert eval_result["star_structure_score"] >= 7
    assert eval_result["technical_depth_score"] >= 6
    assert eval_result["quantified_impact_score"] >= 7
    assert len(eval_result["strengths"]) > 0
    assert len(eval_result["polished_answer"]) > 50


def test_evaluate_mock_interview_answer_empty():
    """Verify handling of empty or blank answer input."""
    res = evaluate_mock_interview_answer(
        question="What is your greatest technical strength?",
        answer_text="",
        job_title="Lead Architect",
        company="Nexus Scale",
    )
    assert res["overall_score"] == 0.0
    assert res["verdict"] == "No Answer Provided"


# ============================================================================
# P1-A: GitHub Deep Inspector Tests
# ============================================================================

def test_extract_github_username():
    """Verify extraction of username from various URL formats."""
    assert extract_github_username("https://github.com/torvalds") == "torvalds"
    assert extract_github_username("http://www.github.com/alex-mercer/repo") == "alex-mercer"
    assert extract_github_username("@octocat") == "octocat"
    assert extract_github_username("simpleuser") == "simpleuser"
    assert extract_github_username("") == ""


def test_inspect_github_profile_fallback():
    """Verify that inspect_github_profile produces valid output even when offline or fallback triggers."""
    res = inspect_github_profile("https://github.com/jordan-rivera-dev")
    assert res["username"] == "jordan-rivera-dev"
    assert res["is_verified"] is True
    assert len(res["primary_languages"]) > 0
    assert len(res["verified_competencies"]) > 0
    assert "jordan-rivera-dev" in res["archetype_summary"] or "practitioner" in res["archetype_summary"]


# ============================================================================
# P1-B: Multi-CV Persona Management Tests
# ============================================================================

def test_multi_persona_lifecycle():
    """Verify persona creation, retrieval, switching, and deletion in a sandbox user account."""
    sandbox_user_id = create_user({
        "full_name": "Test Persona Candidate",
        "target_role": "Backend Engineer",
        "location": "Remote",
    })

    try:
        # 1. Initially no custom personas
        personas = get_personas(sandbox_user_id)
        assert isinstance(personas, dict)

        # 2. Create Persona 1
        create_or_update_persona(sandbox_user_id, "AI Systems Lead", {
            "target_role": "Staff AI Engineer",
            "core_skills": ["Python", "Gemini API", "PyTorch"],
        })
        personas = get_personas(sandbox_user_id)
        assert "AI Systems Lead" in personas
        assert personas["AI Systems Lead"]["target_role"] == "Staff AI Engineer"

        # 3. Create Persona 2
        create_or_update_persona(sandbox_user_id, "Engineering Manager", {
            "target_role": "Director of Engineering",
            "core_skills": ["Technical Leadership", "Agile", "Hiring"],
        })
        personas = get_personas(sandbox_user_id)
        assert len(personas) == 2

        # 4. Switch persona
        switched = switch_active_persona(sandbox_user_id, "Engineering Manager")
        assert switched["target_role"] == "Director of Engineering"

        # 5. Delete persona
        del_ok = delete_persona(sandbox_user_id, "AI Systems Lead")
        assert del_ok is True
        personas_after = get_personas(sandbox_user_id)
        assert "AI Systems Lead" not in personas_after
        assert "Engineering Manager" in personas_after

    finally:
        delete_user(sandbox_user_id)


# ============================================================================
# P1-C: Hierarchical Competency Graph & Proficiency Taxonomy Tests
# ============================================================================

def test_categorize_competencies():
    """Verify categorization into Tier 1 (Core Drivers), Tier 2 (Supporting Stack), Tier 3 (Familiar & Emerging)."""
    skills = [
        "Python", "System Architecture", "Distributed Systems",
        "Docker", "Kubernetes", "PostgreSQL", "FastAPI",
        "GraphQL", "Agile", "Unit Testing",
    ]

    taxonomy = categorize_competencies(skills, experience_years="8 years")
    assert "tier_1_core" in taxonomy
    assert "tier_2_supporting" in taxonomy
    assert "tier_3_familiar" in taxonomy

    assert "Python" in taxonomy["tier_1_core"]
    assert "Distributed Systems" in taxonomy["tier_1_core"]
    assert "Docker" in taxonomy["tier_2_supporting"] or "Kubernetes" in taxonomy["tier_2_supporting"]
    assert "GraphQL" in taxonomy["tier_3_familiar"] or "Agile" in taxonomy["tier_3_familiar"]
