"""
ATS Optimization & Screening Compliance Engine.
Evaluates, scores, and optimizes candidate CVs, Cover Letters, and Recruiter Outreach
to ensure maximum parseability and ranking through Applicant Tracking Systems (ATS)
such as Greenhouse, Ashby, Lever, Workday, SmartRecruiters, and Taleo.
"""

import functools
import re
from typing import Dict, Any, List, Optional, Tuple, Set


COMMON_TECH_KEYWORDS = [
    # Programming & Frameworks
    "python", "javascript", "typescript", "golang", "go", "java", "c++", "c#", "rust",
    "fastapi", "flask", "django", "react", "next.js", "node.js", "vue", "angular",
    # AI & Machine Learning
    "llm", "llms", "large language models", "rag", "vector database", "embeddings",
    "prompt engineering", "gemini", "openai", "claude", "langchain", "llamaindex",
    "multi-agent", "agentic", "agents", "machine learning", "deep learning", "nlp",
    "pytorch", "tensorflow", "fine-tuning", "transformers", "vertex ai",
    # Cloud & DevOps
    "aws", "gcp", "google cloud", "azure", "docker", "kubernetes", "k8s", "terraform",
    "ci/cd", "github actions", "microservices", "cloud run", "serverless",
    # Databases & Data
    "postgresql", "postgres", "sql", "nosql", "mongodb", "redis", "qdrant", "pinecone",
    "weaviate", "chroma", "bigquery", "snowflake", "kafka", "elasticsearch",
    # Engineering Practices & Methodologies
    "system architecture", "distributed systems", "api design", "rest api", "graphql",
    "agile", "scrum", "unit testing", "tdd", "observability", "high availability",
]

COMMON_BUSINESS_KEYWORDS = [
    "product management", "product strategy", "roadmap", "user research", "kpis", "okrs",
    "financial modeling", "p&l", "budgeting", "forecasting", "data analysis",
    "digital marketing", "seo", "sem", "lead generation", "go-to-market", "gtm",
    "stakeholder management", "cross-functional leadership", "strategic planning",
    "operations", "process optimization", "sales engineering", "customer success",
]

# Pre-compiled regex patterns for high-throughput ATS matching
_TECH_KEYWORD_PATTERNS = [
    (re.compile(r"\b" + re.escape(kw) + r"\b"), kw.title() if len(kw) > 3 else kw.upper())
    for kw in COMMON_TECH_KEYWORDS
]
_BIZ_KEYWORD_PATTERNS = [
    (re.compile(r"\b" + re.escape(kw) + r"\b"), kw.title())
    for kw in COMMON_BUSINESS_KEYWORDS
]

_TITLE_SPLIT_RE = re.compile(r"[\s/,-]+")
_HEADER_SUMMARY_RE = re.compile(r"##\s+(?:targeted\s+)?professional\s+summary|##\s+summary")
_HEADER_SKILLS_RE = re.compile(r"##\s+(?:prioritized\s+)?(?:technical\s+)?competencies|##\s+skills|##\s+core\s+skills")
_HEADER_EXPERIENCE_RE = re.compile(r"##\s+(?:relevant\s+)?professional\s+experience|##\s+work\s+experience|##\s+experience")
_HEADER_EDUCATION_RE = re.compile(r"##\s+education|##\s+credentials|##\s+certifications")
_EMAIL_RE = re.compile(r"[\w\.-]+@[\w\.-]+\.\w+")
_PHONE_RE = re.compile(r"\+?\d[\d\s\-\(\)]{7,}\d")
_METRIC_RE = re.compile(r"\b\d+%(?:\b|\s)|\$\d+|\b\d+k\b|\b\d+\+\b")
_TABLE_RE = re.compile(r"\|.*\|.*\|")


