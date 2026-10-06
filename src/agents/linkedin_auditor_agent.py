"""
LinkedIn Profile Auditor & Optimizer Agent:
Analyzes candidate's LinkedIn URL and career profile to provide:
  - 0-100 Overall LinkedIn Optimization Rating & Letter Grade
  - 5-Pillar Score Breakdown (Headline, About, Skills, Experience, URL Branding)
  - 3 Concrete, Ready-to-Use High-Impact Headline Alternatives
  - Optimized Full "About" Bio Rewrite with Recruiter Hook and CTA
  - High-Demand Missing Keywords for LinkedIn Recruiter & Talent CRM algorithms
  - Section-by-Section Profile Optimization Recommendations
"""

import json
import logging
import os
import re
import time
from typing import Dict, Any, List, Optional


def clean_linkedin_url(url: str) -> str:
    """Normalize and validate LinkedIn URL format."""
    clean = url.strip()
    if not clean:
        return ""
    if not clean.startswith("http://") and not clean.startswith("https://"):
        clean = f"https://{clean}"
    return clean


def check_url_slug_hygiene(url: str) -> Dict[str, Any]:
    """Check if the user has customized their public profile URL slug."""
    match = re.search(r"linkedin\.com/in/([^/?#]+)", url.lower())
    if not match:
        return {
            "has_custom_slug": False,
            "slug": "",
            "feedback": "Invalid or missing LinkedIn profile URL format. Use https://linkedin.com/in/your-name",
        }
    slug = match.group(1)
    # Check if slug ends with messy random digits (e.g., john-doe-498b2110)
    has_random_digits = bool(re.search(r"-[0-9a-f]{6,}$", slug) or re.search(r"[0-9]{5,}$", slug))
    if has_random_digits:
        return {
            "has_custom_slug": False,
            "slug": slug,
            "feedback": f"Your URL slug '/in/{slug}' contains default randomized digits. Customize your public handle (e.g. /in/{re.sub(r'-[0-9a-f]+$', '', slug)}) to look professional on CVs and increase search ranking.",
        }
    return {
        "has_custom_slug": True,
        "slug": slug,
        "feedback": f"Excellent custom URL slug '/in/{slug}'! Clean and memorable.",
    }


def _call_gemini_for_linkedin(
    prompt: str,
    api_key: Optional[str] = None,
    preferred_model: Optional[str] = None,
) -> Optional[str]:
    """Query Gemini with automatic model discovery and resilient fallback."""
    effective_api_key = api_key or os.environ.get("GEMINI_API_KEY", "").strip()
    if not effective_api_key:
        return None

    try:
        from google import genai
        from google.genai import types
        from src.agents.resume_parser_agent import get_available_models

        logging.getLogger("google_genai.models").setLevel(logging.ERROR)
        client = genai.Client(api_key=effective_api_key)
        discovered, _ = get_available_models(client, preferred_model)
        cascade = discovered if discovered else ["gemini-2.0-flash", "gemini-2.5-flash", "gemini-3.8-flash"]
    except Exception as e:
        logging.warning(f"Could not initialize Gemini client for LinkedIn auditor: {e}")
        return None

    for model_name in cascade[:6]:
        for attempt in range(2):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
                        temperature=0.25,
                    ),
                )
                if response and response.text:
                    return response.text.strip()
            except Exception as e:
                err_str = str(e).lower()
                if "503" in err_str or "unavailable" in err_str or "high demand" in err_str or "429" in err_str:
                    time.sleep(1.0)
                    continue
                break
    return None


