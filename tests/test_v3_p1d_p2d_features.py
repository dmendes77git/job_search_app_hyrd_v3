"""
Unit and integration test suite for Version 3 Features:
- P1-D: Real-Time Recruiter Readiness Radar & 1-Click Gap Remediation (profile_agent.py)
- P2-D: Market Salary Imputation & Total Rewards Equity Breakdown (salary_evaluator.py)
- Multi-Format Resume Ingestion (.md and normalize_resume_sections in file_parser.py)
"""

import io
import pytest
from src.schemas import UserProfile
from src.agents.profile_agent import (
    analyze_recruiter_gaps,
    auto_quantify_bullet,
)
from src.utils.salary_evaluator import (
    estimate_equity_grant,
    impute_market_salary,
    impute_market_salary_and_rewards,
    evaluate_job_salary,
)
from src.utils.file_parser import extract_text_from_file, normalize_resume_sections


# ============================================================================
# P1-D: Real-Time Recruiter Readiness Radar Tests
# ============================================================================

def test_recruiter_readiness_radar_comprehensive():
    """Verify recruiter gap analysis calculates radar metrics, action verbs, and ATS hygiene."""
    profile = UserProfile(
        full_name="Elena Rostova",
        headline="Staff Distributed Systems Architect",
        email="elena.rostova@techscale.io",
        phone="+1 (415) 890-1234",
        linkedin_url="https://linkedin.com/in/elenarostova",
        location="Remote",
        years_of_experience="9+ years",
        extracted_skills=["Python", "Go", "Kubernetes", "Distributed Systems", "Kafka", "PostgreSQL", "gRPC", "Docker"],
        experience_highlights=[
            "Architected high-throughput message streaming pipeline handling 4.5M events/second with 99.99% uptime.",
            "Spearheaded database partitioning initiative reducing p99 query latency by 42% and saving $32,000 monthly.",
            "Engineered automated failover system cutting mean time to recovery (MTTR) by 75%.",
        ],
        raw_resume_text="Elena Rostova\nStaff Systems Architect\nArchitected streaming systems.\nSpearheaded database partitions.\nEngineered failover.",
    )

    audit = analyze_recruiter_gaps(profile)

    # Core scores
    assert audit["readiness_score"] >= 85
    assert "readiness_label" in audit
    assert len(audit["strengths"]) >= 3

    # Feature P1-D Radar metrics
    assert "radar_metrics" in audit
    radar = audit["radar_metrics"]
    assert "Action Verb Power" in radar
    assert "Metric Quantification" in radar
    assert "ATS Formatting Hygiene" in radar
    assert "Contact Completeness" in radar
    assert "Technical Competency Depth" in radar

    assert audit["action_verb_power_index"] >= 80.0
    assert audit["quantification_density_pct"] == 100.0  # All 3 bullets have metrics
    assert audit["ats_hygiene_score"] >= 90
    assert isinstance(audit["actionable_remediations"], list)


def test_recruiter_readiness_radar_gaps_and_remediations():
    """Verify detection of passive verbs, missing metrics, and missing contact info."""
    profile_weak = UserProfile(
        full_name="Junior Dev",
        headline="Junior Developer",
        email="",  # Missing email
        phone="",  # Missing phone
        linkedin_url="",  # Missing linkedin
        location="On-site",
        years_of_experience="1 year",
        extracted_skills=["HTML", "CSS"],
        experience_highlights=[
            "Assisted with bug fixing and worked on code maintenance.",
            "Helped team members with daily standup tasks.",
        ],
        raw_resume_text="★ Non standard character ★\nAssisted with bugs.\n| Col 1 | Col 2 | Col 3 | Col 4 | Col 5 | Col 6 | Col 7 | Col 8 | Col 9 |\n|---|---|---|---|---|---|---|---|---|",
    )

    audit = analyze_recruiter_gaps(profile_weak)
    assert audit["readiness_score"] <= 60
    assert audit["quantification_density_pct"] == 0.0  # Zero bullets with metrics
    assert audit["action_verb_power_index"] <= 40.0   # Passive verbs present
    assert audit["ats_hygiene_score"] < 80            # Special unicode and table artifacts

    # Remediation suggestions present
    remediations = audit["actionable_remediations"]
    assert any("Email" in r["gap"] for r in remediations)
    assert any("Auto-Quantify" in r["action"] for r in remediations)


def test_auto_quantify_bullet_deterministic():
    """Verify 1-click bullet auto-remediation transforms passive verbs into quantified STAR statements."""
    passive_bullet = "Worked on backend API services and database queries."
    result = auto_quantify_bullet(passive_bullet, context="Backend Engineering")

    assert result["status"] in ("success_deterministic", "success_gemini")
    assert "Architected" in result["quantified"] or "Engineered" in result["quantified"]
    assert "%" in result["quantified"] or "daily" in result["quantified"] or "$" in result["quantified"]
    assert len(result["metrics_added"]) > 0
    assert result["verb_upgraded"] != ""


def test_auto_quantify_bullet_empty():
    """Verify empty input handling in auto-quantify."""
    result = auto_quantify_bullet("")
    assert result["status"] == "empty_input"
    assert result["quantified"] == ""


# ============================================================================
# P2-D: Market Salary Imputation & Total Rewards Equity Tests
# ============================================================================

