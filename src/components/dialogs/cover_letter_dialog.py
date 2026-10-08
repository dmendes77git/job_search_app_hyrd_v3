"""Agent-Tailored Cover Letter Dialog component."""

import re
import streamlit as st
from src.agents.application_agent import generate_customized_cover_letter
from src.utils.document_exporter import (
    create_cover_letter_pdf,
    create_cover_letter_docx,
)
from src.utils.ats_optimizer import detect_job_language
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

    detected_lang = detect_job_language(job)
    lang_state_key = f"cl_language_choice_{job_id}"
    if lang_state_key not in st.session_state:
        st.session_state[lang_state_key] = "pt-pt" if detected_lang.startswith("pt") else "en"

    active_lang = st.session_state[lang_state_key]

    if job_id not in st.session_state.customized_cover_letters:
        with st.spinner(f"🤖 DocAgent reviewing job posting, profile & tailored CV for {job.get('company', 'Company')}..."):
            try:
                from src.pipeline import run_doc_stage
                from src.schemas import DocAgentInput, UserProfile, JobPosting, DocumentTypeEnum
                doc_out = run_doc_stage(
                    DocAgentInput(
                        user_profile=UserProfile(**profile),
                        job_posting=JobPosting(**job),
                        document_types=[DocumentTypeEnum.COVER_LETTER],
                        language=active_lang,
                        model_override=pref_model,
                    ),
                    api_key=api_key,
                )
                letter_text = doc_out.cover_letter_markdown or generate_customized_cover_letter(
                    job, profile, custom_cv=cv_text, api_key=api_key, preferred_model=pref_model, language=active_lang
                )
            except Exception:
                letter_text = generate_customized_cover_letter(
                    job, profile, custom_cv=cv_text, api_key=api_key, preferred_model=pref_model, language=active_lang
                )
            st.session_state.customized_cover_letters[job_id] = letter_text
            flush_session_to_user_workspace()
    else:
        letter_text = st.session_state.customized_cover_letters[job_id]

    # Language Selector Controls
    col_lang, col_lang_info = st.columns([1.3, 2.7])
    with col_lang:
        lang_opts = ["🇵🇹 Português (PT-PT)", "🇺🇸 English"]
        curr_idx = 0 if active_lang == "pt-pt" else 1
        selected_label = st.selectbox(
            "🌐 Document Language / Idioma:",
            options=lang_opts,
            index=curr_idx,
            key=f"select_lang_cl_{job_id}",
        )
        new_lang = "pt-pt" if "Português" in selected_label else "en"
        if new_lang != active_lang:
            st.session_state[lang_state_key] = new_lang
            with st.spinner(f"Re-generating Cover Letter in {selected_label}..."):
                st.session_state.customized_cover_letters[job_id] = generate_customized_cover_letter(
                    job, profile, custom_cv=cv_text, api_key=api_key, preferred_model=pref_model, language=new_lang
                )
                flush_session_to_user_workspace()
                st.toast(f"Cover letter updated to {selected_label}!")
                st.rerun()

    with col_lang_info:
        if active_lang == "pt-pt":
            st.markdown(
                "<div style='margin-top: 1.6rem; font-size: 0.82rem; color: #166534; background: #f0fdf4; padding: 6px 12px; border-radius: 6px; border: 1px solid #bbf7d0;'>"
                "🇵🇹 <strong>Carta em Português Europeu:</strong> Redigida com vocabulário PT-PT profissional e referência explícita de candidatura."
                "</div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                "<div style='margin-top: 1.6rem; font-size: 0.82rem; color: #1e40af; background: #eff6ff; padding: 6px 12px; border-radius: 6px; border: 1px solid #bfdbfe;'>"
                "🇺🇸 <strong>English Cover Letter Active:</strong> Aligned with ATS requisition guidelines & keyword mirroring."
                "</div>",
                unsafe_allow_html=True,
            )

    st.markdown(
        f"<div style='background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 8px; padding: 0.75rem 1rem; margin-bottom: 1rem; font-size: 0.88rem; color: #1e40af;'>"
        f"⚡ <strong>ATS-Aligned Cover Letter:</strong> Crafted specifically for hiring teams and ATS screeners at <strong>{job.get('company', 'Company')}</strong>. Includes formal Requisition Matching line and job-specific keyword mirroring."
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
                try:
                    from src.pipeline import run_doc_stage
                    from src.schemas import DocAgentInput, UserProfile, JobPosting, DocumentTypeEnum
                    doc_out = run_doc_stage(
                        DocAgentInput(
                            user_profile=UserProfile(**profile),
                            job_posting=JobPosting(**job),
                            document_types=[DocumentTypeEnum.COVER_LETTER],
                            language=active_lang,
                            model_override=pref_model,
                        ),
                        api_key=api_key,
                    )
                    st.session_state.customized_cover_letters[job_id] = doc_out.cover_letter_markdown or generate_customized_cover_letter(
                        job, profile, custom_cv=cv_text, api_key=api_key, preferred_model=pref_model, language=active_lang
                    )
                except Exception:
                    st.session_state.customized_cover_letters[job_id] = generate_customized_cover_letter(
                        job, profile, custom_cv=cv_text, api_key=api_key, preferred_model=pref_model, language=active_lang
                    )
                flush_session_to_user_workspace()
                st.toast("Cover letter regenerated by Agent!")
                st.rerun()
