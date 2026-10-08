"""
Core Semantic Matching Engine & Role Match Evaluation.
Implements multi-dimensional scoring algorithms (role, skill, freshness, leveling, salary, location)
and deep recruiter gap analysis.
"""

import logging
import re
from typing import Any, Dict, List, Tuple

from src.utils.date_utils import parse_days_since_posted

from .extractors import (
    check_job_country_match,
    determine_work_mode,
    extract_required_years_experience,
    extract_tech_skills,
)
from .taxonomy import (
    _SENIORITY_TOKENS,
    expand_role_synonyms,
)

logger = logging.getLogger("Hyrd.Scoring.Engine")


def extract_seniority_level(title_or_text: str, default_yoe: Optional[int] = None) -> Tuple[int, str]:
    """Determine standardized seniority level index (1-6) and label.
    1: Junior / Associate (0-2 yrs)
    2: Mid-Level (2-5 yrs)
    3: Senior (5-8 yrs)
    4: Staff / Lead (8-12 yrs)
    5: Principal / Architect (12-15 yrs)
    6: Executive / Director (15+ yrs)
    """
    text = title_or_text.lower()
    if any(k in text for k in ["director", "head of", "vp", "vice president", "chief", "cto", "c-level"]):
        return 6, "Executive / Director"
    if any(k in text for k in ["principal", "architect", "fellow", "distinguished"]):
        return 5, "Principal / Architect"
    if any(k in text for k in ["staff", "lead", "team lead", "tech lead"]):
        return 4, "Staff / Lead"
    if any(k in text for k in ["senior", "sr.", "sr ", "specialist"]):
        return 3, "Senior"
    if any(k in text for k in ["junior", "jr.", "jr ", "intern", "associate", "entry level", "graduate", "trainee"]):
        return 1, "Junior / Associate"
    
    # Fallback to Years of Experience if available
    if default_yoe is not None:
        if default_yoe >= 15:
            return 6, "Executive / Director"
        elif default_yoe >= 12:
            return 5, "Principal / Architect"
        elif default_yoe >= 8:
            return 4, "Staff / Lead"
        elif default_yoe >= 5:
            return 3, "Senior"
        elif default_yoe >= 2:
            return 2, "Mid-Level"
        else:
            return 1, "Junior / Associate"

    return 2, "Mid-Level"


def calculate_temporal_decay(days_posted: int) -> float:
    """Calculate requisition age velocity decay multiplier Lambda in [0.15, 1.0].
    Lambda(t) = 0.15 + 0.85 / (1.0 + (t / 12.0)^1.8)
    """
    if days_posted <= 2:
        return 0.98
    t = float(max(0, days_posted))
    decay = 0.15 + (0.85 / (1.0 + ((t / 12.0) ** 1.8)))
    return float(round(max(0.15, min(1.0, decay)), 3))


def get_channel_advantage_multiplier(source: str, is_direct_ats: bool = False) -> Tuple[float, str]:
    """Calculate competitive channel advantage multiplier Omega and classification."""
    s_lower = (source or "").lower()
    if is_direct_ats or any(ats in s_lower for ats in ["ashby", "greenhouse", "lever", "smartrecruiters", "workday"]):
        return 1.15, "Direct Official ATS Feed"
    elif any(sp in s_lower for sp in ["remoteok", "arbeitnow", "itjobs", "remotive", "landing", "net-empregos"]):
        return 1.00, "Specialized Tech Aggregator"
    elif any(agg in s_lower for agg in ["jobspy", "indeed", "ziprecruiter", "glassdoor", "google"]):
        return 0.82, "High-Traffic Aggregator"
    elif "linkedin" in s_lower:
        return 0.70, "Saturated Job Portal"
    return 1.00, "Standard Job Feed"


