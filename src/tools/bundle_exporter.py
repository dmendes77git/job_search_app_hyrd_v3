"""
Job Application Bundle (.zip) Exporter (Feature P3-A).
Packages all tailored application and interview artifacts for a specific target requisition
into a single, systematically organized in-memory ZIP archive:
1. 01_Resume_[Candidate]_[Company].docx & .pdf
2. 02_CoverLetter_[Candidate]_[Company].docx & .pdf
3. 03_InterviewPrep_Battlecard_[Company].docx
4. 04_CompanyIntelligence_Dossier_[Company].docx & .pdf
5. 05_Executive_Outreach_Campaign.txt

Outputs pure in-memory BytesIO streams for direct Streamlit download without disk writes.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import io
import re
import zipfile
from typing import Any, Dict, Optional

from src.utils.document_exporter import (
    create_cv_docx,
    create_cv_pdf,
    create_cover_letter_docx,
    create_cover_letter_pdf,
    create_interview_prep_docx,
)
from src.tools.dossier_exporter import build_dossier_docx, build_dossier_pdf
from src.agents.application_agent import generate_customized_cv, generate_cover_letter
from src.agents.interview_prep_agent import generate_interview_prep_pack
from src.agents.company_intelligence_agent import generate_company_dossier, get_mock_company_dossier
from src.agents.outreach_agent import generate_outreach_campaign


def _sanitize_filename(name: str) -> str:
    """Sanitize name for cross-platform safe ZIP filenames."""
    clean = re.sub(r"[^\w\-]", "_", (name or "").strip())
    return clean or "Candidate"


def build_application_bundle_zip(
    job: Dict[str, Any],
    profile: Dict[str, Any],
    cached_docs: Optional[Dict[str, Any]] = None,
    api_key: Optional[str] = None,
    preferred_model: Optional[str] = None,
) -> io.BytesIO:
    """
    Generate an in-memory ZIP archive containing the complete suite of tailored application artifacts.
    Reuses existing cached documents if available in candidate session to maximize speed.
    Concurrently executes uncached document generation tasks in parallel.
    """
    cached = cached_docs or {}
    company_name = job.get("company") or "Target_Company"
    cand_name = profile.get("full_name") or "Candidate"
    job_title = job.get("title") or "Position"

    clean_comp = _sanitize_filename(company_name)
    clean_cand = _sanitize_filename(cand_name)

    # Resolve all uncached text/data payloads concurrently via ThreadPoolExecutor
    futures: Dict[str, Any] = {}
    with ThreadPoolExecutor(max_workers=5) as executor:
        if not cached.get("tailored_cv"):
            futures["tailored_cv"] = executor.submit(
                generate_customized_cv,
                job=job,
                profile=profile,
                api_key=api_key,
                preferred_model=preferred_model,
            )
        if not cached.get("cover_letter"):
            futures["cover_letter"] = executor.submit(
                generate_cover_letter,
                job=job,
                profile=profile,
                api_key=api_key,
                preferred_model=preferred_model,
            )
        if not cached.get("interview_prep"):
            futures["interview_prep"] = executor.submit(
                generate_interview_prep_pack,
                job=job,
                profile=profile,
                api_key=api_key,
                preferred_model=preferred_model,
            )
        if not cached.get("company_dossier"):
            futures["company_dossier"] = executor.submit(
                generate_company_dossier,
                company_name=company_name,
                job_title=job_title,
                job_description=job.get("description", ""),
                api_key=api_key,
                preferred_model=preferred_model,
            )
        if not cached.get("outreach_campaign"):
            futures["outreach_campaign"] = executor.submit(
                generate_outreach_campaign,
                job=job,
                profile=profile,
                api_key=api_key,
                preferred_model=preferred_model,
            )

        cv_text = cached.get("tailored_cv") or (futures["tailored_cv"].result() if "tailored_cv" in futures else "")
        cl_text = cached.get("cover_letter") or (futures["cover_letter"].result() if "cover_letter" in futures else "")
        prep_pack = cached.get("interview_prep") or (futures["interview_prep"].result() if "interview_prep" in futures else {})
        dossier = cached.get("company_dossier") or (futures["company_dossier"].result() if "company_dossier" in futures else {})
        outreach = cached.get("outreach_campaign") or (futures["outreach_campaign"].result() if "outreach_campaign" in futures else {})

    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zip_file:
        # 1. Resume / CV (.docx & .pdf)
        cv_docx_buf = create_cv_docx(cv_text)
        zip_file.writestr(f"01_Resume_{clean_cand}_{clean_comp}.docx", cv_docx_buf.getvalue())

        cv_pdf_buf = create_cv_pdf(cv_text, candidate_name=cand_name)
        zip_file.writestr(f"01_Resume_{clean_cand}_{clean_comp}.pdf", cv_pdf_buf.getvalue())

        # 2. Cover Letter (.docx & .pdf)
        cl_docx_buf = create_cover_letter_docx(
            letter_text=cl_text,
            candidate_name=cand_name,
            company=company_name,
            job_title=job_title,
        )
        zip_file.writestr(f"02_CoverLetter_{clean_cand}_{clean_comp}.docx", cl_docx_buf.getvalue())

        cl_pdf_buf = create_cover_letter_pdf(
            letter_text=cl_text,
            candidate_name=cand_name,
            company=company_name,
            job_title=job_title,
        )
        zip_file.writestr(f"02_CoverLetter_{clean_cand}_{clean_comp}.pdf", cl_pdf_buf.getvalue())

        # 3. Interview Preparation Battlecard (.docx)
        prep_docx_buf = create_interview_prep_docx(prep_pack)
        zip_file.writestr(f"03_InterviewPrep_Battlecard_{clean_comp}.docx", prep_docx_buf.getvalue())

        # 4. Company Intelligence Dossier (.docx & .pdf)
        dossier_docx_buf = build_dossier_docx(dossier)
        zip_file.writestr(f"04_CompanyIntelligence_Dossier_{clean_comp}.docx", dossier_docx_buf.getvalue())

        dossier_pdf_buf = build_dossier_pdf(dossier)
        zip_file.writestr(f"04_CompanyIntelligence_Dossier_{clean_comp}.pdf", dossier_pdf_buf.getvalue())

        # 5. Executive Outreach Campaign (.txt)

        outreach_lines = [
            f"EXECUTIVE RECRUITER COLD OUTREACH CAMPAIGN",
            f"Candidate: {cand_name} | Role: {job_title} | Company: {company_name}",
            "=" * 70,
            "",
            "1. LINKEDIN CONNECTION NOTE (<= 300 Characters):",
            outreach.get("linkedin_note", {}).get("text", "") if isinstance(outreach.get("linkedin_note"), dict) else str(outreach.get("linkedin_note", "")),
            "",
            "2. HIRING MANAGER DIRECT EMAIL:",
            f"Subject: {outreach.get('hiring_manager_email', {}).get('subject', '')}",
            outreach.get("hiring_manager_email", {}).get("body", ""),
            "",
            "3. RECRUITER & TALENT INMAIL:",
            f"Subject: {outreach.get('recruiter_inmail', {}).get('subject', '')}",
            outreach.get("recruiter_inmail", {}).get("body", ""),
            "",
            "4. WARM INTERNAL REFERRAL REQUEST:",
            f"Subject: {outreach.get('referral_request', {}).get('subject', '')}",
            outreach.get("referral_request", {}).get("body", ""),
            "",
            "5. POST-INTERVIEW THANK YOU NOTE:",
            f"Subject: {outreach.get('thank_you_note', {}).get('subject', '')}",
            outreach.get("thank_you_note", {}).get("body", ""),
        ]
        zip_file.writestr("05_Executive_Outreach_Campaign.txt", "\n".join(outreach_lines).encode("utf-8"))

    zip_buffer.seek(0)
    return zip_buffer