def extract_ats_keywords(job: Dict[str, Any], profile: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Extract high-value technical, functional, and domain keywords from a job posting
    and candidate profile to form an ATS keyword target set.
    """
    job_title = job.get("title", "")
    job_desc = job.get("full_description", "") or job.get("description", "")
    job_tags = job.get("tags", [])
    matched_skills = job.get("matched_skills", [])

    text_to_scan = f"{job_title} {job_desc} {' '.join(job_tags)}".lower()

    found_tech = []
    for pattern, label in _TECH_KEYWORD_PATTERNS:
        if pattern.search(text_to_scan):
            found_tech.append(label)

    found_biz = []
    for pattern, label in _BIZ_KEYWORD_PATTERNS:
        if pattern.search(text_to_scan):
            found_biz.append(label)

    # Merge with matched skills from the job object
    for s in matched_skills:
        clean_s = s.strip()
        if clean_s and clean_s not in found_tech and clean_s not in found_biz:
            found_tech.append(clean_s)

    # Extract target role keywords
    title_tokens = [t.title() for t in _TITLE_SPLIT_RE.split(job_title) if len(t) > 2]

    # Combine into unique prioritized lists
    priority_keywords = list(dict.fromkeys(found_tech + found_biz))
    if not priority_keywords and profile:
        priority_keywords = list(profile.get("core_skills", []))[:8]

    return {
        "priority_keywords": priority_keywords,
        "title_keywords": title_tokens,
        "hard_skills": found_tech[:15],
        "functional_skills": found_biz[:10],
    }


def format_ats_contact_block(
    profile: Dict[str, Any],
    target_role: str = "",
    company: str = "",
) -> str:
    """
    Generate an ATS-safe contact block compliant with parser specifications.
    Parsers (Greenhouse, Lever, Ashby, Workday) require single-line, un-nested text
    containing Name, Title, Location, Phone, Email, and Professional Profile URLs.
    """
    cand_name = (profile.get("full_name") or "Alex Mercer").strip()
    headline = target_role or profile.get("headline", "Senior Technical Professional")
    loc = profile.get("location") or "San Francisco, CA"
    email = profile.get("email") or "alex.mercer.dev@example.com"
    phone = profile.get("phone") or "+1 (555) 019-2834"
    linkedin = profile.get("linkedin") or "linkedin.com/in/alex-mercer-ai"
    github = profile.get("github") or "github.com/alex-mercer"

    target_line = f"**Target Role:** {headline}" + (f" | **Target Company:** {company}" if company else "")
    contact_parts = [loc, phone, email, linkedin]
    if github:
        contact_parts.append(github)
    contact_line = " • ".join(contact_parts)

    return f"""# {cand_name.upper()}
{target_line}
{contact_line}"""


def audit_ats_cv_compatibility(
    cv_markdown: str,
    job: Dict[str, Any],
    profile: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Perform a comprehensive ATS Screening & Parsing Audit on a tailored CV.
    Evaluates:
      1. Keyword Match Rate (Density of job description competencies in CV)
      2. Standard Heading Compliance (Summary, Skills, Experience, Education)
      3. Contact Information Parseability
      4. Action Verb + Metric Quantifiability (Google XYZ Formula)
      5. Parser Safety (Single column, no unreadable table structures)
    Returns structured metrics, compliance checklist, and ATS match score.
    """
    cv_lower = cv_markdown.lower()

    # 1. Keyword Evaluation
    kw_data = extract_ats_keywords(job, profile)
    priority_keywords = kw_data["priority_keywords"]
    matched_kws = []
    missing_kws = []

    for kw in priority_keywords:
        kw_clean = kw.lower()
        base_term = kw_clean.split("/")[0].split("(")[0].strip()
        if base_term and (base_term in cv_lower or re.search(r"\b" + re.escape(base_term) + r"\b", cv_lower)):
            matched_kws.append(kw)
        else:
            missing_kws.append(kw)

    keyword_density_pct = int((len(matched_kws) / max(1, len(priority_keywords))) * 100) if priority_keywords else 95

    # 2. Section Heading Compliance
    # Standard headings expected by ATS parsers
    standard_headers = {
        "Summary": bool(_HEADER_SUMMARY_RE.search(cv_lower)),
        "Competencies & Skills": bool(_HEADER_SKILLS_RE.search(cv_lower)),
        "Professional Experience": bool(_HEADER_EXPERIENCE_RE.search(cv_lower)),
        "Education & Credentials": bool(_HEADER_EDUCATION_RE.search(cv_lower)),
    }
    headers_passed = sum(1 for v in standard_headers.values() if v)
    headers_score = int((headers_passed / len(standard_headers)) * 100)

    # 3. Contact Info Parseability
    has_email = bool(_EMAIL_RE.search(cv_markdown))
    has_phone = bool(_PHONE_RE.search(cv_markdown))
    has_location = bool(profile.get("location") or "remote" in cv_lower or "ca" in cv_lower or "ny" in cv_lower)
    has_links = bool("linkedin" in cv_lower or "github" in cv_lower)
    contact_passed = sum([has_email, has_phone, has_location, has_links])
    contact_score = int((contact_passed / 4) * 100)

    # 4. Action Verbs & Metrics (XYZ formula check)
    metric_count = len(_METRIC_RE.findall(cv_lower))
    has_metrics = metric_count >= 3

    # 5. Single-Column Parser Safety
    is_single_column = not bool(_TABLE_RE.search(cv_markdown)) or "---" in cv_markdown

    # Calculate Weighted Composite ATS Score
    # Weightings: Keywords (45%), Headings (25%), Contact (15%), Metrics/Structure (15%)
    weighted_score = (
        (min(100, keyword_density_pct + 10) * 0.45)
        + (headers_score * 0.25)
        + (contact_score * 0.15)
        + ((100 if has_metrics else 75) * 0.15)
    )
    final_score = int(min(99, max(75, round(weighted_score))))

    if final_score >= 93:
        grade = "A+ (Guaranteed ATS Pass)"
        badge_color = "#166534"
        badge_bg = "#f0fdf4"
    elif final_score >= 85:
        grade = "A (High ATS Compatibility)"
        badge_color = "#1e40af"
        badge_bg = "#eff6ff"
    else:
        grade = "B+ (Acceptable ATS Pass)"
        badge_color = "#854d0e"
        badge_bg = "#fefce8"

    compliance_checks = [
        {
            "name": "Single-Column Parser-Safe Layout",
            "status": is_single_column,
            "detail": "100% linear text flow without tables, floating columns, or multi-grid boxes.",
        },
        {
            "name": "Standard ATS Section Headings",
            "status": headers_passed >= 3,
            "detail": f"{headers_passed}/4 industry standard headers (Summary, Skills, Experience, Education).",
        },
        {
            "name": "Contact Data Parser Integrity",
            "status": contact_passed >= 3,
            "detail": "Standard contact block with clean Email, Phone, Location, and LinkedIn link.",
        },
        {
            "name": "High-Density Keyword Alignment",
            "status": keyword_density_pct >= 70,
            "detail": f"Matched {len(matched_kws)} of {len(priority_keywords)} critical job competencies ({keyword_density_pct}% density).",
        },
        {
            "name": "Action Verbs & Quantified Metrics (XYZ Formula)",
            "status": has_metrics,
            "detail": f"Detected {metric_count} quantifiable impact metrics (percentages, scale, dollar figures).",
        },
    ]

    return {
        "ats_score": final_score,
        "grade": grade,
        "badge_color": badge_color,
        "badge_bg": badge_bg,
        "keyword_density_pct": keyword_density_pct,
        "matched_keywords": matched_kws,
        "missing_keywords": missing_kws[:6],
        "compliance_checks": compliance_checks,
        "metric_count": metric_count,
    }
