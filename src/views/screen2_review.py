"""
Screen 2: Profile Review Screen.
Displays structured candidate profile extracted by the Gemini Resume Parsing Agent.
Empowers candidates to review and curate Recommended Roles with expert recruiter match scores.
"""

import textwrap
import streamlit as st
from src.state import SCREEN_INPUT, SCREEN_SEARCHING, go_to_screen
from src.mock_data import SAMPLE_PARSED_PROFILE
from src.agents.matching.scoring import evaluate_role_match


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
        st.markdown("#### 🎯 Recommended Roles")
        st.caption("Select the specific roles you want Hyrd's autonomous crawlers to target:")

        target_roles = st.session_state.get("target_job_queries") or profile.get("target_roles", [target_role])

        # Ensure default selected roles in session state
        if "selected_recommended_roles" not in st.session_state or not st.session_state.selected_recommended_roles:
            st.session_state.selected_recommended_roles = list(target_roles)

        active_selected_roles = []

        for idx, role in enumerate(target_roles):
            eval_data = evaluate_role_match(role, profile)
            score = eval_data["score"]
            badge_bg = eval_data["badge_bg"]
            badge_color = eval_data["badge_color"]
            badge_border = eval_data["badge_border"]
            match_label = eval_data["match_label"]
            rationale = eval_data["rationale"]

            # Role row with checkbox and match score badge
            r_col1, r_col2 = st.columns([3.2, 1.3])
            with r_col1:
                is_checked = st.checkbox(
                    f"**{role}**",
                    value=(role in st.session_state.selected_recommended_roles),
                    key=f"chk_rec_role_{idx}_{abs(hash(role)) % 100000}",
                )
                if is_checked:
                    active_selected_roles.append(role)
            with r_col2:
                st.markdown(
                    f"<div style='text-align: right; padding-top: 3px;'>"
                    f"<span style='background: {badge_bg}; color: {badge_color}; border: 1px solid {badge_border}; "
                    f"padding: 3px 9px; border-radius: 12px; font-size: 0.78rem; font-weight: 700; white-space: nowrap;'>"
                    f"🎯 {score}% Match</span></div>",
                    unsafe_allow_html=True,
                )

            # Recruiter evaluation rationale
            st.markdown(
                f"<div style='font-size: 0.82rem; color: #64748b; margin-left: 1.8rem; margin-top: -0.35rem; margin-bottom: 0.75rem;'>"
                f"💡 <strong style='color: #475569;'>Recruiter Analysis:</strong> {rationale} "
                f"<span style='color: {badge_color}; font-weight: 600;'>({match_label})</span></div>",
                unsafe_allow_html=True,
            )

        if not active_selected_roles:
            st.warning("⚠️ Please select at least one Recommended Role to include in the autonomous search.")

        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

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

        target_companies = st.session_state.get("target_companies", "")
        negative_keywords = st.session_state.get("negative_keywords", "")
        if target_companies or negative_keywords:
            st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
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

    st.markdown("---")

    # Navigation buttons
    nav_col1, nav_col2, nav_col3 = st.columns([1, 1, 2])
    with nav_col1:
        if st.button("← Back to Edit Input", use_container_width=True):
            go_to_screen(SCREEN_INPUT)

    with nav_col3:
        confirm_btn = st.button("🚀 Confirm & Launch Agentic Search", type="primary", use_container_width=True)
        if confirm_btn:
            if not active_selected_roles:
                st.error("⚠️ Please select at least one Recommended Role to proceed with the search.")
            else:
                st.session_state.selected_recommended_roles = active_selected_roles
                st.session_state.target_job_queries = active_selected_roles
                st.session_state.target_role = active_selected_roles[0]

                from src.utils.user_manager import flush_session_to_user_workspace
                flush_session_to_user_workspace()
                st.session_state.scrape_progress = 0
                st.session_state.scrape_completed = False
                go_to_screen(SCREEN_SEARCHING)
