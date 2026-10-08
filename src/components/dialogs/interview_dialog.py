"""AI Interview Preparation Pack Dialog component."""

import re
import streamlit as st
from src.agents.interview_prep_agent import (
    generate_interview_prep_pack,
    create_interview_prep_docx,
    evaluate_mock_interview_answer,
)
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

    tab_briefing, tab_tech, tab_star, tab_objections, tab_reverse, tab_cheat, tab_practice, tab_full = st.tabs([
        "📑 Briefing",
        "💻 Technical (5)",
        "🌟 STAR Scenarios (4)",
        "🛡️ Skill Gaps",
        "❓ Reverse Questions",
        "⚡ 15-Min Cheat Sheet",
        "🎯 Mock Practice",
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

    with tab_practice:
        st.markdown("### 🎯 Interactive Mock Interview Simulator & STAR Evaluator")
        st.caption("Practice your spoken or typed responses to role-specific questions and receive instant AI grading against the STAR method.")

        # Extract questions from pack or provide high-yield defaults
        extracted_qs = []
        raw_tech = prep_pack.get("technical_qa", "")
        raw_star = prep_pack.get("behavioral_star", "")
        for line in (raw_tech + "\n" + raw_star).splitlines():
            line_str = line.strip()
            if line_str.startswith("### ") and "?" in line_str:
                extracted_qs.append(line_str.replace("### ", "").strip())
            elif line_str.startswith("### Tech Question") or line_str.startswith("### Behavioral Question"):
                extracted_qs.append(line_str.replace("### ", "").strip())

        if not extracted_qs:
            extracted_qs = [
                "Tell me about a time you architected a high-throughput system or resolved a major bottleneck.",
                "How do you approach aligning conflicting cross-functional priorities under tight deadlines?",
                "Describe a situation where a project failed or stalled. How did you diagnose and pivot?",
                "How do you evaluate and integrate new AI or system technologies into an existing stack?",
            ]

        extracted_qs.append("✍️ Custom Question (Type your own below)")

        selected_q = st.selectbox(
            "Select Question to Practice:",
            options=extracted_qs,
            key=f"mock_q_select_{job_id}",
        )

        active_question = selected_q
        if "Custom Question" in selected_q:
            active_question = st.text_input(
                "Enter Custom Interview Question:",
                placeholder="e.g. How do you design an event-driven microservices architecture?",
                key=f"mock_custom_q_{job_id}",
            )

        cand_answer = st.text_area(
            "Your Answer (Aim for 150-250 words using Situation, Task, Action, Result):",
            placeholder="When I was at... I was tasked with... To solve this, I designed and implemented... As a result, we achieved...",
            height=180,
            key=f"mock_ans_text_{job_id}",
        )

        eval_btn = st.button("🤖 Evaluate My Answer (STAR Method)", key=f"btn_eval_mock_{job_id}", type="primary", use_container_width=True)

        eval_state_key = f"mock_eval_result_{job_id}"
        if eval_btn:
            if not cand_answer.strip():
                st.warning("⚠️ Please enter an answer before running the evaluator.")
            else:
                with st.spinner("AI Coach evaluating STAR structure, technical depth, and quantifiable metrics..."):
                    res = evaluate_mock_interview_answer(
                        question=active_question,
                        answer_text=cand_answer,
                        job_title=title_name,
                        company=company_name,
                        api_key=api_key,
                        preferred_model=pref_model,
                    )
                    st.session_state[eval_state_key] = res

        if eval_state_key in st.session_state:
            res = st.session_state[eval_state_key]
            sc = res["overall_score"]
            verdict = res["verdict"]

            if sc >= 8.0:
                sc_bg, sc_color, sc_border = "#f0fdf4", "#166534", "#bbf7d0"
            elif sc >= 6.5:
                sc_bg, sc_color, sc_border = "#eff6ff", "#1e40af", "#bfdbfe"
            else:
                sc_bg, sc_color, sc_border = "#fffbeb", "#92400e", "#fde68a"

            st.markdown(
                f"""
                <div style="background: {sc_bg}; border: 1.5px solid {sc_border}; border-radius: 8px; padding: 0.85rem 1.1rem; margin-top: 1rem; margin-bottom: 1rem; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                    <div>
                        <div style="font-size: 0.8rem; font-weight: 600; text-transform: uppercase; color: {sc_color};">Executive Interview Evaluation</div>
                        <div style="font-size: 1.25rem; font-weight: 800; color: #0f172a;">{verdict}</div>
                    </div>
                    <div>
                        <span style="background: #ffffff; color: {sc_color}; border: 1px solid {sc_border}; padding: 6px 14px; border-radius: 9999px; font-weight: 800; font-size: 1.05rem;">
                            🎯 {sc} / 10.0
                        </span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # 4 Sub-score metrics
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("STAR Structure", f"{res['star_structure_score']}/10")
            m2.metric("Technical Depth", f"{res['technical_depth_score']}/10")
            m3.metric("Quantified Impact", f"{res['quantified_impact_score']}/10")
            m4.metric("Confidence Tone", f"{res['confidence_tone_score']}/10")

            c_str, c_gro = st.columns(2)
            with c_str:
                st.markdown("#### ✅ What Worked Well")
                for s in res.get("strengths", []):
                    st.markdown(f"- {s}")
            with c_gro:
                st.markdown("#### ⚠️ High-Impact Improvements")
                for g in res.get("growth_areas", []):
                    st.markdown(f"- {g}")

            if res.get("polished_answer"):
                with st.expander("💡 Recommended Executive STAR Polish", expanded=True):
                    st.markdown(res["polished_answer"])

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
