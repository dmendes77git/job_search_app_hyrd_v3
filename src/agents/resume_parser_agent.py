"""
Resume Parsing Agent: Analyzes raw resume text and extracts structured candidate profile
using Google Gemini API with dynamic model discovery, automatic retry on capacity spikes (503/429),
and Pydantic structured output.
"""

import json
import logging
import os
import re
import time
from typing import Dict, Any, List, Optional, Tuple
from pydantic import BaseModel, Field
from src.utils.file_parser import extract_text_from_file


class CandidateProfile(BaseModel):
    full_name: str = Field(description="Candidate's full name")
    email: Optional[str] = Field(default="", description="Email address if available")
    phone: Optional[str] = Field(default="", description="Phone number if available")
    location: str = Field(description="Current location or 'Remote'")
    headline: str = Field(description="Target professional role title e.g. Senior AI Engineer")
    years_of_experience: str = Field(description="Total years of experience e.g. 6+ years")
    summary: str = Field(description="2-3 sentence executive career summary synthesizing strengths")
    core_skills: List[str] = Field(description="Top 6 to 10 primary technical skills, frameworks, and tools")
    experience_highlights: List[str] = Field(description="3 to 5 quantifiable career accomplishments")
    target_roles: List[str] = Field(description="3 to 4 recommended target job titles to search for")
    preferred_min_salary: str = Field(default="$150,000", description="Estimated salary floor for this tier")
    work_mode: str = Field(default="Remote Only", description="Preferred work mode: Remote Only, Hybrid, or On-site")
    linkedin_url: Optional[str] = Field(default="", description="Personal LinkedIn profile URL if mentioned in the resume")


from src.utils.gemini_client import (
    sort_models_by_priority,
    get_available_models,
    clean_markdown_fences,
)


def _clean_and_parse_json(text: str) -> Dict[str, Any]:
    """Parse JSON from model response text, stripping markdown code fences if present."""
    clean_text = text.strip()
    try:
        return json.loads(clean_text)
    except Exception:
        pass

    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", clean_text)
    if fence_match:
        try:
            return json.loads(fence_match.group(1).strip())
        except Exception:
            pass

    first_brace = clean_text.find("{")
    last_brace = clean_text.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        try:
            return json.loads(clean_text[first_brace : last_brace + 1])
        except Exception:
            pass

    raise ValueError(f"Could not parse valid JSON from model response: {clean_text[:200]}")


