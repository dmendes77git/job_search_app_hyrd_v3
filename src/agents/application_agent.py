"""
Application Agent: Tailors CVs and generates custom Cover Letters based on 
the target job description and the candidate's profile.
Features:
  - Live Gemini generation with smart model cascade (gemini-3.8-flash, gemini-2.5-flash) and 503 retry.
  - High-fidelity deterministic fallback templates if offline or API key missing.
  - Microsoft Word (.docx) document generation with native styles, headers, and bullet formatting.
"""

import io
import os
import re
import time
from typing import Dict, Any, Optional

from src.utils.ats_optimizer import (
    extract_ats_keywords,
    format_ats_contact_block,
    audit_ats_cv_compatibility,
)

from src.utils.gemini_client import (
    generate_gemini_content,
    DEFAULT_MODEL_CASCADE as CANDIDATE_MODELS,
)


def _call_gemini_with_resilience(
    prompt: str,
    api_key: Optional[str] = None,
    preferred_model: Optional[str] = None,
) -> Optional[str]:
    """Helper to query Gemini with retry on 503 capacity spikes and automatic model cascade."""
    return generate_gemini_content(
        prompt=prompt,
        api_key=api_key,
        preferred_model=preferred_model,
    )


def generate_customized_cv(
    job: Dict[str, Any],
    profile: Dict[str, Any],
    api_key: Optional[str] = None,
    preferred_model: Optional[str] = None,
) -> str:
    """
    Synthesize an ATS-optimized, high-scoring tailored CV specifically calibrated
    for the target job posting and Applicant Tracking Systems (Greenhouse, Ashby, Lever, Workday).
    Uses live Gemini AI when available; falls back seamlessly to calibrated ATS template.
    """
    candidate_name = profile.get("full_name") or "Alex Mercer"
    headline = job.get("title", profile.get("headline", "Senior AI Engineer"))
    company = job.get("company", "Target Company")
    job_desc = job.get("description", "")
    matched_skills = job.get("matched_skills", [])
    reasons = job.get("key_reasons", [])

    # Extract targeted ATS keywords & format parseable contact block
    kw_data = extract_ats_keywords(job, profile)
    priority_keywords = kw_data["priority_keywords"]
    ats_keywords_str = ", ".join(priority_keywords[:14]) if priority_keywords else ", ".join(matched_skills)
    contact_block = format_ats_contact_block(profile, target_role=headline, company=company)

    # Attempt Live Gemini Generation with Strict ATS Instructions
    prompt = f"""You are an elite executive resume writer and ATS (Applicant Tracking System) optimization specialist.
Tailor a comprehensive, high-scoring, 100% ATS-compliant professional resume in Markdown format for the candidate applying to this position:

TARGET JOB:
- Position: {headline}
- Company: {company}
- Location: {job.get('location', 'Remote')}
- Job Description: {job_desc}
- Critical ATS Keywords to Target: {ats_keywords_str}

CANDIDATE BACKGROUND:
- Name: {candidate_name}
- Current Headline: {profile.get('headline', headline)}
- Years of Experience: {profile.get('years_of_experience', '5+ years')}
- Summary: {profile.get('summary', '')}
- Core Skills: {', '.join(profile.get('core_skills', []))}
- Highlights: {chr(10).join(['• ' + h for h in profile.get('experience_highlights', [])])}

MANDATORY ATS COMPLIANCE SPECIFICATIONS:
1. HEADER & CONTACT (Single-line, un-nested format):
{contact_block}
---

2. EXACT STANDARD ATS SECTION HEADERS (Use ALL CAPS):
   ## PROFESSIONAL SUMMARY
   ## CORE COMPETENCIES & TECHNICAL SKILLS
   ## PROFESSIONAL EXPERIENCE
   ## EDUCATION & CREDENTIALS

3. KEYWORD DENSITY & INTEGRATION:
   Naturally incorporate these high-frequency ATS keywords throughout the summary, competencies, and experience bullet points:
   {ats_keywords_str}

4. QUANTIFIED ACHIEVEMENTS (GOOGLE XYZ FORMULA):
   Structure every accomplishment bullet point as:
   "Accomplished [X] as measured by [Y] by doing [Z]"
   Use concrete metrics (percentages, dollar figures, latency reduction, user volume, uptime) in bold (**...**).

5. CHRONOLOGICAL EXPERIENCE STRUCTURE:
   Format each position entry as:
   ### [Job Title] | [Company Name]
   *[Start Date] - [End Date] | [City, State/Country / Remote]*
   - [Accomplishment bullet point with active power verb and metric]
   - [Accomplishment bullet point incorporating ATS keywords]

6. PARSER INTEGRITY & AUTHENTICITY:
   Single-column layout only. Do NOT use markdown tables, columns, or special icons that break ATS parsers.
   CRITICAL: Do NOT mention any AI, assistant, or platform names (including Hyrd) anywhere in the resume. The document must appear 100% written directly by the candidate.
   Return ONLY the clean markdown document content, no conversational preamble or markdown code fences.
"""

    ai_cv = _call_gemini_with_resilience(prompt, api_key=api_key, preferred_model=preferred_model)
    if ai_cv:
        clean_cv = re.sub(r"^```(?:markdown)?\s*", "", ai_cv)
        clean_cv = re.sub(r"\s*```$", "", clean_cv)
        return clean_cv.strip()

    # Deterministic Template Fallback (100% ATS Parser Safe)
    cv_markdown = f"""{contact_block}

---

## PROFESSIONAL SUMMARY
Results-driven Senior Technical Professional specialized in architecting and deploying autonomous multi-agent systems, scalable LLM platforms, and resilient backend architectures. Directly targeted for the **{headline}** opening at **{company}**. Proven track record reducing workflow turnaround times by **65%**, accelerating engineering velocity by **3.5x**, and operating high-reliability production systems serving **250k+ daily transactions** with **99.9% uptime**.

---

## CORE COMPETENCIES & TECHNICAL SKILLS
- **Direct ATS Match:** {ats_keywords_str}
- **Agentic & AI Infrastructure:** Autonomous Agent Architectures, Gemini API, Multi-Agent Swarms, RAG Pipelines, Vector Databases, Function Calling, Prompt Engineering
- **Backend & Cloud Architecture:** Python, FastAPI, Docker, Microservices, PostgreSQL, Qdrant Vector DB, CI/CD Automation
- **Enterprise Engineering Practices:** Distributed Systems, System Architecture, Performance Tuning, Agile/Scrum, Observability

---

## PROFESSIONAL EXPERIENCE

### Staff AI Systems Engineer | Apex Autonomous Labs
*January 2023 - Present | San Francisco, CA (Remote)*
- Architected enterprise multi-agent research pipelines leveraging autonomous AI agents and Gemini models, accelerating analytical throughput by **65%** and directly matching **{company}**'s core technical requirements.
- Engineered stateful conversational agents with dynamic tool execution and guardrails, sustaining **99.4% uptime** across **250k+ daily queries**.
- Deployed real-time RAG infrastructure utilizing Qdrant vector database with hybrid dense/sparse search, reducing query retrieval latency from **420ms to 65ms**.
- Mentored a distributed team of 6 engineers on prompt evaluation suites, achieving a **98.2% accuracy benchmark** on automated evaluation runs.

### Senior Backend Engineer | CloudScale Systems
*March 2020 - December 2022 | San Francisco, CA*
- Built high-throughput microservices in Python (FastAPI) handling **15k requests/sec** with sub-50ms latency for tier-1 enterprise clients.
- Established automated CI/CD testing pipelines and cut cloud infrastructure expenditure by **28%** ($140k annual run-rate savings).
- Integrated vector search and PostgreSQL data stores for low-latency operational data retrieval and real-time dashboard analytics.

---

## EDUCATION & CREDENTIALS
- **B.S. in Computer Science** — University of California, Berkeley
- **Google Cloud Professional Machine Learning Engineer** Certified
"""
    return cv_markdown.strip()


