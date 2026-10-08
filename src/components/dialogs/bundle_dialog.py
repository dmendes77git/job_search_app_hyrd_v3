"""
Application Bundle (.zip) Dialog Component (Feature P3-A).
Allows candidates to preview and download all tailored requisition artifacts
in a unified, in-memory ZIP package with zero disk writes.
"""

from __future__ import annotations

import re
import streamlit as st
from typing import Any, Dict

from src.tools.bundle_exporter import build_application_bundle_zip


@st.dialog("📦 1-Click Application Bundle (.zip)", width="medium")
def show_bundle_dialog(job: Dict[str, Any], profile: Dict[str, Any]) -> None:
    """Render the Application Bundle dialog, compiling all tailored artifacts into an in-memory ZIP."""
    job_id = job.get("id") or job.get("job_id", "job_custom")
    company_name = job.get("company", "Target Company")
    job_title = job.get("title", "Target Role")
    cand_name = (profile.get("full_name") or st.session_state.get("candidate_name") or "Candidate").strip()
    cand_clean = re.sub(r"[^\w\-]", "_", cand_name)
    clean_company = re.sub(r"[^\w\-]", "_", company_name)

    api_key = st.session_state.get("gemini_api_key")
    pref_model = st.session_state.get("gemini_model")

    st.markdown(
        f"""
        <div style="background: #f8fafc; border: 1.5px solid #e2e8f0; border-radius: 8px; padding: 0.8rem 1rem; margin-bottom: 1rem;">
            <div style="font-weight: 700; color: #0f172a; font-size: 1rem;">🎯 {job_title}</div>
            <div style="color: #2563eb; font-weight: 600; font-size: 0.9rem;">🏢 {company_name}</div>
            <div style="font-size: 0.8rem; color: #64748b; margin-top: 4px;">Candidate: {cand_name}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("#### 📂 Package Contents:")
    st.markdown(
        """
        - 📄 **01_Resume_[Candidate]_[Company]** (`.docx` + `.pdf`)
        - ✉️ **02_CoverLetter_[Candidate]_[Company]** (`.docx` + `.pdf`)
        - 🎤 **03_InterviewPrep_Battlecard_[Company]** (`.docx`)
        - 🏢 **04_CompanyIntelligence_Dossier_[Company]** (`.docx` + `.pdf`)
        - 📬 **05_Executive_Outreach_Campaign** (`.txt`)
        """
    )

    # Gather any already cached artifacts
    cached_docs = {}
    if "customized_cvs" in st.session_state and job_id in st.session_state.customized_cvs:
        cached_docs["tailored_cv"] = st.session_state.customized_cvs[job_id]
    if "customized_cover_letters" in st.session_state and job_id in st.session_state.customized_cover_letters:
        cached_docs["cover_letter"] = st.session_state.customized_cover_letters[job_id]
    if "interview_prep_packs" in st.session_state and job_id in st.session_state.interview_prep_packs:
        cached_docs["interview_prep"] = st.session_state.interview_prep_packs[job_id]
    dossier_key = company_name.strip().lower()
    if "company_dossiers" in st.session_state and dossier_key in st.session_state.company_dossiers:
        cached_docs["company_dossier"] = st.session_state.company_dossiers[dossier_key]
    if "outreach_campaigns" in st.session_state and job_id in st.session_state.outreach_campaigns:
        cached_docs["outreach_campaign"] = st.session_state.outreach_campaigns[job_id]

    ready_count = len(cached_docs)
    st.caption(f"⚡ {ready_count}/5 artifacts pre-generated in your current session. Any missing assets will be generated on the fly.")

    zip_key = f"bundle_zip_{job_id}"
    if zip_key not in st.session_state:
        if st.button("⚡ Generate Complete Bundle (.zip)", key=f"btn_gen_bundle_{job_id}", type="primary", use_container_width=True):
            with st.spinner(f"Packaging tailored documents and dossiers for {company_name}..."):
                zip_stream = build_application_bundle_zip(
                    job=job,
                    profile=profile,
                    cached_docs=cached_docs,
                    api_key=api_key,
                    preferred_model=pref_model,
                )
                st.session_state[zip_key] = zip_stream.getvalue()
                st.rerun()
    else:
        st.success("✅ Application Bundle is compiled and ready for download!")
        zip_bytes = st.session_state[zip_key]
        st.download_button(
            label=f"📥 Download Bundle ({len(zip_bytes) // 1024} KB .zip)",
            data=zip_bytes,
            file_name=f"Application_Bundle_{cand_clean}_{clean_company}.zip",
            mime="application/zip",
            type="primary",
            use_container_width=True,
        )
        if st.button("🔄 Regenerate Bundle", key=f"btn_regen_bundle_{job_id}", use_container_width=True):
            del st.session_state[zip_key]
            st.rerun()
