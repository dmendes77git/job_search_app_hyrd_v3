"""
Screen 0: Candidate Registry & Account Hub.
Allows registering new candidate profiles with rich LinkedIn-like career details,
analyzing personal LinkedIn profiles with dedicated AI optimization agent,
switching between multiple candidate accounts, and isolating their dedicated saved workspaces.
"""

import json
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional
import streamlit as st

from src.agents.linkedin_auditor_agent import audit_linkedin_profile
from src.agents.resume_parser_agent import (
    EXP_LEVEL_OPTIONS,
    parse_resume_with_gemini,
)
from src.state import SCREEN_INPUT, SCREEN_PIPELINE, go_to_screen
from src.utils.file_parser import extract_text_from_file
from src.utils.user_manager import (
    AVATAR_COLORS,
    AVATAR_PALETTE,
    create_user,
    delete_user,
    flush_session_to_user_workspace,
    get_active_user_id,
    get_all_users,
    get_user_profile,
    get_user_workspace,
    load_user_into_session,
    save_user_profile,
)
from src.views.registry import (
    render_linkedin_audit_card,
    render_workspace_switcher,
)


def render_screen0() -> None:
    """Render the Candidate Registry & Multi-User Account Hub screen."""
    all_users = get_all_users()
    active_id = get_active_user_id()
    active_profile = get_user_profile(active_id) if active_id else {}

    # Header Banner
    st.markdown(
        """
        <div style="background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); color: #f8fafc; padding: 1.25rem 1.75rem; border-radius: 12px; margin-bottom: 1.25rem; border: 1px solid #334155;">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 1rem;">
                <div>
                    <div style="display: flex; align-items: center; gap: 0.6rem;">
                        <span style="font-size: 1.5rem;">👤</span>
                        <h2 style="margin: 0; font-size: 1.4rem; color: #ffffff; font-weight: 700;">
                            Candidate Registry & Dedicated Workspace Hub
                        </h2>
                    </div>
                    <div style="font-size: 0.88rem; color: #94a3b8; margin-top: 0.25rem;">
                        Multi-User Career Management • Isolated Candidate Saved Areas • LinkedIn Profile Optimizer Agent
                    </div>
                </div>
                <div style="background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2); border-radius: 8px; padding: 0.45rem 0.9rem; font-size: 0.85rem; color: #e2e8f0;">
                    👥 Registered Candidates: <strong>""" + str(len(all_users)) + """</strong>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Active Candidate Callout
    if active_profile:
        cand_name = active_profile.get("full_name", "Active Candidate")
        headline = active_profile.get("headline", "Professional")
        loc = active_profile.get("location", "Remote")
        color = active_profile.get("avatar_color", AVATAR_PALETTE[0])
        initials = "".join([part[0].upper() for part in cand_name.split() if part][:2]) or "U"
        workspace = get_user_workspace(active_id)
        saved_count = len(workspace.get("saved_jobs", []))
        pipeline_count = len(workspace.get("application_pipeline", {}))
        cv_count = len(workspace.get("customized_cvs", {}))

        st.markdown(
            f"""
            <div style="background: #ffffff; border: 1.5px solid #e2e8f0; border-radius: 10px; padding: 0.85rem 1.1rem; margin-bottom: 1.25rem; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px;">
                <div style="display: flex; align-items: center; gap: 12px;">
                    <div style="width: 44px; height: 44px; border-radius: 50%; background: {color}; color: #ffffff; font-weight: 700; font-size: 1.05rem; display: flex; align-items: center; justify-content: center; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                        {initials}
                    </div>
                    <div>
                        <div style="font-weight: 700; color: #0f172a; font-size: 1.05rem;">
                            {cand_name} <span style="background: #2563eb; color: #ffffff; font-size: 0.72rem; font-weight: 600; padding: 2px 8px; border-radius: 9999px; margin-left: 6px;">CURRENT ACTIVE WORKSPACE</span>
                        </div>
                        <div style="color: #64748b; font-size: 0.85rem;">
                            {headline} • 📍 {loc}
                        </div>
                    </div>
                </div>
                <div style="display: flex; align-items: center; gap: 14px; font-size: 0.85rem; color: #475569;">
                    <span>📌 Saved Roles: <strong>{saved_count}</strong></span>
                    <span>📋 Pipeline Applications: <strong>{pipeline_count}</strong></span>
                    <span>📄 Tailored CVs: <strong>{cv_count}</strong></span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # 3 Main Hub Tabs
    tab_switch, tab_register, tab_edit = st.tabs([
        "👥 Switch Candidate Workspace",
        "➕ Register New Candidate",
        "✏️ Edit Active Profile Details",
    ])

    # ---------------------------------------------------------
    # TAB 1: Switch Candidate Workspace
    # ---------------------------------------------------------
    with tab_switch:
        render_workspace_switcher(all_users=all_users, active_id=active_id)

    # ---------------------------------------------------------
    # TAB 2: Register New Candidate (LinkedIn-style Intake)
    # ---------------------------------------------------------
    with tab_register:
        st.markdown("### ➕ Register New Candidate Profile")
        st.caption("Create a complete professional profile. Auto-populate from an existing resume, analyze your LinkedIn profile with AI, or fill out the fields manually.")

        # Quick Resume Auto-Fill
        with st.expander("⚡ Quick Auto-Fill: Upload Resume (Optional)", expanded=True):
            st.caption("Upload a `.pdf`, `.docx`, or `.txt` resume to automatically parse and populate the registration fields below via Gemini AI.")
            up_file = st.file_uploader("Upload Candidate Resume for Quick Registration", type=["pdf", "docx", "txt"], key="reg_resume_uploader")
            if up_file is not None:
                if st.button("🤖 Auto-Fill Registration Form with Gemini", key="btn_autofill_reg", type="primary"):
                    with st.spinner("Extracting candidate identity, skills, experience, and education from resume..."):
                        raw_text = extract_text_from_file(up_file)
                        api_key = st.session_state.get("gemini_api_key")
                        pref_model = st.session_state.get("gemini_model")
                        parsed, _, _ = parse_resume_with_gemini(raw_text, api_key=api_key, preferred_model=pref_model)

                        if parsed:
                            st.session_state["reg_name"] = parsed.get("full_name", "")
                            st.session_state["reg_email"] = parsed.get("email", "")
                            st.session_state["reg_phone"] = parsed.get("phone", "")
                            st.session_state["reg_loc"] = parsed.get("location", "")
                            st.session_state["reg_headline"] = parsed.get("headline", "")
                            st.session_state["reg_linkedin"] = parsed.get("linkedin_url") or parsed.get("linkedin") or ""
                            st.session_state["reg_summary"] = parsed.get("summary", "")
                            st.session_state["reg_exp_years"] = parsed.get("years_of_experience", "")
                            st.session_state["reg_target_role"] = (parsed.get("target_roles", [""])[0] if parsed.get("target_roles") else parsed.get("headline", ""))
                            st.session_state["reg_salary"] = parsed.get("preferred_min_salary", "$150,000")
                            st.session_state["reg_skills"] = ", ".join(parsed.get("core_skills", []))
                            st.session_state["reg_resume_text"] = raw_text
                            st.toast("Registration form pre-filled from resume!")
                            st.rerun()

        # Registration Form Container
        st.markdown("---")
        st.markdown("#### 1. Personal & Contact Identity")
        c1, c2 = st.columns(2)
        with c1:
            new_name = st.text_input("Full Name *", value=st.session_state.get("reg_name", ""), placeholder="e.g. David Mendes", key="reg_name_widget")
            st.session_state["reg_name"] = new_name
            new_email = st.text_input("Email Address *", value=st.session_state.get("reg_email", ""), placeholder="e.g. david.mendes@example.com", key="reg_email_widget")
            st.session_state["reg_email"] = new_email
            new_phone = st.text_input("Phone Number", value=st.session_state.get("reg_phone", ""), placeholder="e.g. +1 (555) 019-2834", key="reg_phone_widget")
            st.session_state["reg_phone"] = new_phone
            new_linkedin = st.text_input(
                "Personal LinkedIn Address",
                value=st.session_state.get("reg_linkedin", ""),
                placeholder="https://www.linkedin.com/in/username",
                help="Your public LinkedIn profile URL. Triggers the AI LinkedIn Auditor Agent below.",
                key="reg_linkedin_widget",
            )
            st.session_state["reg_linkedin"] = new_linkedin

        with c2:
            new_headline = st.text_input("Professional Headline *", value=st.session_state.get("reg_headline", ""), placeholder="e.g. Senior Full-Stack AI Engineer | Distributed Systems", key="reg_headline_widget")
            st.session_state["reg_headline"] = new_headline
            new_loc = st.text_input("Current Location (City, Country) *", value=st.session_state.get("reg_loc", "Remote"), placeholder="e.g. Lisbon, Portugal or San Francisco, CA", key="reg_loc_widget")
            st.session_state["reg_loc"] = new_loc

            # Avatar Color
            cur_color = st.session_state.get("reg_avatar_color", AVATAR_PALETTE[0])
            col_idx = AVATAR_PALETTE.index(cur_color) if cur_color in AVATAR_PALETTE else 0
            new_color = st.selectbox(
                "Avatar Color",
                options=AVATAR_PALETTE,
                index=col_idx,
                format_func=lambda c: AVATAR_COLORS.get(c, c),
                key="reg_avatar_color_widget",
            )
            st.session_state["reg_avatar_color"] = new_color
            st.markdown(
                f"""
                <div style="display: flex; align-items: center; gap: 8px; margin-top: -6px; margin-bottom: 8px;">
                    <div style="width: 20px; height: 20px; border-radius: 50%; background: {new_color}; border: 1.5px solid #cbd5e1; box-shadow: 0 1px 3px rgba(0,0,0,0.1);"></div>
                    <span style="font-size: 0.82rem; color: #475569; font-weight: 600;">Selected Color: {AVATAR_COLORS.get(new_color, new_color)}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # LinkedIn Profile Auditor Trigger & Scorecard
        if new_linkedin.strip():
            st.markdown("<div style='height: 0.3rem;'></div>", unsafe_allow_html=True)
            li_btn_col1, li_btn_col2 = st.columns([1.6, 1])
            with li_btn_col1:
                if st.button("🔍 Analyze LinkedIn Profile with AI Agent", key="btn_audit_li_reg", type="secondary", use_container_width=True):
                    with st.spinner("🤖 Hyrd Agent auditing LinkedIn profile, searchability, and recruiter conversion metrics..."):
                        audit_res = audit_linkedin_profile(
                            new_linkedin,
                            {
                                "full_name": new_name,
                                "headline": new_headline,
                                "summary": st.session_state.get("reg_summary", ""),
                                "core_skills": st.session_state.get("reg_skills", ""),
                                "target_role": st.session_state.get("reg_target_role", ""),
                                "target_companies": st.session_state.get("reg_target_companies", ""),
                                "experience_highlights": st.session_state.get("reg_highlights", ""),
                            },
                            api_key=st.session_state.get("gemini_api_key"),
                            preferred_model=st.session_state.get("gemini_model"),
                        )
                        st.session_state["reg_li_audit"] = audit_res
                        st.toast("LinkedIn Profile Audit Complete!")

            if st.session_state.get("reg_li_audit"):
                render_linkedin_audit_card(st.session_state["reg_li_audit"], prefix="reg")

        st.markdown("---")
        st.markdown("#### 2. Professional Summary & Bio (About)")
        new_summary = st.text_area(
            "Executive Summary (About Me)",
            value=st.session_state.get("reg_summary", ""),
            height=110,
            placeholder="2-4 sentences summarizing your key domain expertise, signature achievements, and leadership philosophy.",
            key="reg_summary_widget",
        )
        st.session_state["reg_summary"] = new_summary

        st.markdown("---")
        st.markdown("#### 3. Career Seniority & Current Experience")
        c_exp1, c_exp2, c_exp3 = st.columns(3)
        with c_exp1:
            cur_sen = st.session_state.get("reg_seniority", "Senior (5+ years)")
            sen_idx = EXP_LEVEL_OPTIONS.index(cur_sen) if cur_sen in EXP_LEVEL_OPTIONS else 2
            new_seniority = st.selectbox("Seniority Level *", options=EXP_LEVEL_OPTIONS, index=sen_idx, key="reg_seniority_widget")
            st.session_state["reg_seniority"] = new_seniority
        with c_exp2:
            new_exp_years = st.text_input("Years of Experience", value=st.session_state.get("reg_exp_years", "6+ years"), placeholder="e.g. 7 years", key="reg_exp_years_widget")
            st.session_state["reg_exp_years"] = new_exp_years
        with c_exp3:
            new_curr_company = st.text_input("Current / Most Recent Company", value=st.session_state.get("reg_curr_company", ""), placeholder="e.g. Stripe, Linear, or Stealth Startup", key="reg_curr_company_widget")
            st.session_state["reg_curr_company"] = new_curr_company

        st.markdown("---")
        st.markdown("#### 4. Job Search Preferences & Target Role")
        p1, p2, p3 = st.columns(3)
        with p1:
            new_target_role = st.text_input("Target Role Title *", value=st.session_state.get("reg_target_role", "Senior Software Engineer"), placeholder="e.g. Staff AI Platform Engineer", key="reg_target_role_widget")
            st.session_state["reg_target_role"] = new_target_role
        with p2:
            work_mode_opts = ["Remote Only", "Hybrid", "On-site", "No Preference"]
            cur_wm = st.session_state.get("reg_work_mode", "Remote Only")
            wm_idx = work_mode_opts.index(cur_wm) if cur_wm in work_mode_opts else 0
            new_work_mode = st.selectbox("Preferred Work Mode", options=work_mode_opts, index=wm_idx, key="reg_work_mode_widget")
            st.session_state["reg_work_mode"] = new_work_mode
        with p3:
            new_min_salary = st.text_input("Preferred Minimum Salary", value=st.session_state.get("reg_salary", "$150,000"), placeholder="e.g. $165,000 or €120,000", key="reg_salary_widget")
            st.session_state["reg_salary"] = new_min_salary

        sp1, sp2 = st.columns(2)
        with sp1:
            new_target_companies = st.text_input("Target Dream Employers (Optional)", value=st.session_state.get("reg_target_companies", ""), placeholder="e.g. OpenAI, Anthropic, Linear, Stripe", key="reg_target_companies_widget")
            st.session_state["reg_target_companies"] = new_target_companies
        with sp2:
            new_negative_keywords = st.text_input("Negative Exclusions (Optional)", value=st.session_state.get("reg_neg_kw", ""), placeholder="e.g. Crypto, Defense, Gambling, Legacy", key="reg_neg_kw_widget")
            st.session_state["reg_neg_kw"] = new_negative_keywords

        st.markdown("---")
        st.markdown("#### 5. Skills, Experience Highlights & Credentials")
        new_skills_raw = st.text_area(
            "Core Competencies & Skills * (comma-separated)",
            value=st.session_state.get("reg_skills", "Python, Distributed Systems, Docker, Kubernetes, LLMs, GCP"),
            height=85,
            placeholder="e.g. Python, Golang, PyTorch, Kubernetes, Microservices, RAG Pipelines",
            key="reg_skills_widget",
        )
        st.session_state["reg_skills"] = new_skills_raw

        new_exp_highlights = st.text_area(
            "Key Experience Highlights (1 achievement per line)",
            value=st.session_state.get("reg_highlights", "- Scaled real-time inference pipeline by 40% using Kubernetes.\n- Spearheaded autonomous agent architecture reducing latency by 35%."),
            height=95,
            placeholder="- Built distributed event pipeline handling 2M+ daily events.\n- Led team of 6 engineers launching multi-region AWS cloud migration.",
            key="reg_highlights_widget",
        )
        st.session_state["reg_highlights"] = new_exp_highlights

        ed1, ed2, ed3 = st.columns(3)
        with ed1:
            new_degree = st.text_input("Highest Degree Earned", value=st.session_state.get("reg_degree", "B.S. in Computer Science"), placeholder="e.g. M.S. Artificial Intelligence", key="reg_degree_widget")
            st.session_state["reg_degree"] = new_degree
        with ed2:
            new_institution = st.text_input("University / Institution", value=st.session_state.get("reg_institution", "University of California, Berkeley"), placeholder="e.g. Stanford University", key="reg_institution_widget")
            st.session_state["reg_institution"] = new_institution
        with ed3:
            new_grad_year = st.text_input("Graduation Year", value=st.session_state.get("reg_grad_year", "2018"), placeholder="e.g. 2019", key="reg_grad_year_widget")
            st.session_state["reg_grad_year"] = new_grad_year

        new_certs = st.text_input("Certifications (comma-separated)", value=st.session_state.get("reg_certs", "AWS Solutions Architect, CKA"), placeholder="e.g. GCP Professional Data Engineer, CKA", key="reg_certs_widget")
        st.session_state["reg_certs"] = new_certs

        new_resume_text = st.session_state.get("reg_resume_text", "")

        st.markdown("<div style='height: 0.75rem;'></div>", unsafe_allow_html=True)
        submit_reg = st.button("🚀 Register Candidate & Launch Dedicated Workspace", type="primary", use_container_width=True, key="btn_submit_reg_candidate")

        if submit_reg:
            if not new_name.strip() or not new_email.strip() or not new_headline.strip():
                st.error("Please fill in all required fields marked with * (Full Name, Email, Headline).")
            else:
                skills_list = [s.strip() for s in re.split(r"[,;\n]+", new_skills_raw) if s.strip()]
                exp_highlights_list = [h.strip() for h in new_exp_highlights.splitlines() if h.strip()]

                edu_list = []
                if new_degree.strip() or new_institution.strip():
                    edu_list.append({
                        "degree": new_degree.strip(),
                        "institution": new_institution.strip(),
                        "year": new_grad_year.strip(),
                    })

                certs_list = [c.strip() for c in new_certs.split(",") if c.strip()]

                new_profile_data = {
                    "full_name": new_name.strip(),
                    "email": new_email.strip(),
                    "phone": new_phone.strip(),
                    "location": new_loc.strip(),
                    "headline": new_headline.strip(),
                    "avatar_color": new_color,
                    "summary": new_summary.strip(),
                    "seniority_level": new_seniority,
                    "years_of_experience": new_exp_years.strip(),
                    "current_company": new_curr_company.strip(),
                    "target_role": new_target_role.strip(),
                    "target_roles": [new_target_role.strip()] if new_target_role.strip() else [],
                    "remote_pref": new_work_mode,
                    "min_salary": new_min_salary.strip(),
                    "target_companies": new_target_companies.strip(),
                    "negative_keywords": new_negative_keywords.strip(),
                    "core_skills": skills_list,
                    "experience_highlights": exp_highlights_list,
                    "education": edu_list,
                    "certifications": certs_list,
                    "linkedin": new_linkedin.strip(),
                    "github": "",
                    "portfolio": "",
                    "resume_text": new_resume_text or f"{new_name}\n{new_headline}\n{new_loc} • {new_email} • {new_phone}\nLinkedIn: {new_linkedin}\n\nSummary:\n{new_summary}\n\nSkills:\n{', '.join(skills_list)}",
                }

                created_id = create_user(new_profile_data)
                flush_session_to_user_workspace()
                load_user_into_session(created_id)

                st.toast(f"Candidate profile created for {new_name}!")
                go_to_screen(SCREEN_INPUT)

    # ---------------------------------------------------------
    # TAB 3: Edit Active Profile Details
    # ---------------------------------------------------------
    with tab_edit:
        st.markdown(f"### ✏️ Edit Profile for {active_profile.get('full_name', 'Active Candidate')}")
        st.caption("Update profile information, personal LinkedIn address, target titles, dream company targets, and competencies in your dedicated workspace.")

        if not active_profile:
            st.warning("No active candidate profile loaded.")
        else:
            # Rehydrate edit fields when active profile changes
            if st.session_state.get("last_edit_user_id") != active_id:
                st.session_state["edit_name"] = active_profile.get("full_name", "")
                st.session_state["edit_email"] = active_profile.get("email", "")
                st.session_state["edit_phone"] = active_profile.get("phone", "")
                st.session_state["edit_loc"] = active_profile.get("location", "")
                st.session_state["edit_headline"] = active_profile.get("headline", "")
                st.session_state["edit_linkedin"] = active_profile.get("linkedin", "")
                st.session_state["edit_summary"] = active_profile.get("summary", "")
                st.session_state["edit_years"] = active_profile.get("years_of_experience", "")
                st.session_state["edit_target_role"] = active_profile.get("target_role", "")
                st.session_state["edit_min_sal"] = active_profile.get("min_salary", "$140,000")
                st.session_state["edit_target_comp"] = active_profile.get("target_companies", "")
                st.session_state["edit_neg_kw"] = active_profile.get("negative_keywords", "")
                st.session_state["edit_skills"] = ", ".join(active_profile.get("core_skills", []))
                st.session_state["edit_github"] = active_profile.get("github", "")
                st.session_state["edit_portfolio"] = active_profile.get("portfolio", "")
                st.session_state["edit_avatar_col"] = active_profile.get("avatar_color", AVATAR_PALETTE[0])
                st.session_state["edit_seniority"] = active_profile.get("seniority_level", "Senior (5+ years)")
                st.session_state["edit_work_mode"] = active_profile.get("remote_pref", "Remote Only")
                st.session_state["last_edit_user_id"] = active_id

            st.markdown("#### 1. Identity & LinkedIn Contact")
            e_col1, e_col2 = st.columns(2)
            with e_col1:
                e_name = st.text_input("Full Name", value=st.session_state.get("edit_name", ""), key="edit_name_input")
                st.session_state["edit_name"] = e_name
                e_email = st.text_input("Email Address", value=st.session_state.get("edit_email", ""), key="edit_email_input")
                st.session_state["edit_email"] = e_email
                e_phone = st.text_input("Phone Number", value=st.session_state.get("edit_phone", ""), key="edit_phone_input")
                st.session_state["edit_phone"] = e_phone
                e_li = st.text_input("Personal LinkedIn Address", value=st.session_state.get("edit_linkedin", ""), placeholder="https://www.linkedin.com/in/username", key="edit_linkedin_input")
                st.session_state["edit_linkedin"] = e_li
            with e_col2:
                e_headline = st.text_input("Professional Headline", value=st.session_state.get("edit_headline", ""), key="edit_headline_input")
                st.session_state["edit_headline"] = e_headline
                e_loc = st.text_input("Current Location", value=st.session_state.get("edit_loc", ""), key="edit_loc_input")
                st.session_state["edit_loc"] = e_loc
                e_gh = st.text_input("GitHub Profile (Optional)", value=st.session_state.get("edit_github", ""), placeholder="https://github.com/username", key="edit_github_input")
                st.session_state["edit_github"] = e_gh
                e_port = st.text_input("Portfolio / Website (Optional)", value=st.session_state.get("edit_portfolio", ""), placeholder="https://mywebsite.com", key="edit_portfolio_input")
                st.session_state["edit_portfolio"] = e_port

            # Edit LinkedIn Profile Auditor Trigger & Scorecard
            if e_li.strip():
                st.markdown("<div style='height: 0.3rem;'></div>", unsafe_allow_html=True)
                li_edit_c1, _ = st.columns([1.6, 1])
                with li_edit_c1:
                    if st.button("🔍 Re-Analyze LinkedIn Profile with AI Agent", key="btn_audit_li_edit", type="secondary", use_container_width=True):
                        with st.spinner("🤖 Hyrd Agent re-evaluating LinkedIn profile optimization..."):
                            audit_res = audit_linkedin_profile(
                                e_li,
                                {
                                    "full_name": e_name,
                                    "headline": e_headline,
                                    "summary": st.session_state.get("edit_summary", ""),
                                    "core_skills": st.session_state.get("edit_skills", ""),
                                    "target_role": st.session_state.get("edit_target_role", ""),
                                    "target_companies": st.session_state.get("edit_target_comp", ""),
                                    "experience_highlights": "",
                                },
                                api_key=st.session_state.get("gemini_api_key"),
                                preferred_model=st.session_state.get("gemini_model"),
                            )
                            st.session_state["edit_li_audit"] = audit_res
                            st.toast("LinkedIn Profile Re-Audit Complete!")

                if st.session_state.get("edit_li_audit"):
                    render_linkedin_audit_card(st.session_state["edit_li_audit"], prefix="edit")

            st.markdown("---")
            st.markdown("#### 2. Professional Summary")
            e_summary = st.text_area("Executive Summary", value=st.session_state.get("edit_summary", ""), height=110, key="edit_summary_input")
            st.session_state["edit_summary"] = e_summary

            st.markdown("---")
            st.markdown("#### 3. Career Seniority & Current Experience")
            es_c1, es_c2 = st.columns(2)
            with es_c1:
                cur_sen = st.session_state.get("edit_seniority", "Senior (5+ years)")
                sen_idx = EXP_LEVEL_OPTIONS.index(cur_sen) if cur_sen in EXP_LEVEL_OPTIONS else 2
                e_seniority = st.selectbox("Seniority Level", options=EXP_LEVEL_OPTIONS, index=sen_idx, key="edit_seniority_input")
                st.session_state["edit_seniority"] = e_seniority
            with es_c2:
                e_years = st.text_input("Years of Experience", value=st.session_state.get("edit_years", ""), key="edit_years_input")
                st.session_state["edit_years"] = e_years

            st.markdown("---")
            st.markdown("#### 4. Job Search Preferences & Target Role")
            ep1, ep2, ep3 = st.columns(3)
            with ep1:
                e_target_role = st.text_input("Target Role Title", value=st.session_state.get("edit_target_role", ""), key="edit_target_role_input")
                st.session_state["edit_target_role"] = e_target_role
            with ep2:
                work_mode_opts = ["Remote Only", "Hybrid", "On-site", "No Preference"]
                cur_wm = st.session_state.get("edit_work_mode", "Remote Only")
                wm_idx = work_mode_opts.index(cur_wm) if cur_wm in work_mode_opts else 0
                e_work_mode = st.selectbox("Preferred Work Mode", options=work_mode_opts, index=wm_idx, key="edit_work_mode_input")
                st.session_state["edit_work_mode"] = e_work_mode
            with ep3:
                e_min_sal = st.text_input("Preferred Minimum Salary", value=st.session_state.get("edit_min_sal", ""), key="edit_min_sal_input")
                st.session_state["edit_min_sal"] = e_min_sal

            esp1, esp2 = st.columns(2)
            with esp1:
                e_target_comp = st.text_input("Target Employers", value=st.session_state.get("edit_target_comp", ""), key="edit_target_comp_input")
                st.session_state["edit_target_comp"] = e_target_comp
            with esp2:
                e_neg_kw = st.text_input("Negative Exclusions", value=st.session_state.get("edit_neg_kw", ""), key="edit_neg_kw_input")
                st.session_state["edit_neg_kw"] = e_neg_kw

            st.markdown("---")
            st.markdown("#### 5. Skills")
            e_skills = st.text_area("Core Skills (comma-separated)", value=st.session_state.get("edit_skills", ""), height=85, key="edit_skills_input")
            st.session_state["edit_skills"] = e_skills

            st.markdown("<div style='height: 0.75rem;'></div>", unsafe_allow_html=True)
            if st.button("💾 Save Profile Changes", type="primary", use_container_width=True, key="btn_save_edit_profile"):
                skills_arr = [s.strip() for s in re.split(r"[,;\n]+", e_skills) if s.strip()]

                updated_profile = dict(active_profile)
                updated_profile.update({
                    "full_name": e_name.strip(),
                    "email": e_email.strip(),
                    "phone": e_phone.strip(),
                    "location": e_loc.strip(),
                    "headline": e_headline.strip(),
                    "linkedin": e_li.strip(),
                    "summary": e_summary.strip(),
                    "seniority_level": e_seniority,
                    "years_of_experience": e_years.strip(),
                    "target_role": e_target_role.strip(),
                    "target_roles": [e_target_role.strip()] if e_target_role.strip() else [],
                    "remote_pref": e_work_mode,
                    "min_salary": e_min_sal.strip(),
                    "target_companies": e_target_comp.strip(),
                    "negative_keywords": e_neg_kw.strip(),
                    "core_skills": skills_arr,
                    "github": e_gh.strip(),
                    "portfolio": e_port.strip(),
                })

                save_user_profile(active_id, updated_profile)
                load_user_into_session(active_id)
                st.toast(f"Profile saved for {e_name}!")
                st.rerun()


__all__ = [
    "render_screen0",
    "render_linkedin_audit_card",
]