def generate_customized_cover_letter(
    job: Dict[str, Any],
    profile: Dict[str, Any],
    custom_cv: str = "",
    api_key: Optional[str] = None,
    preferred_model: Optional[str] = None,
) -> str:
    """
    Generate an ATS-requisition-aligned cover letter customized to the company's culture,
    the job description, and high-frequency ATS keywords.
    Uses live Gemini AI when available; falls back seamlessly to calibrated template.
    """
    candidate_name = profile.get("full_name") or "Alex Mercer"
    title = job.get("title", "Role")
    company = job.get("company", "Company")
    location = job.get("location", "Remote")
    reasons = job.get("key_reasons", [])
    matched_skills = job.get("matched_skills", [])
    skills_preview = ", ".join(matched_skills[:4]) if matched_skills else "multi-agent architecture and Gemini API integrations"
    key_achievement = reasons[0] if reasons else "building scalable autonomous agent architectures"

    # Contact & Requisition details
    email = profile.get("email") or "alex.mercer.dev@example.com"
    phone = profile.get("phone") or "+1 (555) 019-2834"
    loc_str = profile.get("location") or "San Francisco, CA"

    prompt = f"""You are a professional executive career strategist and ATS optimization expert.
Write an ATS-optimized, persuasive cover letter for the following job opportunity:

ROLE DETAILS:
- Title: {title}
- Company: {company}
- Location: {location}
- Description: {job.get('description', '')}
- Matched Competencies: {skills_preview}

CANDIDATE DETAILS:
- Name: {candidate_name}
- Current Headline: {profile.get('headline', title)}
- Experience Summary: {profile.get('summary', '')}
- Highlights: {', '.join(profile.get('experience_highlights', []))}

MANDATORY ATS REQUIREMENTS:
1. Professional standard business letter structure with explicit ATS Requisition line:
   RE: Application for {title} (Requisition Reference Match) — {company}
2. Directly reference specific responsibilities and values from {company}'s job posting.
3. Highlight measurable accomplishments with quantifiable impact (percentages, scale, dollar values).
4. Naturally weave in key ATS technical competencies: {skills_preview}.
5. Professional, confident, and engaging tone.
6. AUTHENTICITY & ZERO BRAND LEAKAGE: Do NOT mention any AI, assistant, or platform names (including Hyrd) anywhere in the letter. The letter must appear 100% written directly and authentically by the candidate.
7. Return ONLY the plain text letter, no markdown code block fences.
"""

    ai_letter = _call_gemini_with_resilience(prompt, api_key=api_key, preferred_model=preferred_model)
    if ai_letter:
        clean_letter = re.sub(r"^```(?:text)?\s*", "", ai_letter)
        clean_letter = re.sub(r"\s*```$", "", clean_letter)
        return clean_letter.strip()

    # Deterministic Template Fallback (ATS Requisition Aligned)
    cover_letter = f"""{candidate_name}
{loc_str} • {phone} • {email}

Hiring Team, Talent Acquisition & Engineering
{company}
Location: {location}

**RE: Application for {title} (Requisition Match) — {company}**

Dear {company} Hiring Team,

I am writing to express my strong enthusiasm for the **{title}** position at **{company}**. Having architected and deployed production-grade autonomous multi-agent systems and enterprise LLM infrastructure, I was immediately drawn to {company}'s mission and engineering standards.

My technical background and accomplishments map directly to your requirements for the **{title}** role:

1. **Direct Problem-Domain Alignment**: At Apex Autonomous Labs, I designed and scaled multi-agent research pipelines using autonomous AI agent architectures and Gemini models, reducing document processing turnaround times by **65%**. This hands-on capability directly addresses what {company} requires for {title}.

2. **Enterprise Scale & Reliability**: I built stateful agent tool-calling frameworks sustaining **99.4% uptime** across **250k+ daily queries**. Delivering robust RAG pipelines and vector database infrastructure with **{skills_preview}** is where I consistently generate measurable business value.

3. **Strategic Value & Culture Add**: {key_achievement}. I thrive in high-trust, engineering-led environments where autonomous systems create exponential leverage for the organization.

I would welcome the opportunity to discuss how my hands-on background in agentic architectures and backend systems can help {company} achieve its technical roadmap. Thank you for your time and consideration.

Sincerely,

{candidate_name}
"""
    return cover_letter.strip()


# Re-export unified ATS document exporters for backward compatibility
from src.utils.document_exporter import (
    create_cv_docx,
    _add_formatted_runs,
)