def parse_resume_with_gemini(
    resume_text: str,
    api_key: Optional[str] = None,
    preferred_model: Optional[str] = None,
) -> Tuple[Dict[str, Any], bool, str]:
    """
    Parse resume text using the Gemini API.
    Features:
      - Dynamic discovery of authorized models via client.models.list() to prevent 404s.
      - Automatic retry with exponential backoff on 503 capacity spikes.
      - Seamless model cascade across active models.
      - Graceful fallback to heuristic parser if API is completely unavailable.
    """
    effective_api_key = api_key or os.environ.get("GEMINI_API_KEY", "").strip()

    if not effective_api_key:
        fallback = _heuristic_fallback_parser(resume_text)
        return (
            fallback,
            False,
            "💡 No Gemini API key detected. Profile extracted using heuristic agent. Add GEMINI_API_KEY in the sidebar or .env for full AI reasoning.",
        )

    try:
        from google import genai
        from google.genai import types

        logging.getLogger("google_genai.models").setLevel(logging.ERROR)
        client = genai.Client(api_key=effective_api_key)
    except Exception as e:
        fallback = _heuristic_fallback_parser(resume_text)
        return (
            fallback,
            False,
            f"⚠️ Could not initialize Google GenAI client ({e}). Profile extracted using local fallback parser.",
        )

    # 1. Dynamically discover authorized models for this user's API key
    discovered_models, list_err = get_available_models(client, preferred_model)
    if list_err and any(code in list_err for code in ["401", "403", "API_KEY_INVALID", "PERMISSION_DENIED"]):
        fallback = _heuristic_fallback_parser(resume_text)
        return (
            fallback,
            False,
            f"⚠️ Gemini API Key Error: Your API key was rejected by Google ({list_err[:120]}). Extracted profile using local fallback parser.",
        )

    if discovered_models:
        models_to_try = discovered_models
    else:
        # Fallback list if listing failed
        models_to_try = ["gemini-2.0-flash", "gemini-2.5-flash", "gemini-3.8-flash", "gemini-1.5-flash"]

    prompt = f"""You are an expert technical recruiting agent.
Analyze the following resume/work history and extract a structured candidate profile.
Identify the candidate's core strengths, technical competencies, career achievements, and recommend ideal job search titles.

RESUME CONTENT:
\"\"\"
{resume_text}
\"\"\"
"""

    last_error_msg = ""
    attempted_models = []

    for model_index, model_name in enumerate(models_to_try[:6]):
        attempted_models.append(model_name)
        for attempt in range(2):
            try:
                # First try structured JSON output with AFC disabled to avoid SDK warnings
                try:
                    response = client.models.generate_content(
                        model=model_name,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            response_schema=CandidateProfile,
                            temperature=0.2,
                            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
                        ),
                    )
                except Exception as schema_err:
                    # If model doesn't support response_schema, fall back to plain JSON prompt
                    if "schema" in str(schema_err).lower() or "not supported" in str(schema_err).lower():
                        response = client.models.generate_content(
                            model=model_name,
                            contents=prompt + "\n\nCRITICAL: Return ONLY a valid JSON object matching the requested schema.",
                            config=types.GenerateContentConfig(
                                temperature=0.2,
                                automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
                            ),
                        )
                    else:
                        raise schema_err

                data = _clean_and_parse_json(response.text)
                profile_obj = CandidateProfile.model_validate(data)
                profile_dict = profile_obj.model_dump()

                if model_index == 0 and attempt == 0:
                    status = f"✓ Profile parsed successfully with live Gemini Agent ({model_name})."
                elif model_index == 0:
                    status = f"✓ Profile parsed successfully with live Gemini Agent ({model_name}, succeeded on retry)."
                else:
                    status = (
                        f"✓ Profile parsed successfully with live Gemini Agent "
                        f"(fallback: {model_name} after {models_to_try[0]} capacity spike)."
                    )

                return (profile_dict, True, status)

            except Exception as e:
                err_str = str(e)
                last_error_msg = err_str

                # Client / auth errors (non-retryable)
                if any(code in err_str for code in ["401", "403", "API_KEY_INVALID", "PERMISSION_DENIED"]):
                    fallback = _heuristic_fallback_parser(resume_text)
                    return (
                        fallback,
                        False,
                        f"⚠️ Gemini Authentication Error: Invalid API key ({err_str[:120]}...). Extracted profile using local fallback parser.",
                    )

                # If 404 (model deprecated / unsupported), break immediately to try next model
                if "404" in err_str or "not found" in err_str.lower():
                    break

                # Transient errors (503 UNAVAILABLE, 429 RATE_LIMIT, high demand)
                is_transient = any(
                    token in err_str.lower()
                    for token in ["503", "429", "unavailable", "high demand", "capacity", "spikes in demand", "resource_exhausted", "500", "502", "504"]
                )

                if is_transient and attempt == 0:
                    time.sleep(2.0)
                    continue
                else:
                    break

    # If all models failed
    fallback = _heuristic_fallback_parser(resume_text)
    clean_err = last_error_msg.replace("\n", " ").strip()[:140]
    return (
        fallback,
        False,
        f"⚠️ Gemini servers temporarily busy across models [{', '.join(attempted_models[:3])}] ({clean_err}...). Extracted profile using local fallback parser.",
    )


EXP_LEVEL_OPTIONS = [
    "Junior (0-2 years)",
    "Mid-Level (3-5 years)",
    "Senior (5+ years)",
    "Staff / Principal / Lead (8+ years)",
    "Manager / Director / Head",
    "Executive / VP / C-Level",
]


def match_experience_level(exp_str: str) -> str:
    """Map any experience description to one of the standard EXP_LEVEL_OPTIONS."""
    if not exp_str:
        return "Senior (5+ years)"
    s = exp_str.lower()
    if re.search(r"\b(vp|vice president|c-level|chief|ceo|cto|coo|cfo|executive|partner|founder)\b", s):
        return "Executive / VP / C-Level"
    if re.search(r"\b(director|head of)\b", s):
        return "Manager / Director / Head"
    if re.search(r"\b(staff|principal|lead)\b", s) or re.search(r"\b(8\+|9\+|10\+|12\+|15\+)\b", s):
        return "Staff / Principal / Lead (8+ years)"
    if re.search(r"\b(senior|5\+|6\+|7\+)\b", s) or re.search(r"\b([5-7]\s*years?)\b", s):
        return "Senior (5+ years)"
    if re.search(r"\b(mid|3\+|4\+|3\s*years?|4\s*years?)\b", s):
        return "Mid-Level (3-5 years)"
    if re.search(r"\b(junior|entry|intern|0-2|1\s*year|2\s*years?|associate|graduate)\b", s):
        return "Junior (0-2 years)"
    for opt in EXP_LEVEL_OPTIONS:
        if opt.lower() in s or s in opt.lower():
            return opt
    return "Senior (5+ years)"


