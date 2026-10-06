"""Agent-Tailored Cover Letter Dialog component."""

import re
import streamlit as st
from src.agents.application_agent import generate_customized_cover_letter
from src.utils.document_exporter import (
    create_cover_letter_pdf,
    create_cover_letter_docx,
)
from src.utils.user_manager import flush_session_to_user_workspace


@st.dialog("✉️ Agent-Tailored Cover Letter", width="large")
def show_cover_letter_dialog(job: dict, profile: dict) -> None:
    """Render the tailored cover letter preview, live editor, and text download modal."""
    job_id = job.get("id") or job.get("job_id", "job_custom")
    if "customized_cover_letters" not in st.session_state:
        st.session_state.customized_cover_letters = {}

    cand_name = (profile.get("full_name") or st.session_state.get("candidate_name") or "Candidate").strip()
    cand_clean = re.sub(r"[^\w\-]", "_", cand_name)
    clean_company = job.get("company", "Company").replace(" ", "_").lower()
    api_key = st.session_state.get("gemini_api_key")
    pref_model = st.session_state.get("gemini_model")
    cv_text = st.session_state.get("customized_cvs", {}).get(job_id, "")

    if job_id not in st.session_state.customized_cover_letters:
        with st.spinner(f"🤖 Hyrd Agent reviewing job posting, profile & tailored CV for {job.get('company', 'Company')}..."):
            letter_text = generate_customized_cover_letter(
                job, profile, custom_cv=cv_text, api_key=api_key, preferred_model=pref_model
            )
            st.session_state.customized_cover_letters[job_id] = letter_text
            flush_session_to_user_workspace()
    else:
        letter_text = st.session_state.customized_cover_letters[job_id]

    st.markdown(
        f"<div style='background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 8px; padding: 0.75rem 1rem; margin-bottom: 1rem; font-size: 0.88rem; color: #1e40af;'>"
        f"⚡ <strong>ATS-Aligned Cover Letter:</strong> Crafted specifically for hiring teams and ATS screeners at <strong>{job.get('company', 'Company')}</strong>. Includes formal Requisition Matching line (<code>RE: Application for {job.get('title', 'Target Role')}</code>) and job-specific keyword mirroring."
        f"</div>",
        unsafe_allow_html=True,
    )

    tab_preview, tab_edit = st.tabs(["👁️ Formatted Preview", "✏️ Edit & Customize"])
    with tab_preview:
        st.markdown(st.session_state.customized_cover_letters[job_id])

    with tab_edit:
        edited_letter = st.text_area(
            "Edit Cover Letter",
            value=st.session_state.customized_cover_letters[job_id],
            height=380,
            key=f"text_edit_cl_{job_id}",
        )
        if st.button("💾 Save Edits", key=f"save_cl_edit_{job_id}"):
            st.session_state.customized_cover_letters[job_id] = edited_letter
            flush_session_to_user_workspace()
            st.toast("Cover letter updates saved!")
            st.rerun()

    cl_p_col1, cl_p_col2, cl_p_col3, cl_p_col4 = st.columns([1, 1, 0.8, 0.9])
    with cl_p_col1:
        cl_pdf = create_cover_letter_pdf(
            st.session_state.customized_cover_letters[job_id],
            candidate_name=cand_name,
            company=job.get("company", "Company"),
            job_title=job.get("title", "Target Role"),
        )
        st.download_button(
            label="📥 Download PDF (.pdf)",
            data=cl_pdf.getvalue(),
            file_name=f"CoverLetter_{cand_clean}_{clean_company}.pdf",
            mime="application/pdf",
            use_container_width=True,
            help="Executive letterhead PDF layout ready for hiring managers and recruiters.",
        )
    with cl_p_col2:
        cl_docx = create_cover_letter_docx(
            st.session_state.customized_cover_letters[job_id],
            candidate_name=cand_name,
            company=job.get("company", "Company"),
            job_title=job.get("title", "Target Role"),
        )
        st.download_button(
            label="📥 Download Word (.docx)",
            data=cl_docx.getvalue(),
            file_name=f"CoverLetter_{cand_clean}_{clean_company}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True,
            help="Formatted Microsoft Word (.docx) with executive typography.",
        )
    with cl_p_col3:
        st.download_button(
            label="📥 Plain Text (.txt)",
            data=st.session_state.customized_cover_letters[job_id],
            file_name=f"CoverLetter_{cand_clean}_{clean_company}.txt",
            mime="text/plain",
            use_container_width=True,
        )
    with cl_p_col4:
        if st.button("🔄 Regenerate", key=f"regen_cl_{job_id}", use_container_width=True):
            with st.spinner("Re-analyzing job requirements and regenerating Cover Letter..."):
                st.session_state.customized_cover_letters[job_id] = generate_customized_cover_letter(
                    job, profile, custom_cv=cv_text, api_key=api_key, preferred_model=pref_model
                )
                flush_session_to_user_workspace()
                st.toast("Cover letter regenerated by Agent!")
                st.rerun()
