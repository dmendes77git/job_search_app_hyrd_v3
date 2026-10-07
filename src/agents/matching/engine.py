"""
Core Semantic Matching Engine & Role Match Evaluation.
Implements multi-dimensional scoring algorithms (role, skill, freshness, leveling, salary, location)
and deep recruiter gap analysis.
"""

import logging
import re
from typing import Any, Dict, List, Tuple

from src.utils.date_utils import parse_days_since_posted
from src.utils.salary_evaluator import parse_numeric_salary

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


def calculate_semantic_fit(
    job: Dict[str, Any],
    profile: Dict[str, Any],
    target_countries: List[str],
) -> Tuple[int, List[str], List[str], str]:
    """
    Profile-driven multi-dimensional semantic scoring engine:
      1. Target Role & Synonym Alignment (0-45 points)
      2. Core Anchors vs. Secondary Skills Overlap (0-35 points)
      3. Freshness / Recency Boost (-3 to +4 points)
      4. Experience & Leveling (YoE) Calibration (-5 to +3 points)
      5. Salary Fit Factor (-4 to +3 points)
      6. Work Mode & Country/Location Alignment (0-20 points)
    Returns:
      (fit_score, matched_skills, reasons, job_type_label)
    Also populates job['matched_skills'] and job['missing_skills'].
    """
    target_role = (profile.get("headline") or profile.get("target_role") or "Professional").lower()
    core_skills = profile.get("core_skills") or []
    job_title = job.get("title", "").lower()
    job_text = (
        job.get("title", "")
        + " "
        + job.get("description", "")
        + " "
        + " ".join(job.get("tags", []))
    ).lower()

    mode_label, is_remote, is_hybrid, is_onsite = determine_work_mode(job)
    user_work_mode = (profile.get("work_mode") or "Remote Only").lower()

    score = 65.0  # Base calibration score

    # 1. Title & Role Token Alignment
    role_tokens = [t for t in re.split(r"[\s/,-]+", target_role) if len(t) > 2]
    selected_roles = profile.get("selected_roles") or []
    for r in selected_roles:
        role_tokens.extend([t for t in re.split(r"[\s/,-]+", r.lower()) if len(t) > 2])

    # Expand synonyms for the target role
    synonym_titles = expand_role_synonyms(target_role)
    for syn in synonym_titles:
        role_tokens.extend([t for t in re.split(r"[\s/,-]+", syn.lower()) if len(t) > 2])

    role_tokens = list(dict.fromkeys(role_tokens))

    matched_role_tokens = [t for t in role_tokens if t in job_title]
    if matched_role_tokens:
        score += min(24.0, len(matched_role_tokens) * 8.0)
    elif any(t in job_text for t in role_tokens):
        score += 8.0

    # Common seniority & responsibility token alignment
    for st in _SENIORITY_TOKENS:
        if st in target_role and st in job_title:
            score += 3.0

    # 2. Must-Have Core Anchors vs. Secondary Skills Overlap
    core_anchors = []
    secondary_skills = []
    role_token_set = set(role_tokens)
    for idx, skill in enumerate(core_skills):
        skill_term = skill.split("/")[0].split("(")[0].strip().lower()
        if idx < 3 or any(rt in skill_term for rt in role_token_set):
            core_anchors.append(skill)
        else:
            secondary_skills.append(skill)

    matched_skills = []
    matched_core_anchors = []
    matched_secondary = []

    for skill in core_anchors:
        base_term = skill.split("/")[0].split("(")[0].strip().lower()
        if len(base_term) > 2 and (base_term in job_text or base_term in job_title):
            matched_skills.append(skill)
            matched_core_anchors.append(skill)
            score += 6.0  # Core anchor bonus

    for skill in secondary_skills:
        base_term = skill.split("/")[0].split("(")[0].strip().lower()
        if len(base_term) > 2 and (base_term in job_text or base_term in job_title):
            matched_skills.append(skill)
            matched_secondary.append(skill)
            score += 2.0  # Secondary skill bonus

    # Missing Core Anchor penalty
    if core_skills and not matched_core_anchors and not matched_skills:
        matched_skills = core_skills[:2]
        score -= 4.0

    # Tech Stack & Missing Skills Extraction
    extracted_job_tech = extract_tech_skills(job_text)
    cand_skill_lower = {s.lower() for s in core_skills}
    missing_tech = [
        t for t in extracted_job_tech
        if not any(t.lower() in cs or cs in t.lower() for cs in cand_skill_lower)
    ]
    job["matched_skills"] = matched_skills
    job["missing_skills"] = missing_tech[:4]

    # 3. Recency & Freshness Boost
    days_count, days_label = parse_days_since_posted(job.get("posted", "Recent"), job_id=job.get("id", ""))
    job["days_since_posted"] = days_count
    job["days_since_posted_label"] = days_label
    freshness_reason = None
    if days_count <= 3:
        score += 4.0
        freshness_reason = f"🔥 Fresh requisition: Published {days_count} {'day' if days_count == 1 else 'days'} ago with active hiring momentum."
    elif days_count <= 7:
        score += 2.0
        freshness_reason = "Active requisition: Published within the last 7 days."
    elif days_count > 21:
        score -= 3.0
        freshness_reason = "Aging requisition (>3 weeks): Likely in advanced interview stages."

    # 4. Experience & Leveling (YoE) Calibration
    req_yoe = extract_required_years_experience(job_text)
    cand_yoe_str = str(profile.get("years_of_experience") or profile.get("experience_level") or "")
    cand_yoe_m = re.search(r"(\d+)", cand_yoe_str)
    cand_yoe = int(cand_yoe_m.group(1)) if cand_yoe_m else None
    yoe_reason = None

    if req_yoe is not None and cand_yoe is not None:
        if cand_yoe >= req_yoe:
            score += 3.0
            yoe_reason = f"Leveling match: Your {cand_yoe}+ years experience fulfills the required {req_yoe}+ years."
        elif 0 < (req_yoe - cand_yoe) <= 2:
            score += 1.5
            yoe_reason = f"High-growth stretch opportunity: Requisition asks for {req_yoe} yrs (you offer {cand_yoe}+ yrs)."
        elif cand_yoe >= 8 and req_yoe <= 2:
            score -= 10.0
            yoe_reason = f"Scope advisory: Role specifies {req_yoe} yrs, which is below your senior background."

    # Seniority mismatch check: penalize entry/junior roles for senior candidates
    cand_is_senior = (cand_yoe is not None and cand_yoe >= 6) or any(
        st in target_role for st in ["senior", "lead", "staff", "principal", "director", "head"]
    )
    job_is_junior = any(
        jt in job_title or jt in job_text
        for jt in ["entry level", "junior", "intern", "associate"]
    )
    if cand_is_senior and job_is_junior:
        score -= 8.0
        if not yoe_reason:
            yoe_reason = "Leveling advisory: Entry/junior level role does not match your senior background."

    # 5. Salary Fit Factor
    desired_sal_raw = (
        profile.get("preferred_min_salary")
        or profile.get("desired_salary")
        or profile.get("min_salary")
        or ""
    )
    desired_sal = parse_numeric_salary(str(desired_sal_raw))
    job_sal = parse_numeric_salary(str(job.get("salary", "")))
    salary_reason = None

    if desired_sal and job_sal:
        if job_sal >= desired_sal:
            score += 3.0
            salary_reason = "Compensation alignment: Offered salary meets or exceeds your minimum target."
        elif job_sal < desired_sal * 0.75 and desired_sal > 30000:
            score -= 4.0
            salary_reason = "Compensation advisory: Posted compensation is below your target minimum threshold."

    # 6. Work Mode & Location Alignment
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

    if matched_core_anchors:
        reasons.append(f"Core anchor alignment: Strong match on {', '.join(matched_core_anchors[:3])}.")
    elif len(matched_skills) >= 2:
        reasons.append(f"Direct alignment with candidate skills: {', '.join(matched_skills[:3])}.")

    if freshness_reason:
        reasons.append(freshness_reason)
    if yoe_reason:
        reasons.append(yoe_reason)
    if salary_reason:
        reasons.append(salary_reason)

    if any(t in job_title for t in ["senior", "lead", "manager", "director", "head", "staff"]):
        reasons.append(f"Seniority level aligns with your career trajectory in {target_role.title()}.")

    final_score = int(min(98, max(72, round(score))))
    return final_score, matched_skills, reasons[:4], mode_label


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