def generate_fallback_linkedin_audit(
    linkedin_url: str,
    profile_data: Dict[str, Any],
) -> Dict[str, Any]:
    """Generate high-fidelity, deterministic LinkedIn audit when offline or no API key."""
    name = (profile_data.get("full_name") or "Candidate").strip()
    headline = (profile_data.get("headline") or "Professional").strip()
    summary = (profile_data.get("summary") or "").strip()
    skills = profile_data.get("core_skills", [])
    if isinstance(skills, str):
        skills = [s.strip() for s in skills.split(",") if s.strip()]
    role = profile_data.get("target_role") or headline or "Target Role"
    companies = profile_data.get("target_companies") or "Top Technology Firms"
    slug_info = check_url_slug_hygiene(linkedin_url)

    # Score components
    h_len = len(headline)
    headline_score = 90 if ("|" in headline or "•" in headline) and h_len > 35 else (75 if h_len > 20 else 55)
    about_score = 92 if len(summary.split()) > 40 else (70 if summary else 45)
    skills_score = min(95, 60 + len(skills) * 4) if skills else 50
    slug_score = 95 if slug_info["has_custom_slug"] else 65
    exp_score = 85

    overall_score = round(headline_score * 0.25 + about_score * 0.25 + skills_score * 0.20 + exp_score * 0.20 + slug_score * 0.10)
    
    if overall_score >= 90:
        grade = "A+"
        tier = "All-Star Recruiter Magnet"
        color = "#15803d"
        bg = "#dcfce7"
    elif overall_score >= 80:
        grade = "A"
        tier = "Strong Professional Presence"
        color = "#2563eb"
        bg = "#eff6ff"
    elif overall_score >= 70:
        grade = "B+"
        tier = "Good Baseline — Missing Keyword Hooks"
        color = "#d97706"
        bg = "#fef3c7"
    else:
        grade = "C"
        tier = "Under-Optimized Profile"
        color = "#dc2626"
        bg = "#fee2e2"

    skills_joined = ", ".join(skills[:5]) if skills else "Distributed Systems, Architecture, Cloud Infrastructure"
    target_comp_clean = companies.split(",")[0].strip() if companies else "High-Growth Companies"

    headlines = [
        f"{role} | {skills_joined} | Ex-Impact Leader",
        f"{role} @ Scale | Delivering Quantifiable Engineering & Product ROI | {target_comp_clean} Focused",
        f"Senior {role} • Specializing in {', '.join(skills[:3]) if skills else 'Modern Engineering'} • Transforming Complex Systems into Business Value",
    ]

    about_rewrite = (
        f"I am a {role} passionate about building scalable, high-impact systems that solve real-world industry challenges.\n\n"
        f"Over the course of my career, I have specialized in {', '.join(skills[:4]) if skills else 'engineering and innovation'}, partnering across cross-functional engineering, product, and executive teams.\n\n"
        f"🎯 Core Strengths:\n"
        f"• Technical Leadership & Architecture: Leading end-to-end design and execution for mission-critical platforms.\n"
        f"• Quantifiable Impact: Driving measurable throughput gains, reducing operational overhead, and mentoring high-performing teams.\n"
        f"• Domain Mastery: In-depth expertise in {skills_joined}.\n\n"
        f"📬 I welcome conversations regarding {role} opportunities, technical advisory, and collaborative technology innovation. Feel free to connect or email me directly."
    )

    missing_keywords = [
        "Cross-functional Leadership",
        "System Architecture",
        "Strategic Roadmapping",
        "End-to-End Delivery",
        "Stakeholder Management",
        "High-Availability Infrastructure",
    ]

    return {
        "overall_score": overall_score,
        "grade": grade,
        "tier": tier,
        "badge_color": color,
        "badge_bg": bg,
        "headline_score": headline_score,
        "about_score": about_score,
        "skills_score": skills_score,
        "experience_score": exp_score,
        "slug_score": slug_score,
        "slug_feedback": slug_info["feedback"],
        "headline_alternatives": headlines,
        "about_rewrite": about_rewrite,
        "missing_keywords": missing_keywords,
        "action_items": [
            f"Update your headline to include exact keywords ({skills_joined}) so recruiters find you via boolean searches.",
            "Format your About section with clear spacing, a strong first sentence hook, and a prominent call-to-action.",
            "Ensure your top 5 pinned skills directly reflect the primary requirements of your target roles.",
            slug_info["feedback"],
            "Add quantifiable metrics (percentages, dollar amounts, latencies) to your experience bullet points.",
        ],
    }


