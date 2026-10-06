"""
Salary Benchmark Evaluator.
Evaluates proposed job salaries against candidate CV/profile experience,
stated minimum salary preferences, and market rate benchmarks across industry domains.
Calculates a numerical Salary Score (0-100) and market rank (e.g. Above Market, Within Market Standard, Below Market).
"""

import functools
import re
from typing import Any, Dict, Optional, Tuple


# Market rate annual benchmarks in USD by role family and seniority tier
MARKET_BENCHMARKS: Dict[str, Dict[str, Tuple[float, float]]] = {
    "ai_ml": {
        "entry": (95000.0, 135000.0),
        "mid": (135000.0, 175000.0),
        "senior": (170000.0, 215000.0),
        "lead_staff": (200000.0, 260000.0),
        "executive": (245000.0, 340000.0),
    },
    "software_eng": {
        "entry": (85000.0, 120000.0),
        "mid": (120000.0, 160000.0),
        "senior": (155000.0, 195000.0),
        "lead_staff": (185000.0, 240000.0),
        "executive": (220000.0, 310000.0),
    },
    "data": {
        "entry": (80000.0, 115000.0),
        "mid": (115000.0, 155000.0),
        "senior": (150000.0, 190000.0),
        "lead_staff": (180000.0, 230000.0),
        "executive": (210000.0, 295000.0),
    },
    "product": {
        "entry": (80000.0, 110000.0),
        "mid": (115000.0, 150000.0),
        "senior": (150000.0, 195000.0),
        "lead_staff": (180000.0, 235000.0),
        "executive": (215000.0, 300000.0),
    },
    "marketing_sales": {
        "entry": (60000.0, 85000.0),
        "mid": (85000.0, 125000.0),
        "senior": (125000.0, 170000.0),
        "lead_staff": (155000.0, 210000.0),
        "executive": (190000.0, 275000.0),
    },
    "finance_ops": {
        "entry": (65000.0, 90000.0),
        "mid": (90000.0, 130000.0),
        "senior": (130000.0, 175000.0),
        "lead_staff": (160000.0, 215000.0),
        "executive": (195000.0, 285000.0),
    },
    "general": {
        "entry": (65000.0, 95000.0),
        "mid": (95000.0, 135000.0),
        "senior": (135000.0, 180000.0),
        "lead_staff": (165000.0, 220000.0),
        "executive": (200000.0, 280000.0),
    },
}

TIER_LABELS = {
    "entry": "Junior / Entry (0-2 yrs)",
    "mid": "Mid-Level (3-5 yrs)",
    "senior": "Senior (5-8 yrs)",
    "lead_staff": "Lead / Staff / Principal (8+ yrs)",
    "executive": "Executive / Director (10+ yrs)",
}

# Pre-compiled regular expressions
_K_MATCH_RE = re.compile(r"(\d+(?:\.\d+)?)\s*k\b")
_NUMS_RE = re.compile(r"[\d,]+(?:\.\d+)?")
_STANDARD_NUM_RE = re.compile(r"\b\d{1,3}(?:[,\s]\d{3})+(?:\.\d+)?\b|\b\d{5,7}\b")
_SHORT_NUM_RE = re.compile(r"\b\d{2,4}\b")
_CLEAN_COMMA_SPACE_RE = re.compile(r"[,\s]")


@functools.lru_cache(maxsize=512)
def parse_numeric_salary(raw_str: str) -> Optional[float]:
    """
    Extract a single primary numeric annual salary from a string.
    Supports formats like "$160,000", "160k", "€120.000", "£85k", "85000".
    """
    if not raw_str:
        return None
    s = raw_str.strip().lower()
    # Check for 'k' notation e.g. 160k
    k_match = _K_MATCH_RE.search(s)
    if k_match:
        try:
            return float(k_match.group(1)) * 1000.0
        except ValueError:
            pass

    # Clean punctuation and find first large number
    nums = _NUMS_RE.findall(s)
    for n in nums:
        cleaned = n.replace(",", "")
        try:
            val = float(cleaned)
            if val >= 10000:
                # Annual salary
                return val
            elif 30 <= val <= 250:
                # Likely hourly rate -> convert to annual (2000 hrs)
                return val * 2000.0
            elif 2000 <= val <= 9999:
                # Likely monthly salary -> convert to annual (12 months)
                return val * 12.0
        except ValueError:
            continue
    return None


