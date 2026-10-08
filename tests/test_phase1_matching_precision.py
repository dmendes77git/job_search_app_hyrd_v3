"""
Unit tests for Phase 1 Matching Precision Features:
- P2-A: Configurable Hard Deal-Breakers Engine (gatekeeper.py)
- P2-B: Cross-Source Fuzzy Deduplication (job_deduplicator.py)
- P2-C: Empirical Bayesian Callback Model (callback_model.py)
"""

import pytest
from src.agents.matching.gatekeeper import evaluate_dealbreakers
from src.utils.job_deduplicator import deduplicate_jobs, normalize_company_name, normalize_job_title
from src.agents.matching.callback_model import calculate_bayesian_callback_probability


def test_dealbreakers_visa_sponsorship():
    """Verify strict visa sponsorship dealbreaker triggers on explicit no-sponsorship text."""
    job = {
        "title": "Senior Backend Engineer",
        "company": "Enterprise Corp",
        "description": "We are seeking a senior engineer. Note: We will not sponsor visas for this role.",
    }
    profile_requires_visa = {
        "requires_visa_sponsorship": True,
        "summary": "Experienced backend developer",
    }
    profile_no_visa_needed = {
        "requires_visa_sponsorship": False,
        "summary": "Experienced backend developer",
    }

    audit_fail = evaluate_dealbreakers(job, profile_requires_visa)
    assert audit_fail["is_disqualified"] is True
    assert audit_fail["visa_sponsorship_pass"] is False
    assert audit_fail["dealbreaker_type"] == "visa_sponsorship"

    audit_pass = evaluate_dealbreakers(job, profile_no_visa_needed)
    assert audit_pass["is_disqualified"] is False
    assert audit_pass["visa_sponsorship_pass"] is True


def test_dealbreakers_strict_work_mode():
    """Verify strict work mode dealbreaker rejects on-site/hybrid when candidate is Remote Only."""
    job_onsite = {
        "title": "Software Engineer",
        "company": "Berlin Tech GmbH",
        "description": "Office attendance required 3 days a week in Berlin. Hybrid role.",
        "location": "Berlin, Germany",
    }
    profile_strict_remote = {
        "work_mode": "Remote Only",
        "strict_work_mode": True,
        "location_preference": "Remote",
    }
    profile_flexible = {
        "work_mode": "Remote Only",
        "strict_work_mode": False,
        "location_preference": "Remote",
    }

    audit_strict = evaluate_dealbreakers(job_onsite, profile_strict_remote)
    assert audit_strict["is_disqualified"] is True
    assert audit_strict["dealbreaker_type"] == "work_mode_mismatch"

    audit_flex = evaluate_dealbreakers(job_onsite, profile_flexible)
    # When flexible, it's not a hard dealbreaker
    assert audit_flex["dealbreaker_type"] != "work_mode_mismatch"


def test_dealbreakers_strict_salary_floor():
    """Verify strict salary floor rejects positions where max salary is below minimum preference."""
    job_low_salary = {
        "title": "Staff Engineer",
        "company": "Budget Co",
        "description": "Exciting role with modern tech.",
        "salary": "$90,000 - $110,000",
    }
    profile_strict_floor = {
        "preferred_salary_min": 150000.0,
        "strict_salary_floor": True,
    }

    audit = evaluate_dealbreakers(job_low_salary, profile_strict_floor)
    assert audit["is_disqualified"] is True
    assert audit["salary_floor_pass"] is False
    assert audit["dealbreaker_type"] == "salary_below_floor"


def test_dealbreakers_negative_keywords():
    """Verify negative keywords in job title trigger immediate disqualification."""
    job_intern = {
        "title": "Summer AI Intern",
        "company": "Tech Corp",
        "description": "Internship for students.",
    }
    profile = {
        "negative_keywords": ["intern", "junior"],
    }
    audit = evaluate_dealbreakers(job_intern, profile)
    assert audit["is_disqualified"] is True
    assert audit["negative_keywords_pass"] is False
    assert audit["dealbreaker_type"] == "negative_keyword"


def test_cross_source_deduplication():
    """Verify fuzzy deduplication collapses cross-posted jobs and canonicalizes to Direct ATS."""
    jobs = [
        {
            "id": "indeed_123",
            "title": "Senior AI Engineer (Remote)",
            "company": "Toast, Inc.",
            "source": "indeed",
            "salary": "$160,000 - $180,000",
            "full_description": "Indeed snippet",
        },
        {
            "id": "greenhouse_456",
            "title": "Senior AI Engineer",
            "company": "Toast",
            "source": "greenhouse",
            "salary": "Competitive",
            "full_description": "Comprehensive direct greenhouse job requisition description with requirements.",
        },
        {
            "id": "zip_789",
            "title": "Senior AI Engineer - Remote",
            "company": "Toast Inc",
            "source": "ziprecruiter",
            "salary": "$165,000",
            "full_description": "Zip recruiter posting",
        },
        {
            "id": "linear_999",
            "title": "Product Designer",
            "company": "Linear",
            "source": "ashby",
            "salary": "$150,000",
            "full_description": "Design systems lead",
        },
    ]

    deduped, metrics = deduplicate_jobs(jobs)
    assert metrics["total_input"] == 4
    assert metrics["unique_output"] == 2  # Toast + Linear
    assert metrics["duplicates_removed"] == 2
    assert metrics["cross_listed_clusters"] == 1

    # Verify canonical record for Toast was chosen as Greenhouse (Direct ATS)
    toast_job = next(j for j in deduped if "Toast" in j["company"])
    assert toast_job["source"] == "greenhouse"
    assert toast_job["cross_listed"] is True
    assert "indeed" in toast_job["merged_sources"]
    # Salary was backfilled from secondary sources since Greenhouse had 'Competitive'
    assert any(s in toast_job["salary"] for s in ["$160,000", "$165,000"])


def test_bayesian_callback_probability():
    """Verify Bayesian callback calculation behaves according to empirical institutional properties."""
    # Scenario A: High fit, Direct ATS, fresh posting, zero gaps
    res_high = calculate_bayesian_callback_probability(
        fit_score=94.0,
        days_posted=1,
        source="greenhouse",
        is_direct_ats=True,
        missing_skills_count=0,
        seniority_delta=0,
        is_target_company=True,
    )
    assert res_high["probability_of_response"] >= 0.70
    assert res_high["interview_likelihood_pct"] >= 70.0
    assert any("Early Applicant" in d for d in res_high["diagnostics"])

    # Scenario B: Low fit, Aggregator, stale posting (30 days), 4 gaps
    res_low = calculate_bayesian_callback_probability(
        fit_score=50.0,
        days_posted=30,
        source="indeed",
        is_direct_ats=False,
        missing_skills_count=4,
        seniority_delta=2,
    )
    assert res_low["probability_of_response"] <= 0.25
    assert res_low["interview_likelihood_pct"] <= 25.0
    assert any("Core Skill Gaps" in d for d in res_low["diagnostics"])
