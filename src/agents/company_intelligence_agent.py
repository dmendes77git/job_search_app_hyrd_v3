"""
Company Intelligence & Executive Dossier Agent.
Conducts deep-dive AI investigations into target employers:
- Business Model, Funding Rounds, & Investors
- Engineering Stack & Architecture Patterns
- Leadership Team & Key Executives
- Recent Product Momentum & News
- Strategic Interview Talking Points
- Culture, Work-Life Balance & Glassdoor Sentiment
"""

import copy
import json
import logging
import os
import re
from typing import Dict, Any, Optional

logger = logging.getLogger("CompanyIntelligenceAgent")

_DOSSIER_CACHE: Dict[str, Dict[str, Any]] = {}


def clear_dossier_cache() -> None:
    """Clear in-memory cached company dossiers."""
    global _DOSSIER_CACHE
    _DOSSIER_CACHE.clear()


def get_mock_company_dossier(company_name: str, job_title: str = "Engineer") -> Dict[str, Any]:
    """Fallback high-quality structured dossier when offline or no API key provided."""
    clean_name = company_name.strip()
    return {
        "company_name": clean_name,
        "summary": f"{clean_name} is a high-growth technology leader recognized for product craftsmanship, developer-first tooling, and engineering autonomy.",
        "stage_and_funding": {
            "stage": "Series B - Growth Stage",
            "valuation": "$1.2B+ (Unicorn)",
            "total_raised": "$110M",
            "notable_investors": ["Sequoia Capital", "Accel", "Founders Fund", "Y Combinator"],
            "headcount": "150 - 500 employees (Global Remote)",
        },
        "tech_stack": {
            "core_languages": ["TypeScript", "Python", "Go", "Rust"],
            "frontend_and_apps": ["React", "Next.js", "Tailwind CSS", "Electron"],
            "backend_and_data": ["PostgreSQL", "Redis", "Kafka", "ClickHouse"],
            "cloud_and_infra": ["AWS", "Google Cloud", "Kubernetes", "Terraform", "Docker"],
            "ai_and_ml": ["PyTorch", "Hugging Face", "LLM APIs (Gemini, Claude, OpenAI)"],
        },
        "engineering_culture": {
            "style": "High-agency, product-minded engineering",
            "remote_policy": "100% Distributed / Remote-first with flexible timezones",
            "release_frequency": "Continuous deployment (multiple daily releases)",
            "highlights": [
                "Strong emphasis on documentation, async communication, and PR velocity.",
                "Engineers own features end-to-end from technical design document to production telemetry.",
                "Active contributors to modern open-source ecosystems.",
            ],
        },
        "leadership_team": [
            {"role": "CEO / Co-Founder", "name": f"Leadership Team at {clean_name}"},
            {"role": "CTO / Head of Engineering", "name": "VP of Technology & Architecture"},
            {"role": "Head of Talent", "name": "Global Talent Acquisition Lead"},
        ],
        "recent_momentum": [
            f"Expanded core product capabilities with AI-assisted workflow automation.",
            f"Crossed major customer milestones across North America and Europe.",
            f"Featured as one of the fastest growing developer platforms of the year.",
        ],
        "strategic_interview_questions": [
            f"How does the engineering organization at {clean_name} balance technical debt repayment against shipping fast for product milestones?",
            f"Given {clean_name}'s recent momentum, what are the primary scaling bottlenecks the infrastructure team is tackling this quarter?",
            f"What does an exemplary first 90 days look like for someone stepping into this {job_title} role?",
        ],
        "culture_and_sentiment": {
            "overall_rating": "4.6 / 5.0 (Glassdoor / Blind Benchmark)",
            "pros": [
                "High caliber, humble, and supportive teammates.",
                "Substantial autonomy without micromanagement.",
                "Competitive compensation with meaningful equity.",
            ],
            "watch_outs": [
                "High ownership means self-direction is required; minimal hand-holding.",
                "Fast-moving environment requires comfort with ambiguity.",
            ],
        },
        "ats_system": "Ashby / Greenhouse (Rigorous skills-first screening)",
    }