def test_impute_market_salary_tech_premium():
    """Verify predictive salary imputation applies location calibration and high-demand stack premium."""
    # Scenario A: Senior AI Engineer in Germany
    imputed_de = impute_market_salary(
        job_title="Senior AI Engineer",
        target_location="Germany",
        tech_stack=["Python", "PyTorch", "LLMs", "Distributed Systems"],
        exp_level_str="Senior",
    )

    assert imputed_de["location_name"] == "Germany"
    assert imputed_de["location_factor"] < 1.0  # EU geographic adjustment
    assert imputed_de["tech_premium_applied"] is True
    assert len(imputed_de["premium_skills"]) > 0
    assert imputed_de["currency_symbol"] == "€"
    assert "Estimated:" in imputed_de["display_badge"]
    assert "(Market Imputed)" in imputed_de["display_badge"]

    # Scenario B: Lead Staff Engineer in US
    imputed_us = impute_market_salary(
        job_title="Lead Staff Infrastructure Architect",
        target_location="San Francisco, CA",
        tech_stack=["Kubernetes", "Go", "Cloud Architecture"],
        exp_level_str="8+ years",
    )
    assert imputed_us["tier"] == "lead_staff"
    assert imputed_us["imputed_min_usd"] >= 160000.0


def test_estimate_equity_grant_across_stages():
    """Verify startup stage detection and equity grant bracket assignment."""
    # Pre-Seed / Seed Lead
    eq_seed = estimate_equity_grant("Early stage pre-seed stealth startup", seniority_tier="lead_staff", role_title="Lead Engineer")
    assert eq_seed["stage"] == "Pre-Seed"
    assert "%" in eq_seed["equity_band"]
    assert "Stock Options" in eq_seed["equity_type"]

    # Series A Senior
    eq_a = estimate_equity_grant("Series A enterprise SaaS company", seniority_tier="senior", role_title="Senior Engineer")
    assert eq_a["stage"] == "Series A"
    assert "0.08%" in eq_a["equity_band"] or "0.20%" in eq_a["equity_band"]

    # Series C+
    eq_c = estimate_equity_grant("Series C growth scaleup", seniority_tier="mid", role_title="Software Engineer")
    assert eq_c["stage"] == "Series C+"
    assert "%" in eq_c["equity_band"]

    # Public Enterprise
    eq_public = estimate_equity_grant("Global public enterprise (NASDAQ)", seniority_tier="senior", role_title="Senior Engineer")
    assert eq_public["stage"] == "Public / Enterprise"
    assert "RSUs" in eq_public["equity_type"]
    assert "$" in eq_public["equity_band"]


def test_impute_market_salary_and_rewards_disclosed_vs_imputed():
    """Verify unified imputation returns correct badges and total rewards summaries."""
    # Undisclosed salary -> Imputed
    res_undisclosed = impute_market_salary_and_rewards(
        job_salary_str="Competitive Salary + Benefits",
        job_title="Senior Machine Learning Engineer",
        company="Nexus Scale (Series B)",
        job_description="Developing agentic systems with PyTorch.",
        target_location="Remote",
    )
    assert res_undisclosed["is_imputed"] is True
    assert "Market Imputed" in res_undisclosed["display_badge"]
    assert "Base +" in res_undisclosed["total_rewards_summary"]
    assert "Stock Options" in res_undisclosed["total_rewards_summary"]

    # Disclosed salary -> Not imputed
    res_disclosed = impute_market_salary_and_rewards(
        job_salary_str="$175,000 - $210,000",
        job_title="Staff AI Architect",
        company="Stripe",
        job_description="Public fintech platform.",
    )
    assert res_disclosed["is_imputed"] is False
    assert "Disclosed: $175k - $210k" in res_disclosed["display_badge"]


def test_evaluate_job_salary_p2d_enrichment():
    """Verify evaluate_job_salary includes is_imputed, imputed_salary_badge, and equity_breakdown."""
    eval_undisclosed = evaluate_job_salary("Competitive", job_title="Senior Backend Engineer")
    assert eval_undisclosed["is_imputed"] is True
    assert "(Market Imputed)" in eval_undisclosed["imputed_salary_badge"]
    assert "equity_breakdown" in eval_undisclosed

    eval_disclosed = evaluate_job_salary("$160,000 - $190,000", job_title="Senior Backend Engineer")
    assert eval_disclosed["is_imputed"] is False
    assert "Disclosed:" in eval_disclosed["imputed_salary_badge"]
    assert "equity_breakdown" in eval_disclosed


# ============================================================================
# Multi-Format Ingestion & Normalizer Tests
# ============================================================================

def test_normalize_resume_sections():
    """Verify semantic section extraction from markdown/plain text resume."""
    raw_md = """# Maya Lin
Staff Systems Engineer
Email: maya.lin@dev.com

## PROFESSIONAL SUMMARY
Seasoned systems architect with 8 years building distributed databases.

## CORE SKILLS
- Rust, Go, Python, Distributed Systems, Raft, Paxos

## WORK EXPERIENCE
### Principal Engineer | ScaleBase
- Designed replicated log storage handling 2M IOPS.

## EDUCATION
B.S. in Computer Science, Stanford University

## CERTIFICATIONS
AWS Solutions Architect Professional
"""
    sections = normalize_resume_sections(raw_md)
    assert "Seasoned systems architect" in sections["summary"]
    assert "Rust" in sections["skills"]
    assert "ScaleBase" in sections["experience"]
    assert "Stanford" in sections["education"]
    assert "AWS Solutions Architect" in sections["certifications"]


def test_file_parser_markdown_support():
    """Verify extract_text_from_file handles .md uploaded buffers cleanly."""
    class FakeUploadedFile:
        def __init__(self, name: str, content: bytes):
            self.name = name
            self._content = content
        def getvalue(self):
            return self._content

    md_file = FakeUploadedFile("resume.md", b"# Candidate Resume\nExperience with Python and Docker.")
    extracted = extract_text_from_file(md_file)
    assert "Candidate Resume" in extracted
    assert "Python" in extracted
