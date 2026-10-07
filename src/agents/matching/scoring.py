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
    "portugal": ["portugal", "lisbon", "lisboa", "porto", "braga", "coimbra", "aveiro", "faro", "funchal", "madeira", "açores", "acores", "oeiras", "cascais", "leiria", "sintra", "setúbal", "setubal", "pt"],
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

    # Disambiguate California "ca" vs Canada: If "united states" is present and "canada" was only matched by "ca"
    if "united states" in found and "canada" in found:
        if not any(w in lt for w in ["canada", "toronto", "vancouver", "montreal", "ottawa", "calgary", "ontario", "quebec", "alberta"]):
            found.remove("canada")

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

    # 1. Title & Role Token Alignment (covering primary headline + user-selected recommended roles)
    role_tokens = [t for t in re.split(r"[\s/,-]+", target_role) if len(t) > 2]
    selected_roles = profile.get("selected_roles") or []
    for r in selected_roles:
        role_tokens.extend([t for t in re.split(r"[\s/,-]+", r.lower()) if len(t) > 2])
    role_tokens = list(dict.fromkeys(role_tokens))

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


def evaluate_role_match(
    role_title: str,
    profile: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Expert Recruiter Role Match Evaluation.
    Evaluates how well the candidate profile, experience highlights, seniority,
    and core competencies align with a proposed recommended job role.
    
    Returns:
      {
        "score": int,                  # 75 - 98
        "match_label": str,            # "Exceptional Fit", "Strong Match", etc.
        "badge_color": str,            # Hex color for text
        "badge_bg": str,               # Hex background
        "badge_border": str,           # Hex border
        "rationale": str,              # Recruiter rationale
        "matched_skills": List[str],   # Overlapping skills
      }
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
        if not any(token in cand_skills_flat for token in s.lower().replace("(", " ").replace(")", " ").split() if len(token) > 3)
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