def calculate_gatekeeper_audit(
    job: Dict[str, Any],
    profile: Dict[str, Any],
    target_countries: List[str],
) -> Dict[str, Any]:
    """Perform strict hard-barrier checks for work authorization, security clearance, and location radius."""
    job_text = (job.get("title", "") + " " + job.get("description", "") + " " + job.get("full_description", "")).lower()
    cand_text = (
        profile.get("summary", "")
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
    reasons = []

    # 1. Security Clearance Check
    clearance_patterns = ["security clearance required", "active secret", "top secret", "ts/sci", "polygraph", "clearance required"]
    if any(cp in job_text for cp in clearance_patterns):
        if not any(cp in cand_text for cp in ["clearance", "secret", "ts/sci", "top secret"]):
            work_auth_pass = False
            reasons.append("Active Security Clearance required by employer.")

    # 2. Strict US Citizenship / National Only Check
    citizenship_patterns = ["us citizenship required", "must be a u.s. citizen", "u.s. citizens only", "us citizens only"]
    if any(cp in job_text for cp in citizenship_patterns):
        cand_loc = (profile.get("location_preference") or profile.get("location") or "").lower()
        if not any(us_ind in cand_loc for us_ind in ["united states", "usa", "u.s.", "us"]):
            work_auth_pass = False
            reasons.append("Strict US Citizenship required (candidate outside target region).")

    # 3. Visa Sponsorship Prohibition Check
    no_visa_patterns = ["no visa sponsorship", "unable to sponsor", "cannot sponsor", "not offer visa sponsorship", "sponsorship not available"]
    if any(nv in job_text for nv in no_visa_patterns):
        country_match, _ = check_job_country_match(job.get("location", ""), target_countries)
        if not country_match and target_countries and "remote" not in [tc.lower() for tc in target_countries]:
            work_auth_pass = False
            reasons.append("Employer does not provide visa sponsorship.")

    # 4. Physical Geographic Radius for On-site / Hybrid roles
    mode_label, is_remote, is_hybrid, is_onsite = determine_work_mode(job)
    user_work_mode = (profile.get("work_mode") or "Remote Only").lower()

    if (is_onsite or is_hybrid) and "remote only" in user_work_mode:
        geo_radius_pass = False
        reasons.append(f"Role requires physical presence ({mode_label}) but candidate prefers Remote Only.")
    elif is_onsite or is_hybrid:
        country_match, _ = check_job_country_match(job.get("location", ""), target_countries)
        clean_tc = [tc.lower() for tc in target_countries]
        if not country_match and target_countries and clean_tc != ["remote"]:
            geo_radius_pass = False
            reasons.append(f"Physical on-site/hybrid role in {job.get('location', 'unspecified location')} outside candidate target countries.")

    # Compute overall gate factor
    if not work_auth_pass:
        overall_gate = 0.0
    elif not geo_radius_pass:
        overall_gate = 0.0
    elif not mandatory_cert_pass:
        overall_gate = 0.0
    else:
        overall_gate = 1.0

    return {
        "work_auth_pass": work_auth_pass,
        "geo_radius_pass": geo_radius_pass,
        "mandatory_cert_pass": mandatory_cert_pass,
        "overall_gate_factor": overall_gate,
        "disqualification_reason": "; ".join(reasons) if reasons else None,
    }


def calculate_quality_match(
    job: Dict[str, Any],
    profile: Dict[str, Any],
    target_countries: List[str],
) -> Dict[str, Any]:
    """Execute redesigned Dual-Engine Quality Match algorithm from 03_MATCH_LOGIC_BLUEPRINT.md.
    Decouples Profile Fit Score (0-100) from Likelihood of Success (0-100%).
    """
    import math

    target_role = (profile.get("headline") or profile.get("target_role") or "Professional").lower()
    core_skills = profile.get("core_skills") or profile.get("extracted_skills") or []
    job_title = job.get("title", "").lower()
    job_desc = job.get("description", "") or job.get("full_description", "")
    job_tags = job.get("tags", [])
    job_text = f"{job_title} {job_desc} {' '.join(job_tags)}".lower()

    mode_label, is_remote, is_hybrid, is_onsite = determine_work_mode(job)
    user_work_mode = (profile.get("work_mode") or "Remote Only").lower()

    # ---------------------------------------------------------
    # 1. DEEP SKILL ALIGNMENT (S_skill: 0-100) - Weight 0.40
    # ---------------------------------------------------------
    # Segment requisition requirements into Must-Have vs Secondary
    must_have_skills: List[str] = []
    secondary_skills: List[str] = []

    for idx, skill in enumerate(core_skills):
        if idx < 4:
            must_have_skills.append(skill)
        else:
            secondary_skills.append(skill)

    matched_skills = []
    matched_must_have = []
    matched_secondary = []
    missing_must_have = []
    capability_matches = []

    for s in must_have_skills:
        clean_s = s.split("/")[0].split("(")[0].strip().lower()
        if len(clean_s) >= 2 and (clean_s in job_text or clean_s in job_title):
            matched_skills.append(s)
            matched_must_have.append(s)
            capability_matches.append({
                "skill_name": s,
                "is_must_have": True,
                "matched": True,
                "mastery_score": 1.0,
            })
        else:
            missing_must_have.append(s)
            capability_matches.append({
                "skill_name": s,
                "is_must_have": True,
                "matched": False,
                "mastery_score": 0.0,
            })

    for s in secondary_skills:
        clean_s = s.split("/")[0].split("(")[0].strip().lower()
        if len(clean_s) >= 2 and (clean_s in job_text or clean_s in job_title):
            matched_skills.append(s)
            matched_secondary.append(s)
            capability_matches.append({
                "skill_name": s,
                "is_must_have": False,
                "matched": True,
                "mastery_score": 0.85,
            })
        else:
            capability_matches.append({
                "skill_name": s,
                "is_must_have": False,
                "matched": False,
                "mastery_score": 0.0,
            })

    must_pct = (len(matched_must_have) / len(must_have_skills)) if must_have_skills else 1.0
    sec_pct = (len(matched_secondary) / len(secondary_skills)) if secondary_skills else 1.0
    raw_skill_score = 100.0 * (0.75 * must_pct + 0.25 * sec_pct)

    # Exponential Critical Gap Penalty
    gamma_gaps = (1.0 - 0.22) ** len(missing_must_have)
    s_skill = min(100.0, max(0.0, raw_skill_score * gamma_gaps))

    # Missing tech in job
    extracted_job_tech = extract_tech_skills(job_text)
    cand_skill_lower = {s.lower() for s in core_skills}
    missing_tech = [
        t for t in extracted_job_tech
        if not any(t.lower() in cs or cs in t.lower() for cs in cand_skill_lower)
    ]

    # ---------------------------------------------------------
    # 2. ROLE & DOMAIN CONGRUENCE (S_role: 0-100) - Weight 0.25
    # ---------------------------------------------------------
    cand_role_tokens = [t for t in re.split(r"[\s/,-]+", target_role) if len(t) > 2]
    synonym_titles = expand_role_synonyms(target_role)
    all_role_tokens = list(dict.fromkeys(cand_role_tokens + [t for syn in synonym_titles for t in re.split(r"[\s/,-]+", syn.lower()) if len(t) > 2]))

    title_matches = [t for t in all_role_tokens if t in job_title]
    if target_role in job_title or any(syn.lower() in job_title for syn in synonym_titles):
        sim_title = 100.0
    elif title_matches:
        sim_title = min(95.0, 50.0 + len(title_matches) * 15.0)
    elif any(t in job_text for t in all_role_tokens):
        sim_title = 60.0
    else:
        sim_title = 20.0

    # Domain keyword alignment
    domains = [
        ("ai", ["ai", "agent", "agentic", "llm", "machine learning", "ml", "nlp", "deep learning"]),
        ("software", ["software", "engineer", "developer", "backend", "frontend", "full stack", "fullstack", "platform", "systems", "architect"]),
        ("data", ["data", "analytics", "database", "sql", "pipeline", "etl", "bi"]),
        ("cloud", ["cloud", "devops", "sre", "infrastructure", "kubernetes", "aws", "gcp"]),
        ("product", ["product", "product manager", "strategy", "roadmap", "agile"]),
    ]
    sim_domain = 40.0
    for _, kws in domains:
        cand_in = any(k in target_role for k in kws)
        job_in = any(k in job_title or k in job_text for k in kws)
        if cand_in and job_in:
            sim_domain = 100.0
            break
        elif cand_in and not job_in:
            sim_domain = 25.0

    s_role = 0.60 * sim_title + 0.40 * sim_domain

    # ---------------------------------------------------------
    # 3. SENIORITY & LEVELING CALIBRATION (S_level: 0-100) - Weight 0.20
    # ---------------------------------------------------------
    cand_yoe_str = str(profile.get("years_of_experience") or profile.get("experience_level") or "")
    cand_yoe_m = re.search(r"(\d+)", cand_yoe_str)
    cand_yoe = int(cand_yoe_m.group(1)) if cand_yoe_m else 5
    cand_level_idx, cand_level_name = extract_seniority_level(target_role, default_yoe=cand_yoe)

    req_yoe = extract_required_years_experience(job_text)
    entry_or_jr = any(k in job_text for k in ["entry level", "entry-level", "junior", "intern", "trainee", "associate"])
    if entry_or_jr or (req_yoe is not None and req_yoe <= 2):
        job_level_idx, job_level_name = 1, "Junior / Associate"
    else:
        job_level_idx, job_level_name = extract_seniority_level(job_title, default_yoe=req_yoe)

    delta_l = cand_level_idx - job_level_idx
    if delta_l == 0:
        s_level = 100.0
        level_assessment = f"Exact leveling alignment: Role matches your {cand_level_name} background."
    elif delta_l == 1:
        s_level = 90.0
        level_assessment = f"Comfortable leveling: Your {cand_level_name} expertise slightly exceeds role requirement."
    elif delta_l == -1:
        s_level = 75.0
        level_assessment = f"Growth stretch role: Role targets {job_level_name} (you are {cand_level_name})."
    elif delta_l >= 2:
        s_level = max(10.0, 100.0 - 40.0 * (delta_l - 1))
        level_assessment = f"Overqualification advisory: {job_level_name} role may pose compensation and engagement limits for a {cand_level_name}."
    else:  # delta_l <= -2
        s_level = max(0.0, 100.0 - 50.0 * abs(delta_l))
        level_assessment = f"Underqualification warning: Requisition targets {job_level_name} requiring higher experience tenure."

    yoe_reason = None
    if req_yoe is not None and cand_yoe is not None:
        if cand_yoe >= req_yoe and req_yoe >= 3:
            yoe_reason = f"Leveling match: Your {cand_yoe}+ years experience fulfills the required {req_yoe}+ years."
        elif 0 < (req_yoe - cand_yoe) <= 2:
            yoe_reason = f"High-growth stretch opportunity: Requisition asks for {req_yoe} yrs (you offer {cand_yoe}+ yrs)."
        elif cand_yoe >= 6 and req_yoe <= 2:
            yoe_reason = f"Scope advisory: Role specifies {req_yoe} yrs, which is below your senior background."
    elif (cand_yoe and cand_yoe >= 6) and entry_or_jr:
        yoe_reason = "Leveling advisory: Entry/junior level role does not match your senior background."

    # ---------------------------------------------------------
    # 4. PREFERENCES & COMPENSATION (S_pref: 0-100) - Weight 0.15
    # ---------------------------------------------------------
    from src.utils.salary_evaluator import parse_numeric_salary
    desired_sal_raw = (profile.get("preferred_min_salary") or profile.get("min_salary") or "")
    desired_sal = parse_numeric_salary(str(desired_sal_raw))
    job_sal = parse_numeric_salary(str(job.get("salary", "")))
    salary_reason = None
    if desired_sal and job_sal:
        r_sal = job_sal / desired_sal
        if r_sal >= 1.05:
            score_sal = 100.0
            salary_reason = "Compensation alignment: Offered salary meets or exceeds your minimum target."
        elif r_sal >= 0.95:
            score_sal = 85.0
            salary_reason = "Compensation alignment: Offered salary meets or exceeds your minimum target."
        elif r_sal >= 0.80:
            score_sal = 60.0
            salary_reason = "Compensation advisory: Posted compensation is below your target minimum threshold."
        else:
            score_sal = 20.0
            salary_reason = "Compensation advisory: Posted compensation is below your target minimum threshold."
    else:
        score_sal = 80.0

    if is_remote and ("remote" in user_work_mode or "no preference" in user_work_mode):
        score_mode = 100.0
    elif is_hybrid and ("hybrid" in user_work_mode or "no preference" in user_work_mode or "open" in user_work_mode):
        score_mode = 100.0
    elif is_onsite and ("on-site" in user_work_mode or "no preference" in user_work_mode or "open" in user_work_mode):
        score_mode = 100.0
    elif is_remote:
        score_mode = 90.0
    else:
        score_mode = 30.0

    is_target_co = job.get("is_target_company", False)
    score_co = 100.0 if is_target_co else 50.0

    s_pref = 0.50 * score_sal + 0.35 * score_mode + 0.15 * score_co

    # ---------------------------------------------------------
    # FINAL PROFILE FIT SCORE (S_fit: 0 - 100)
    # ---------------------------------------------------------
    profile_fit_score = float(round(0.40 * s_skill + 0.25 * s_role + 0.20 * s_level + 0.15 * s_pref, 1))

    # Requisition Age & Velocity Calibration
    days_posted, days_label = parse_days_since_posted(job.get("posted", "Recent"), job_id=job.get("id", ""))
    lambda_decay = calculate_temporal_decay(days_posted)
    freshness_reason = None
    freshness_delta = 0.0
    if days_posted <= 3:
        freshness_delta = 3.0
        freshness_reason = f"⚡ Fresh requisition: Published {days_posted} days ago with active hiring momentum (Hot opening)."
    elif days_posted > 21:
        freshness_delta = -3.0
        freshness_reason = f"Aging requisition (>3 weeks): Likely in advanced interview stages ({days_posted}d ago)."

    profile_fit_score = float(round(max(0.0, min(100.0, profile_fit_score + freshness_delta)), 1))

    # ---------------------------------------------------------
    # 5. LIKELIHOOD OF SUCCESS (P_success: 0 - 100%)
    # ---------------------------------------------------------
    # Base probability sigmoid
    p_base = 0.88 / (1.0 + math.exp(-0.09 * (profile_fit_score - 72.0)))

    # Hard Gatekeeper Audit
    gatekeeper = calculate_gatekeeper_audit(job, profile, target_countries)
    phi_gate = gatekeeper["overall_gate_factor"]

    # Ingestion Channel Multiplier
    omega_channel, channel_type = get_channel_advantage_multiplier(
        job.get("source", "Aggregator"),
        is_direct_ats=job.get("is_direct_ats", False)
    )

    # ATS Keyword Density Friction
    total_must = len(must_have_skills) if must_have_skills else 1
    matched_must = len(matched_must_have)
    psi_friction = max(0.50, min(1.0, 0.60 + 0.40 * (matched_must / total_must)))

    # Compute raw callback likelihood
    raw_p_success = p_base * phi_gate * lambda_decay * omega_channel * psi_friction * 100.0
    interview_likelihood_pct = float(round(max(0.0, min(95.0, raw_p_success)), 1))

    # ---------------------------------------------------------
    # 6. STRATEGIC QUADRANT & ACTIONABLE DIRECTIVES
    # ---------------------------------------------------------
    if profile_fit_score >= 85.0 and interview_likelihood_pct >= 60.0:
        strategic_quadrant = "QI"
        recommended_action = "Priority Fast-Track: High capability match with peak hiring velocity. Apply immediately via direct ATS with tailored CV."
    elif profile_fit_score >= 80.0 and interview_likelihood_pct < 40.0:
        strategic_quadrant = "QII"
        recommended_action = "High Fit / Stale Market: High technical capability but requisition is aging or saturated. Do NOT cold apply; execute LinkedIn InMail outreach for referral."
    elif profile_fit_score >= 65.0 and interview_likelihood_pct >= 50.0:
        strategic_quadrant = "QIII"
        recommended_action = "High Viability Stretch: Strong hiring velocity and candidate pipeline. Apply with bridge skill narrative in cover letter."
    else:
        strategic_quadrant = "QIV"
        if phi_gate == 0.0:
            recommended_action = f"Disqualified: {gatekeeper.get('disqualification_reason') or 'Hard requirement barrier failed.'}"
        else:
            recommended_action = "Low Viability / Misaligned: Significant capability gap or leveling mismatch. Archive or skip to preserve application quota."

    # Rationale Statements
    reasons = []
    if is_target_co:
        reasons.append(f"⭐ Target dream employer specified in your profile ({job.get('company', 'Company')}).")
    if job.get("is_direct_ats"):
        reasons.append("⚡ Direct ATS Official Submission: Unmediated employer requisition with maximum callback odds.")
    if matched_must_have:
        reasons.append(f"Core capability match: Verified proficiency in {', '.join(matched_must_have[:3])}.")
    if freshness_reason:
        reasons.append(freshness_reason)
    if yoe_reason:
        reasons.append(yoe_reason)
    elif level_assessment:
        reasons.append(level_assessment)
    if salary_reason:
        reasons.append(salary_reason)
    if gatekeeper.get("disqualification_reason"):
        reasons.append(f"🛑 Barrier Alert: {gatekeeper['disqualification_reason']}")

    return {
        "profile_fit_score": profile_fit_score,
        "interview_likelihood_pct": interview_likelihood_pct,
        "strategic_quadrant": strategic_quadrant,
        "matched_skills": matched_skills,
        "missing_skills": missing_tech[:5],
        "reasons": reasons[:6],
        "mode_label": mode_label,
        "recommended_action": recommended_action,
        "dimension_scores": {
            "skill": round(s_skill, 1),
            "role": round(s_role, 1),
            "level": round(s_level, 1),
            "pref": round(s_pref, 1),
            "semantic_fit": profile_fit_score,
            "compensation": round(score_sal, 1),
        },
        "capability_matches": capability_matches,
        "leveling_analysis": {
            "candidate_level": cand_level_name,
            "role_level": job_level_name,
            "level_delta": delta_l,
            "score": round(s_level, 1),
            "assessment": level_assessment,
        },
        "gatekeeper_audit": gatekeeper,
        "viability_metrics": {
            "days_since_posted": days_posted,
            "decay_multiplier": lambda_decay,
            "channel_type": channel_type,
            "channel_multiplier": omega_channel,
            "ats_keyword_density_pct": round(psi_friction * 100.0, 1),
        },
    }


def calculate_semantic_fit(
    job: Dict[str, Any],
    profile: Dict[str, Any],
    target_countries: List[str],
) -> Tuple[int, List[str], List[str], str]:
    """Profile-driven multi-dimensional semantic scoring engine (Decoupled Dual-Engine).
    Returns (fit_score, matched_skills, reasons, job_type_label).
    Also populates job with decoupled metrics and audit models.
    """
    res = calculate_quality_match(job, profile, target_countries)
    fit_score = int(round(res["profile_fit_score"]))

    job["profile_fit_score"] = res["profile_fit_score"]
    job["interview_likelihood_pct"] = res["interview_likelihood_pct"]
    job["strategic_quadrant"] = res["strategic_quadrant"]
    job["matched_skills"] = res["matched_skills"]
    job["missing_skills"] = res["missing_skills"]
    job["key_reasons"] = res["reasons"]
    job["job_type"] = res["mode_label"]
    job["dimension_scores"] = res["dimension_scores"]
    job["capability_matches"] = res.get("capability_matches", [])
    job["gatekeeper_audit"] = res["gatekeeper_audit"]
    job["leveling_analysis"] = res["leveling_analysis"]
    job["viability_metrics"] = res["viability_metrics"]
    job["recommended_action"] = res["recommended_action"]
    job["fit_score"] = fit_score

    # Calibrate UI badge color
    if fit_score >= 88:
        job["badge_color"] = "#10b981"  # Emerald green
    elif fit_score >= 75:
        job["badge_color"] = "#2563eb"  # Royal blue
    else:
        job["badge_color"] = "#f59e0b"  # Amber warning

    return fit_score, res["matched_skills"], res["reasons"][:6], res["mode_label"]


def evaluate_role_match(
    role_title: str,
    profile: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Expert Recruiter Role Match Evaluation.
    Evaluates how well the candidate profile, experience highlights, seniority,
    and core competencies align with a proposed recommended job role.
    """
    if not role_title:
        return {
            "score": 75,
            "match_label": "General Fit",
            "badge_color": "#475569",
            "badge_bg": "#f1f5f9",
            "badge_border": "#cbd5e1",
            "rationale": "General alignment with candidate career profile.",
            "matched_skills": [],
        }

    cand_headline = (profile.get("headline") or profile.get("target_role") or "Professional").lower()
    core_skills = profile.get("core_skills") or []
    summary = (profile.get("summary") or "").lower()
    years_exp = (profile.get("years_of_experience") or profile.get("experience_level") or "").lower()

    role_clean = role_title.strip()
    role_lower = role_clean.lower()

    score = 75.0

    # 1. Headline / Title Similarity
    cand_tokens = [t for t in re.split(r"[\s/,-]+", cand_headline) if len(t) > 2]
    role_tokens = [t for t in re.split(r"[\s/,-]+", role_lower) if len(t) > 2]

    # Exact or near-exact match
    if cand_headline in role_lower or role_lower in cand_headline:
        score += 12.0
    else:
        shared_tokens = [t for t in role_tokens if t in cand_tokens]
        if shared_tokens:
            score += min(10.0, len(shared_tokens) * 3.5)

    # Domain keyword alignment (AI, Data, Eng, Product, Cloud, etc.)
    domains = [
        ("ai", ["ai", "agent", "agentic", "llm", "machine learning", "ml", "nlp", "deep learning", "prompt"]),
        ("software", ["software", "engineer", "developer", "backend", "frontend", "full stack", "fullstack", "platform", "systems", "architect"]),
        ("data", ["data", "analytics", "database", "sql", "pipeline", "etl", "bi"]),
        ("cloud", ["cloud", "devops", "sre", "infrastructure", "kubernetes", "aws", "gcp", "azure"]),
        ("product", ["product", "roadmap", "strategy", "scrum", "agile"]),
    ]
    for _, d_kws in domains:
        cand_has = any(k in cand_headline or k in summary for k in d_kws)
        role_has = any(k in role_lower for k in d_kws)
        if cand_has and role_has:
            score += 3.0
            break

    # 2. Seniority Alignment
    role_seniority = [st for st in _SENIORITY_TOKENS if st in role_lower]
    cand_seniority = [st for st in _SENIORITY_TOKENS if st in cand_headline or st in years_exp]

    if role_seniority and cand_seniority:
        if any(rs in cand_seniority for rs in role_seniority):
            score += 4.0
        elif ("staff" in role_seniority or "lead" in role_seniority or "principal" in role_seniority) and "senior" in cand_seniority:
            score += 3.5  # Natural senior advancement
        elif "senior" in role_seniority and any(s in cand_seniority for s in ["lead", "staff", "principal"]):
            score += 3.5
        elif "junior" in role_seniority and any(s in cand_seniority for s in ["senior", "lead", "staff", "manager"]):
            score -= 4.0  # Overqualified
    elif "senior" in role_lower and any(s in years_exp for s in ["5+", "6+", "7+", "8+", "10+"]):
        score += 3.0

    # 3. Core Skills Overlap
    matched_skills = []
    text_corpus = f"{role_lower} {' '.join(role_tokens)}"
    for skill in core_skills:
        skill_term = skill.split("/")[0].split("(")[0].strip().lower()
        if len(skill_term) > 2 and (skill_term in text_corpus or any(t in skill_term for t in role_tokens)):
            matched_skills.append(skill)
            score += 2.5

    # If no specific skill matched by token, find top relevant skills from profile
    if not matched_skills and core_skills:
        matched_skills = core_skills[:2]

    final_score = int(min(98, max(75, round(score))))

    # Recruiter Rationale & Badge styling
    skills_sample = ", ".join(matched_skills[:2]) if matched_skills else "technical competencies"

    if final_score >= 93:
        match_label = "Exceptional Fit"
        badge_color = "#166534"
        badge_bg = "#f0fdf4"
        badge_border = "#bbf7d0"
        rationale = f"Direct alignment with candidate's specialized expertise in {skills_sample} and senior track record."
    elif final_score >= 86:
        match_label = "Strong Match"
        badge_color = "#1e40af"
        badge_bg = "#eff6ff"
        badge_border = "#bfdbfe"
        rationale = f"Strong strategic fit leveraging candidate's core background in {skills_sample}."
    elif final_score >= 80:
        match_label = "High Potential"
        badge_color = "#854d0e"
        badge_bg = "#fefce8"
        badge_border = "#fde68a"
        rationale = f"High-growth role complementing candidate's demonstrated background in {skills_sample}."
    else:
        match_label = "Adjacent Match"
        badge_color = "#334155"
        badge_bg = "#f1f5f9"
        badge_border = "#cbd5e1"
        rationale = f"Transferable domain alignment with candidate's problem-solving background."

    # Seniority assessment
    if role_seniority and cand_seniority:
        seniority_assessment = f"Direct alignment between candidate experience ({', '.join(cand_seniority).title()}) and target role level ({', '.join(role_seniority).title()})."
    elif role_seniority:
        seniority_assessment = f"Target role calls for {', '.join(role_seniority).title()} scope, matching candidate's career progression and demonstrated impact."
    else:
        seniority_assessment = "Leveling and scope are well-balanced with candidate's professional background."

    # Key strengths & recommendations
    primary_skills_text = ", ".join(matched_skills[:3]) if matched_skills else "core competencies"
    strengths = [
        f"Demonstrated domain depth in {primary_skills_text}.",
        f"Career track record strongly aligns with {role_clean} expectations.",
        "Demonstrated technical capability to deliver high-impact results autonomously.",
    ]
    recommendations = [
        f"Feature specific case studies and quantifiable impact in {matched_skills[0] if matched_skills else 'core domain'} on your CV.",
        f"Emphasize architectural decision-making and cross-functional leadership relevant to {role_clean}.",
        "Customize screening elevator pitch to highlight alignment with target company scale and engineering challenges.",
    ]

    # 4. Gap Analysis: What is missing to achieve 100% match?
    cand_skills_flat = " ".join([s.lower() for s in core_skills])

    if any(k in role_lower for k in ["ai", "agent", "agentic", "llm", "ml", "machine learning", "nlp"]):
        catalog_skills = [
            "Evaluation Frameworks (Ragas, TruLens)",
            "Vector DB Optimization (Qdrant, Milvus)",
            "Agent Observability (LangSmith, Phoenix)",
            "Fine-Tuning & PEFT / LoRA",
            "Model Distillation & Quantization (AWQ/GGUF)",
            "Multi-Agent Swarm Orchestration",
        ]
        catalog_exp = [
            "Quantified production throughput (e.g. 5M+ tokens/day with latency <1.5s).",
            "Documented safety guardrails, PII masking, and evaluation benchmarks.",
            "End-to-end autonomous agent workflow design with human-in-the-loop controls.",
        ]
        catalog_certs = [
            "Google Cloud Professional Machine Learning Engineer",
            "DeepLearning.AI Production AI & LLM Systems Specialization",
            "AWS Certified Machine Learning - Specialty",
        ]
    elif any(k in role_lower for k in ["data", "analytics", "pipeline", "etl"]):
        catalog_skills = [
            "Streaming Architecture (Apache Flink / Kafka)",
            "Modern Semantic Layer (dbt, Cube)",
            "Lakehouse Storage (Apache Iceberg, Delta Lake)",
            "Data Quality Frameworks (Great Expectations, Monte Carlo)",
            "Schema Registry & Distributed CDC",
        ]
        catalog_exp = [
            "Managing multi-terabyte pipelines with sub-hourly freshness SLAs.",
            "Authoring enterprise data contracts across federated analytics teams.",
            "Cloud migration from legacy warehouses to managed Lakehouses.",
        ]
        catalog_certs = [
            "Databricks Certified Data Engineer Professional",
            "Google Cloud Professional Data Engineer",
            "Snowflake SnowPro Advanced Architect",
        ]
    elif any(k in role_lower for k in ["cloud", "devops", "sre", "infrastructure", "platform"]):
        catalog_skills = [
            "Infrastructure as Code (Terraform / OpenTofu)",
            "Service Mesh (Istio / Linkerd)",
            "FinOps Cloud Cost Optimization",
            "Chaos Engineering & Automated Disaster Recovery",
            "GitOps (ArgoCD, Flux)",
        ]
        catalog_exp = [
            "Operating multi-region active-active clusters with 99.99% uptime.",
            "Leading SOC2 / ISO 27001 infrastructure security compliance audits.",
            "Designing automated canary deployments and zero-downtime rollouts.",
        ]
        catalog_certs = [
            "Certified Kubernetes Administrator (CKA)",
            "AWS Certified Solutions Architect - Professional",
            "HashiCorp Certified: Terraform Associate",
        ]
    else:
        catalog_skills = [
            "High-Throughput Distributed Systems (Kafka, gRPC)",
            "Distributed Caching & Concurrency Control (Redis Enterprise)",
            "Telemetry & Distributed Tracing (OpenTelemetry)",
            "Database Query Optimization at Scale",
            "API Gateway & Zero-Trust Authentication",
        ]
        catalog_exp = [
            "Documented architecture decisions supporting 10x traffic spikes.",
            "Driving cross-functional technical initiatives across multiple product teams.",
            "Mentoring senior engineers and defining engineering excellence standards.",
        ]
        catalog_certs = [
            "AWS Certified Solutions Architect - Professional",
            "Google Cloud Professional Cloud Architect",
            "Certified Kubernetes Application Developer (CKAD)",
        ]

    # Filter out skills already in candidate core_skills
    missing_skills = [
        s for s in catalog_skills
        if not any(
            token in cand_skills_flat
            for token in s.lower().replace("(", " ").replace(")", " ").split()
            if len(token) > 3
        )
    ][:3]
    if not missing_skills:
        missing_skills = catalog_skills[:2]

    # Filter/tailor experience gaps based on current score
    gap_points = max(2, 100 - final_score)
    experience_gaps = catalog_exp[:2]
    if any(st in role_lower for st in ["staff", "lead", "principal", "director"]):
        experience_gaps.append("Direct evidence of multi-team technical strategy and stakeholder management.")

    certifications = catalog_certs[:2]

    gap_summary = (
        f"To bridge the remaining {gap_points}% to a 100% match: "
        f"Spotlight exposure to {missing_skills[0]} and emphasize {experience_gaps[0].lower().rstrip('.')} on your resume and interview talking points."
    )

    gap_to_100 = {
        "gap_percentage": gap_points,
        "missing_skills": missing_skills,
        "experience_gaps": experience_gaps,
        "certifications": certifications,
        "summary": gap_summary,
    }

    return {
        "score": final_score,
        "match_label": match_label,
        "badge_color": badge_color,
        "badge_bg": badge_bg,
        "badge_border": badge_border,
        "rationale": rationale,
        "matched_skills": matched_skills,
        "seniority_assessment": seniority_assessment,
        "strengths": strengths,
        "recommendations": recommendations,
        "gap_to_100": gap_to_100,
    }
