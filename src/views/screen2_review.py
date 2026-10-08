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
from src.agents.profile_agent import (
    categorize_competencies,
    analyze_recruiter_gaps,
    auto_quantify_bullet,
)


@st.dialog("📋 Recruiter Role Fit Analysis", width="medium")
def show_recruiter_analysis_dialog(role: str, eval_data: dict, candidate_name: str) -> None:
    """Pop-up modal presenting expert recruiter match analysis and recommendations."""
    score = eval_data.get("score", 85)
    match_label = eval_data.get("match_label", "Strong Match")
    badge_bg = eval_data.get("badge_bg", "#eff6ff")
    badge_color = eval_data.get("badge_color", "#1e40af")
    badge_border = eval_data.get("badge_border", "#bfdbfe")
    rationale = eval_data.get("rationale", "")
    matched_skills = eval_data.get("matched_skills", [])
    seniority = eval_data.get("seniority_assessment", "Aligned with professional trajectory.")
    strengths = eval_data.get("strengths", [])
    recommendations = eval_data.get("recommendations", [])

    st.markdown(f"### 🎯 {role}")
    st.caption(f"Candidate Evaluation for **{candidate_name}**")

    # Header Card with Score & Tier in the same pill badge format
    st.markdown(
        f"""
        <div style='background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; padding: 0.85rem 1.1rem; margin: 0.6rem 0 1rem 0; display: flex; align-items: center; justify-content: space-between;'>
            <div>
                <div style='font-size: 0.8rem; color: #64748b; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;'>Fit Assessment</div>
                <div style='font-size: 1.35rem; font-weight: 800; color: #0f172a; margin-top: 0.15rem;'>{score}% Overall Alignment</div>
            </div>
            <div>
                <span style='background: {badge_bg}; color: {badge_color}; border: 1px solid {badge_border}; padding: 6px 14px; border-radius: 16px; font-size: 0.88rem; font-weight: 700; white-space: nowrap;'>
                    🎯 {score}% Match • {match_label}
                </span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("#### 💡 Executive Recruiter Rationale")
    st.info(rationale)

    if matched_skills:
        st.markdown("#### 🛠️ Key Competency Overlap")
        badges = " ".join([
            f"<span style='display: inline-block; background: #eff6ff; color: #1d4ed8; border: 1px solid #bfdbfe; padding: 3px 9px; border-radius: 6px; font-size: 0.82rem; font-weight: 500; margin: 2px 4px 4px 0;'>{s}</span>"
            for s in matched_skills
        ])
        st.markdown(f"<div style='margin-bottom: 0.75rem;'>{badges}</div>", unsafe_allow_html=True)

    if seniority:
        st.markdown("#### 📈 Seniority & Leveling Assessment")
        st.markdown(seniority)

    if strengths:
        st.markdown("#### ✅ Core Candidate Advantages")
        for s in strengths:
            st.markdown(f"- {s}")

    # What is Missing to Achieve 100% Match
    gap_data = eval_data.get("gap_to_100") or {}
    missing_skills = gap_data.get("missing_skills", [])
    experience_gaps = gap_data.get("experience_gaps", [])
    certifications = gap_data.get("certifications", [])
    gap_summary = gap_data.get("summary", "")

    st.markdown("---")
    st.markdown("#### 🎯 What's Missing to Achieve a 100% Match?")
    if gap_summary:
        st.markdown(
            f"""
            <div style='background: #fffbeb; border: 1px solid #fde68a; border-radius: 8px; padding: 0.75rem 1rem; margin-bottom: 0.85rem; font-size: 0.88rem; color: #92400e;'>
                <strong>Recruiter Diagnostic:</strong> {gap_summary}
            </div>
            """,
            unsafe_allow_html=True,
        )

    g_col1, g_col2 = st.columns(2, gap="medium")
    with g_col1:
        st.markdown("**🛠️ High-Impact Skills & Tools to Add**")
        if missing_skills:
            gap_badges = " ".join([
                f"<span style='display: inline-block; background: #fef2f2; color: #991b1b; border: 1px solid #fecaca; padding: 3px 8px; border-radius: 6px; font-size: 0.8rem; font-weight: 600; margin: 2px 4px 4px 0;'>+ {s}</span>"
                for s in missing_skills
            ])
            st.markdown(f"<div style='margin-bottom: 0.5rem;'>{gap_badges}</div>", unsafe_allow_html=True)
            st.caption("Commonly requested tools for this title not explicitly emphasized on your profile.")
        else:
            st.caption("Candidate covers all primary technical requirements.")

        if certifications:
            st.markdown("<div style='margin-top: 0.75rem;'><strong>📜 Recommended Certifications</strong></div>", unsafe_allow_html=True)
            for cert in certifications:
                st.markdown(f"- 🎓 {cert}")
            st.caption("Credentials that immediately validate senior competence to ATS and recruiters.")

    with g_col2:
        st.markdown("**📈 Experience & Scale Proof-Points**")
        if experience_gaps:
            for exp in experience_gaps:
                st.markdown(f"- 📌 {exp}")
            st.caption("Explicitly spotlighting these operational scales in your CV/interview will eliminate recruiter hesitation.")

    st.markdown("---")

    if recommendations:
        st.markdown("#### 🚀 Actionable Application Advice")
        for r in recommendations:
            st.markdown(f"- {r}")

    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
    if st.button("Close Analysis", key=f"dlg_close_{abs(hash(role)) % 100000}", use_container_width=True):
        st.rerun()


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
            gh_link = st.session_state.get("github_url") or profile.get("github_url")
            if gh_link:
                contact_info.append(f"🐙 {gh_link}")

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

        # Feature P1-A: GitHub Code-Verified Archetype
        gh_summary = st.session_state.get("github_summary") or profile.get("github_summary")
        if gh_summary:
            st.markdown(
                f"""
                <div style="background: #f0fdf4; border-left: 3px solid #166534; padding: 0.6rem 0.85rem; margin-top: 0.65rem; border-radius: 0 6px 6px 0; font-size: 0.86rem; color: #166534;">
                    <strong>🐙 Code-Verified Engineering Archetype (P1-A):</strong> {gh_summary}
                </div>
                """,
                unsafe_allow_html=True,
            )

    # Feature P1-D: Real-Time Recruiter Readiness Radar & 1-Click Gap Remediation
    gaps_data = st.session_state.get("recruiter_gap_analysis")
    if not gaps_data:
        from src.schemas import UserProfile
        try:
            u_prof = UserProfile(**{k: v for k, v in profile.items() if k in UserProfile.model_fields})
            gaps_data = analyze_recruiter_gaps(u_prof)
            st.session_state.recruiter_gap_analysis = gaps_data
        except Exception:
            gaps_data = None

    if gaps_data:
        readiness_score = gaps_data.get("readiness_score", 85)
        readiness_label = gaps_data.get("readiness_label", "Strong Contender")
        radar = gaps_data.get("radar_metrics", {})

        with st.container(border=True):
            r_head1, r_head2 = st.columns([3, 1], vertical_alignment="center")
            with r_head1:
                st.markdown(
                    f"#### 📡 Recruiter Readiness Radar & ATS Audit (P1-D)\n"
                    f"<span style='font-size: 0.85rem; color: #64748b;'>"
                    f"Real-time benchmark evaluating leadership action verbs, hard metric density, and ATS formatting hygiene."
                    f"</span>",
                    unsafe_allow_html=True,
                )
            with r_head2:
                st.markdown(
                    f"<div style='text-align: right;'>"
                    f"<span style='background: #eff6ff; color: #1e40af; border: 1px solid #bfdbfe; "
                    f"padding: 0.35rem 0.75rem; border-radius: 9999px; font-size: 0.84rem; font-weight: 700; white-space: nowrap;'>"
                    f"🎯 {readiness_score}% • {readiness_label}</span></div>",
                    unsafe_allow_html=True,
                )

            # 5 Radar Metric Columns
            m_cols = st.columns(5)
            metric_keys = [
                ("Action Verb Power", "⚡", "%"),
                ("Metric Quantification", "📊", "%"),
                ("ATS Formatting Hygiene", "🧼", "/100"),
                ("Contact Completeness", "📞", "/100"),
                ("Technical Competency Depth", "🛠️", "/100"),
            ]
            for m_idx, (m_label, m_icon, m_unit) in enumerate(metric_keys):
                val = radar.get(m_label, 80)
                m_color = "#166534" if val >= 80 else "#b45309" if val >= 60 else "#b91c1c"
                with m_cols[m_idx]:
                    st.markdown(
                        f"""
                        <div style='background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 0.5rem 0.6rem; text-align: center;'>
                            <div style='font-size: 0.72rem; color: #64748b; font-weight: 600; text-transform: uppercase;'>{m_icon} {m_label[:14]}</div>
                            <div style='font-size: 1.15rem; font-weight: 800; color: {m_color}; margin-top: 0.2rem;'>{int(val)}{m_unit}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

            # 1-Click Remediation & Bullet Auto-Quantifier Expander
            with st.expander("⚡ 1-Click Auto-Remediation & STAR Bullet Optimizer", expanded=False):
                st.markdown(
                    "Transform vague or passive experience statements into **ATS-optimized, STAR-quantified bullet points** "
                    "with executive action verbs and metric evidence."
                )

                sample_bullet = ""
                highlights = profile.get("experience_highlights", [])
                if highlights:
                    sample_bullet = highlights[0]

                bullet_input = st.text_area(
                    "Draft Experience Bullet to Quantify:",
                    value=st.session_state.get("draft_bullet_to_quantify", sample_bullet),
                    key="txt_bullet_quantify_input",
                    height=70,
                    placeholder="e.g. Worked on optimizing database queries and backend API endpoints.",
                )

                q_col1, q_col2 = st.columns([1, 2])
                with q_col1:
                    if st.button("⚡ Auto-Quantify Bullet", use_container_width=True, type="primary"):
                        with st.spinner("Upgrading bullet using STAR framework & executive verbs..."):
                            q_res = auto_quantify_bullet(
                                bullet=bullet_input,
                                context=target_role,
                                api_key=st.session_state.get("gemini_api_key"),
                            )
                            st.session_state.last_quantified_bullet_result = q_res

                quant_res = st.session_state.get("last_quantified_bullet_result")
                if quant_res and quant_res.get("quantified"):
                    st.markdown("##### ✨ Quantified STAR Accomplishment:")
                    st.success(f"**{quant_res['quantified']}**")
                    if quant_res.get("metrics_added"):
                        st.caption(f"📈 **Injected Metrics & Power Verb:** `{quant_res.get('verb_upgraded')}` • {', '.join(quant_res['metrics_added'])}")

    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

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

            # Role row with checkbox, match score & dynamic qualitative tier, and Recruiter Analysis button
            r_col1, r_col2, r_col3 = st.columns([2.2, 2.0, 1.0], vertical_alignment="center")
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
                    f"<div style='text-align: right;'>"
                    f"<span style='background: {badge_bg}; color: {badge_color}; border: 1px solid {badge_border}; "
                    f"padding: 3px 9px; border-radius: 12px; font-size: 0.78rem; font-weight: 700; white-space: nowrap;'>"
                    f"🎯 {score}% Match • {match_label}</span></div>",
                    unsafe_allow_html=True,
                )
            with r_col3:
                if st.button(
                    "💡 Analysis",
                    key=f"btn_rec_analysis_{idx}_{abs(hash(role)) % 100000}",
                    help=f"View Recruiter Analysis for {role}",
                    use_container_width=True,
                ):
                    show_recruiter_analysis_dialog(role, eval_data, candidate_name)

            st.markdown("<div style='margin-bottom: 4px;'></div>", unsafe_allow_html=True)

        if not active_selected_roles:
            st.warning("⚠️ Please select at least one Recommended Role to include in the autonomous search.")

        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

        # Feature P1-C: Hierarchical Competency Graph & Proficiency Taxonomy
        st.markdown("#### 🛠️ Core Competencies & Proficiency Taxonomy (P1-C)")
        skills = st.session_state.get("primary_skills") or profile.get("core_skills", [])
        tiers = st.session_state.get("competency_tiers") or profile.get("competency_tiers")
        if not tiers and skills:
            tiers = categorize_competencies(skills)

        if tiers:
            t1 = tiers.get("tier_1_core", [])
            t2 = tiers.get("tier_2_supporting", [])
            t3 = tiers.get("tier_3_familiar", [])

            if t1:
                st.markdown("<div style='font-size: 0.82rem; font-weight: 700; color: #166534; margin-top: 4px;'>🟢 Tier 1: Core Drivers (Primary Stack)</div>", unsafe_allow_html=True)
                t1_html = "".join([
                    f"<span style='display: inline-block; background: #dcfce7; color: #15803d; border: 1px solid #86efac; padding: 0.2rem 0.55rem; border-radius: 6px; font-size: 0.82rem; font-weight: 600; margin: 0.15rem 0.25rem 0.15rem 0;'>✓ {s}</span>"
                    for s in t1
                ])
                st.markdown(f"<div style='margin-bottom: 0.5rem;'>{t1_html}</div>", unsafe_allow_html=True)

            if t2:
                st.markdown("<div style='font-size: 0.82rem; font-weight: 700; color: #1e40af; margin-top: 4px;'>🔵 Tier 2: Supporting Stack (Frameworks & Infra)</div>", unsafe_allow_html=True)
                t2_html = "".join([
                    f"<span style='display: inline-block; background: #eff6ff; color: #1d4ed8; border: 1px solid #bfdbfe; padding: 0.2rem 0.55rem; border-radius: 6px; font-size: 0.82rem; font-weight: 500; margin: 0.15rem 0.25rem 0.15rem 0;'>{s}</span>"
                    for s in t2
                ])
                st.markdown(f"<div style='margin-bottom: 0.5rem;'>{t2_html}</div>", unsafe_allow_html=True)

            if t3:
                st.markdown("<div style='font-size: 0.82rem; font-weight: 700; color: #854d0e; margin-top: 4px;'>🟡 Tier 3: Familiar & Emerging (Tools & APIs)</div>", unsafe_allow_html=True)
                t3_html = "".join([
                    f"<span style='display: inline-block; background: #fefce8; color: #854d0e; border: 1px solid #fde047; padding: 0.2rem 0.55rem; border-radius: 6px; font-size: 0.82rem; font-weight: 500; margin: 0.15rem 0.25rem 0.15rem 0;'>{s}</span>"
                    for s in t3
                ])
                st.markdown(f"<div style='margin-bottom: 0.5rem;'>{t3_html}</div>", unsafe_allow_html=True)
        elif skills:
            skills_html = "".join([
                f"<span style='display: inline-block; background: #eff6ff; color: #1d4ed8; border: 1px solid #bfdbfe; padding: 0.25rem 0.65rem; border-radius: 6px; font-size: 0.85rem; font-weight: 500; margin: 0.2rem 0.3rem 0.2rem 0;'>{s}</span>"
                for s in skills
            ])
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
