"""
Screen 2: Profile Review Screen.
Displays structured candidate profile extracted by the Gemini Resume Parsing Agent.
"""

import textwrap
import streamlit as st
from src.state import SCREEN_INPUT, SCREEN_SEARCHING, go_to_screen
from src.mock_data import SAMPLE_PARSED_PROFILE


def render_screen2() -> None:
    """Render the structured profile review screen for candidate confirmation."""
    st.markdown("### 🔍 Screen 2: Profile Review & Synthesis")
    st.markdown(
        "Review the structured profile extracted by the **Gemini 3.8 Flash** agent. "
        "Verify your target parameters before releasing the autonomous search agents onto live job boards and ATS feeds."
    )

    # Show Agent Status Banner
    parser_status = st.session_state.get("parser_status", "")
    if parser_status:
        if parser_status.startswith("✓"):
            st.success(parser_status)
        elif parser_status.startswith("⚠️"):
            st.warning(parser_status)
        else:
            st.info(parser_status)

    # Fallback if accessed directly
    profile = st.session_state.get("parsed_profile") or SAMPLE_PARSED_PROFILE

    candidate_name = st.session_state.get("candidate_name") or profile.get("full_name", "Alex Mercer")
    target_role = st.session_state.get("target_role") or profile.get("headline", "Senior AI Engineer")
    target_location = st.session_state.get("target_location") or profile.get("location", "Remote")
    exp_level = st.session_state.get("experience_level") or profile.get("years_of_experience", "Senior")
    min_salary = st.session_state.get("min_salary") or profile.get("preferred_min_salary", "$160,000")
    email = profile.get("email", "")
    phone = profile.get("phone", "")

    # Main Profile Card
    with st.container(border=True):
        p_left, p_right = st.columns([3, 1])
        with p_left:
            st.subheader(candidate_name)
            st.markdown(
                f"<div style='font-size: 1.05rem; font-weight: 600; color: #2563eb; margin-top: -0.5rem;'>"
                f"{target_role}</div>",
                unsafe_allow_html=True,
            )
            contact_info = []
            if target_location:
                contact_info.append(f"📍 {target_location}")
            work_mode = st.session_state.get("remote_pref") or profile.get("work_mode", "Remote Only")
            if work_mode:
                contact_info.append(f"🏢 {work_mode}")
            if exp_level:
                contact_info.append(f"💼 {exp_level}")
            if min_salary:
                contact_info.append(f"💰 Min {min_salary}")
            if email:
                contact_info.append(f"✉️ {email}")
            if phone:
                contact_info.append(f"📞 {phone}")

            st.markdown(
                f"<div style='font-size: 0.88rem; color: #64748b; margin-top: 0.25rem;'>"
                f"{' &nbsp;•&nbsp; '.join(contact_info)}</div>",
                unsafe_allow_html=True,
            )
        with p_right:
            st.markdown(
                "<div style='text-align: right; margin-top: 0.5rem;'>"
                "<span style='background: #f0fdf4; border: 1px solid #bbf7d0; color: #166534; padding: 0.35rem 0.75rem; border-radius: 9999px; font-size: 0.82rem; font-weight: 600;'>"
                "✓ Profile Extracted</span></div>",
                unsafe_allow_html=True,
            )

        st.divider()
        st.markdown("**Executive Summary**")
        st.write(profile.get("summary", "Technical professional with deep engineering expertise."))

    col1, col2 = st.columns(2, gap="large")

    with col1:
        st.markdown("#### 🛠️ Core Competencies & Skills")
        skills = st.session_state.get("primary_skills") or profile.get("core_skills", [])
        if skills:
            skills_html = "".join(
                [
                    f"<span style='display: inline-block; background: #eff6ff; color: #1d4ed8; border: 1px solid #bfdbfe; "
                    f"padding: 0.25rem 0.65rem; border-radius: 6px; font-size: 0.85rem; font-weight: 500; margin: 0.2rem 0.3rem 0.2rem 0;'>"
                    f"{skill}</span>"
                    for skill in skills
                ]
            )
            st.markdown(f"<div style='margin-bottom: 1rem;'>{skills_html}</div>", unsafe_allow_html=True)
        else:
            st.info("No specific skills extracted.")

        st.markdown("#### 🎯 Target Job Queries")
        target_roles = st.session_state.get("target_job_queries") or profile.get("target_roles", [target_role])
        for role in target_roles:
            st.markdown(f"- **{role}**")

        target_companies = st.session_state.get("target_companies", "")
        negative_keywords = st.session_state.get("negative_keywords", "")
        if target_companies or negative_keywords:
            st.markdown("#### 🎯 Target Employers & Exclusions")
            if target_companies:
                comps = [c.strip() for c in target_companies.split(",") if c.strip()]
                comps_badges = "".join([
                    f"<span style='display: inline-block; background: #f0fdf4; color: #166534; border: 1px solid #bbf7d0; "
                    f"padding: 0.2rem 0.55rem; border-radius: 6px; font-size: 0.82rem; font-weight: 600; margin: 0.15rem 0.25rem 0.15rem 0;'>"
                    f"🏢 {c}</span>"
                    for c in comps
                ])
                st.markdown(f"<div style='margin-bottom: 0.5rem;'><strong>Target ATS Companies:</strong><br>{comps_badges}</div>", unsafe_allow_html=True)
            if negative_keywords:
                negs = [n.strip() for n in negative_keywords.split(",") if n.strip()]
                negs_badges = "".join([
                    f"<span style='display: inline-block; background: #fef2f2; color: #991b1b; border: 1px solid #fecaca; "
                    f"padding: 0.2rem 0.55rem; border-radius: 6px; font-size: 0.82rem; font-weight: 600; margin: 0.15rem 0.25rem 0.15rem 0;'>"
                    f"🚫 {n}</span>"
                    for n in negs
                ])
                st.markdown(f"<div style='margin-bottom: 0.5rem;'><strong>Exclusion Keywords:</strong><br>{negs_badges}</div>", unsafe_allow_html=True)

    with col2:
        st.markdown("#### 🌟 Key Experience Highlights")
        highlights = profile.get("experience_highlights", [])
        for item in highlights:
            st.markdown(
                f"""
                <div style="background: #fafafa; border-left: 3px solid #2563eb; padding: 0.6rem 0.85rem; margin-bottom: 0.5rem; font-size: 0.9rem; color: #27272a; border-radius: 0 6px 6px 0;">
                    {item}
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("---")

    # Navigation buttons
    nav_col1, nav_col2, nav_col3 = st.columns([1, 1, 2])
    with nav_col1:
        if st.button("← Back to Edit Input", use_container_width=True):
            go_to_screen(SCREEN_INPUT)

    with nav_col3:
        if st.button("🚀 Confirm & Launch Agentic Search", type="primary", use_container_width=True):
            from src.utils.user_manager import flush_session_to_user_workspace
            flush_session_to_user_workspace()
            st.session_state.scrape_progress = 0
            st.session_state.scrape_completed = False
            go_to_screen(SCREEN_SEARCHING)
