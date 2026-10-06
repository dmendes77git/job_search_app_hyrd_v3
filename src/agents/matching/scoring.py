"""
Semantic Matching & Geographic Location Alignment Engine.
Scores candidate profiles against job postings across title alignment,
skill overlap, work mode preferences, and geographic eligibility.
"""

import functools
import re
from typing import Any, Dict, List, Optional, Tuple

# Pre-defined country and major global city synonyms for geographic matching
COUNTRY_SYNONYMS: Dict[str, List[str]] = {
    "germany": ["germany", "deutschland", "berlin", "munich", "münchen", "hamburg", "frankfurt", "cologne", "köln", "stuttgart", "düsseldorf", "freiburg", "de"],
    "united kingdom": ["united kingdom", "uk", "great britain", "england", "scotland", "wales", "london", "manchester", "birmingham", "edinburgh", "bristol", "cambridge", "oxford", "leeds", "gb"],
    "united states": ["united states", "usa", "us", "u.s.", "america", "new york", "san francisco", "california", "texas", "austin", "seattle", "boston", "chicago", "los angeles", "denver", "atlanta", "nyc", "sf", "florida", "miami"],
    "canada": ["canada", "toronto", "vancouver", "montreal", "ottawa", "calgary", "ontario", "quebec", "british columbia", "alberta", "ca"],
    "netherlands": ["netherlands", "holland", "amsterdam", "rotterdam", "utrecht", "hague", "eindhoven", "nl"],
    "france": ["france", "paris", "lyon", "toulouse", "marseille", "bordeaux", "nantes", "fr"],
    "spain": ["spain", "españa", "madrid", "barcelona", "valencia", "seville", "es"],
    "switzerland": ["switzerland", "schweiz", "suisse", "zurich", "zürich", "geneva", "genève", "basel", "lausanne", "ch"],
    "ireland": ["ireland", "dublin", "cork", "galway", "ie"],
    "australia": ["australia", "sydney", "melbourne", "brisbane", "perth", "au"],
    "sweden": ["sweden", "sverige", "stockholm", "gothenburg", "malmö", "se"],
    "denmark": ["denmark", "danmark", "copenhagen", "københavn", "dk"],
    "poland": ["poland", "polska", "warsaw", "warszawa", "krakow", "kraków", "wroclaw", "wrocław", "pl"],
    "austria": ["austria", "österreich", "vienna", "wien", "salzburg", "graz", "at"],
    "singapore": ["singapore", "sg"],
    "israel": ["israel", "tel aviv", "jerusalem", "il"],
    "japan": ["japan", "tokyo", "osaka", "jp"],
    "india": ["india", "bangalore", "bengaluru", "hyderabad", "pune", "mumbai", "delhi", "in"],
    "portugal": ["portugal", "lisbon", "porto", "pt"],
    "italy": ["italy", "italia", "milan", "rome", "it"],
    "norway": ["norway", "norge", "oslo", "no"],
    "finland": ["finland", "suomi", "helsinki", "fi"],
    "brazil": ["brazil", "brasil", "são paulo", "rio", "br"],
    "mexico": ["mexico", "méxico", "mexico city", "monterrey", "guadalajara", "mx"],
}

# Pre-compiled word-boundary regex patterns for high-frequency country matching
_COMPILED_COUNTRY_PATTERNS: Dict[str, List[re.Pattern]] = {
    country: [re.compile(r"\b" + re.escape(s) + r"\b", re.IGNORECASE) for s in syns]
    for country, syns in COUNTRY_SYNONYMS.items()
}

_STOPWORDS_LOCATION = {"remote", "worldwide", "global", "anywhere", "hybrid", "onsite", "site", "any"}
_SENIORITY_TOKENS = ["senior", "lead", "manager", "director", "head", "specialist", "coordinator", "officer", "executive", "vp", "staff", "principal"]


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

    return sorted(list(found))