def audit_linkedin_profile(
    linkedin_url: str,
    profile_data: Dict[str, Any],
    api_key: Optional[str] = None,
    preferred_model: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Perform deep AI analysis on a candidate's LinkedIn URL and career record.
    Returns structured scorecard, scores, headline alternatives, and about bio rewrite.
    """
    norm_url = clean_linkedin_url(linkedin_url)
    slug_info = check_url_slug_hygiene(norm_url)
    name = (profile_data.get("full_name") or "Candidate").strip()
    headline = (profile_data.get("headline") or "Professional").strip()
    summary = (profile_data.get("summary") or "").strip()
    skills = profile_data.get("core_skills", [])
    if isinstance(skills, list):
        skills_str = ", ".join(skills)
    else:
        skills_str = str(skills)
    role = profile_data.get("target_role") or headline or "Target Role"
    companies = profile_data.get("target_companies") or ""
    experience_highlights = profile_data.get("experience_highlights", [])
    exp_str = "\n".join(experience_highlights) if isinstance(experience_highlights, list) else str(experience_highlights)

    prompt = f"""You are an elite Executive LinkedIn Optimization Consultant and Talent Acquisition Strategist.
Audit this candidate's LinkedIn presence and career identity to optimize their profile for LinkedIn Recruiter, executive headhunters, and ATS Talent CRMs.

CANDIDATE DATA:
- Name: {name}
- Current Headline: {headline}
- Target Role: {role}
- LinkedIn URL: {norm_url} (Slug valid: {slug_info['has_custom_slug']})
- Professional Summary: {summary}
- Core Skills: {skills_str}
- Accomplishments / Experience:
{exp_str}
- Target Companies: {companies}

TASK:
Analyze the profile and generate a comprehensive JSON audit with the following EXACT schema. Return ONLY valid raw JSON without markdown or backticks.

{{
  "overall_score": <integer 0-100>,
  "grade": "<A+ | A | B+ | B | C>",
  "tier": "<e.g. All-Star Recruiter Magnet | Strong Presence | Needs Optimization>",
  "headline_score": <integer 0-100>,
  "about_score": <integer 0-100>,
  "skills_score": <integer 0-100>,
  "experience_score": <integer 0-100>,
  "slug_score": <integer 0-100>,
  "slug_feedback": "<assessment of their LinkedIn URL>",
  "headline_alternatives": [
    "<High-impact headline Option 1: Role | Core Skills | Value Proposition>",
    "<High-impact headline Option 2: Metrics & Business Impact driven>",
    "<High-impact headline Option 3: Recruiter Search & Boolean keyword optimized>"
  ],
  "about_rewrite": "<Full 3-section formatted About bio with Hook, Signature Accomplishments bullets, and Call-to-Action to connect>",
  "missing_keywords": ["<keyword 1>", "<keyword 2>", "<keyword 3>", "<keyword 4>", "<keyword 5>", "<keyword 6>"],
  "action_items": [
    "<Action item 1: Headline enhancement>",
    "<Action item 2: About section & Storytelling>",
    "<Action item 3: Skills calibration>",
    "<Action item 4: Experience bullet quantification>",
    "<Action item 5: Networking & Activity advice>"
  ]
}}"""

    raw_response = _call_gemini_for_linkedin(prompt, api_key=api_key, preferred_model=preferred_model)
    if raw_response:
        try:
            # Clean possible markdown fencing
            cleaned = re.sub(r"^```(?:json)?\s*", "", raw_response, flags=re.MULTILINE)
            cleaned = re.sub(r"\s*```$", "", cleaned, flags=re.MULTILINE).strip()
            data = json.loads(cleaned)

            overall_score = int(data.get("overall_score", 82))
            if overall_score >= 90:
                data["badge_color"] = "#15803d"
                data["badge_bg"] = "#dcfce7"
            elif overall_score >= 80:
                data["badge_color"] = "#2563eb"
                data["badge_bg"] = "#eff6ff"
            elif overall_score >= 70:
                data["badge_color"] = "#d97706"
                data["badge_bg"] = "#fef3c7"
            else:
                data["badge_color"] = "#dc2626"
                data["badge_bg"] = "#fee2e2"

            if not data.get("slug_feedback"):
                data["slug_feedback"] = slug_info["feedback"]

            return data
        except Exception as e:
            logging.warning(f"Failed to parse Gemini LinkedIn audit response: {e}")

    # Fallback if Gemini unavailable or JSON parse error
    return generate_fallback_linkedin_audit(norm_url, profile_data)
