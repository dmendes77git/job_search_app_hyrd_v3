"""
Matching and semantic scoring module for candidate job fit.
"""

from .scoring import (
    COUNTRY_SYNONYMS,
    extract_target_countries,
    check_job_country_match,
    determine_work_mode,
    calculate_semantic_fit,
    evaluate_role_match,
)

__all__ = [
    "COUNTRY_SYNONYMS",
    "extract_target_countries",
    "check_job_country_match",
    "determine_work_mode",
    "calculate_semantic_fit",
    "evaluate_role_match",
]

