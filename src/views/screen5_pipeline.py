"""
Screen 5: Application Pipeline & Kanban Tracker.
Interactive visual pipeline to track job applications across stages:
Saved -> Applied -> Interviewing -> Offer Received -> Archived.
"""

import json
import streamlit as st
from src.state import SCREEN_DASHBOARD, go_to_screen
from src.mock_data import MOCK_JOB_RESULTS, SAMPLE_PARSED_PROFILE
from src.components.application_dialogs import (
    show_cv_dialog,
    show_cover_letter_dialog,
    show_interview_prep_dialog,
    show_outreach_dialog,
    show_company_dossier_dialog,
)
from src.utils.pipeline_manager import (
    STAGE_SAVED,
    STAGE_APPLIED,
    STAGE_INTERVIEWING,
    STAGE_OFFER,
    STAGE_ARCHIVED,
    STAGE_ORDER,
    STAGE_CONFIG,
    get_pipeline,
    add_or_update_pipeline,
    set_job_stage,
    remove_from_pipeline,
    update_job_notes,
    initialize_sample_pipeline_if_empty,
)


@st.dialog("➕ Add Custom Job to Pipeline", width="medium")
def show_add_custom_job_dialog() -> None:
    """Modal form allowing candidates to manually track applications from external sources."""
    st.markdown("#### ➕ Log an External or Referral Application")
    st.caption("Manually track positions applied to via LinkedIn InMail, direct company career pages, or employee referrals.")

    with st.form("add_custom_job_form"):
        col1, col2 = st.columns(2)
        with col1:
            title = st.text_input("Job Title *", placeholder="e.g. Staff AI Systems Architect")
            company = st.text_input("Company Name *", placeholder="e.g. OpenAI, Anthropic, Databricks...")
            location = st.text_input("Location / Work Mode", placeholder="e.g. Remote, San Francisco, London...")
        with col2:
            salary = st.text_input("Salary / Compensation Range", placeholder="e.g. $180,000 - $230,000")
            stage = st.selectbox(
                "Initial Pipeline Stage",
                options=[STAGE_SAVED, STAGE_APPLIED, STAGE_INTERVIEWING, STAGE_OFFER],
                format_func=lambda s: f"{STAGE_CONFIG[s]['icon']} {STAGE_CONFIG[s]['label']}",
                index=1,
            )
            apply_url = st.text_input("Job URL / Career Page", placeholder="https://company.com/careers/...")

        notes = st.text_area("Initial Notes / Recruiter Contact", placeholder="Referred by John on LinkedIn. Initial recruiter screening next Tuesday.")
        interview_date = st.text_input("Next Interview Date (Optional)", placeholder="e.g. Thursday Oct 8, 2:00 PM EST")

        submitted = st.form_submit_button("💾 Add to Pipeline", type="primary", use_container_width=True)
        if submitted:
            if not title.strip() or not company.strip():
                st.error("Please provide both Job Title and Company Name.")
                return

            custom_id = f"custom-{company.replace(' ', '_').lower()}-{title[:10].replace(' ', '_').lower()}"
            job_dict = {
                "id": custom_id,
                "title": title.strip(),
                "company": company.strip(),
                "location": location.strip() or "Remote",
                "salary": salary.strip() or "Competitive",
                "job_type": "Full-time",
                "fit_score": 90,
                "badge_color": "#2563eb",
                "apply_url": apply_url.strip() or "https://www.google.com/search?q=jobs",
                "description": f"Role: {title} at {company}. Logged manually via Application Tracker.",
                "source": "Custom / Referral",
            }

            add_or_update_pipeline(
                job_dict,
                stage=stage,
                notes=notes.strip(),
                interview_date=interview_date.strip(),
            )
            st.toast(f"Added {title} at {company} to {STAGE_CONFIG[stage]['label']}!")
            st.rerun()


