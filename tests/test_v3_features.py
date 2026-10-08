"""
Unit and integration test suite for v3 features:
1. ATS Document Exporter (PDF & DOCX)
2. Company Intelligence Agent
3. Autonomous Job Scout & Daily Digest
"""

import io
import os
import sys
import pytest

from src.utils.document_exporter import (
    create_cv_pdf,
    create_cv_docx,
    create_cover_letter_pdf,
    create_cover_letter_docx,
)
from src.agents.company_intelligence_agent import generate_company_dossier
from src.agents.job_scout_agent import run_job_scout_cycle


SAMPLE_CV = """# Alex Mercer
alex.mercer@email.com | (555) 019-2834 | San Francisco, CA | linkedin.com/in/alexmercer

## PROFESSIONAL SUMMARY
Principal AI Platform Engineer with 8+ years architecting multi-agent pipelines and cloud platforms.

## CORE COMPETENCIES
- Python, FastAPI, Docker, Kubernetes, Google Cloud, AWS
- Multi-Agent Orchestration, Streamlit, LangChain, Gemini API

## PROFESSIONAL EXPERIENCE
### Staff AI Engineer | TechCorp Inc.
*2022 - Present | San Francisco, CA*
- Scaled distributed ingestion pipelines reducing query latency by 45%.
- Deployed LLM agents serving 2.5M daily queries with 99.9% uptime.
"""

SAMPLE_COVER_LETTER = """RE: Application for Senior AI Engineer at Linear

Dear Linear Engineering Team,

I am writing to express my strong enthusiasm for the Senior AI Engineer role at Linear. Having followed Linear's engineering craftsmanship and product velocity, I would be thrilled to contribute to your core workflow intelligence.

In my previous roles, I architected resilient cloud systems and autonomous LLM agents that boosted developer throughput by 40%.

Sincerely,
Alex Mercer
"""


def test_ats_resume_exporter_pdf_docx():
    """Verify ATS resume generation produces valid, non-empty PDF and Word DOCX bytes."""
    cv_pdf = create_cv_pdf(SAMPLE_CV, candidate_name="Alex Mercer")
    assert isinstance(cv_pdf, io.BytesIO)
    assert len(cv_pdf.getvalue()) > 500

    cv_docx = create_cv_docx(SAMPLE_CV)
    assert isinstance(cv_docx, io.BytesIO)
    assert len(cv_docx.getvalue()) > 500


def test_ats_cover_letter_exporter_pdf_docx():
    """Verify ATS cover letter generation produces valid, non-empty PDF and Word DOCX bytes."""
    cl_pdf = create_cover_letter_pdf(SAMPLE_COVER_LETTER, candidate_name="Alex Mercer", company="Linear")
    assert isinstance(cl_pdf, io.BytesIO)
    assert len(cl_pdf.getvalue()) > 500

    cl_docx = create_cover_letter_docx(SAMPLE_COVER_LETTER, candidate_name="Alex Mercer", company="Linear")
    assert isinstance(cl_docx, io.BytesIO)
    assert len(cl_docx.getvalue()) > 500


def test_company_intelligence_agent():
    """Verify company intelligence dossier generation with stage, tech stack, and questions."""
    dossier = generate_company_dossier("Linear", job_title="Senior AI Engineer")
    assert "stage_and_funding" in dossier
    assert "tech_stack" in dossier
    assert "leadership_team" in dossier
    assert "strategic_interview_questions" in dossier
    assert len(dossier["strategic_interview_questions"]) >= 3
    assert dossier["company_name"] == "Linear"


def test_autonomous_job_scout_cycle():
    """Verify autonomous job scout cycle generates a valid morning career digest."""
    sample_profile = {
        "full_name": "Alex Mercer",
        "headline": "Senior AI Software Engineer",
        "target_role": "Senior AI Software Engineer",
        "location": "Remote",
        "work_mode": "Remote Only",
        "target_companies": "Linear, OpenAI",
        "core_skills": ["Python", "FastAPI", "Kubernetes", "AI Agents"],
    }

    scout_result = run_job_scout_cycle(sample_profile, existing_job_ids=set())
    digest = scout_result["digest"]
    assert "id" in digest
    assert "headline" in digest
    assert "market_signals" in digest
    assert "featured_jobs" in digest
    assert "email_preview" in digest
    assert digest["stats"]["total_screened"] >= 0
