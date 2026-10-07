"""
Screen 4: Final Job Search Dashboard.
Displays ranked job matches, fit scores, and agentic matching rationales.
"""

import json
import re
import textwrap
import streamlit as st
from src.state import reset_wizard, SCREEN_INPUT, SCREEN_PIPELINE, go_to_screen
from src.mock_data import MOCK_JOB_RESULTS, SAMPLE_PARSED_PROFILE
from src.utils.salary_evaluator import evaluate_job_salary
from src.utils.date_utils import parse_days_since_posted
from src.components.application_dialogs import (
    show_cv_dialog,
    show_cover_letter_dialog,
    show_interview_prep_dialog,
    show_outreach_dialog,
    show_company_dossier_dialog,
)
from src.components.job_scout_dialog import show_job_scout_dialog
from src.utils.pipeline_manager import (
    STAGE_SAVED,
    STAGE_APPLIED,
    add_or_update_pipeline,
    remove_from_pipeline,
    get_pipeline,
)


def render_screen4() -> None:
    """Render the final dashboard displaying ranked job matches and recommendations."""
    profile = st.session_state.get("parsed_profile") or SAMPLE_PARSED_PROFILE

    target_loc_global = st.session_state.get("target_location") or profile.get("target_location") or profile.get("location") or ""
    loc_sub = f", and regional compensation benchmarks for **{target_loc_global}**" if target_loc_global else ", and market compensation benchmarks"

    # Header with title and quick link to Kanban
    head_left, head_right = st.columns([3, 1.8])
    with head_left:
        st.markdown("### 📊 Screen 4: AI Job Match Dashboard")
        st.markdown(
            "Here are the top roles identified and vetted by Hyrd. "
            f"Each opportunity has been evaluated against your resume experience, target salary{loc_sub}, and core skills."
        )
    with head_right:
        st.markdown("<div style='text-align: right; margin-top: 0.65rem;'>", unsafe_allow_html=True)
        pipeline_count = len(get_pipeline())
        if st.button(
            f"📋 Application Kanban ({pipeline_count}) →",
            type="primary",
            use_container_width=True,
            help="Open your interactive Application Pipeline & Kanban tracker",
        ):
            go_to_screen(SCREEN_PIPELINE)
        st.markdown("</div>", unsafe_allow_html=True)

    # Read live discovered jobs or fallback to mock
    jobs_source = st.session_state.get("discovered_jobs") or MOCK_JOB_RESULTS
    total_scraped = st.session_state.get("total_scraped_count") or (len(jobs_source) * 10)
    top_score = max([j["fit_score"] for j in jobs_source]) if jobs_source else 95
    top_company = jobs_source[0]["company"] if jobs_source else "Top Opportunity"

    # Top KPI Metrics Row
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric(label="Total Roles Scraped", value=f"{total_scraped}", delta="17 Concurrent Scrapers Active")
    with m2:
        st.metric(label="High-Fit Matches", value=f"{len(jobs_source)}", delta="Ranked by Fit")
    with m3:
        st.metric(label="Top Match Score", value=f"{top_score}%", delta=top_company[:18])
    with m4:
        st.metric(label="Target Title", value=st.session_state.get("target_role", "Target Role")[:22] + "...")

    st.markdown("<br>", unsafe_allow_html=True)

    # Autonomous Job Scout & Morning Career Digest Banner
    scout_cfg = st.session_state.get("job_scout_config", {})
    last_scout = scout_cfg.get("last_run_timestamp")
    digest_count = len(st.session_state.get("job_scout_digests", []))
    is_scout_active = scout_cfg.get("is_active", True)
    badge_color = "#047857" if is_scout_active else "#64748b"
    badge_bg = "#ecfdf5" if is_scout_active else "#f1f5f9"
    badge_txt = "🟢 Active Background Monitor" if is_scout_active else "⏸️ Monitoring Paused"

    with st.container(border=True):
        sb_col1, sb_col2, sb_col3 = st.columns([2.6, 1, 1], gap="small")
        with sb_col1:
            st.markdown(
                f"""<div style='display: flex; align-items: center; gap: 8px;'>
                    <span style='font-size: 1rem; font-weight: 700; color: #0f172a;'>🔭 Autonomous Job Scout</span>
                    <span style='background: {badge_bg}; color: {badge_color}; border: 1px solid {badge_color}40; font-size: 0.75rem; padding: 2px 8px; border-radius: 9999px; font-weight: 600;'>{badge_txt}</span>
                </div>
                <div style='font-size: 0.83rem; color: #64748b; margin-top: 4px;'>
                    Tracking Ashby, Greenhouse, Lever, Workday & remote hubs • Last scouted: <strong>{last_scout or 'Today'}</strong> • Digests: <strong>{digest_count} archived</strong>
                </div>""",
                unsafe_allow_html=True,
            )
        with sb_col2:
            if st.button("📰 Morning Digest", key="btn_open_scout_digest_s4", use_container_width=True, help="Read today's synthesized morning career intelligence digest"):
                show_job_scout_dialog(profile)
        with sb_col3:
            if st.button("⚡ Run Scout Now", key="btn_trigger_scout_inline_s4", use_container_width=True, help="Trigger live background scraper across all ATS targets"):
                show_job_scout_dialog(profile)

    st.markdown("<div style='height: 0.25rem;'></div>", unsafe_allow_html=True)

    # Filters and Controls
    with st.expander("🔍 Filter & Search Opportunities", expanded=False):
        fcol1, fcol2, fcol3, fcol4 = st.columns(4)
        with fcol1:
            search_query = st.text_input("Filter by Keyword / Company / Domain", placeholder="e.g. Finance, Marketing, Python, Toast, Berlin...")
        with fcol2:
            min_score = st.slider("Minimum Match Score", min_value=70, max_value=98, value=75, step=1)
        with fcol3:
            loc_filter = st.selectbox("Work Mode Filter", ["All Work Modes", "Remote Only", "Hybrid Only", "On-site Only"])
        with fcol4:
            salary_filter = st.selectbox("Salary Rank Filter", ["All Salary Ranks", "Within Market Standard & Above", "Above Market Only"])

    # Filter job results based on controls
    filtered_jobs = []
    cand_min_pref = st.session_state.get("min_salary") or profile.get("preferred_min_salary", "")
    target_loc = st.session_state.get("target_location") or profile.get("target_location") or profile.get("location") or ""

    for job in jobs_source:
        if job["fit_score"] < min_score:
            continue
        if search_query:
            query_lower = search_query.lower()
            in_title = query_lower in job["title"].lower()
            in_company = query_lower in job["company"].lower()
            in_skills = any(query_lower in s.lower() for s in job["matched_skills"])
            if not (in_title or in_company or in_skills):
                continue

        job_type_lower = job.get("job_type", "").lower()
        if loc_filter == "Remote Only" and "remote" not in job_type_lower:
            continue
        elif loc_filter == "Hybrid Only" and "hybrid" not in job_type_lower:
            continue
        elif loc_filter == "On-site Only" and "on-site" not in job_type_lower:
            continue

        # Evaluate proposed salary against candidate profile, preferences, and target location market benchmarks
        salary_eval = evaluate_job_salary(
            job_salary_str=job.get("salary", ""),
            job_title=job.get("title", ""),
            profile=profile,
            desired_min_salary_str=cand_min_pref,
            target_location=target_loc,
            job_location=job.get("location", ""),
        )
        job["salary_eval"] = salary_eval

        if salary_filter == "Above Market Only" and salary_eval["rank"] != "Above Market":
            continue
        elif salary_filter == "Within Market Standard & Above" and salary_eval["rank"] not in ["Within Market Standard", "Above Market"]:
            continue

        filtered_jobs.append(job)

    st.markdown(f"**Showing {len(filtered_jobs)} of {len(jobs_source)} matched positions**")

    # Render Job Cards
    for job in filtered_jobs:
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

        # Native Bordered Card Container
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

            # Header Line 2: Company name / number of employees / source tag
            src_l = source_label.lower()
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
                if is_target else ""
            )

            st.markdown(
                f"<div style='color: #2563eb; font-weight: 600; font-size: 1rem; margin-top: -0.65rem; margin-bottom: 0.25rem; display: flex; align-items: center; gap: 0.6rem; flex-wrap: wrap;'>"
                f"<span>{job['company']} &nbsp;/&nbsp; {job['company_size']}</span>"
                f"<span style='background: {badge_bg}; color: {badge_color}; border: 1px solid {badge_border}; font-size: 0.75rem; font-weight: 600; padding: 0.15rem 0.5rem; border-radius: 4px;'>"
                f"{badge_icon} {source_label}</span>"
                f"{target_badge_html}</div>",
                unsafe_allow_html=True,
            )
            st.divider()

            # 2-Column Layout
            col_left, col_right = st.columns([1.1, 1.9], gap="large")
            with col_left:
                # Escape dollar sign to prevent LaTeX math font distortion so salary matches location font & size exactly
                raw_salary = job.get("salary", "Competitive")
                clean_salary = raw_salary.replace("$", r"\$")

                st.markdown(f"📍 **Location:** {job['location']}")

                # Days since posted (moved after Location)
                days_count, days_label = parse_days_since_posted(job.get("posted", "Recent"), job_id=job.get("id", ""))
                day_unit = "day" if days_count == 1 else "days"

                if days_count <= 3:
                    f_bg, f_color, f_border, f_icon = "#ecfdf5", "#047857", "#a7f3d0", "🔥 New"
                elif days_count <= 14:
                    f_bg, f_color, f_border, f_icon = "#eff6ff", "#1d4ed8", "#bfdbfe", "⏱️ Recent"
                else:
                    f_bg, f_color, f_border, f_icon = "#f8fafc", "#475569", "#e2e8f0", "📅 Active"

                st.markdown(
                    f"<div style='margin-top: 0.15rem; margin-bottom: 0.35rem; display: flex; align-items: center; gap: 0.45rem; flex-wrap: wrap; font-size: 0.95rem;'>"
                    f"<span>📅 <strong>Days since posted:</strong> <strong>{days_count} {day_unit}</strong></span>"
                    f"<span style='background: {f_bg}; color: {f_color}; border: 1px solid {f_border}; padding: 0.12rem 0.55rem; border-radius: 9999px; font-size: 0.78rem; font-weight: 600; white-space: nowrap;'>"
                    f"{f_icon} ({days_label})</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

                st.markdown(f"💼 **Job Type:** {job_type}")
                st.markdown(f"💰 **Salary:** {clean_salary}")

                # Salary Score and Market Benchmark Rank with Location Badge
                score_val = salary_eval["score"]
                rank_label = salary_eval["rank"]
                rank_icon = salary_eval["rank_icon"]
                s_badge_bg = salary_eval["badge_bg"]
                s_badge_text = salary_eval["badge_text"]
                s_badge_border = salary_eval["badge_border"]
                loc_badge = salary_eval.get("location_badge") or "📍 Market Benchmark"

                st.markdown(
                    f"<div style='margin-top: 0.15rem; margin-bottom: 0.35rem; display: flex; align-items: center; gap: 0.45rem; flex-wrap: wrap; font-size: 0.95rem;'>"
                    f"<span>📊 <strong>Salary Score:</strong> <strong>{score_val}/100</strong></span>"
                    f"<span style='background: {s_badge_bg}; color: {s_badge_text}; border: 1px solid {s_badge_border}; padding: 0.12rem 0.55rem; border-radius: 9999px; font-size: 0.78rem; font-weight: 600; white-space: nowrap;'>"
                    f"{rank_icon} {rank_label}</span>"
                    f"<span style='background: #f8fafc; color: #475569; border: 1px solid #e2e8f0; padding: 0.12rem 0.5rem; border-radius: 4px; font-size: 0.74rem; font-weight: 500; white-space: nowrap;'>"
                    f"{loc_badge}</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

            with col_right:
                st.markdown("**JOB DESCRIPTION**")
                st.write(job["description"])

            st.divider()

            # Card details and action buttons
            col_reasons, col_actions = st.columns([2.5, 1.5], gap="medium")

            with col_reasons:
                with st.expander("🤖 Agent Match Insights & Skill Analysis", expanded=False):
                    st.markdown("**Why You're a Match:**")
                    for reason in job["key_reasons"]:
                        st.markdown(f"- {reason}")

                    st.markdown("**Matched Skills:**")
                    matched_html = " ".join(
                        [
                            f"<span style='background: #dcfce7; color: #15803d; border: 1px solid #86efac; padding: 0.15rem 0.5rem; border-radius: 4px; font-size: 0.8rem; font-weight: 500;'>✓ {s}</span>"
                            for s in job["matched_skills"]
                        ]
                    )
                    st.markdown(f"<div style='margin-bottom: 0.5rem;'>{matched_html}</div>", unsafe_allow_html=True)

                    if job.get("missing_skills"):
                        missing_html = " ".join(
                            [
                                f"<span style='background: #fef3c7; color: #b45309; border: 1px solid #fde68a; padding: 0.15rem 0.5rem; border-radius: 4px; font-size: 0.8rem;'>! {s}</span>"
                                for s in job["missing_skills"]
                            ]
                        )
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
                # 1. Primary External Link: Opens the job in a new browser tab
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
                    if st.button(track_label, key=f"track_{job_id}", type="secondary" if not is_applied else "primary", use_container_width=True):
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
                    if st.button(cv_btn_text, key=f"btn_cv_{job_id}", use_container_width=True, help="Preview, audit score, or download ATS-optimized CV for this company"):
                        show_cv_dialog(job, profile)
                with row1_col2:
                    cl_ready = job_id in st.session_state.get("customized_cover_letters", {})
                    cl_btn_text = "✉️ Cover Letter ✓" if cl_ready else "✉️ Cover Letter"
                    if st.button(cl_btn_text, key=f"btn_cl_{job_id}", use_container_width=True, help="Preview or download tailored cover letter"):
                        show_cover_letter_dialog(job, profile)

                row2_col1, row2_col2 = st.columns(2)
                with row2_col1:
                    prep_ready = job_id in st.session_state.get("interview_prep_packs", {})
                    prep_btn_text = "🎤 Prep Pack ✓" if prep_ready else "🎤 Prep Pack"
                    if st.button(prep_btn_text, key=f"btn_prep_{job_id}", use_container_width=True, help="Role-specific interview preparation pack (Q&A, STAR stories, cheat sheet)"):
                        show_interview_prep_dialog(job, profile)
                with row2_col2:
                    outreach_ready = job_id in st.session_state.get("outreach_campaigns", {})
                    outreach_btn_text = "📬 Outreach ✓" if outreach_ready else "📬 Outreach Drafter"
                    if st.button(outreach_btn_text, key=f"btn_outreach_{job_id}", use_container_width=True, help="Multi-channel cold outreach drafter (LinkedIn note, hiring manager email, InMail, referral request)"):
                        show_outreach_dialog(job, profile)

                doss_ready = job.get("company", "").strip().lower() in st.session_state.get("company_dossiers", {})
                doss_label = "🏢 Company Dossier ✓" if doss_ready else "🏢 Company Dossier"
                if st.button(doss_label, key=f"btn_dossier_{job_id}", use_container_width=True, help="Deep-dive employer intelligence: tech stack, funding, leadership, and interview talking points"):
                    show_company_dossier_dialog(job, profile)

        st.markdown("<div style='height: 0.5rem;'></div>", unsafe_allow_html=True)

    st.markdown("---")

    # Bottom Actions
    b_col1, b_col2, b_col3, b_col4 = st.columns([1, 1, 1.2, 1])
    with b_col1:
        if st.button("🔄 Start New Search (Reset)", use_container_width=True):
            reset_wizard()

    with b_col2:
        if st.button("✏️ Modify Search Preferences", use_container_width=True):
            go_to_screen(SCREEN_INPUT)

    with b_col3:
        if st.button("📋 Open Application Kanban", type="primary", use_container_width=True):
            go_to_screen(SCREEN_PIPELINE)

    with b_col4:
        st.download_button(
            label="📥 Export Matches (JSON)",
            data=json.dumps(filtered_jobs, indent=2),
            file_name="hyrd_job_matches.json",
            mime="application/json",
            use_container_width=True,
        )