def extract_candidate_name_from_text(resume_text: str) -> str:
    """Extract candidate name from the top header lines of the resume text."""
    lines = [l.strip() for l in resume_text.splitlines() if l.strip()]
    if not lines:
        return ""
    for line in lines[:5]:
        clean = re.sub(r"[,|•/\\#\*\-]+", " ", line).strip()
        if any(x in clean.lower() for x in ["@", "http", "www.", "linkedin", "github", "phone", "resume", "curriculum", "page", "tel", "email"]):
            continue
        words = clean.split()
        if 2 <= len(words) <= 4 and all(len(w) > 1 and w[0].isupper() for w in words if w):
            return clean.title()
    first = lines[0].strip()
    if 2 < len(first) < 35 and not any(x in first.lower() for x in ["@", "http", "resume", "curriculum"]):
        return first.title()
    return ""


def detect_experience_level(resume_text: str) -> str:
    """Infer candidate experience level from resume text content."""
    t = resume_text.lower()
    m = re.search(r"(\d+)\+?\s*years?", t)
    years = int(m.group(1)) if m else None

    if re.search(r"\b(vp|vice president|c-level|chief|ceo|cto|coo|cfo|executive|partner|founder)\b", t):
        return "Executive / VP / C-Level"
    if re.search(r"\b(director|head of)\b", t):
        return "Manager / Director / Head"
    if re.search(r"\b(staff|principal|lead)\b", t) or (years and years >= 8):
        return "Staff / Principal / Lead (8+ years)"
    if (years and years >= 5) or "senior" in t:
        return "Senior (5+ years)"
    if (years and years >= 3) or "mid" in t:
        return "Mid-Level (3-5 years)"
    if years and years < 3:
        return "Junior (0-2 years)"
    return "Senior (5+ years)"


def extract_target_job_queries(resume_text: str, headline: str = "") -> List[str]:
    """Generate 3-5 target job query options across any profession for the dropdown list."""
    t = resume_text.lower()
    queries = []
    if headline:
        queries.append(headline)

    domain_rules = {
        "ai_eng": (
            ["antigravity", "agentic", "ai engineer", "llm", "machine learning", "pytorch", "vector database"],
            ["Senior AI / Agentic Systems Engineer", "Lead Agentic Systems Architect", "LLM Platform Engineer", "Applied AI Research Engineer"],
        ),
        "software": (
            ["software engineer", "backend engineer", "frontend engineer", "full stack", "developer", "microservices"],
            ["Senior Software Engineer", "Staff Backend Engineer", "Full Stack Tech Lead", "Engineering Manager"],
        ),
        "product": (
            ["product manager", "product management", "product owner", "product roadmap", "product strategy"],
            ["Senior Product Manager", "Product Lead", "Group Product Manager", "Technical Product Manager"],
        ),
        "design": (
            ["product designer", "ux designer", "ui designer", "visual designer", "figma", "ux research"],
            ["Lead Product Designer", "Senior UX/UI Designer", "Design Director", "UX Researcher"],
        ),
        "marketing": (
            ["marketing manager", "growth marketing", "digital marketing", "content marketing", "brand strategy", "campaign"],
            ["Senior Marketing Manager", "Director of Marketing", "Product Marketing Lead", "Growth Marketing Specialist"],
        ),
        "finance": (
            ["financial analyst", "fp&a", "financial modeling", "accounting", "accountant", "cpa", "controller", "budgeting"],
            ["Senior Financial Analyst", "FP&A Manager", "Finance Business Partner", "Accounting Lead"],
        ),
        "operations": (
            ["operations manager", "business operations", "head of operations", "logistics", "supply chain", "coo"],
            ["Operations Manager", "Head of Operations", "Business Operations Lead", "Director of Operations"],
        ),
        "hr": (
            ["human resources", "talent acquisition", "recruiter", "recruiting", "people operations", "hrbp"],
            ["HR Manager", "Talent Acquisition Lead", "Head of People", "HR Business Partner"],
        ),
        "sales": (
            ["account executive", "business development", "sales director", "sales manager", "b2b sales"],
            ["Enterprise Account Executive", "Sales Director", "Head of Sales", "Business Development Manager"],
        ),
    }

    best_domain = None
    best_score = 0
    for domain, (keywords, options) in domain_rules.items():
        score = sum(3 for k in keywords if re.search(r"\b" + re.escape(k) + r"\b", t))
        if score > best_score:
            best_score = score
            best_domain = domain

    if best_domain and best_score > 0:
        queries.extend(domain_rules[best_domain][1])
    else:
        queries.extend(["Senior Project Manager", "Operations Lead", "Business Analyst", "Strategy Consultant"])

    seen = set()
    deduped = []
    for q in queries:
        if q.lower() not in seen:
            seen.add(q.lower())
            deduped.append(q)
    return deduped[:5]


