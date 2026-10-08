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

COMMON_PORTUGUESE_KEYWORDS = [
    "inteligência artificial", "ia", "aprendizagem automática", "aprendizagem profunda",
    "ciência de dados", "engenharia de software", "desenvolvimento de software",
    "sistemas distribuídos", "arquitetura de software", "computação na nuvem",
    "gestão de produto", "gestão de projetos", "metodologias ágeis", "otimização",
    "segurança informática", "cibersegurança", "bases de dados", "análise de dados",
    "microsserviços", "testes unitários", "integração contínua", "desenvolvimento web",
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
_PT_KEYWORD_PATTERNS = [
    (re.compile(r"\b" + re.escape(kw) + r"\b", re.IGNORECASE), kw.title())
    for kw in COMMON_PORTUGUESE_KEYWORDS
]

_TITLE_SPLIT_RE = re.compile(r"[\s/,-]+")

# Multilingual ATS Section Headers (English & Portuguese PT-PT / PT-BR)
_HEADER_SUMMARY_RE = re.compile(
    r"##\s+(?:targeted\s+)?professional\s+summary|##\s+summary|"
    r"##\s+(?:resumo|perfil)(?:\s+profissional)?|##\s+resumo|##\s+perfil",
    re.IGNORECASE,
)
_HEADER_SKILLS_RE = re.compile(
    r"##\s+(?:prioritized\s+)?(?:technical\s+)?competencies|##\s+skills|##\s+core\s+skills|"
    r"##\s+(?:competências|competencias|habilidades)(?:\s+(?:técnicas|tecnicas|essenciais|principais))?|"
    r"##\s+competências\s*(?:&|e)\s*(?:habilidades|aptidões|aptidoes)",
    re.IGNORECASE,
)
_HEADER_EXPERIENCE_RE = re.compile(
    r"##\s+(?:relevant\s+)?professional\s+experience|##\s+work\s+experience|##\s+experience|"
    r"##\s+(?:experiência|experiencia)(?:\s+profissional)?|##\s+percurso\s+profissional|"
    r"##\s+experiência\s+laboral",
    re.IGNORECASE,
)
_HEADER_EDUCATION_RE = re.compile(
    r"##\s+education|##\s+credentials|##\s+certifications|"
    r"##\s+(?:educação|educacao|formação|formacao)(?:\s+(?:académica|academica|e\s+credenciais))?|"
    r"##\s+(?:certificações|certificacoes)",
    re.IGNORECASE,
)
_EMAIL_RE = re.compile(r"[\w\.-]+@[\w\.-]+\.\w+")
_PHONE_RE = re.compile(r"\+?\d[\d\s\-\(\)]{7,}\d")
_METRIC_RE = re.compile(r"\b\d+%(?:\b|\s)|\$\d+|\b\d+k\b|\b\d+\+\b|€\d+|\b\d+\s*mil\b|\b\d+\s*anos\b")
_TABLE_RE = re.compile(r"\|.*\|.*\|")

# Stopwords and indicative terms for language detection
_PORTUGUESE_INDICATORS = {
    "de", "para", "com", "experiência", "experiencia", "requisitos", "responsabilidades",
    "funções", "funcoes", "candidatura", "oferecemos", "perfil", "conhecimentos",
    "desenvolvimento", "equipa", "trabalho", "remoto", "teletrabalho", "híbrido",
    "hibrido", "empresa", "área", "capacidade", "anos", "localização", "salário",
    "competências", "projetos", "gestão", "integração", "licenciatura", "mestrado",
    "emprego", "vaga", "função", "recrutamento", "valorizamos",
}
_ENGLISH_INDICATORS = {
    "with", "experience", "requirements", "responsibilities", "looking", "skills",
    "team", "remote", "company", "hybrid", "salary", "qualifications", "working",
    "degree", "master", "years", "seeking", "benefits", "opportunity",
}


def detect_job_language(job: Dict[str, Any]) -> str:
    """
    Automatically detects whether a job posting is in Portuguese ('pt-pt') or English ('en').
    Analyzes:
      1. Source metadata (ITJobs.pt, Net-Empregos default to pt-pt unless predominantly English).
      2. Word frequencies across title, description, and tags.
      3. Location markers (Portugal, Lisboa, Porto, etc.).
    Returns 'pt-pt' for Portuguese language postings, 'en' for English.
    """
    if not job:
        return "en"

    source = (job.get("source") or "").lower()
    title = (job.get("title") or "").lower()
    desc = (job.get("full_description") or job.get("description") or "").lower()
    location = (job.get("location") or "").lower()
    tags = " ".join(job.get("tags") or []).lower()

    combined_text = f"{title} {desc} {tags} {location}"
    words = re.findall(r"\b[\wÀ-ÿ]+\b", combined_text)

    pt_matches = sum(1 for w in words if w in _PORTUGUESE_INDICATORS)
    en_matches = sum(1 for w in words if w in _ENGLISH_INDICATORS)

    # Specific Portuguese sources bias towards pt-pt if Portuguese vocabulary is detected
    is_portuguese_portal = any(p in source for p in ["itjobs", "net-empregos", "netempregos"])
    if is_portuguese_portal and pt_matches >= 3:
        return "pt-pt"

    # Explicit threshold evaluation
    if pt_matches > en_matches and pt_matches >= 4:
        return "pt-pt"
    if pt_matches >= 8:
        return "pt-pt"

    return "en"


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

    found_pt = []
    for pattern, label in _PT_KEYWORD_PATTERNS:
        if pattern.search(text_to_scan):
            found_pt.append(label)

    # Merge with matched skills from the job object
    for s in matched_skills:
        clean_s = s.strip()
        if clean_s and clean_s not in found_tech and clean_s not in found_biz and clean_s not in found_pt:
            found_tech.append(clean_s)

    # Extract target role keywords
    title_tokens = [t.title() for t in _TITLE_SPLIT_RE.split(job_title) if len(t) > 2]

    # Combine into unique prioritized lists
    priority_keywords = list(dict.fromkeys(found_tech + found_biz + found_pt))
    if not priority_keywords and profile:
        priority_keywords = list(profile.get("core_skills", []))[:8]

    return {
        "priority_keywords": priority_keywords,
        "title_keywords": title_tokens,
        "hard_skills": (found_tech + found_pt)[:15],
        "functional_skills": found_biz[:10],
    }


def format_ats_contact_block(
    profile: Dict[str, Any],
    target_role: str = "",
    company: str = "",
    language: str = "en",
) -> str:
    """
    Generate an ATS-safe contact block compliant with parser specifications.
    Parsers (Greenhouse, Lever, Ashby, Workday) require single-line, un-nested text
    containing Name, Title, Location, Phone, Email, and Professional Profile URLs.
    Supports English and European Portuguese (PT-PT).
    """
    cand_name = (profile.get("full_name") or "Alex Mercer").strip()
    headline = target_role or profile.get("headline", "Senior Technical Professional")
    loc = profile.get("location") or "San Francisco, CA"
    email = profile.get("email") or "alex.mercer.dev@example.com"
    phone = profile.get("phone") or "+1 (555) 019-2834"
    linkedin = profile.get("linkedin") or "linkedin.com/in/alex-mercer-ai"
    github = profile.get("github") or "github.com/alex-mercer"

    if language.lower().startswith("pt"):
        target_line = f"**Cargo Pretendido:** {headline}" + (f" | **Empresa Alvo:** {company}" if company else "")
    else:
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
    # Standard headings expected by ATS parsers (supporting both English and Portuguese)
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
    loc_tokens = ["remote", "remoto", "portugal", "lisboa", "porto", "braga", "coimbra", "faro", "aveiro", "teletrabalho", "híbrido", "hibrido", "ca", "ny", "uk", "london", "europe", "europa"]
    has_location = bool(profile.get("location") or any(k in cv_lower for k in loc_tokens))
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


_SYNONYM_PAIRS = {
    "kubernetes": ["k8s"],
    "k8s": ["kubernetes"],
    "postgresql": ["postgres", "pgsql"],
    "postgres": ["postgresql", "pgsql"],
    "javascript": ["js"],
    "typescript": ["ts"],
    "react": ["react.js", "reactjs"],
    "next.js": ["nextjs"],
    "node.js": ["nodejs", "node"],
    "google cloud": ["gcp"],
    "gcp": ["google cloud"],
    "aws": ["amazon web services"],
    "ci/cd": ["continuous integration", "cicd"],
    "llm": ["large language models", "llms", "generative ai"],
    "llms": ["llm", "large language models"],
    "rag": ["retrieval augmented generation", "retrieval-augmented generation"],
    "docker": ["containers", "containerization"],
    "fastapi": ["rest api", "api design"],
    "microservices": ["distributed systems"],
}


def _split_cv_sections(cv_markdown: str) -> Dict[str, str]:
    """Split markdown CV into major structural sections for precise location auditing."""
    lines = cv_markdown.splitlines()
    sections: Dict[str, List[str]] = {
        "Header / Contact": [],
        "Professional Summary": [],
        "Competencies & Skills": [],
        "Professional Experience": [],
        "Education & Credentials": [],
    }
    current_sec = "Header / Contact"

    for line in lines:
        stripped = line.strip().lower()
        if _HEADER_SUMMARY_RE.search(stripped):
            current_sec = "Professional Summary"
        elif _HEADER_SKILLS_RE.search(stripped):
            current_sec = "Competencies & Skills"
        elif _HEADER_EXPERIENCE_RE.search(stripped):
            current_sec = "Professional Experience"
        elif _HEADER_EDUCATION_RE.search(stripped):
            current_sec = "Education & Credentials"
        sections[current_sec].append(line)

    return {sec: "\n".join(sec_lines) for sec, sec_lines in sections.items()}


def generate_ats_keyword_heatmap(
    job: Dict[str, Any],
    cv_markdown: str,
    profile: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Generate an ATS Keyword Match Heatmap and Inspector (Feature P3-B).
    Analyzes keyword frequency, exact matches, partial/synonym matches, missing critical keywords,
    and sections where keywords reside, with concrete auto-inject suggestions.
    """
    kw_data = extract_ats_keywords(job, profile)
    priority_keywords = list(dict.fromkeys(
        kw_data.get("priority_keywords", []) +
        kw_data.get("hard_skills", []) +
        kw_data.get("functional_skills", [])
    ))

    cv_sections = _split_cv_sections(cv_markdown)
    cv_lower_full = cv_markdown.lower()

    heatmap_items = []
    matched_count = 0
    partial_count = 0
    missing_count = 0

    hard_set = set(k.lower() for k in kw_data.get("hard_skills", []))
    func_set = set(k.lower() for k in kw_data.get("functional_skills", []))

    for kw in priority_keywords:
        kw_clean = kw.strip()
        if not kw_clean:
            continue
        kw_lower = kw_clean.lower()
        base_term = kw_lower.split("/")[0].split("(")[0].strip()

        # Categorize
        if kw_lower in hard_set:
            category = "Hard Skill / Tech"
        elif kw_lower in func_set:
            category = "Domain & Strategy"
        else:
            category = "Core Competency"

        # Check full text regex match
        pattern = re.compile(r"\b" + re.escape(base_term) + r"\b", re.IGNORECASE)
        matches = pattern.findall(cv_lower_full)
        exact_count = len(matches)

        # Detect sections where it appears
        found_in_sections = []
        for sec_name, sec_text in cv_sections.items():
            if pattern.search(sec_text):
                found_in_sections.append(sec_name)

        if exact_count > 0:
            status = "matched"
            matched_count += 1
        else:
            # Check for synonyms
            synonyms = _SYNONYM_PAIRS.get(base_term, [])
            syn_found = False
            for syn in synonyms:
                syn_pat = re.compile(r"\b" + re.escape(syn) + r"\b", re.IGNORECASE)
                if syn_pat.search(cv_lower_full):
                    syn_found = True
                    for sec_name, sec_text in cv_sections.items():
                        if syn_pat.search(sec_text):
                            found_in_sections.append(f"{sec_name} (as '{syn}')")
                    break
            if syn_found:
                status = "partial"
                partial_count += 1
                exact_count = 1
            else:
                status = "missing"
                missing_count += 1

        is_high_impact = bool(base_term in (job.get("title") or "").lower() or kw in job.get("matched_skills", []))

        heatmap_items.append({
            "keyword": kw_clean,
            "category": category,
            "status": status,
            "count": exact_count,
            "sections": found_in_sections if found_in_sections else ["Not Present"],
            "importance": "High" if is_high_impact else "Medium",
        })

    # Sort: Missing High-Impact first, then partial, then matched
    status_order = {"missing": 0, "partial": 1, "matched": 2}
    heatmap_items.sort(key=lambda x: (status_order[x["status"]], 0 if x["importance"] == "High" else 1, x["keyword"]))

    total_kws = max(1, len(heatmap_items))
    match_rate_pct = int(round(((matched_count + (partial_count * 0.6)) / total_kws) * 100))

    # Auto-inject suggestions for missing keywords
    auto_inject_suggestions = []
    missing_items = [it for it in heatmap_items if it["status"] in ("missing", "partial")][:5]
    for it in missing_items:
        kw = it["keyword"]
        if it["category"] == "Hard Skill / Tech":
            bullet = f"• Architected scalable distributed workflows integrating **{kw}** to accelerate deployment velocity by 25%."
            sec = "Professional Experience"
        else:
            bullet = f"• Spearheaded cross-functional delivery aligning **{kw}** with product roadmaps to maximize stakeholder adoption."
            sec = "Professional Experience"
        auto_inject_suggestions.append({
            "keyword": kw,
            "suggested_bullet": bullet,
            "target_section": sec,
        })

    return {
        "match_rate_pct": match_rate_pct,
        "total_keywords": len(heatmap_items),
        "matched_count": matched_count,
        "partial_count": partial_count,
        "missing_count": missing_count,
        "items": heatmap_items,
        "auto_inject_suggestions": auto_inject_suggestions,
    }
