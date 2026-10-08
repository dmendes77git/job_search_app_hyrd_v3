"""
Configurable Hard Deal-Breakers Engine (Feature P2-A).
Evaluates opportunities against hard disqualification constraints:
- Strict Visa Sponsorship Requirements
- Strict Work Mode Exclusions (Remote Only vs On-site/Hybrid)
- Strict Minimum Compensation Floors
- Strict Negative Keywords & Role Exclusions
- Security Clearance & Mandatory Citizenship Verification

Disqualified opportunities are partitioned from the primary feed and tagged
with specific dealbreaker diagnostic reasons.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple
from src.agents.matching.extractors import check_job_country_match, determine_work_mode


NO_VISA_SPONSORSHIP_PATTERNS = [
    r"\bno\s+visa\s+sponsorship\b",
    r"\bunable\s+to\s+sponsor\b",
    r"\bcannot\s+sponsor\b",
    r"\bwill\s+not\s+sponsor\b",
    r"\bnot\s+offering\s+visa\s+sponsorship\b",
    r"\bdoes\s+not\s+provide\s+visa\s+sponsorship\b",
    r"\bsponsorship\s+(?:is\s+)?not\s+available\b",
    r"\bmust\s+be\s+authorized\s+to\s+work\s+without\s+sponsorship\b",
    r"\bwithout\s+(?:employer\s+)?sponsorship\b",
    r"\bno\s+sponsorship\s+provided\b",
    r"\bnot\s+eligible\s+for\s+sponsorship\b",
]

_NO_VISA_RE = re.compile("|".join(NO_VISA_SPONSORSHIP_PATTERNS), re.IGNORECASE)

CLEARANCE_PATTERNS = [
    r"\bsecurity\s+clearance\s+required\b",
    r"\bactive\s+secret\b",
    r"\btop\s+secret\b",
    r"\bts/sci\b",
    r"\bpolygraph\s+required\b",
    r"\bmust\s+hold\s+(?:an\s+)?active\s+clearance\b",
]
_CLEARANCE_RE = re.compile("|".join(CLEARANCE_PATTERNS), re.IGNORECASE)

CITIZENSHIP_PATTERNS = [
    r"\bus\s+citizenship\s+required\b",
    r"\bmust\s+be\s+a\s+u\.?s\.?\s+citizen\b",
    r"\bu\.?s\.?\s+citizens\s+only\b",
    r"\bus\s+citizens\s+only\b",
]
_CITIZENSHIP_RE = re.compile("|".join(CITIZENSHIP_PATTERNS), re.IGNORECASE)


def extract_job_max_salary(job: Dict[str, Any]) -> Optional[float]:
    """Attempt to parse numerical upper bound of salary from job dictionary."""
    # Check metadata or salary string
    raw_sal = str(job.get("salary") or job.get("salary_range") or job.get("metadata", {}).get("salary", ""))
    if not raw_sal:
        return None
    
    # Check for patterns like $100,000 - $140,000 or 100k - 140k
    k_matches = re.findall(r"(\d+(?:\.\d+)?)\s*k\b", raw_sal, re.IGNORECASE)
    if k_matches:
        try:
            return float(k_matches[-1]) * 1000.0
        except ValueError:
            pass

    num_matches = re.findall(r"(?:[\$€£]\s*)?(\d{2,3}(?:,\d{3})+)", raw_sal)
    if num_matches:
        try:
            clean_num = float(num_matches[-1].replace(",", ""))
            return clean_num
        except ValueError:
            pass

    return None


def evaluate_dealbreakers(
    job: Dict[str, Any],
    profile: Dict[str, Any],
    target_countries: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Perform rigorous dealbreaker evaluation against candidate hard constraints.
    Returns structured GatekeeperAudit dictionary.
    """
    target_countries = target_countries or []
    job_title = str(job.get("title", ""))
    job_comp = str(job.get("company", ""))
    job_desc = str(job.get("full_description", "") or job.get("description", ""))
    job_text = f"{job_title} {job_comp} {job_desc}".lower()

    cand_text = (
        str(profile.get("summary", ""))
        + " "
        + " ".join(profile.get("extracted_skills", []))
        + " "
        + " ".join(profile.get("core_skills", []))
        + " "
        + " ".join(profile.get("certifications", []))
    ).lower()

    work_auth_pass = True
    geo_radius_pass = True
    mandatory_cert_pass = True
    visa_sponsorship_pass = True
    salary_floor_pass = True
    negative_keywords_pass = True

    dealbreaker_type: Optional[str] = None
    reasons: List[str] = []

    # 1. Security Clearance Check
    if _CLEARANCE_RE.search(job_text):
        if not any(k in cand_text for k in ["clearance", "secret", "ts/sci", "top secret"]):
            work_auth_pass = False
            dealbreaker_type = dealbreaker_type or "clearance"
            reasons.append("Active Security Clearance required by employer.")

    # 2. Strict US Citizenship Check
    if _CITIZENSHIP_RE.search(job_text):
        cand_loc = str(profile.get("location_preference") or profile.get("location") or "").lower()
        if not any(us_ind in cand_loc for us_ind in ["united states", "usa", "u.s.", "us"]):
            work_auth_pass = False
            dealbreaker_type = dealbreaker_type or "citizenship"
            reasons.append("Strict US Citizenship required (candidate location outside target territory).")

    # 3. Visa Sponsorship Dealbreaker
    requires_sponsorship = bool(
        profile.get("requires_visa_sponsorship", False)
        or "sponsorship" in str(profile.get("work_authorization", "")).lower()
    )
    if requires_sponsorship:
        if _NO_VISA_RE.search(job_text):
            visa_sponsorship_pass = False
            work_auth_pass = False
            dealbreaker_type = dealbreaker_type or "visa_sponsorship"
            reasons.append("Employer explicitly does not offer visa sponsorship.")

    # 4. Strict Work Mode Dealbreaker
    strict_work_mode = bool(profile.get("strict_work_mode", False))
    user_work_mode = str(profile.get("work_mode", "Remote Only")).lower()
    mode_label, is_remote, is_hybrid, is_onsite = determine_work_mode(job)

    if strict_work_mode:
        if "remote only" in user_work_mode and (is_onsite or is_hybrid):
            geo_radius_pass = False
            dealbreaker_type = dealbreaker_type or "work_mode_mismatch"
            reasons.append(f"Position requires physical attendance ({mode_label}) but candidate strictly requires Remote Only.")
        elif ("on-site" in user_work_mode or "onsite" in user_work_mode) and is_remote:
            geo_radius_pass = False
            dealbreaker_type = dealbreaker_type or "work_mode_mismatch"
            reasons.append("Position is pure remote but candidate strictly requires On-site.")

    # Physical Geographic Radius for on-site / hybrid roles
    if is_onsite or is_hybrid:
        country_match, _ = check_job_country_match(job.get("location", ""), target_countries)
        clean_tc = [tc.lower() for tc in target_countries]
        if not country_match and target_countries and clean_tc != ["remote"]:
            geo_radius_pass = False
            dealbreaker_type = dealbreaker_type or "location_mismatch"
            reasons.append(f"Physical presence in '{job.get('location', 'unspecified')}' outside candidate target region.")

    # 5. Strict Salary Floor Dealbreaker
    strict_salary_floor = bool(profile.get("strict_salary_floor", False))
    pref_min_sal = profile.get("preferred_salary_min")
    if strict_salary_floor and pref_min_sal and float(pref_min_sal) > 0:
        max_sal = extract_job_max_salary(job)
        if max_sal is not None and max_sal < float(pref_min_sal):
            salary_floor_pass = False
            dealbreaker_type = dealbreaker_type or "salary_below_floor"
            reasons.append(f"Disclosed maximum salary ({int(max_sal):,}) falls below candidate strict floor ({int(pref_min_sal):,}).")

    # 6. Negative Keywords Dealbreaker
    negative_kws = profile.get("negative_keywords") or []
    if isinstance(negative_kws, str):
        negative_kws = [k.strip() for k in negative_kws.split(",") if k.strip()]
    
    if negative_kws:
        for nk in negative_kws:
            pattern = r"\b" + re.escape(nk.lower()) + r"\b"
            if re.search(pattern, job_title.lower()):
                negative_keywords_pass = False
                dealbreaker_type = dealbreaker_type or "negative_keyword"
                reasons.append(f"Job title matches excluded negative keyword: '{nk}'.")
                break

    is_disqualified = not (
        work_auth_pass
        and geo_radius_pass
        and mandatory_cert_pass
        and visa_sponsorship_pass
        and salary_floor_pass
        and negative_keywords_pass
    )

    overall_gate_factor = 0.0 if is_disqualified else 1.0

    return {
        "work_auth_pass": work_auth_pass,
        "geo_radius_pass": geo_radius_pass,
        "mandatory_cert_pass": mandatory_cert_pass,
        "visa_sponsorship_pass": visa_sponsorship_pass,
        "salary_floor_pass": salary_floor_pass,
        "negative_keywords_pass": negative_keywords_pass,
        "overall_gate_factor": overall_gate_factor,
        "is_disqualified": is_disqualified,
        "dealbreaker_type": dealbreaker_type,
        "disqualification_reason": "; ".join(reasons) if reasons else None,
    }
