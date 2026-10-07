"""
Screen 4: Final Job Search Dashboard.
Displays ranked job matches, fit scores, and agentic matching rationales.
"""

import json
import streamlit as st

from src.components.job_scout_dialog import show_job_scout_dialog
from src.mock_data import MOCK_JOB_RESULTS, SAMPLE_PARSED_PROFILE
from src.state import SCREEN_INPUT, SCREEN_PIPELINE, go_to_screen, reset_wizard
from src.utils.pipeline_manager import get_pipeline
from src.utils.salary_evaluator import evaluate_job_salary
from src.views.dashboard import render_job_card


def render_screen4() -> None:
    """Render the final dashboard displaying ranked job matches and recommendations."""
    profile = st.session_state.get("parsed_profile") or SAMPLE_PARSED_PROFILE

    target_loc_global = (
        st.session_state.get("target_location")
        or profile.get("target_location")
        or profile.get("location")
        or ""
    )
    loc_sub = (
        f", and regional compensation benchmarks for **{target_loc_global}**"
        if target_loc_global
        else ", and market compensation benchmarks"
    )

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
            if st.button(
                "📰 Morning Digest",
                key="btn_open_scout_digest_s4",
                use_container_width=True,
                help="Read today's synthesized morning career intelligence digest",
            ):
                show_job_scout_dialog(profile)
        with sb_col3:
            if st.button(
                "⚡ Run Scout Now",
                key="btn_trigger_scout_inline_s4",
                use_container_width=True,
                help="Trigger live background scraper across all ATS targets",
            ):
                show_job_scout_dialog(profile)

    st.markdown("<div style='height: 0.25rem;'></div>", unsafe_allow_html=True)

    # Filters and Controls
    with st.expander("🔍 Filter & Search Opportunities", expanded=False):
        fcol1, fcol2, fcol3, fcol4, fcol5 = st.columns(5)
        with fcol1:
            search_query = st.text_input(
                "Filter by Keyword / Company / Domain",
                placeholder="e.g. Finance, Marketing, Python, Toast, Berlin...",
            )
        with fcol2:
            min_score = st.slider("Minimum Match Score", min_value=70, max_value=98, value=75, step=1)
        with fcol3:
            loc_filter = st.selectbox(
                "Work Mode Filter",
                ["All Work Modes", "Remote Only", "Hybrid Only", "On-site Only"],
            )
        with fcol4:
            salary_filter = st.selectbox(
                "Salary Rank Filter",
                ["All Salary Ranks", "Within Market Standard & Above", "Above Market Only"],
            )
        with fcol5:
            source_type_filter = st.selectbox(
                "Source Channel",
                ["All Channels", "Direct ATS Only", "Portuguese Portals Only", "Remote Hubs Only"],
            )

    # Filter job results based on controls
    filtered_jobs = []
    cand_min_pref = st.session_state.get("min_salary") or profile.get("preferred_min_salary", "")
    target_loc = (
        st.session_state.get("target_location")
        or profile.get("target_location")
        or profile.get("location")
        or ""
    )

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

        src_lower = job.get("source", "").lower()
        if source_type_filter == "Direct ATS Only" and not (
            job.get("is_direct_ats")
            or any(ats in src_lower for ats in ["ashby", "greenhouse", "lever", "smartrecruiters"])
        ):
            continue
        elif source_type_filter == "Portuguese Portals Only" and not any(
            pt in src_lower for pt in ["itjobs", "net-empregos", "netempregos", "landing"]
        ):
            continue
        elif source_type_filter == "Remote Hubs Only" and not any(
            rh in src_lower for rh in ["remoteok", "remotive", "weworkremotely", "jobicy"]
        ):
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
        elif salary_filter == "Within Market Standard & Above" and salary_eval["rank"] not in [
            "Within Market Standard",
            "Above Market",
        ]:
            continue

        filtered_jobs.append(job)

    st.markdown(f"**Showing {len(filtered_jobs)} of {len(jobs_source)} matched positions**")

    # Render Job Cards
    for job in filtered_jobs:
        render_job_card(
            job=job,
            profile=profile,
            cand_min_pref=cand_min_pref,
            target_loc=target_loc,
        )

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