@functools.lru_cache(maxsize=512)
def _parse_salary_range_cached(salary_str: str) -> Tuple[bool, Optional[float], Optional[float], Optional[float], str, bool]:
    """Internal cached helper returning immutable tuple."""
    if not salary_str:
        return False, None, None, None, "$", True

    raw = salary_str.strip()
    curr_multiplier = 1.0
    curr_symbol = "$"
    if "€" in raw or "eur" in raw.lower():
        curr_multiplier = 1.08
        curr_symbol = "€"
    elif "£" in raw or "gbp" in raw.lower():
        curr_multiplier = 1.28
        curr_symbol = "£"

    # Hourly detection
    is_hourly = "/ hr" in raw.lower() or "/hr" in raw.lower() or "hourly" in raw.lower()
    is_monthly = "/ mo" in raw.lower() or "/mo" in raw.lower() or "monthly" in raw.lower()

    # Look for 'k' numbers e.g. $120k - $160k
    k_matches = _K_MATCH_RE.findall(raw.lower())
    if len(k_matches) >= 2:
        val1 = float(k_matches[0]) * 1000.0 * curr_multiplier
        val2 = float(k_matches[1]) * 1000.0 * curr_multiplier
        s_min, s_max = min(val1, val2), max(val1, val2)
        return (
            True,
            s_min,
            s_max,
            (s_min + s_max) / 2.0,
            curr_symbol,
            "(est" in raw.lower() or "comp" in raw.lower(),
        )

    # Standard number extraction
    nums = _STANDARD_NUM_RE.findall(raw)
    cleaned_nums = []
    for n in nums:
        try:
            val = float(_CLEAN_COMMA_SPACE_RE.sub("", n))
            cleaned_nums.append(val)
        except ValueError:
            continue

    if not cleaned_nums:
        # Check for 2-digit numbers if hourly
        short_nums = _SHORT_NUM_RE.findall(raw)
        for n in short_nums:
            try:
                val = float(n)
                if is_hourly and 20 <= val <= 250:
                    cleaned_nums.append(val * 2000.0)
                elif is_monthly and 2000 <= val <= 25000:
                    cleaned_nums.append(val * 12.0)
            except ValueError:
                continue

    if len(cleaned_nums) >= 2:
        val1 = cleaned_nums[0] * curr_multiplier
        val2 = cleaned_nums[1] * curr_multiplier
        s_min, s_max = min(val1, val2), max(val1, val2)
        return (
            True,
            s_min,
            s_max,
            (s_min + s_max) / 2.0,
            curr_symbol,
            "(est" in raw.lower() or "comp" in raw.lower(),
        )
    elif len(cleaned_nums) == 1:
        val = cleaned_nums[0] * curr_multiplier
        return (
            True,
            val,
            val * 1.25,
            val * 1.12,
            curr_symbol,
            True,
        )

    return False, None, None, None, curr_symbol, True


def parse_salary_range(salary_str: str) -> Dict[str, Any]:
    """
    Parse a salary range string from a job posting into numeric min, max, and midpoint.
    Handles currency conversion multipliers (EUR, GBP to USD).
    """
    has_sal, s_min, s_max, mid, symbol, is_est = _parse_salary_range_cached(salary_str)
    return {
        "has_salary": has_sal,
        "min_usd": s_min,
        "max_usd": s_max,
        "midpoint_usd": mid,
        "currency_symbol": symbol,
        "is_estimated": is_est,
    }


@functools.lru_cache(maxsize=512)
def detect_role_domain(role_title: str) -> str:
    """Detect the market rate domain from a job or candidate target title."""
    t = (role_title or "").lower()
    if any(k in t for k in ["agent", "llm", "ai ", "ai/", "artificial intelligence", "machine learning", "ml ", "ml/", "deep learning", "nlp", "computer vision", "prompt", "research engineer"]):
        return "ai_ml"
    if any(k in t for k in ["data engineer", "data scientist", "data analyst", "analytics", "database", "bi "]):
        return "data"
    if any(k in t for k in ["product manager", "product owner", "product lead", "group pm", "technical product"]):
        return "product"
    if any(k in t for k in ["marketing", "growth", "seo", "sales", "business development", "account executive"]):
        return "marketing_sales"
    if any(k in t for k in ["finance", "financial", "accounting", "operations", "recruiter", "human resources", "hr ", "people"]):
        return "finance_ops"
    if any(k in t for k in ["software", "backend", "frontend", "full stack", "fullstack", "platform", "cloud", "devops", "systems", "infrastructure", "sre", "architect", "engineer", "developer"]):
        return "software_eng"
    return "general"


@functools.lru_cache(maxsize=512)
def detect_seniority_tier(role_title: str, exp_level_str: str = "") -> str:
    """Detect the seniority tier based on role title and candidate experience level."""
    combined = f"{role_title} {exp_level_str}".lower()

    if any(k in combined for k in ["director", "vp", "vice president", "chief", "cto", "cpo", "cfo", "head of", "executive"]):
        return "executive"
    if any(k in combined for k in ["lead", "staff", "principal", "architect", "8+ years", "distinguished"]):
        return "lead_staff"
    if any(k in combined for k in ["senior", "sr", "5+ years", "6+ years", "7+ years", "5-8 years"]):
        return "senior"
    if any(k in combined for k in ["junior", "entry", "associate", "graduate", "0-2 years", "intern"]):
        return "entry"
    if any(k in combined for k in ["mid", "intermediate", "3-5 years", "3+ years", "4+ years"]):
        return "mid"

    # Default to senior for tech/engineering candidates with multi-year profiles
    return "senior"


