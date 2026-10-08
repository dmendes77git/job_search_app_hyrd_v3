"""ATS-Optimized Tailored CV Dialog component."""

import re
import streamlit as st
from src.agents.application_agent import generate_customized_cv
from src.utils.document_exporter import create_cv_pdf, create_cv_docx
from src.utils.ats_optimizer import audit_ats_cv_compatibility, detect_job_language
from src.utils.user_manager import flush_session_to_user_workspace


@st.dialog("📄 ATS-Optimized Tailored CV", width="large")
def show_cv_dialog(job: dict, profile: dict) -> None:
    """Render the ATS-optimized CV preview, live editor, ATS screening audit, and Word .docx download modal."""
    job_id = job.get("id") or job.get("job_id", "job_custom")
    if "customized_cvs" not in st.session_state:
        st.session_state.customized_cvs = {}

    cand_name = (profile.get("full_name") or st.session_state.get("candidate_name") or "Candidate").strip()
    cand_clean = re.sub(r"[^\w\-]", "_", cand_name)
    clean_company = job.get("company", "Company").replace(" ", "_").lower()
    api_key = st.session_state.get("gemini_api_key")
    pref_model = st.session_state.get("gemini_model")

    detected_lang = detect_job_language(job)
    lang_state_key = f"cv_language_choice_{job_id}"
    if lang_state_key not in st.session_state:
        st.session_state[lang_state_key] = "pt-pt" if detected_lang.startswith("pt") else "en"

    active_lang = st.session_state[lang_state_key]

    if job_id not in st.session_state.customized_cvs:
        with st.spinner(f"🤖 DocAgent analyzing ATS requirements & tailoring CV for {job.get('company', 'Company')}..."):
            try:
                from src.pipeline import run_doc_stage
                from src.schemas import DocAgentInput, UserProfile, JobPosting, DocumentTypeEnum
                doc_out = run_doc_stage(
                    DocAgentInput(
                        user_profile=UserProfile(**profile),
                        job_posting=JobPosting(**job),
                        document_types=[DocumentTypeEnum.CV],
                        language=active_lang,
                        model_override=pref_model,
                    ),
                    api_key=api_key,
                )
                cv_text = doc_out.cv_markdown or generate_customized_cv(
                    job, profile, api_key=api_key, preferred_model=pref_model, language=active_lang
                )
            except Exception:
                cv_text = generate_customized_cv(
                    job, profile, api_key=api_key, preferred_model=pref_model, language=active_lang
                )
            st.session_state.customized_cvs[job_id] = cv_text
            flush_session_to_user_workspace()
    else:
        cv_text = st.session_state.customized_cvs[job_id]

    # Run comprehensive ATS compatibility audit
    audit = audit_ats_cv_compatibility(cv_text, job, profile)
    ats_score = audit["ats_score"]
    grade = audit["grade"]
    badge_bg = audit["badge_bg"]
    badge_color = audit["badge_color"]

    # Language Selector Controls
    col_lang, col_lang_info = st.columns([1.3, 2.7])
    with col_lang:
        lang_opts = ["🇵🇹 Português (PT-PT)", "🇺🇸 English"]
        curr_idx = 0 if active_lang == "pt-pt" else 1
        selected_label = st.selectbox(
            "🌐 Document Language / Idioma:",
            options=lang_opts,
            index=curr_idx,
            key=f"select_lang_cv_{job_id}",
        )
        new_lang = "pt-pt" if "Português" in selected_label else "en"
        if new_lang != active_lang:
            st.session_state[lang_state_key] = new_lang
            with st.spinner(f"Re-generating CV in {selected_label}..."):
                st.session_state.customized_cvs[job_id] = generate_customized_cv(
                    job, profile, api_key=api_key, preferred_model=pref_model, language=new_lang
                )
                flush_session_to_user_workspace()
                st.toast(f"CV updated to {selected_label}!")
                st.rerun()

    with col_lang_info:
        if active_lang == "pt-pt":
            st.markdown(
                "<div style='margin-top: 1.6rem; font-size: 0.82rem; color: #166534; background: #f0fdf4; padding: 6px 12px; border-radius: 6px; border: 1px solid #bbf7d0;'>"
                "🇵🇹 <strong>Norma PT-PT Ativa:</strong> Redigido de acordo com o Acordo Ortográfico e cabeçalhos ATS padrão para o mercado europeu."
                "</div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                "<div style='margin-top: 1.6rem; font-size: 0.82rem; color: #1e40af; background: #eff6ff; padding: 6px 12px; border-radius: 6px; border: 1px solid #bfdbfe;'>"
                "🇺🇸 <strong>English ATS Active:</strong> Optimized with standard international ATS headers & keyword density."
                "</div>",
                unsafe_allow_html=True,
            )

    # ATS Top Banner
    st.markdown(
        f"""<div style='background: {badge_bg}; border: 1px solid {badge_color}40; border-radius: 8px; padding: 0.85rem 1.1rem; margin-bottom: 1rem;'>
            <div style='display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;'>
                <div>
                    <span style='font-size: 1.15rem; font-weight: 700; color: {badge_color};'>🎯 ATS Compatibility Score: {ats_score}/100</span>
                    <span style='background: {badge_color}18; color: {badge_color}; padding: 3px 8px; border-radius: 6px; font-weight: 600; font-size: 0.82rem; margin-left: 8px;'>{grade}</span>
                </div>
                <div style='font-size: 0.82rem; color: #475569;'>
                    <strong>Target:</strong> {job.get('title', 'Target Role')} @ {job.get('company', 'Company')}
                </div>
            </div>
            <div style='font-size: 0.84rem; color: #334155; margin-top: 6px;'>
                🛡️ <strong>ATS Screening Engine:</strong> Formatted for 100% parser compatibility across <strong>Greenhouse, Ashby, Lever, Workday, & SmartRecruiters</strong> (single-column layout, standard section titles, and job-description keyword mirroring).
            </div>
        </div>""",
        unsafe_allow_html=True,
    )

    tab_preview, tab_audit, tab_edit = st.tabs([
        "👁️ Formatted Preview",
        f"🎯 ATS Screening Audit ({ats_score}%)",
        "✏️ Edit & Customize",
    ])

    with tab_preview:
        st.markdown(st.session_state.customized_cvs[job_id])

    with tab_audit:
        st.markdown("### 🎯 ATS Screening & Parsing Audit Report")
        st.caption("Applicant Tracking Systems parse and rank candidates based on keyword matches, standard header taxonomy, and clean layout.")

        # Metric summary cards
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("ATS Match Score", f"{ats_score}/100", delta="Ready to Apply" if ats_score >= 85 else "Review Keywords")
        m2.metric("Keyword Density", f"{audit['keyword_density_pct']}%")
        m3.metric("Matched Keywords", f"{len(audit['matched_keywords'])}")
        m4.metric("Quantified Metrics", f"{audit['metric_count']}")

        st.markdown("---")
        st.markdown("#### 📋 5-Point ATS Parser Compliance Checklist")
        for check in audit["compliance_checks"]:
            icon = "✅" if check["status"] else "⚠️"
            status_text = "PASSED" if check["status"] else "ATTENTION NEEDED"
            color = "#166534" if check["status"] else "#b45309"
            st.markdown(
                f"<div style='margin-bottom: 8px; font-size: 0.9rem;'>"
                f"{icon} <strong>{check['name']}</strong> — <span style='color:{color}; font-weight:600;'>{status_text}</span><br>"
                f"<span style='color: #64748b; font-size: 0.83rem; margin-left: 1.5rem;'>{check['detail']}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )

        st.markdown("---")
        st.markdown("#### 🔑 ATS Priority Keyword Match")

        # Display matched keywords
        if audit["matched_keywords"]:
            st.markdown("**Matched in Tailored CV:**")
            pills_html = " ".join([
                f"<span style='display:inline-block; background:#dcfce7; color:#166534; padding:3px 8px; border-radius:12px; font-size:0.8rem; margin:2px; font-weight:500;'>✓ {kw}</span>"
                for kw in audit["matched_keywords"]
            ])
            st.markdown(pills_html, unsafe_allow_html=True)

        # Display missing keywords if any
        if audit["missing_keywords"]:
            st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
            st.markdown("**Recommended Bonus Keywords to Increase Rank:**")
            pills_html = " ".join([
                f"<span style='display:inline-block; background:#f1f5f9; color:#475569; padding:3px 8px; border-radius:12px; font-size:0.8rem; margin:2px;'>+ {kw}</span>"
                for kw in audit["missing_keywords"]
            ])
            st.markdown(pills_html, unsafe_allow_html=True)
            st.caption("💡 Tip: You can switch to the 'Edit & Customize' tab and organically weave these terms into your bullet points.")

        st.markdown("---")
        st.info(
            "ℹ️ **Export Compliance:** When downloading via Word (.docx), the document is exported using standard ATS typography: "
            "Calibri font, 0.75-inch margins, standard heading styles, and single-column body text to prevent OCR parsing errors."
        )

    with tab_edit:
        st.caption("Edit the Markdown text below. When saved, the ATS Audit scorecard will automatically recalculate.")
        edited_cv = st.text_area(
            "Edit CV Markdown",
            value=st.session_state.customized_cvs[job_id],
            height=380,
            key=f"text_edit_cv_{job_id}",
        )
        if st.button("💾 Save Edits & Recalculate ATS Score", key=f"save_cv_edit_{job_id}", type="primary"):
            st.session_state.customized_cvs[job_id] = edited_cv
            flush_session_to_user_workspace()
            st.toast("CV updates saved! ATS Audit recalculated.")
            st.rerun()

    d_col1, d_col2, d_col3 = st.columns([1, 1, 0.9])
    with d_col1:
        pdf_buffer = create_cv_pdf(st.session_state.customized_cvs[job_id], candidate_name=cand_name)
        st.download_button(
            label="📥 Download ATS PDF (.pdf)",
            data=pdf_buffer.getvalue(),
            file_name=f"CV_{cand_clean}_{clean_company}.pdf",
            mime="application/pdf",
            use_container_width=True,
            help="100% ATS parser-compliant single-column PDF with clean Helvetica typography.",
        )
    with d_col2:
        docx_buffer = create_cv_docx(st.session_state.customized_cvs[job_id])
        st.download_button(
            label="📥 Download ATS Word (.docx)",
            data=docx_buffer.getvalue(),
            file_name=f"CV_{cand_clean}_{clean_company}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True,
            help="Exports in 100% ATS parser-safe single-column format with Calibri 11pt typography.",
        )
    with d_col3:
        if st.button("🔄 Regenerate", key=f"regen_cv_{job_id}", use_container_width=True):
            with st.spinner("Re-analyzing job requirements and regenerating ATS-optimized CV..."):
                try:
                    from src.pipeline import run_doc_stage
                    from src.schemas import DocAgentInput, UserProfile, JobPosting, DocumentTypeEnum
                    doc_out = run_doc_stage(
                        DocAgentInput(
                            user_profile=UserProfile(**profile),
                            job_posting=JobPosting(**job),
                            document_types=[DocumentTypeEnum.CV],
                            language=active_lang,
                            model_override=pref_model,
                        ),
                        api_key=api_key,
                    )
                    st.session_state.customized_cvs[job_id] = doc_out.cv_markdown or generate_customized_cv(
                        job, profile, api_key=api_key, preferred_model=pref_model, language=active_lang
                    )
                except Exception:
                    st.session_state.customized_cvs[job_id] = generate_customized_cv(
                        job, profile, api_key=api_key, preferred_model=pref_model, language=active_lang
                    )
                flush_session_to_user_workspace()
                st.toast("CV regenerated with ATS optimization!")
                st.rerun()
