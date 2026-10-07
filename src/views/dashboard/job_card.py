"""
Job Card Component for Screen 4 Dashboard.
Renders an individual matched opportunity card with metadata, Tech Stack Alignment Matrix,
salary market benchmarking, and agentic action triggers.
"""

from typing import Any, Dict
import streamlit as st

from src.components.application_dialogs import (
    show_company_dossier_dialog,
    show_cover_letter_dialog,
    show_cv_dialog,
    show_interview_prep_dialog,
    show_outreach_dialog,
)
from src.components.source_badges import (
    render_freshness_badge,
    render_salary_badge,
    render_tech_stack_matrix_html,
)
from src.utils.date_utils import parse_days_since_posted
from src.utils.pipeline_manager import (
    STAGE_APPLIED,
    STAGE_SAVED,
    add_or_update_pipeline,
    get_pipeline,
    remove_from_pipeline,
)
from src.utils.salary_evaluator import evaluate_job_salary


def render_job_card(
    job: Dict[str, Any],
    profile: Dict[str, Any],
    cand_min_pref: str = "",
    target_loc: str = "",
) -> None:
    """Render a comprehensive, interactive job card inside a Streamlit bordered container."""
    job_id = job["id"]
    is_saved = job_id in st.session_state.get("saved_jobs", set())
    is_applied = job_id in st.session_state.get("applied_jobs", set())
    job_type = job.get("job_type", "Full-time (Remote)")
    source_label = job.get("source", "Live ATS")
    salary_eval = job.get("salary_eval") or evaluate_job_salary(
        job_salary_str=job.get("salary", ""),
        job_title=job.get("title", ""),
        profile=profile,
        desired_min_salary_str=cand_min_pref,
        target_location=target_loc,
        job_location=job.get("location", ""),
    )

    with st.container(border=True):
        # Header Line 1: Job Position + Match Score Badge
        h_left, h_right = st.columns([3, 1])
        with h_left:
            st.markdown(f"### {job['title']}")
        with h_right:
            st.markdown(
                f"<div style='text-align: right; margin-top: 0.35rem;'>"
                f"<span style='background: {job['badge_color']}; color: #ffffff; padding: 0.28rem 0.8rem; border-radius: 9999px; font-size: 0.85rem; font-weight: 700; white-space: nowrap;'>"
                f"{job['fit_score']}% Match</span></div>",
                unsafe_allow_html=True,
            )

        # Header Line 2: Company name / size / source badge / Direct ATS Trust Tag / Target Dream
        src_l = source_label.lower()
        is_direct_ats = job.get("is_direct_ats") or any(
            ats in src_l for ats in ["ashby", "greenhouse", "lever", "smartrecruiters"]
        )

        if "linkedin" in src_l:
            badge_bg, badge_color, badge_border, badge_icon = "#eff6ff", "#0a66c2", "#bfdbfe", "💼"
        elif "itjobs" in src_l:
            badge_bg, badge_color, badge_border, badge_icon = "#fdf4ff", "#86198f", "#f5d0fe", "🇵🇹"
        elif "net-empregos" in src_l or "netempregos" in src_l:
            badge_bg, badge_color, badge_border, badge_icon = "#f0fdf4", "#15803d", "#bbf7d0", "🇵🇹"
        elif "landing" in src_l:
            badge_bg, badge_color, badge_border, badge_icon = "#fff7ed", "#c2410c", "#fed7aa", "🚀"
        else:
            badge_bg, badge_color, badge_border, badge_icon = "#f1f5f9", "#475569", "#e2e8f0", "🌐"

        is_target = job.get("is_target_company", False)
        target_badge_html = (
            "<span style='background: #f0fdf4; color: #166534; border: 1px solid #bbf7d0; font-size: 0.75rem; font-weight: 700; padding: 0.15rem 0.5rem; border-radius: 4px;'>"
            "⭐ Target Dream Company</span>"
            if is_target
            else ""
        )

        direct_ats_badge_html = (
            "<span style='background: #f5f3ff; color: #6d28d9; border: 1px solid #ddd6fe; font-size: 0.75rem; font-weight: 700; padding: 0.15rem 0.5rem; border-radius: 4px;'>"
            "⚡ Direct ATS Official Submission</span>"
            if is_direct_ats
            else ""
        )

        st.markdown(
            f"<div style='color: #2563eb; font-weight: 600; font-size: 1rem; margin-top: -0.65rem; margin-bottom: 0.25rem; display: flex; align-items: center; gap: 0.6rem; flex-wrap: wrap;'>"
            f"<span>{job['company']} &nbsp;/&nbsp; {job['company_size']}</span>"
            f"<span style='background: {badge_bg}; color: {badge_color}; border: 1px solid {badge_border}; font-size: 0.75rem; font-weight: 600; padding: 0.15rem 0.5rem; border-radius: 4px;'>"
            f"{badge_icon} {source_label}</span>"
            f"{direct_ats_badge_html}"
            f"{target_badge_html}</div>",
            unsafe_allow_html=True,
        )
        st.divider()

        # 2-Column Layout
        col_left, col_right = st.columns([1.1, 1.9], gap="large")
        with col_left:
            # Escape dollar sign to prevent LaTeX math font distortion
            raw_salary = job.get("salary", "Competitive")
            clean_salary = raw_salary.replace("$", r"\$")

            st.markdown(f"📍 **Location:** {job['location']}")

            # Days since posted (moved after Location)
            days_count, days_label = parse_days_since_posted(
                job.get("posted", "Recent"), job_id=job.get("id", "")
            )
            st.markdown(render_freshness_badge(days_count, days_label), unsafe_allow_html=True)

            st.markdown(f"💼 **Job Type:** {job_type}")
            st.markdown(f"💰 **Salary:** {clean_salary}")

            # Salary Score and Market Benchmark Rank with Location Badge
            st.markdown(render_salary_badge(salary_eval), unsafe_allow_html=True)

        with col_right:
            st.markdown("**JOB DESCRIPTION**")
            st.write(job["description"])

            # Tech Stack Alignment Matrix
            matched_skills_list = job.get("matched_skills", [])
            missing_skills_list = job.get("missing_skills", [])
            matrix_html = render_tech_stack_matrix_html(matched_skills_list, missing_skills_list)
            if matrix_html:
                st.markdown(matrix_html, unsafe_allow_html=True)

        st.divider()

        # Card details and action buttons
        col_reasons, col_actions = st.columns([2.5, 1.5], gap="medium")

        with col_reasons:
            with st.expander("🤖 Agent Match Insights & Skill Analysis", expanded=False):
                st.markdown("**Why You're a Match:**")
                for reason in job.get("key_reasons", []):
                    st.markdown(f"- {reason}")

                st.markdown("**Matched Skills:**")
                matched_html = " ".join([
                    f"<span style='background: #dcfce7; color: #15803d; border: 1px solid #86efac; padding: 0.15rem 0.5rem; border-radius: 4px; font-size: 0.8rem; font-weight: 500;'>✓ {s}</span>"
                    for s in job.get("matched_skills", [])
                ])
                st.markdown(f"<div style='margin-bottom: 0.5rem;'>{matched_html}</div>", unsafe_allow_html=True)

                if job.get("missing_skills"):
                    missing_html = " ".join([
                        f"<span style='background: #fef3c7; color: #b45309; border: 1px solid #fde68a; padding: 0.15rem 0.5rem; border-radius: 4px; font-size: 0.8rem;'>! {s}</span>"
                        for s in job["missing_skills"]
                    ])
                    st.markdown(f"**Potential Growth Gaps:**<br>{missing_html}", unsafe_allow_html=True)

                st.markdown("**💰 Market Compensation Evaluation:**")
                loc_calib = salary_eval.get("location_context", "Standard Benchmark")
                st.markdown(
                    f"- **Market Benchmark ({salary_eval['benchmark_title']}):** {salary_eval['benchmark_range'].replace('$', r'\$')}\n"
                    f"- **Salary Score:** {salary_eval['score']}/100 ({salary_eval['rank']})\n"
                    f"- **Target Location Calibration:** {loc_calib}\n"
                    f"- **Assessment:** {salary_eval['assessment'].replace('$', r'\$')}"
                )

        with col_actions:
            # 1. Primary External Link
            st.link_button(
                "Apply on Job Site ↗",
                url=job.get("apply_url", "https://www.google.com/search?q=jobs"),
                type="primary",
                use_container_width=True,
            )

            # 2. Secondary Row: Bookmark & In-App Application Tracker
            btn_col1, btn_col2 = st.columns(2)
            with btn_col1:
                save_label = "Saved ★" if is_saved else "Save ☆"
                if st.button(save_label, key=f"save_{job_id}", use_container_width=True):
                    if is_saved:
                        st.session_state.saved_jobs.remove(job_id)
                        pipeline = get_pipeline()
                        if job_id in pipeline and pipeline[job_id].get("stage") == STAGE_SAVED:
                            remove_from_pipeline(job_id)
                    else:
                        st.session_state.saved_jobs.add(job_id)
                        add_or_update_pipeline(job, stage=STAGE_SAVED)
                        st.toast(f"Saved {job['title']} to your Application Kanban!")
                    st.rerun()

            with btn_col2:
                track_label = "Applied ✓" if is_applied else "Track App"
                if st.button(
                    track_label,
                    key=f"track_{job_id}",
                    type="secondary" if not is_applied else "primary",
                    use_container_width=True,
                ):
                    if is_applied:
                        st.session_state.applied_jobs.remove(job_id)
                        pipeline = get_pipeline()
                        if job_id in pipeline and pipeline[job_id].get("stage") == STAGE_APPLIED:
                            pipeline[job_id]["stage"] = STAGE_SAVED
                        st.toast(f"Reverted application status for {job['title']}")
                    else:
                        st.session_state.applied_jobs.add(job_id)
                        add_or_update_pipeline(job, stage=STAGE_APPLIED)
                        st.toast(f"Moved {job['title']} to 'Applied' in your Application Kanban!")
                    st.rerun()

            # 3. Action Buttons below "Save" and "Track App"
            row1_col1, row1_col2 = st.columns(2)
            with row1_col1:
                cv_ready = job_id in st.session_state.get("customized_cvs", {})
                cv_btn_text = "📄 Tailored CV (ATS) ✓" if cv_ready else "📄 Tailored CV (ATS)"
                if st.button(
                    cv_btn_text,
                    key=f"btn_cv_{job_id}",
                    use_container_width=True,
                    help="Preview, audit score, or download ATS-optimized CV for this company",
                ):
                    show_cv_dialog(job, profile)
            with row1_col2:
                cl_ready = job_id in st.session_state.get("customized_cover_letters", {})
                cl_btn_text = "✉️ Cover Letter ✓" if cl_ready else "✉️ Cover Letter"
                if st.button(
                    cl_btn_text,
                    key=f"btn_cl_{job_id}",
                    use_container_width=True,
                    help="Preview or download tailored cover letter",
                ):
                    show_cover_letter_dialog(job, profile)

            row2_col1, row2_col2 = st.columns(2)
            with row2_col1:
                prep_ready = job_id in st.session_state.get("interview_prep_packs", {})
                prep_btn_text = "🎤 Prep Pack ✓" if prep_ready else "🎤 Prep Pack"
                if st.button(
                    prep_btn_text,
                    key=f"btn_prep_{job_id}",
                    use_container_width=True,
                    help="Role-specific interview preparation pack (Q&A, STAR stories, cheat sheet)",
                ):
                    show_interview_prep_dialog(job, profile)
            with row2_col2:
                outreach_ready = job_id in st.session_state.get("outreach_campaigns", {})
                outreach_btn_text = "📬 Outreach ✓" if outreach_ready else "📬 Outreach Drafter"
                if st.button(
                    outreach_btn_text,
                    key=f"btn_outreach_{job_id}",
                    use_container_width=True,
                    help="Multi-channel cold outreach drafter (LinkedIn note, hiring manager email, InMail, referral request)",
                ):
                    show_outreach_dialog(job, profile)

            doss_ready = job.get("company", "").strip().lower() in st.session_state.get(
                "company_dossiers", {}
            )
            doss_label = "🏢 Company Dossier ✓" if doss_ready else "🏢 Company Dossier"
            if st.button(
                doss_label,
                key=f"btn_dossier_{job_id}",
                use_container_width=True,
                help="Deep-dive employer intelligence: tech stack, funding, leadership, and interview talking points",
            ):
                show_company_dossier_dialog(job, profile)

    st.markdown("<div style='height: 0.5rem;'></div>", unsafe_allow_html=True)