def generate_company_dossier(
    company_name: str,
    job_title: str = "",
    job_description: str = "",
    api_key: Optional[str] = None,
    preferred_model: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generate an in-depth intelligence dossier for a target employer using Gemini.
    Returns structured JSON with tech stack, funding, leadership, and talking points.
    """
    company_clean = company_name.strip()
    if not company_clean:
        return get_mock_company_dossier("Target Company", job_title=job_title)

    cache_key = f"{company_clean.lower()}::{job_title.lower()}"
    if cache_key in _DOSSIER_CACHE:
        return copy.deepcopy(_DOSSIER_CACHE[cache_key])

    key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not key:
        mock_dossier = get_mock_company_dossier(company_clean, job_title=job_title)
        _DOSSIER_CACHE[cache_key] = copy.deepcopy(mock_dossier)
        return mock_dossier

    prompt = f"""You are an elite corporate intelligence analyst and executive career strategist.
Generate an exhaustive, highly accurate intelligence dossier on this employer for a senior candidate applying for the position of: '{job_title or 'Engineer'}'.

COMPANY NAME: {company_clean}
JOB CONTEXT (if available): {job_description[:600] if job_description else 'N/A'}

Provide your response in strict, valid JSON with EXACTLY this structure:
{{
  "company_name": "{company_clean}",
  "summary": "<2-3 sentence crisp executive summary of what they do, who they sell to, and market standing>",
  "stage_and_funding": {{
    "stage": "<e.g. Series B, Series D, Public (NASDAQ/NYSE), Bootstrapped>",
    "valuation": "<estimated valuation or market cap>",
    "total_raised": "<total funding raised>",
    "notable_investors": ["<investor 1>", "<investor 2>", "<investor 3>"],
    "headcount": "<approximate employee count and remote/hybrid posture>"
  }},
  "tech_stack": {{
    "core_languages": ["<language 1>", "<language 2>", "<language 3>"],
    "frontend_and_apps": ["<framework 1>", "<framework 2>"],
    "backend_and_data": ["<database 1>", "<backend tool 2>"],
    "cloud_and_infra": ["<cloud provider>", "<container/orchestration>"],
    "ai_and_ml": ["<AI/ML tooling if applicable>"]
  }},
  "engineering_culture": {{
    "style": "<e.g. High-agency, async-first, design-driven>",
    "remote_policy": "<e.g. 100% Remote, Hybrid (2 days in office), etc.>",
    "release_frequency": "<e.g. Continuous deployment, bi-weekly sprints>",
    "highlights": [
      "<specific culture trait 1>",
      "<specific culture trait 2>",
      "<specific culture trait 3>"
    ]
  }},
  "leadership_team": [
    {{"role": "CEO / Co-Founder", "name": "<Name or executive profile>"}},
    {{"role": "CTO / Engineering Lead", "name": "<Name or tech leadership profile>"}},
    {{"role": "Head of Talent", "name": "<Talent / People Lead>"}}
  ],
  "recent_momentum": [
    "<recent product launch or milestone 1>",
    "<major company news or expansion 2>",
    "<strategic market achievement 3>"
  ],
  "strategic_interview_questions": [
    "<sharp, highly informed question 1 for the candidate to ask>",
    "<sharp question 2 demonstrating deep technical/architectural curiosity>",
    "<sharp question 3 regarding business goals, product vision, or 90-day success>"
  ],
  "culture_and_sentiment": {{
    "overall_rating": "<e.g. 4.5 / 5.0>",
    "pros": [
      "<genuine upside 1>",
      "<genuine upside 2>",
      "<genuine upside 3>"
    ],
    "watch_outs": [
      "<practical trade-off or challenge 1 to be aware of>",
      "<practical challenge 2>"
    ]
  }},
  "ats_system": "<Likely ATS e.g. Ashby, Greenhouse, Lever, Workday>"
}}

IMPORTANT: Return ONLY the JSON object. Do NOT wrap in markdown code blocks or preamble.
"""

    from src.utils.gemini_client import generate_gemini_json

    data = generate_gemini_json(prompt, api_key=key, preferred_model=preferred_model)
    if isinstance(data, dict) and "company_name" in data:
        _DOSSIER_CACHE[cache_key] = copy.deepcopy(data)
        return data

    fallback = get_mock_company_dossier(company_clean, job_title=job_title)
    _DOSSIER_CACHE[cache_key] = copy.deepcopy(fallback)
    return fallback
