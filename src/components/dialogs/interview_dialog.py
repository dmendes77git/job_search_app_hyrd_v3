"""AI Interview Preparation Pack Dialog component."""

import re
import streamlit as st
from src.agents.interview_prep_agent import generate_interview_prep_pack, create_interview_prep_docx
from src.utils.user_manager import flush_session_to_user_workspace


@st.dialog("🎤 AI Interview Preparation Pack", width="large")
def show_interview_prep_dialog(job: dict, profile: dict) -> None:
    """Render the AI-generated Interview Prep Pack with Q&As, STAR answers, and Word download."""
    job_id = job.get("id") or job.get("job_id", "job_custom")
    if "interview_prep_packs" not in st.session_state:
        st.session_state.interview_prep_packs = {}

    cand_name = (profile.get("full_name") or st.session_state.get("candidate_name") or "Candidate").strip()
    cand_clean = re.sub(r"[^\w\-]", "_", cand_name)
    company_name = job.get("company", "Target Company")
    clean_company = company_name.replace(" ", "_").lower()
    title_name = job.get("title", "Target Role")
    api_key = st.session_state.get("gemini_api_key")
    pref_model = st.session_state.get("gemini_model")

    if job_id not in st.session_state.interview_prep_packs:
        with st.spinner(f"🤖 Hyrd Agent researching {company_name}, formulating technical Q&A, and building STAR responses..."):
            prep_pack = generate_interview_prep_pack(job, profile, api_key=api_key, preferred_model=pref_model)
            st.session_state.interview_prep_packs[job_id] = prep_pack
            flush_session_to_user_workspace()
    else:
        prep_pack = st.session_state.interview_prep_packs[job_id]

    st.markdown(
        f"<div style='background: #f5f3ff; border: 1px solid #ddd6fe; border-radius: 8px; padding: 0.75rem 1rem; margin-bottom: 1rem; font-size: 0.88rem; color: #5b21b6;'>"
        f"⚡ <strong>AI Interview Coaching Active:</strong> Customized master pack prepared for <strong>{title_name}</strong> at <strong>{company_name}</strong>."
        f"</div>",
        unsafe_allow_html=True,
    )

    tab_briefing, tab_tech, tab_star, tab_objections, tab_reverse, tab_cheat, tab_full = st.tabs([
        "📑 Briefing",
        "💻 Technical (5)",
        "🌟 STAR Scenarios (4)",
        "🛡️ Skill Gaps",
        "❓ Reverse Questions",
        "⚡ 15-Min Cheat Sheet",
        "✏️ Full Pack & Edit",
    ])

    with tab_briefing:
        st.markdown("### 🏢 Executive Interview Briefing")
        st.markdown(prep_pack.get("briefing") or "Briefing details.")

    with tab_tech:
        st.markdown("### 💻 Role-Specific Technical & Architecture Q&A")
        st.markdown(prep_pack.get("technical_qa") or "Technical questions and answers.")

    with tab_star:
        st.markdown("### 🌟 Behavioral & Leadership Scenarios (STAR Method)")
        st.markdown(prep_pack.get("behavioral_star") or "Behavioral questions mapped to candidate experience.")

    with tab_objections:
        st.markdown("### 🛡️ Anticipating Concerns & Objection Handling")
        st.markdown(prep_pack.get("objections") or "Strategies to turn skill gaps into learning strengths.")

    with tab_reverse:
        st.markdown("### ❓ High-Impact Reverse Questions to Ask the Interviewers")
        st.markdown(prep_pack.get("reverse_questions") or "Strategic questions categorized by interviewer role.")

    with tab_cheat:
        st.markdown("### ⚡ 15-Minute Pre-Call Rapid Review")
        st.markdown(prep_pack.get("cheat_sheet") or "Quick elevator pitch, key metrics, and keywords.")

    with tab_full:
        edited_pack = st.text_area(
            "Edit Full Interview Prep Markdown",
            value=prep_pack.get("raw_markdown", ""),
            height=380,
            key=f"text_edit_pack_{job_id}",
        )
        if st.button("💾 Save Edits to Prep Pack", key=f"save_pack_edit_{job_id}"):
            prep_pack["raw_markdown"] = edited_pack
            st.session_state.interview_prep_packs[job_id] = prep_pack
            flush_session_to_user_workspace()
            st.toast("Interview prep pack saved!")
            st.rerun()

    d_col1, d_col2, d_col3 = st.columns([1.2, 1.2, 1])
    with d_col1:
        docx_buffer = create_interview_prep_docx(prep_pack)
        st.download_button(
            label="📥 Download Prep Guide (.docx)",
            data=docx_buffer.getvalue(),
            file_name=f"InterviewPrep_{cand_clean}_{clean_company}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True,
        )
    with d_col2:
        cheat_text = prep_pack.get("cheat_sheet") or prep_pack.get("raw_markdown", "")
        st.download_button(
            label="📥 Download Cheat Sheet (.txt)",
            data=cheat_text,
            file_name=f"CheatSheet_{cand_clean}_{clean_company}.txt",
            mime="text/plain",
            use_container_width=True,
        )
    with d_col3:
        if st.button("🔄 Regenerate", key=f"regen_pack_{job_id}", use_container_width=True):
            with st.spinner("Regenerating targeted interview questions & STAR responses..."):
                st.session_state.interview_prep_packs[job_id] = generate_interview_prep_pack(
                    job, profile, api_key=api_key, preferred_model=pref_model
                )
                flush_session_to_user_workspace()
                st.toast("Interview Prep Pack regenerated by Agent!")
                st.rerun()
