"""
Screen 3: Searching & Scraping Loading Screen.
Executes the live Job Scraper & Aggregator Agent across LinkedIn, Arbeitnow, Jobicy, RemoteOK, and Remotive,
performs semantic matching & ranking, and streams live agent telemetry.
"""

from datetime import datetime
import time
import streamlit as st
from src.state import SCREEN_DASHBOARD, go_to_screen
from src.mock_data import SAMPLE_PARSED_PROFILE
from src.agents.job_scraper_agent import search_live_jobs_pipeline


def render_screen3() -> None:
    raw_profile = st.session_state.get("parsed_profile") or SAMPLE_PARSED_PROFILE
    profile = dict(raw_profile)
    if st.session_state.get("target_location"):
        profile["location"] = st.session_state["target_location"]
    if st.session_state.get("remote_pref"):
        profile["work_mode"] = st.session_state["remote_pref"]
    if st.session_state.get("target_role"):
        profile["target_role"] = st.session_state["target_role"]
        profile["headline"] = st.session_state["target_role"]
    if st.session_state.get("primary_skills"):
        profile["core_skills"] = st.session_state["primary_skills"]
    if st.session_state.get("target_companies"):
        profile["target_companies"] = st.session_state["target_companies"]
    if st.session_state.get("negative_keywords"):
        profile["negative_keywords"] = st.session_state["negative_keywords"]
    if st.session_state.get("selected_recommended_roles"):
        profile["selected_roles"] = st.session_state["selected_recommended_roles"]
        profile["target_roles"] = st.session_state["selected_recommended_roles"]
    if st.session_state.get("apify_api_token"):
        profile["apify_api_token"] = st.session_state["apify_api_token"]
    if st.session_state.get("gemini_api_key"):
        profile["gemini_api_key"] = st.session_state["gemini_api_key"]


    st.markdown("### ⚡ Screen 3: Concurrent Async Search & Multi-Source Scraping")
    st.markdown(
        "Hyrd's Multi-Agent pipeline is dispatching autonomous crawlers across 17 major sources: "
        "**LinkedIn, Ashby, Greenhouse, Lever, SmartRecruiters, JobSpy (Indeed), We Work Remotely, TelecomCareers, ZipRecruiter, ITJobs.pt, Net-Empregos, Landing.jobs, Apify, Arbeitnow, Jobicy, RemoteOK, and Remotive**. "
        "Each opportunity is semantically matched against your resume, evaluated for compensation, and ranked by fit."
    )

    # Status Containers
    status_placeholder = st.empty()
    progress_bar = st.progress(0)
    log_placeholder = st.empty()

    # Check if this screen was already completed in this session
    already_done = st.session_state.get("scrape_completed", False) and bool(st.session_state.get("discovered_jobs"))

    if not already_done:
        accumulated_logs = []

        def on_agent_progress(pct: int, agent_name: str, message: str) -> None:
            progress_bar.progress(pct)
            timestamp = datetime.now().strftime("%H:%M:%S")
            entry = {"time": timestamp, "agent": agent_name, "message": message}
            accumulated_logs.append(entry)

            # Update status badge
            status_placeholder.markdown(
                f"""
                <div style="
                    background: #f8fafc;
                    border: 1px solid #cbd5e1;
                    border-radius: 8px;
                    padding: 0.85rem 1.25rem;
                    margin-bottom: 1rem;
                    display: flex;
                    align-items: center;
                    gap: 0.75rem;
                ">
                    <span style="font-size: 1.3rem;">🔄</span>
                    <div>
                        <div style="font-size: 0.85rem; font-weight: 600; color: #0284c7; text-transform: uppercase;">
                            {agent_name} Active ({pct}% Completed)
                        </div>
                        <div style="font-size: 0.95rem; color: #1e293b;">
                            {message}
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Render log history
            log_html = "".join(
                [
                    f"<div style='font-family: monospace; font-size: 0.85rem; padding: 0.35rem 0; border-bottom: 1px solid #1e293b; color: #e2e8f0;'>"
                    f"<span style='color: #64748b;'>[{l['time']}]</span> "
                    f"<strong style='color: #38bdf8;'>[{l['agent']}]</strong> {l['message']}</div>"
                    for l in accumulated_logs
                ]
            )
            log_placeholder.markdown(
                f"""
                <div style="
                    background: #0f172a;
                    color: #e2e8f0;
                    padding: 1rem;
                    border-radius: 8px;
                    max-height: 250px;
                    overflow-y: auto;
                    margin-bottom: 1.5rem;
                    border: 1px solid #334155;
                ">
                    <div style="font-size: 0.75rem; font-weight: 700; color: #94a3b8; text-transform: uppercase; margin-bottom: 0.5rem; letter-spacing: 0.05em;">
                        Agent Execution Stream • Live Feed
                    </div>
                    {log_html}
                </div>
                """,
                unsafe_allow_html=True,
            )

        # Execute Live Scraper Pipeline
        jobs, total_scraped = search_live_jobs_pipeline(profile, on_progress=on_agent_progress)

        st.session_state.discovered_jobs = jobs
        st.session_state.total_scraped_count = total_scraped
        st.session_state.live_scrape_logs = accumulated_logs
        st.session_state.scrape_completed = True
        progress_bar.progress(100)

        try:
            from src.utils.user_manager import flush_session_to_user_workspace
            flush_session_to_user_workspace()
        except Exception:
            pass

    # Finished state display
    discovered_jobs = st.session_state.get("discovered_jobs", [])
    total_scraped = st.session_state.get("total_scraped_count", len(discovered_jobs))
    logs = st.session_state.get("live_scrape_logs", [])

    status_placeholder.markdown(
        f"""
        <div style="
            background: #f0fdf4;
            border: 1px solid #86efac;
            border-radius: 8px;
            padding: 1rem 1.25rem;
            margin-bottom: 1rem;
            display: flex;
            align-items: center;
            gap: 0.75rem;
        ">
            <span style="font-size: 1.5rem;">🎉</span>
            <div>
                <div style="font-size: 0.9rem; font-weight: 700; color: #166534; text-transform: uppercase;">
                    Pipeline Execution Complete
                </div>
                <div style="font-size: 0.95rem; color: #14532d;">
                    Scraped <strong>{total_scraped}</strong> live opportunities concurrently across 17 job networks and ATS systems.
                    Identified <strong>{len(discovered_jobs)}</strong> high-fit matching roles for your background.
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if already_done and logs:
        progress_bar.progress(100)
        log_html = "".join(
            [
                f"<div style='font-family: monospace; font-size: 0.85rem; padding: 0.35rem 0; border-bottom: 1px solid #1e293b; color: #e2e8f0;'>"
                f"<span style='color: #64748b;'>[{l['time']}]</span> "
                f"<strong style='color: #38bdf8;'>[{l['agent']}]</strong> {l['message']}</div>"
                for l in logs
            ]
        )
        log_placeholder.markdown(
            f"""
            <div style="
                background: #0f172a;
                color: #e2e8f0;
                padding: 1rem;
                border-radius: 8px;
                max-height: 250px;
                overflow-y: auto;
                margin-bottom: 1.5rem;
                border: 1px solid #334155;
            ">
                <div style="font-size: 0.75rem; font-weight: 700; color: #94a3b8; text-transform: uppercase; margin-bottom: 0.5rem; letter-spacing: 0.05em;">
                    Agent Execution Stream • Discovered {len(discovered_jobs)} Roles
                </div>
                {log_html}
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("---")

    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        if st.button("🔄 Re-crawl & Search Again", use_container_width=True):
            st.session_state.scrape_completed = False
            st.session_state.discovered_jobs = []
            st.session_state.live_scrape_logs = []
            st.rerun()

    with col3:
        if st.button("📊 View Discovered Job Dashboard →", type="primary", use_container_width=True):
            go_to_screen(SCREEN_DASHBOARD)
