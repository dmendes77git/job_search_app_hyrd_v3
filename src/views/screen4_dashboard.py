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
        fcol1, fcol2, fcol3, fcol4, fcol5, fcol6 = st.columns(6)
        with fcol1:
            search_query = st.text_input(
                "Keyword / Company",
                placeholder="e.g. Python, Toast...",
            )
        with fcol2:
            min_score = st.slider("Min Fit Score", min_value=30, max_value=98, value=50, step=1)
        with fcol3:
            quadrant_filter = st.selectbox(
                "Strategic Quadrant",
                ["All Quadrants", "QI: Priority Fast-Track", "QII: Referral Outreach", "QIII: Stretch Role", "QIV: Low Viability"],
            )
        with fcol4:
            loc_filter = st.selectbox(
                "Work Mode Filter",
                ["All Work Modes", "Remote Only", "Hybrid Only", "On-site Only"],
            )
        with fcol5:
            salary_filter = st.selectbox(
                "Salary Rank Filter",
                ["All Salary Ranks", "Within Market Standard & Above", "Above Market Only"],
            )
        with fcol6:
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
        fit = job.get("profile_fit_score", job.get("fit_score", 0))
        if fit < min_score:
            continue
        if quadrant_filter != "All Quadrants":
            q_prefix = quadrant_filter.split(":")[0].strip()
            if job.get("strategic_quadrant") != q_prefix:
                continue
        if search_query:
            query_lower = search_query.lower()
            in_title = query_lower in (job.get("title") or "").lower()
            in_company = query_lower in (job.get("company") or job.get("company_name") or "").lower()
            in_skills = any(query_lower in str(s).lower() for s in job.get("matched_skills", []))
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

        # Evaluate proposed salary against candidate profile, preferences, and target location market benchmarks (with caching)
        salary_eval = job.get("salary_eval")
        if not salary_eval:
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

    # Filter state tracking to reset page to 1 when filters change
    current_filter_sig = (
        search_query,
        min_score,
        quadrant_filter,
        loc_filter,
        salary_filter,
        source_type_filter,
    )
    if st.session_state.get("_dashboard_filter_sig") != current_filter_sig:
        st.session_state._dashboard_filter_sig = current_filter_sig
        st.session_state.dashboard_page = 1

    total_matched = len(filtered_jobs)

    # Page size selector & status header
    p_hdr1, p_hdr2, p_hdr3, p_hdr4 = st.columns([2.2, 0.9, 0.9, 1.0], gap="small")

    with p_hdr4:
        page_size_options = [10, 15, 25, 50]
        curr_page_size = st.session_state.get("dashboard_page_size", 15)
        ps_idx = page_size_options.index(curr_page_size) if curr_page_size in page_size_options else 1
        page_size = st.selectbox("Per page", options=page_size_options, index=ps_idx, key="dash_page_size_select")
        st.session_state.dashboard_page_size = page_size

    total_pages = max(1, (total_matched + page_size - 1) // page_size)
    curr_page = max(1, min(st.session_state.get("dashboard_page", 1), total_pages))
    st.session_state.dashboard_page = curr_page

    start_idx = (curr_page - 1) * page_size
    end_idx = min(start_idx + page_size, total_matched)
    paged_jobs = filtered_jobs[start_idx:end_idx]

    with p_hdr1:
        if total_matched > 0:
            st.markdown(
                f"<div style='font-size: 0.95rem; font-weight: 600; color: #1e293b; padding-top: 0.4rem;'>"
                f"Showing {start_idx + 1}–{end_idx} of {total_matched} positions "
                f"<span style='color: #64748b; font-weight: 400;'>• Page {curr_page} of {total_pages}</span></div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"<div style='font-size: 0.95rem; font-weight: 600; color: #e11d48; padding-top: 0.4rem;'>"
                f"No positions matching current filter criteria ({total_matched}/{len(jobs_source)} matched).</div>",
                unsafe_allow_html=True,
            )

    with p_hdr2:
        if st.button("⬅️ Prev Page", key="dash_prev_top", disabled=(curr_page <= 1), use_container_width=True):
            st.session_state.dashboard_page = max(1, curr_page - 1)
            st.rerun()

    with p_hdr3:
        if st.button("Next Page ➡️", key="dash_next_top", disabled=(curr_page >= total_pages), use_container_width=True):
            st.session_state.dashboard_page = min(total_pages, curr_page + 1)
            st.rerun()

    st.markdown("<div style='height: 0.35rem;'></div>", unsafe_allow_html=True)

    # Render Job Cards for current page only
    for job in paged_jobs:
        render_job_card(
            job=job,
            profile=profile,
            cand_min_pref=cand_min_pref,
            target_loc=target_loc,
        )

    # Bottom Pagination Bar (if multiple pages exist)
    if total_pages > 1:
        st.markdown("<div style='height: 0.5rem;'></div>", unsafe_allow_html=True)
        bot_p1, bot_p2, bot_p3 = st.columns([2, 1, 1], gap="small")
        with bot_p1:
            st.markdown(
                f"<div style='font-size: 0.85rem; color: #64748b; padding-top: 0.5rem;'>"
                f"Page <strong>{curr_page}</strong> of <strong>{total_pages}</strong> ({total_matched} opportunities)</div>",
                unsafe_allow_html=True,
            )
        with bot_p2:
            if st.button("⬅️ Previous Page", key="dash_prev_bot", disabled=(curr_page <= 1), use_container_width=True):
                st.session_state.dashboard_page = max(1, curr_page - 1)
                st.rerun()
        with bot_p3:
            if st.button("Next Page ➡️", key="dash_next_bot", disabled=(curr_page >= total_pages), use_container_width=True):
                st.session_state.dashboard_page = min(total_pages, curr_page + 1)
                st.rerun()

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
            data=json.dumps(filtered_jobs, indent=2, default=str),
            file_name="hyrd_job_matches.json",
            mime="application/json",
            use_container_width=True,
        )
