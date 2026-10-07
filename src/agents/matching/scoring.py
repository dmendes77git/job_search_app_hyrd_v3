"""
Semantic Matching & Geographic Location Alignment Engine.
Scores candidate profiles against job postings across title alignment,
skill overlap, work mode preferences, and geographic eligibility.
"""

import functools
import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from src.utils.date_utils import parse_days_since_posted
from src.utils.salary_evaluator import parse_numeric_salary

logger = logging.getLogger("Hyrd.Scoring")

# Industry-standard role synonym and equivalence mappings for query expansion
ROLE_SYNONYMS: Dict[str, List[str]] = {
    "ai engineer": ["machine learning engineer", "ml engineer", "llm engineer", "applied ai scientist", "genai engineer", "ai research engineer"],
    "machine learning": ["ai engineer", "data scientist", "deep learning engineer", "mlops engineer", "applied scientist"],
    "software engineer": ["software developer", "full stack engineer", "backend engineer", "systems engineer", "platform engineer"],
    "full stack": ["fullstack engineer", "full-stack developer", "web engineer", "software engineer"],
    "backend": ["server engineer", "distributed systems engineer", "backend developer", "api engineer"],
    "frontend": ["front end engineer", "ui engineer", "web developer", "react developer"],
    "devops": ["cloud engineer", "site reliability engineer", "sre", "platform engineer", "infrastructure engineer"],
    "data engineer": ["analytics engineer", "big data engineer", "data platform engineer", "etl developer"],
    "data scientist": ["machine learning scientist", "data analyst", "applied scientist", "statistician"],
    "product manager": ["technical product manager", "product lead", "group product manager", "product owner"],
}


def expand_role_synonyms(role_title: str) -> List[str]:
    """
    Expand a job role title to include common industry-standard synonyms and equivalences.
    """
    if not role_title:
        return []
    clean = role_title.strip()
    clean_lower = clean.lower()
    results = [clean]
    for key, syns in ROLE_SYNONYMS.items():
        if key in clean_lower:
            for s in syns:
                if s not in clean_lower:
                    results.append(s.title())
    return list(dict.fromkeys(results))


# Recognized technology stack keywords for tech stack alignment & gap extraction
COMMON_TECH_STACK_KEYWORDS: List[str] = [
    # Languages
    "python", "typescript", "javascript", "golang", "rust", "java", "c++", "c#", "ruby", "scala", "swift", "kotlin",
    # AI & ML
    "pytorch", "tensorflow", "scikit-learn", "llm", "rag", "langchain", "llamaindex", "huggingface", "transformers",
    "vector db", "pinecone", "weaviate", "qdrant", "milvus", "agentic", "agents", "openai", "gemini",
    # Web Frameworks
    "react", "next.js", "vue", "angular", "node.js", "django", "fastapi", "flask", "spring boot", "graphql", "rest api",
    # Cloud, DevOps & Containers
    "docker", "kubernetes", "k8s", "terraform", "aws", "gcp", "azure", "ci/cd", "github actions", "helm", "ansible",
    # Databases & Streaming
    "postgresql", "postgres", "mysql", "mongodb", "redis", "elasticsearch", "kafka", "flink", "spark", "snowflake", "bigquery", "dbt",
    # Architecture & Tools
    "microservices", "distributed systems", "linux", "git", "grpc", "agile",
]


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
    job_text = (job.get("title", "") + " " + job.get("description", "") + " " + " ".join(job.get("tags", []))).lower()

    mode_label, is_remote, is_hybrid, is_onsite = determine_work_mode(job)
    user_work_mode = (profile.get("work_mode") or "Remote Only").lower()

    score = 65.0  # Base calibration score

    # 1. Title & Role Token Alignment (covering primary headline + user-selected recommended roles + synonyms)
    role_tokens = [t for t in re.split(r"[\s/,-]+", target_role) if len(t) > 2]
    selected_roles = profile.get("selected_roles") or []
    for r in selected_roles:
        role_tokens.extend([t for t in re.split(r"[\s/,-]+", r.lower()) if len(t) > 2])

    # Expand synonyms for the target role (Point 1.C)
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

    # 2. Must-Have Core Anchors vs. Secondary Skills Overlap (Point 2.B)
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

    # Tech Stack & Missing Skills Extraction (Point 3.A)
    extracted_job_tech = extract_tech_skills(job_text)
    cand_skill_lower = {s.lower() for s in core_skills}
    missing_tech = [
        t for t in extracted_job_tech
        if not any(t.lower() in cs or cs in t.lower() for cs in cand_skill_lower)
    ]
    job["matched_skills"] = matched_skills
    job["missing_skills"] = missing_tech[:4]

    # 3. Recency & Freshness Boost (Point 2.A)
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

    # 4. Experience & Leveling (YoE) Calibration (Point 2.C)
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
    cand_is_senior = (cand_yoe is not None and cand_yoe >= 6) or any(st in target_role for st in ["senior", "lead", "staff", "principal", "director", "head"])
    job_is_junior = any(jt in job_title or jt in job_text for jt in ["entry level", "junior", "intern", "associate"])
    if cand_is_senior and job_is_junior:
        score -= 8.0
        if not yoe_reason:
            yoe_reason = "Leveling advisory: Entry/junior level role does not match your senior background."


    # 5. Salary Fit Factor (Point 2.D)
    desired_sal_raw = profile.get("preferred_min_salary") or profile.get("desired_salary") or profile.get("min_salary") or ""
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