@st.dialog("📝 Application Notes & Interview Details", width="medium")
def show_notes_dialog(job: dict) -> None:
    """Dialog to inspect and edit interview schedules, recruiter details, and notes."""
    job_id = job["id"]
    pipeline = get_pipeline()
    job_data = pipeline.get(job_id, job)

    st.markdown(f"#### 📝 Notes & Schedule: {job_data['title']}")
    st.markdown(f"**Company**: {job_data['company']} &nbsp;•&nbsp; **Current Stage**: {STAGE_CONFIG[job_data['stage']]['icon']} {STAGE_CONFIG[job_data['stage']]['label']}")

    notes_val = st.text_area(
        "Application & Interview Notes",
        value=job_data.get("notes", ""),
        height=140,
        placeholder="Key notes from discussions, interview prep reminders, technical questions asked...",
        key=f"modal_notes_{job_id}",
    )

    col1, col2 = st.columns(2)
    with col1:
        int_date_val = st.text_input(
            "Next Interview Date & Time",
            value=job_data.get("interview_date", ""),
            placeholder="e.g. Wednesday Oct 7, 3:30 PM",
            key=f"modal_int_{job_id}",
        )
    with col2:
        recruiter_val = st.text_input(
            "Recruiter / Hiring Contact",
            value=job_data.get("recruiter_contact", ""),
            placeholder="e.g. Sarah Connor (recruiter@company.com)",
            key=f"modal_rec_{job_id}",
        )

    sal_offered_val = st.text_input(
        "Offered Compensation (If applicable)",
        value=job_data.get("salary_offered", ""),
        placeholder="e.g. $210,000 base + 15% bonus + equity",
        key=f"modal_sal_{job_id}",
    )

    if st.button("💾 Save Application Details", type="primary", use_container_width=True, key=f"save_meta_{job_id}"):
        update_job_notes(
            job_id,
            notes=notes_val.strip(),
            interview_date=int_date_val.strip(),
            recruiter_contact=recruiter_val.strip(),
            salary_offered=sal_offered_val.strip(),
        )
        st.toast("Application details updated!")
        st.rerun()