def extract_skills_from_text(resume_text: str) -> List[str]:
    """Extract primary competency focus from resume text."""
    skills = []
    m = re.search(r"(?:skills|competencies|technologies|proficiencies|areas of expertise)[^\n]*\n(.*?)(?:\n\s*[A-Z\s]{4,}|\Z)", resume_text, re.DOTALL | re.IGNORECASE)
    if m:
        section = m.group(1)
        for line in section.strip().splitlines():
            clean_l = re.sub(r"^[-\s*•·]+", "", line).strip()
            if ":" in clean_l:
                parts = clean_l.split(":", 1)[1].split(",")
                for p in parts:
                    p_clean = p.strip()
                    if 2 < len(p_clean) < 45 and not p_clean.lower().startswith(("http", "www", "phone", "email", "tel")):
                        skills.append(p_clean)
            elif clean_l:
                for item in re.split(r"[,|•;]+", clean_l):
                    it_clean = item.strip()
                    if 2 < len(it_clean) < 45 and not it_clean.lower().startswith(("http", "www", "phone", "email", "tel")):
                        skills.append(it_clean)

    known_pool = [
        "Python", "Agentic AI Frameworks", "Gemini API / LLMs", "Multi-Agent Orchestration",
        "FastAPI", "Streamlit", "Docker", "PostgreSQL", "Vector Databases",
        "Digital Marketing", "SEO / SEM", "Google Analytics", "Brand Strategy", "Content Strategy",
        "Financial Modeling", "Budgeting & Forecasting", "Excel / VBA", "GAAP", "FP&A",
        "Product Strategy", "Agile / Scrum", "Roadmapping", "User Research", "A/B Testing",
        "Project Management", "Operations Management", "Process Optimization", "Leadership",
    ]
    t = resume_text.lower()
    for kp in known_pool:
        k_base = kp.split("/")[0].split("&")[0].strip().lower()
        if len(k_base) > 2 and k_base in t:
            skills.append(kp)

    seen = set()
    deduped = []
    for s in skills:
        if s.lower() not in seen:
            seen.add(s.lower())
            deduped.append(s)
    return deduped[:10]


def extract_initial_profile_from_text(resume_text: str) -> Dict[str, Any]:
    """Fast initial extraction of candidate attributes when a CV is uploaded or submitted."""
    name = extract_candidate_name_from_text(resume_text)
    exp = detect_experience_level(resume_text)
    queries = extract_target_job_queries(resume_text)
    skills = extract_skills_from_text(resume_text)
    return {
        "full_name": name,
        "experience_level": exp,
        "target_roles": queries,
        "headline": queries[0] if queries else "Professional",
        "core_skills": skills,
    }


def _heuristic_fallback_parser(resume_text: str) -> Dict[str, Any]:
    """
    Local heuristic parser when Gemini API key is not present or endpoints are unreachable.
    Extracts name, contact info, experience, target job queries, and skills across all domains.
    """
    lines = [l.strip() for l in resume_text.splitlines() if l.strip()]

    full_name = extract_candidate_name_from_text(resume_text) or "Candidate"
    email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", resume_text)
    email = email_match.group(0) if email_match else "candidate@example.com"

    li_match = re.search(r"https?://(?:www\.)?linkedin\.com/in/[\w\-]+", resume_text, re.IGNORECASE)
    linkedin_url = li_match.group(0) if li_match else ""

    exp_level = detect_experience_level(resume_text)
    target_queries = extract_target_job_queries(resume_text)
    headline = target_queries[0] if target_queries else "Senior Professional"
    skills = extract_skills_from_text(resume_text)
    if not skills:
        skills = ["Project Management", "Leadership", "Strategic Planning", "Data Analysis", "Operations"]

    bullet_lines = [
        l.lstrip("-*•").strip()
        for l in lines
        if l.startswith(("-", "*", "•")) and len(l) > 25
    ]
    highlights = bullet_lines[:4] if bullet_lines else [
        "Extensive experience delivering scalable solutions and leading strategic initiatives.",
        "Hands-on expertise across modern workflows, tools, and execution frameworks.",
        "Demonstrated track record of delivering mission-critical projects and measurable impact.",
    ]

    return {
        "full_name": full_name,
        "email": email,
        "phone": "",
        "location": "",
        "headline": headline,
        "years_of_experience": exp_level,
        "summary": (
            f"Experienced professional targeting {headline} opportunities. "
            f"Core background in {', '.join(skills[:3])}."
        ),
        "core_skills": skills,
        "experience_highlights": highlights,
        "target_roles": target_queries,
        "preferred_min_salary": "",
        "work_mode": "Remote Only",
        "linkedin_url": linkedin_url,
    }