def rerank_top_jobs_with_gemini(
    top_jobs: List[Dict[str, Any]],
    profile: Dict[str, Any],
    api_key: Optional[str] = None,
    limit: int = 15,
) -> List[Dict[str, Any]]:
    """
    Pass 2 Hybrid Reranker: Uses Google Gemini to perform deep semantic reranking
    on the top candidate pool, evaluating nuanced cultural, technical, and scope alignment.
    Falls back gracefully to existing heuristic rank if Gemini is unavailable or errors.
    """
    if not top_jobs or len(top_jobs) <= 1:
        return top_jobs

    import os
    effective_key = api_key or os.environ.get("GEMINI_API_KEY", "")
    if not effective_key:
        return top_jobs

    candidates_to_rerank = top_jobs[:limit]

    jobs_summary = []
    for j in candidates_to_rerank:
        jobs_summary.append({
            "id": j.get("id"),
            "title": j.get("title"),
            "company": j.get("company"),
            "current_score": j.get("fit_score", 85),
            "description_snippet": (j.get("description", "") or "")[:220],
        })

    prompt = f"""You are an elite executive talent recruiter.
Evaluate these {len(jobs_summary)} job opportunities against this candidate profile:
Candidate Target Role: {profile.get("headline") or profile.get("target_role")}
Years Experience: {profile.get("years_of_experience")}
Core Skills: {", ".join((profile.get("core_skills") or [])[:8])}
Summary: {profile.get("summary", "")[:250]}

Jobs to Evaluate:
{json.dumps(jobs_summary, indent=2)}

For each job, provide a calibrated score adjustment (an integer between -4 and +4) and a concise 1-sentence executive recruiter verdict on why this role fits the candidate.
Return JSON formatted as:
[
  {{"id": "job_id", "score_adjustment": 2, "recruiter_verdict": "..."}}
]
"""
    try:
        from src.utils.gemini_client import generate_gemini_json
        result = generate_gemini_json(prompt, api_key=effective_key)
        if isinstance(result, list):
            eval_map = {item.get("id"): item for item in result if isinstance(item, dict) and "id" in item}
            for j in candidates_to_rerank:
                jid = j.get("id")
                if jid in eval_map:
                    adj = int(eval_map[jid].get("score_adjustment", 0))
                    adj = max(-4, min(4, adj))
                    new_score = int(min(99, max(72, j.get("fit_score", 85) + adj)))
                    j["fit_score"] = new_score
                    verdict = eval_map[jid].get("recruiter_verdict")
                    if verdict:
                        j["gemini_verdict"] = verdict
                        if "key_reasons" in j and isinstance(j["key_reasons"], list):
                            j["key_reasons"].insert(0, f"🤖 Recruiter Verdict: {verdict}")

            candidates_to_rerank.sort(key=lambda x: x.get("fit_score", 0), reverse=True)
            return candidates_to_rerank + top_jobs[limit:]
    except Exception as e:
        logger.debug(f"Gemini reranking skipped ({e}), using heuristic scores.")

    return top_jobs


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

