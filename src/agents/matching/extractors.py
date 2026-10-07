"""
Entity & Feature Extraction Functions for Candidate-Job Matching.
Extracts technology skills, required years of experience, geographic eligibility,
and work mode indicators from unstructured job postings.
"""

import functools
import re
from typing import Any, Dict, List, Optional, Tuple

from .taxonomy import (
    COMMON_TECH_STACK_KEYWORDS,
    _COMPILED_COUNTRY_PATTERNS,
    _STOPWORDS_LOCATION,
)


def extract_tech_skills(text: str) -> List[str]:
    """
    Extract recognized technology and engineering stack skills from a text body.
    """
    if not text:
        return []
    text_lower = text.lower()
    found = []
    for kw in COMMON_TECH_STACK_KEYWORDS:
        pattern = r"\b" + re.escape(kw) + r"\b"
        if re.search(pattern, text_lower):
            found.append(kw.title() if len(kw) > 3 else kw.upper())
    return list(dict.fromkeys(found))


def extract_required_years_experience(text: str) -> Optional[int]:
    """
    Extract required years of experience integer from job posting text.
    Handles '5+ years', '3-5 years', 'minimum 7 years of experience', etc.
    """
    if not text:
        return None
    m = re.search(
        r"\b(\d{1,2})\+?\s*(?:-\s*\d{1,2})?\s*(?:to\s*\d{1,2}\s*)?(?:years?|yrs?)(?:\s+of)?(?:\s+(?:relevant|hands-on|professional|work)?\s*experience)?\b",
        text.lower(),
    )
    if m:
        try:
            return int(m.group(1))
        except ValueError:
            return None
    return None


@functools.lru_cache(maxsize=256)
def extract_target_countries(location_text: str) -> List[str]:
    """
    Extract standardized country names from a user's location input string.
    Returns list of lowercase country keys e.g. ['germany', 'united kingdom'].
    Cached for fast repeated evaluation during bulk scraping.
    """
    if not location_text:
        return []
    lt = location_text.lower()
    found = set()

    for country, patterns in _COMPILED_COUNTRY_PATTERNS.items():
        for pat in patterns:
            if pat.search(lt):
                found.add(country)
                break

    # If no predefined country matched, extract significant tokens
    if not found:
        words = [w.strip() for w in re.split(r"[,;/\-]+", lt) if len(w.strip()) > 2]
        for w in words:
            if w not in _STOPWORDS_LOCATION:
                found.add(w)

    # Disambiguate California "ca" vs Canada: If "united states" is present and "canada" was only matched by "ca"
    if "united states" in found and "canada" in found:
        if not any(
            w in lt
            for w in [
                "canada",
                "toronto",
                "vancouver",
                "montreal",
                "ottawa",
                "calgary",
                "ontario",
                "quebec",
                "alberta",
            ]
        ):
            found.remove("canada")

    return sorted(list(found))


def check_job_country_match(
    job_location: str, target_countries: List[str]
) -> Tuple[bool, Optional[str]]:
    """
    Check if a job's physical location matches one of the candidate's target countries/cities.
    Returns (is_match, matched_country_name).
    """
    if not target_countries:
        return True, None

    jl = job_location.lower()
    for country in target_countries:
        patterns = _COMPILED_COUNTRY_PATTERNS.get(country)
        if patterns:
            for pat in patterns:
                if pat.search(jl):
                    return True, country.title()
        else:
            # Custom city or unrecognized country token
            if country in jl:
                return True, country.title()

    # Generic substring match fallback
    for country in target_countries:
        if country in jl:
            return True, country.title()

    return False, None


def determine_work_mode(job: Dict[str, Any]) -> Tuple[str, bool, bool, bool]:
    """
    Determine if a job is Remote, Hybrid, or On-site.
    Returns: (mode_label, is_remote, is_hybrid, is_onsite)
    """
    raw_text = (
        job.get("title", "")
        + " "
        + job.get("location", "")
        + " "
        + job.get("job_type", "")
        + " "
        + job.get("description", "")
        + " "
        + " ".join(job.get("tags", []))
    ).lower()

    is_explicit_remote = (
        job.get("remote") is True
        or "remote" in raw_text
        or "remoto" in raw_text
        or "teletrabalho" in raw_text
        or "anywhere" in raw_text
        or "worldwide" in raw_text
        or "work from home" in raw_text
    )

    is_explicit_hybrid = (
        "hybrid" in raw_text
        or "híbrido" in raw_text
        or "hibrido" in raw_text
    )

    loc = job.get("location") or "General"
    if is_explicit_hybrid:
        return f"Hybrid ({loc})", True, True, False
    elif is_explicit_remote:
        return f"Remote ({loc})", True, False, False
    else:
        return f"On-site ({loc})", False, False, True