def check_job_country_match(job_location: str, target_countries: List[str]) -> Tuple[bool, Optional[str]]:
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
        + " ".join(job.get("tags", []))
    ).lower()

    is_explicit_remote = (
        job.get("remote") is True
        or "remote" in raw_text
        or "anywhere" in raw_text
        or "worldwide" in raw_text
        or "work from home" in raw_text
    )

    is_explicit_hybrid = "hybrid" in raw_text

    loc = job.get("location") or "General"
    if is_explicit_hybrid:
        return f"Hybrid ({loc})", True, True, False
    elif is_explicit_remote:
        return f"Remote ({loc})", True, False, False
    else:
        return f"On-site ({loc})", False, False, True


def calculate_semantic_fit(
    job: Dict[str, Any],
    profile: Dict[str, Any],
    target_countries: List[str],
) -> Tuple[int, List[str], List[str], str]:
    """
    Profile-driven semantic scoring engine for ANY job domain.
    Evaluates:
      1. Target Role & Title Alignment (0-45 points)
      2. Core Skills & Competency Overlap (0-35 points)
      3. Work Mode & Country/Location Alignment (0-20 points)
    Returns:
      (fit_score, matched_skills, reasons, job_type_label)
    """
    target_role = (profile.get("headline") or profile.get("target_role") or "Professional").lower()
    core_skills = profile.get("core_skills") or []
    job_title = job.get("title", "").lower()
    job_text = (job.get("title", "") + " " + job.get("description", "") + " " + " ".join(job.get("tags", []))).lower()

    mode_label, is_remote, is_hybrid, is_onsite = determine_work_mode(job)
    user_work_mode = (profile.get("work_mode") or "Remote Only").lower()

    score = 65.0  # Base calibration score

    # 1. Title & Role Token Alignment
    role_tokens = [t for t in re.split(r"[\s/,-]+", target_role) if len(t) > 2]
    matched_role_tokens = [t for t in role_tokens if t in job_title]
    if matched_role_tokens:
        score += min(24, len(matched_role_tokens) * 8)
    elif any(t in job_text for t in role_tokens):
        score += 8

    # Common seniority & responsibility token alignment
    for st in _SENIORITY_TOKENS:
        if st in target_role and st in job_title:
            score += 3.0

    # 2. Skill Overlap
    matched_skills = []
    for skill in core_skills:
        base_term = skill.split("/")[0].split("(")[0].strip().lower()
        if len(base_term) > 2 and (base_term in job_text or base_term in job_title):
            matched_skills.append(skill)
            score += 3.0

    if not matched_skills and core_skills:
        matched_skills = core_skills[:2]

    # 3. Work Mode & Location Alignment
    country_match, matched_country = check_job_country_match(job.get("location", ""), target_countries)
    reasons = []

    if is_remote and ("remote" in user_work_mode or "no preference" in user_work_mode):
        score += 6.0
        reasons.append("100% Remote position matching your work mode preference.")
    elif is_hybrid and ("hybrid" in user_work_mode or "no preference" in user_work_mode or "open" in user_work_mode):
        score += 7.0
        loc_display = matched_country or job.get("location", "Target Region")
        reasons.append(f"Hybrid role in your target region: {loc_display}.")
    elif is_onsite and ("on-site" in user_work_mode or "no preference" in user_work_mode or "open" in user_work_mode):
        score += 6.0
        loc_display = matched_country or job.get("location", "Target Region")
        reasons.append(f"On-site role located in {loc_display}.")

    if len(matched_skills) >= 2:
        reasons.append(f"Direct alignment with candidate skills: {', '.join(matched_skills[:3])}.")
    if any(t in job_title for t in ["senior", "lead", "manager", "director", "head", "staff"]):
        reasons.append(f"Seniority level aligns with your career trajectory in {target_role.title()}.")
    reasons.append(f"Role title directly complements your background in {target_role.title()}.")

    final_score = int(min(98, max(72, round(score))))
    return final_score, matched_skills, reasons[:3], mode_label
