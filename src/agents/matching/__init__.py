"""
Matching and semantic scoring module for candidate job fit.
"""

from .scoring import (
    COUNTRY_SYNONYMS,
    ROLE_SYNONYMS,
    COMMON_TECH_STACK_KEYWORDS,
    extract_target_countries,
    check_job_country_match,
    determine_work_mode,
    calculate_semantic_fit,
    evaluate_role_match,
    expand_role_synonyms,
    extract_tech_skills,
    extract_required_years_experience,
    evaluate_dealbreakers,
    calculate_bayesian_callback_probability,
    rerank_top_jobs_with_gemini,
)

__all__ = [
    "COUNTRY_SYNONYMS",
    "ROLE_SYNONYMS",
    "COMMON_TECH_STACK_KEYWORDS",
    "extract_target_countries",
    "check_job_country_match",
    "determine_work_mode",
    "calculate_semantic_fit",
    "evaluate_role_match",
    "expand_role_synonyms",
    "extract_tech_skills",
    "extract_required_years_experience",
    "evaluate_dealbreakers",
    "calculate_bayesian_callback_probability",
    "rerank_top_jobs_with_gemini",
]


