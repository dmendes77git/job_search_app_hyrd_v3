"""
Integration test suite for v3 features:
1. ATS Document Exporter (PDF & DOCX)
2. Company Intelligence Agent
3. Autonomous Job Scout & Daily Digest
"""

import os
import sys
import io

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# 1. Test Document Exporter
print("--- 1. Testing Document Exporter (ATS PDF & DOCX) ---")
from src.utils.document_exporter import (
    create_cv_pdf,
    create_cv_docx,
    create_cover_letter_pdf,
    create_cover_letter_docx,
)

sample_cv = """# Alex Mercer
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

sample_cl = """RE: Application for Senior AI Engineer at Linear

Dear Linear Engineering Team,

I am writing to express my strong enthusiasm for the Senior AI Engineer role at Linear. Having followed Linear's engineering craftsmanship and product velocity, I would be thrilled to contribute to your core workflow intelligence.

In my previous roles, I architected resilient cloud systems and autonomous LLM agents that boosted developer throughput by 40%.

Sincerely,
Alex Mercer
"""

cv_pdf = create_cv_pdf(sample_cv, candidate_name="Alex Mercer")
assert isinstance(cv_pdf, io.BytesIO) and len(cv_pdf.getvalue()) > 500
print(f"✅ CV ATS PDF generated successfully! ({len(cv_pdf.getvalue())} bytes)")

cv_docx = create_cv_docx(sample_cv)
assert isinstance(cv_docx, io.BytesIO) and len(cv_docx.getvalue()) > 500
print(f"✅ CV ATS DOCX generated successfully! ({len(cv_docx.getvalue())} bytes)")

cl_pdf = create_cover_letter_pdf(sample_cl, candidate_name="Alex Mercer", company="Linear")
assert isinstance(cl_pdf, io.BytesIO) and len(cl_pdf.getvalue()) > 500
print(f"✅ Cover Letter PDF generated successfully! ({len(cl_pdf.getvalue())} bytes)")

cl_docx = create_cover_letter_docx(sample_cl, candidate_name="Alex Mercer", company="Linear")
assert isinstance(cl_docx, io.BytesIO) and len(cl_docx.getvalue()) > 500
print(f"✅ Cover Letter DOCX generated successfully! ({len(cl_docx.getvalue())} bytes)")


# 2. Test Company Intelligence Agent
print("\n--- 2. Testing Company Intelligence Agent ---")
from src.agents.company_intelligence_agent import generate_company_dossier

dossier = generate_company_dossier("Linear", job_title="Senior AI Engineer")
assert "stage_and_funding" in dossier
assert "tech_stack" in dossier
assert "leadership_team" in dossier
assert "strategic_interview_questions" in dossier
assert len(dossier["strategic_interview_questions"]) >= 3
print(f"✅ Company Intelligence Dossier for '{dossier['company_name']}' generated:")
print(f"   Stage: {dossier['stage_and_funding'].get('stage')}")
print(f"   ATS: {dossier.get('ats_system')}")
print(f"   Talking Point #1: \"{dossier['strategic_interview_questions'][0][:65]}...\"")


# 3. Test Autonomous Job Scout Agent
print("\n--- 3. Testing Autonomous Job Scout & Daily Digest ---")
from src.agents.job_scout_agent import run_job_scout_cycle

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
print(f"✅ Morning Career Digest generated successfully:")
print(f"   Headline: {digest['headline']}")
print(f"   Screened: {digest['stats']['total_screened']} jobs")
print(f"   Featured Matches: {len(digest['featured_jobs'])}")
print(f"   Top Fit Score: {digest['stats']['top_match_score']}%")

print("\n🚀 ALL 3 NEW V3 FEATURE SUITES PASSED VERIFICATION!")