def render_screen5() -> None:
    """Render the Kanban Application Pipeline dashboard."""
    profile = st.session_state.get("parsed_profile") or SAMPLE_PARSED_PROFILE
    jobs_source = st.session_state.get("discovered_jobs") or MOCK_JOB_RESULTS

    # Seed pipeline if accessed for first time
    initialize_sample_pipeline_if_empty(jobs_source)
    pipeline = get_pipeline()

    # Synchronize any jobs that were bookmarked on Screen 4
    for saved_id in st.session_state.get("saved_jobs", set()):
        if saved_id not in pipeline:
            matched_j = next((j for j in jobs_source if j["id"] == saved_id), None)
            if matched_j:
                add_or_update_pipeline(matched_j, stage=STAGE_SAVED)

    for applied_id in st.session_state.get("applied_jobs", set()):
        if applied_id in pipeline:
            if pipeline[applied_id]["stage"] == STAGE_SAVED:
                pipeline[applied_id]["stage"] = STAGE_APPLIED
        else:
            matched_j = next((j for j in jobs_source if j["id"] == applied_id), None)
            if matched_j:
                add_or_update_pipeline(matched_j, stage=STAGE_APPLIED)

    # 1. Header Toolbar
    head_col1, head_col2 = st.columns([3, 2])
    with head_col1:
        st.markdown("### 📋 Screen 5: Application Pipeline & Kanban Tracker")
        st.markdown(
            "Manage your active job hunting funnel, interview schedules, and tailored CV assets across each hiring stage."
        )
    with head_col2:
        st.markdown("<div style='text-align: right; margin-top: 0.5rem;'>", unsafe_allow_html=True)
        tb1, tb2 = st.columns([1, 1])
        with tb1:
            if st.button("➕ Add Custom Job", use_container_width=True, help="Manually track a job from LinkedIn, referral or company website"):
                show_add_custom_job_dialog()
        with tb2:
            if st.button("📊 Back to Job Search", type="primary", use_container_width=True, help="Return to Screen 4 Job Dashboard"):
                go_to_screen(SCREEN_DASHBOARD)
        st.markdown("</div>", unsafe_allow_html=True)

    # 2. Stage Breakdown KPI Row
    by_stage: Dict[str, list] = {s: [] for s in STAGE_ORDER}
    for item in pipeline.values():
        stg = item.get("stage", STAGE_SAVED)
        if stg in by_stage:
            by_stage[stg].append(item)
        else:
            by_stage[STAGE_SAVED].append(item)

    k1, k2, k3, k4, k5 = st.columns(5)
    with k1:
        st.metric(label="📌 Saved to Review", value=f"{len(by_stage[STAGE_SAVED])}", delta="Pipeline Intake")
    with k2:
        st.metric(label="📤 Applications Sent", value=f"{len(by_stage[STAGE_APPLIED])}", delta="Under Review")
    with k3:
        st.metric(label="💬 In Interview", value=f"{len(by_stage[STAGE_INTERVIEWING])}", delta="Active Rounds")
    with k4:
        st.metric(label="🏆 Offers Received", value=f"{len(by_stage[STAGE_OFFER])}", delta="Evaluating")
    with k5:
        total_active = len(pipeline) - len(by_stage[STAGE_ARCHIVED])
        st.metric(label="⚡ Total Active Funnel", value=f"{total_active} Roles", delta=f"{len(by_stage[STAGE_ARCHIVED])} archived")

    st.markdown("<br>", unsafe_allow_html=True)

    # 3. Four-Column Interactive Kanban Board
    kanban_stages = [STAGE_SAVED, STAGE_APPLIED, STAGE_INTERVIEWING, STAGE_OFFER]
    cols = st.columns(4, gap="medium")

    for idx, stage_key in enumerate(kanban_stages):
        cfg = STAGE_CONFIG[stage_key]
        stage_jobs = by_stage[stage_key]

        with cols[idx]:
            # Stage Column Header
            st.markdown(
                f"""
                <div style="
                    background: {cfg['bg']};
                    border-top: 4px solid {cfg['color']};
                    border-left: 1px solid {cfg['border']};
                    border-right: 1px solid {cfg['border']};
                    border-bottom: 1px solid {cfg['border']};
                    border-radius: 8px;
                    padding: 0.65rem 0.85rem;
                    margin-bottom: 0.85rem;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                ">
                    <span style="font-weight: 700; font-size: 0.95rem; color: #1e293b;">
                        {cfg['icon']} {cfg['label']}
                    </span>
                    <span style="
                        background: {cfg['badge_bg']};
                        color: {cfg['color']};
                        font-weight: 700;
                        font-size: 0.82rem;
                        padding: 0.15rem 0.55rem;
                        border-radius: 9999px;
                        border: 1px solid {cfg['border']};
                    ">{len(stage_jobs)}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

            if not stage_jobs:
                st.markdown(
                    f"<div style='border: 1.5px dashed #cbd5e1; border-radius: 8px; padding: 1.5rem 0.5rem; text-align: center; color: #94a3b8; font-size: 0.82rem;'>"
                    f"No roles in {cfg['label'].lower()} yet."
                    f"</div>",
                    unsafe_allow_html=True,
                )
            else:
                for job in stage_jobs:
                    job_id = job["id"]
                    clean_salary = str(job.get("salary", "Competitive")).replace("$", r"\$")

                    # Bordered Kanban Card
                    with st.container(border=True):
                        # Card Header: Title + Match Badge
                        st.markdown(
                            f"<div style='display: flex; justify-content: space-between; align-items: flex-start; gap: 0.4rem; margin-bottom: 0.2rem;'>"
                            f"<strong style='font-size: 0.92rem; color: #0f172a; line-height: 1.3;'>{job['title']}</strong>"
                            f"<span style='background: {job.get('badge_color', '#2563eb')}; color: #ffffff; padding: 0.12rem 0.45rem; border-radius: 9999px; font-size: 0.72rem; font-weight: 700; flex-shrink: 0;'>"
                            f"{job.get('fit_score', 85)}%</span>"
                            f"</div>",
                            unsafe_allow_html=True,
                        )

                        # Company, Location, Salary
                        st.markdown(
                            f"<div style='font-size: 0.8rem; color: #2563eb; font-weight: 600; margin-bottom: 0.2rem;'>"
                            f"{job['company']} &nbsp;•&nbsp; <span style='color: #64748b;'>{job.get('location', 'Remote')}</span>"
                            f"</div>",
                            unsafe_allow_html=True,
                        )
                        st.markdown(
                            f"<div style='font-size: 0.78rem; color: #475569; margin-bottom: 0.5rem;'>"
                            f"💰 {clean_salary}"
                            f"</div>",
                            unsafe_allow_html=True,
                        )

                        # Interview Date Badge if set
                        if job.get("interview_date"):
                            st.markdown(
                                f"<div style='background: #fffbeb; border: 1px solid #fde68a; border-radius: 6px; padding: 0.25rem 0.5rem; font-size: 0.76rem; color: #b45309; font-weight: 600; margin-bottom: 0.45rem;'>"
                                f"🗓️ {job['interview_date']}"
                                f"</div>",
                                unsafe_allow_html=True,
                            )

                        # Stage Move Selector
                        current_stage_idx = STAGE_ORDER.index(stage_key) if stage_key in STAGE_ORDER else 0
                        new_stage = st.selectbox(
                            "Move Stage",
                            options=STAGE_ORDER,
                            index=current_stage_idx,
                            format_func=lambda s: f"{STAGE_CONFIG[s]['icon']} {STAGE_CONFIG[s]['label']}",
                            key=f"stage_select_{job_id}",
                            label_visibility="collapsed",
                        )
                        if new_stage != stage_key:
                            set_job_stage(job_id, new_stage)
                            st.toast(f"Moved {job['title']} to {STAGE_CONFIG[new_stage]['label']}!")
                            st.rerun()

                        # Compact Action Bar
                        act_col1, act_col2 = st.columns([1, 1])
                        with act_col1:
                            if st.button("📄 Tailored CV (ATS)", key=f"k_cv_{job_id}", use_container_width=True, help="Preview, audit score, or download ATS-optimized CV for this company"):
                                show_cv_dialog(job, profile)
                        with act_col2:
                            if st.button("✉️ Cover Letter", key=f"k_cl_{job_id}", use_container_width=True, help="Preview or download tailored cover letter for this company"):
                                show_cover_letter_dialog(job, profile)

                        # Row 2: Interview Prep Pack & Outreach Drafter
                        act2_col1, act2_col2 = st.columns([1, 1])
                        with act2_col1:
                            if st.button("🎤 Prep Pack", key=f"k_prep_{job_id}", use_container_width=True, help="Role-specific interview preparation pack (Q&A, STAR stories, cheat sheet)"):
                                show_interview_prep_dialog(job, profile)
                        with act2_col2:
                            if st.button("📬 Outreach", key=f"k_out_{job_id}", use_container_width=True, help="Multi-channel cold outreach & LinkedIn message drafter"):
                                show_outreach_dialog(job, profile)

                        # Notes, Dossier & Link
                        bot_col1, bot_col2, bot_col3 = st.columns([1, 1, 0.9])
                        with bot_col1:
                            notes_label = "📝 Notes" if not job.get("notes") else "📝 Notes (1+)"
                            if st.button(notes_label, key=f"btn_notes_{job_id}", use_container_width=True):
                                show_notes_dialog(job)
                        with bot_col2:
                            doss_ready = job.get("company", "").strip().lower() in st.session_state.get("company_dossiers", {})
                            doss_lbl = "🏢 Dossier ✓" if doss_ready else "🏢 Dossier"
                            if st.button(doss_lbl, key=f"btn_doss_pipe_{job_id}", use_container_width=True, help="Deep-dive employer intelligence & interview talking points"):
                                show_company_dossier_dialog(job, profile)
                        with bot_col3:
                            st.link_button(
                                "Apply ↗",
                                url=job.get("apply_url", "https://www.google.com/search?q=jobs"),
                                use_container_width=True,
                            )

    st.markdown("---")

    # 4. Collapsible Archived / Inactive Applications
    archived_jobs = by_stage[STAGE_ARCHIVED]
    with st.expander(f"📁 Archived & Inactive Applications ({len(archived_jobs)})", expanded=False):
        if not archived_jobs:
            st.info("No applications archived. Inactive or closed applications can be moved here to keep your active board clean.")
        else:
            for job in archived_jobs:
                job_id = job["id"]
                a_col1, a_col2, a_col3, a_col4 = st.columns([2.5, 1.5, 1.5, 1])
                with a_col1:
                    st.markdown(f"**{job['title']}** at {job['company']}")
                    st.caption(f"📍 {job.get('location', 'Remote')} • 💰 {job.get('salary', 'Competitive')}")
                with a_col2:
                    st.markdown(f"Status: *Archived*")
                    if job.get("notes"):
                        st.caption(f"Notes: {job['notes'][:50]}...")
                with a_col3:
                    if st.button("↩️ Restore to Applied", key=f"restore_{job_id}", use_container_width=True):
                        set_job_stage(job_id, STAGE_APPLIED)
                        st.toast(f"Restored {job['title']} to Applied!")
                        st.rerun()
                with a_col4:
                    if st.button("🗑️ Delete", key=f"del_arch_{job_id}", use_container_width=True):
                        remove_from_pipeline(job_id)
                        st.toast(f"Deleted {job['title']}")
                        st.rerun()

    # 5. Bottom Navigation Bar
    b_col1, b_col2, b_col3 = st.columns([1.5, 1, 1.5])
    with b_col1:
        if st.button("← Back to Job Search Dashboard", use_container_width=True):
            go_to_screen(SCREEN_DASHBOARD)
    with b_col3:
        st.download_button(
            label="📥 Export Pipeline (JSON)",
            data=json.dumps(pipeline, indent=2),
            file_name="hyrd_application_pipeline.json",
            mime="application/json",
            use_container_width=True,
        )
