"""
Semantic Matching & Geographic Location Alignment Engine.
Facade module that maintains 100% backward compatibility by re-exporting all
taxonomies, extractors, scoring engines, and reranking utilities.
"""

from .taxonomy import (
    ROLE_SYNONYMS,
    COMMON_TECH_STACK_KEYWORDS,
    COUNTRY_SYNONYMS,
    _COMPILED_COUNTRY_PATTERNS,
    _STOPWORDS_LOCATION,
    _SENIORITY_TOKENS,
    expand_role_synonyms,
)
from .extractors import (
    extract_tech_skills,
    extract_required_years_experience,
    extract_target_countries,
    check_job_country_match,
    determine_work_mode,
)
from .engine import (
    calculate_semantic_fit,
    calculate_quality_match,
    evaluate_role_match,
    extract_seniority_level,
    calculate_temporal_decay,
    get_channel_advantage_multiplier,
    calculate_gatekeeper_audit,
)
from .gatekeeper import evaluate_dealbreakers
from .callback_model import calculate_bayesian_callback_probability
from .reranker import (
    rerank_top_jobs_with_gemini,
)

__all__ = [
    "ROLE_SYNONYMS",
    "COMMON_TECH_STACK_KEYWORDS",
    "COUNTRY_SYNONYMS",
    "_COMPILED_COUNTRY_PATTERNS",
    "_STOPWORDS_LOCATION",
    "_SENIORITY_TOKENS",
    "expand_role_synonyms",
    "extract_tech_skills",
    "extract_required_years_experience",
    "extract_target_countries",
    "check_job_country_match",
    "determine_work_mode",
    "calculate_semantic_fit",
    "calculate_quality_match",
    "evaluate_role_match",
    "extract_seniority_level",
    "calculate_temporal_decay",
    "get_channel_advantage_multiplier",
    "calculate_gatekeeper_audit",
    "evaluate_dealbreakers",
    "calculate_bayesian_callback_probability",
    "rerank_top_jobs_with_gemini",
]
