"""
Autonomous Job Scout & Morning Career Digest UI Modal.
Provides:
- Scout Automation Controller (Active toggle, schedule frequency, ATS monitoring)
- Real-time Scout Execution trigger
- Interactive Morning Career Intelligence Digest
- 1-Click Pipeline Queuing and Email Newsletter Export
"""

import json
import streamlit as st
from datetime import datetime
from src.agents.job_scout_agent import run_job_scout_cycle
from src.utils.pipeline_manager import STAGE_SAVED, add_or_update_pipeline
from src.utils.user_manager import flush_session_to_user_workspace
from src.components.application_dialogs import show_cv_dialog


@st.dialog("🔭 Autonomous Job Scout & Morning Career Digest", width="large")
def show_job_scout_dialog(profile: dict) -> None:
    """Render the Job Scout control center and Morning Digest reader."""
    if "job_scout_config" not in st.session_state:
        st.session_state.job_scout_config = {}
    if "job_scout_digests" not in st.session_state:
        st.session_state.job_scout_digests = []

    scout_cfg = st.session_state.job_scout_config
    is_active = scout_cfg.get("is_active", True)
    frequency = scout_cfg.get("frequency", "Daily (Morning 8:00 AM)")
    target_comp_str = scout_cfg.get("target_companies") or profile.get("target_companies", "Linear, OpenAI, Stripe, Figma")
    last_run = scout_cfg.get("last_run_timestamp", "Never")

    # Top Control Banner
    status_bg = "#ecfdf5" if is_active else "#f8fafc"
    status_border = "#6ee7b7" if is_active else "#cbd5e1"
    status_text = "#047857" if is_active else "#64748b"
    status_label = "🟢 SCOUT AGENT ACTIVE" if is_active else "⏸️ SCOUT AGENT PAUSED"

    st.markdown(
        f"""<div style='background: {status_bg}; border: 1px solid {status_border}; border-radius: 8px; padding: 0.85rem 1.1rem; margin-bottom: 1rem;'>
            <div style='display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;'>
                <div>
                    <span style='font-size: 0.95rem; font-weight: 700; color: {status_text};'>{status_label}</span>
                    <span style='color: #475569; font-size: 0.82rem; margin-left: 10px;'>Cadence: <strong>{frequency}</strong></span>
                </div>
                <div style='font-size: 0.82rem; color: #64748b;'>
                    Last Scout Cycle: <strong>{last_run}</strong>
                </div>
            </div>
            <div style='font-size: 0.84rem; color: #334155; margin-top: 6px;'>
                🛡️ <strong>Autonomous ATS Monitoring:</strong> Actively scans Ashby, Greenhouse, Lever, Workday, Remotive & JobSpy for <strong>{profile.get('target_role') or 'your target roles'}</strong>.
            </div>
        </div>""",
        unsafe_allow_html=True,
    )

    # Action Toolbar
    act_col1, act_col2, act_col3 = st.columns([1.4, 1.2, 1])
    with act_col1:
        if st.button("⚡ Run Scout Agent Now (Manual Trigger)", type="primary", use_container_width=True):
            api_key = st.session_state.get("gemini_api_key")
            pref_model = st.session_state.get("gemini_model")
            
            existing_ids = {j.get("id") for j in st.session_state.get("discovered_jobs", [])}
            
            with st.spinner("🤖 Hyrd Scout Agent scanning 17 job channels, cross-referencing ATS boards & synthesizing Morning Digest..."):
                result = run_job_scout_cycle(
                    profile=profile,
                    existing_job_ids=existing_ids,
                    api_key=api_key,
                    preferred_model=pref_model,
                )
                
                # Prepend new digest
                new_digest = result["digest"]
                st.session_state.job_scout_digests.insert(0, new_digest)
                
                # Merge new jobs into discovered jobs
                current_jobs = st.session_state.get("discovered_jobs", [])
                merged_ids = {j.get("id") for j in current_jobs}
                for nj in result.get("all_matched_jobs", []):
                    if nj.get("id") not in merged_ids:
                        current_jobs.append(nj)
                        merged_ids.add(nj.get("id"))
                st.session_state.discovered_jobs = current_jobs
                st.session_state.total_scraped_count = len(current_jobs)
                
                # Update scout config
                scout_cfg["last_run_timestamp"] = new_digest["timestamp"]
                st.session_state.job_scout_config = scout_cfg
                
                flush_session_to_user_workspace()
                st.toast(f"✨ Scout completed! {new_digest['stats']['new_jobs_found']} opportunities analyzed.")
                st.rerun()

    with act_col2:
        new_active = st.toggle("Autonomous Scout Active", value=is_active, key="toggle_scout_active")
        if new_active != is_active:
            scout_cfg["is_active"] = new_active
            st.session_state.job_scout_config = scout_cfg
            flush_session_to_user_workspace()
            st.rerun()

    with act_col3:
        with st.popover("⚙️ Scout Settings"):
            st.markdown("##### Scout Configuration")
            new_freq = st.selectbox(
                "Run Frequency",
                ["Every 6 Hours", "Daily (Morning 8:00 AM)", "Daily (Evening 6:00 PM)", "On Demand Only"],
                index=["Every 6 Hours", "Daily (Morning 8:00 AM)", "Daily (Evening 6:00 PM)", "On Demand Only"].index(frequency) if frequency in ["Every 6 Hours", "Daily (Morning 8:00 AM)", "Daily (Evening 6:00 PM)", "On Demand Only"] else 1,
            )
            new_targets = st.text_input("Priority ATS Employers", value=target_comp_str, placeholder="e.g. Linear, OpenAI, Figma")
            if st.button("Save Settings", key="save_scout_settings_btn"):
                scout_cfg["frequency"] = new_freq
                scout_cfg["target_companies"] = new_targets
                st.session_state.job_scout_config = scout_cfg
                flush_session_to_user_workspace()
                st.toast("Scout preferences updated!")
                st.rerun()

    # Digest Tabs
    tab_digest, tab_email, tab_history = st.tabs([
        "📰 Morning Career Digest",
        "📧 Email Alert Preview",
        "📜 Past Digest Archive",
    ])

    latest_digest = st.session_state.job_scout_digests[0] if st.session_state.job_scout_digests else None

    with tab_digest:
        if not latest_digest:
            st.info("No scout digest generated yet. Click **⚡ Run Scout Agent Now** above to launch the autonomous scout cycle!")
        else:
            st.markdown(f"### {latest_digest.get('headline')}")
            st.caption(f"🗓️ Generated on {latest_digest.get('timestamp')} for **{profile.get('full_name', 'Candidate')}**")

            # Metrics
            st_data = latest_digest.get("stats", {})
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Fresh Matches", f"{st_data.get('new_jobs_found', 0)}")
            m2.metric("Screened Postings", f"{st_data.get('total_screened', 0)}")
            m3.metric("Dream ATS Targets", f"{st_data.get('target_company_matches', 0)}")
            m4.metric("Top Fit Score", f"{st_data.get('top_match_score', 95)}%")

            st.markdown(
                f"""<div style='background: #f8fafc; border-left: 4px solid #3b82f6; padding: 0.9rem 1.1rem; border-radius: 4px; margin: 1rem 0;'>
                    <div style='font-weight: 700; color: #1e3a8a; margin-bottom: 4px;'>📋 Executive Summary:</div>
                    <div style='color: #334155; font-size: 0.92rem; line-height: 1.5;'>{latest_digest.get('executive_summary')}</div>
                </div>""",
                unsafe_allow_html=True,
            )

            st.markdown("#### 💡 Hiring Tempo & Market Signals")
            for sig in latest_digest.get("market_signals", []):
                st.markdown(
                    f"<div style='background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 6px; padding: 8px 12px; margin-bottom: 6px; color: #166534; font-size: 0.88rem;'>"
                    f"⚡ {sig}"
                    f"</div>",
                    unsafe_allow_html=True,
                )

            st.markdown("---")
            st.markdown("#### 🎯 Curated Priority Openings for Today")
            
            for j in latest_digest.get("featured_jobs", []):
                job_id = j.get("id")
                is_target = j.get("is_target_company")
                badge_str = "⭐ Dream Employer" if is_target else "🔥 High Match"
                badge_bg = "#ecfdf5" if is_target else "#eff6ff"
                badge_color = "#059669" if is_target else "#2563eb"

                with st.container(border=True):
                    h_col1, h_col2 = st.columns([3, 1])
                    with h_col1:
                        st.markdown(f"**{j.get('title')}** at **{j.get('company')}**")
                        st.caption(f"📍 {j.get('location', 'Remote')} • 💰 {j.get('salary', 'Competitive')} • Source: {j.get('source', 'ATS')}")
                    with h_col2:
                        st.markdown(
                            f"<div style='text-align: right;'><span style='background: {badge_bg}; color: {badge_color}; border: 1px solid {badge_color}40; padding: 3px 8px; border-radius: 6px; font-weight: 700; font-size: 0.82rem;'>{j.get('fit_score')}% • {badge_str}</span></div>",
                            unsafe_allow_html=True,
                        )

                    btn_c1, btn_c2, btn_c3 = st.columns([1.2, 1.2, 1])
                    with btn_c1:
                        if st.button("📌 Auto-Add to Kanban", key=f"digest_save_{job_id}_{latest_digest['id']}", use_container_width=True):
                            add_or_update_pipeline(j, stage=STAGE_SAVED)
                            flush_session_to_user_workspace()
                            st.toast(f"Saved {j.get('title')} to Kanban!")
                    with btn_c2:
                        if st.button("📄 Tailor ATS CV", key=f"digest_cv_{job_id}_{latest_digest['id']}", use_container_width=True):
                            show_cv_dialog(j, profile)
                    with btn_c3:
                        st.link_button("Apply ↗", url=j.get("apply_url", "#"), use_container_width=True)

            st.markdown(
                f"<div style='margin-top: 1rem; padding: 0.75rem 1rem; background: #fffbeb; border: 1px solid #fde68a; border-radius: 6px; color: #92400e; font-size: 0.88rem;'>"
                f"🧭 <strong>Recommended Action:</strong> {latest_digest.get('action_plan')}"
                f"</div>",
                unsafe_allow_html=True,
            )

    with tab_email:
        if not latest_digest:
            st.info("Generate a scout digest first to preview the email newsletter.")
        else:
            st.markdown("#### 📧 Candidate Email Newsletter Format")
            st.caption("Ready-to-send executive morning newsletter digest formatted in Markdown.")

            st.text_area(
                "Email Markdown Content",
                value=latest_digest.get("email_preview", ""),
                height=320,
                key=f"email_preview_txt_{latest_digest['id']}",
            )

            st.download_button(
                label="📥 Download Email Digest (.md)",
                data=latest_digest.get("email_preview", ""),
                file_name=f"CareerDigest_{datetime.now().strftime('%Y%m%d')}.md",
                mime="text/markdown",
                use_container_width=True,
            )

    with tab_history:
        all_digests = st.session_state.job_scout_digests
        if len(all_digests) <= 1:
            st.info("Only the latest digest exists. As the scout runs periodically, previous digests will be cataloged here.")
        else:
            st.markdown(f"#### 📜 Past Digests Archive ({len(all_digests)} Total)")
            for old_d in all_digests[1:]:
                with st.expander(f"🗓️ {old_d.get('timestamp')} — {old_d.get('headline')}", expanded=False):
                    st.write(old_d.get("executive_summary"))
                    st.markdown(f"- **Matches:** {old_d.get('stats', {}).get('new_jobs_found')} | **Top Score:** {old_d.get('stats', {}).get('top_match_score')}%")
                    st.markdown(old_d.get("email_preview", ""))