def evaluate_job_salary(
    job_salary_str: str,
    job_title: str = "",
    profile: Optional[Dict[str, Any]] = None,
    desired_min_salary_str: str = "",
) -> Dict[str, Any]:
    """
    Comprehensive evaluation of a proposed job salary against:
    1. Candidate profile experience & seniority
    2. Stated candidate minimum salary preference
    3. Market rate benchmarks for the role domain and seniority tier
    Returns numerical score (0-100), qualitative rank, badge styling, and assessment text.
    """
    prof = profile or {}
    cand_role = prof.get("headline") or prof.get("target_role") or job_title or "Software Engineer"
    cand_exp = prof.get("years_of_experience") or prof.get("experience_level") or "Senior (5+ years)"

    domain = detect_role_domain(job_title or cand_role)
    tier = detect_seniority_tier(job_title or cand_role, cand_exp)

    bench_min, bench_max = MARKET_BENCHMARKS.get(domain, MARKET_BENCHMARKS["general"]).get(
        tier, (140000.0, 185000.0)
    )
    bench_mid = (bench_min + bench_max) / 2.0

    parsed_salary = parse_salary_range(job_salary_str)
    cand_min_num = parse_numeric_salary(desired_min_salary_str or prof.get("preferred_min_salary", ""))

    tier_label = TIER_LABELS.get(tier, "Senior Tier")

    if not parsed_salary["has_salary"]:
        # Undisclosed / Competitive Salary: Estimate benchmark and assign standard calibration
        score = 80
        rank = "Within Market Standard"
        badge_bg = "#eff6ff"
        badge_text = "#1e40af"
        badge_border = "#bfdbfe"
        rank_icon = "🔵"
        assessment = (
            f"Salary undisclosed in job posting. Evaluated at market standard based on benchmark "
            f"for {tier_label} in {domain.replace('_', ' ').title()} (${int(bench_min):,} - ${int(bench_max):,})."
        )
        return {
            "score": score,
            "rank": rank,
            "badge_bg": badge_bg,
            "badge_text": badge_text,
            "badge_border": badge_border,
            "rank_icon": rank_icon,
            "benchmark_range": f"${int(bench_min):,} - ${int(bench_max):,}",
            "benchmark_title": f"{tier_label} • {domain.replace('_', ' ').upper()}",
            "assessment": assessment,
            "is_estimated": True,
        }

    job_mid = parsed_salary["midpoint_usd"]
    ratio = job_mid / bench_mid

    # Base score and rank calculation from market benchmark ratio
    if ratio >= 1.12:
        rank = "Above Market"
        rank_icon = "🟢"
        badge_bg = "#f0fdf4"
        badge_text = "#166534"
        badge_border = "#bbf7d0"
        score = int(min(98, 88 + (ratio - 1.12) * 45))
        diff_pct = (ratio - 1.0) * 100.0
        assessment = (
            f"Proposed compensation (${int(parsed_salary['min_usd']):,} - ${int(parsed_salary['max_usd']):,}) "
            f"is {diff_pct:+.1f}% above the median market benchmark (${int(bench_mid):,}) for {tier_label}."
        )
    elif ratio >= 0.88:
        rank = "Within Market Standard"
        rank_icon = "🔵"
        badge_bg = "#eff6ff"
        badge_text = "#1e40af"
        badge_border = "#bfdbfe"
        score = int(min(87, max(75, 75 + ((ratio - 0.88) / 0.24) * 12)))
        diff_pct = (ratio - 1.0) * 100.0
        sign = "+" if diff_pct >= 0 else ""
        assessment = (
            f"Proposed compensation (${int(parsed_salary['min_usd']):,} - ${int(parsed_salary['max_usd']):,}) "
            f"aligns closely with the market benchmark (${int(bench_min):,} - ${int(bench_max):,}, {sign}{diff_pct:.1f}% vs median)."
        )
    else:
        rank = "Below Market"
        rank_icon = "🟠"
        badge_bg = "#fffbeb"
        badge_text = "#b45309"
        badge_border = "#fde68a"
        score = int(max(48, min(73, ratio * 82)))
        deficit_pct = (1.0 - ratio) * 100.0
        assessment = (
            f"Proposed compensation (${int(parsed_salary['min_usd']):,} - ${int(parsed_salary['max_usd']):,}) "
            f"is {deficit_pct:.1f}% below typical market benchmarks (${int(bench_min):,} - ${int(bench_max):,}) for this seniority level."
        )

    # Candidate minimum preference alignment
    if cand_min_num:
        if job_mid >= cand_min_num:
            score = min(99, score + 3)
            assessment += f" Exceeds candidate's stated minimum expectation (${int(cand_min_num):,})."
        else:
            score = max(42, score - 6)
            gap = cand_min_num - job_mid
            assessment += f" Below candidate's desired minimum expectation by approx. ${int(gap):,}."

    return {
        "score": score,
        "rank": rank,
        "badge_bg": badge_bg,
        "badge_text": badge_text,
        "badge_border": badge_border,
        "rank_icon": rank_icon,
        "benchmark_range": f"${int(bench_min):,} - ${int(bench_max):,}",
        "benchmark_title": f"{tier_label} • {domain.replace('_', ' ').upper()}",
        "assessment": assessment,
        "is_estimated": parsed_salary["is_estimated"],
    }
