"""
Screen 1: User Input Form with File Upload (.pdf, .docx, .txt) and Gemini Resume Parsing Agent.
"""

import streamlit as st
from src.state import SCREEN_REVIEW, go_to_screen
from src.mock_data import SAMPLE_RESUME, SAMPLE_PARSED_PROFILE
from src.utils.file_parser import extract_text_from_file
from src.utils.user_manager import (
    get_active_user_id,
    get_user_profile,
    flush_session_to_user_workspace,
    get_personas,
    create_or_update_persona,
    switch_active_persona,
)
from src.tools.github_inspector import inspect_github_profile
from src.agents.profile_agent import categorize_competencies
from src.agents.resume_parser_agent import (
    EXP_LEVEL_OPTIONS,
    match_experience_level,
    extract_initial_profile_from_text,
    parse_resume_with_gemini,
)


def render_screen1() -> None:
    """Render the initial user input and resume submission form with file upload and Gemini parsing."""
    active_id = get_active_user_id()
    active_profile = get_user_profile(active_id) if active_id else {}
    if active_profile:
        cand_name = active_profile.get("full_name", "Candidate")
        headline = active_profile.get("headline", "Professional")
        loc = active_profile.get("location", "Remote")
        color = active_profile.get("avatar_color", "#2563eb")
        initials = "".join([part[0].upper() for part in cand_name.split() if part][:2]) or "U"
        st.markdown(
            f"""
            <div style="background: #ffffff; border: 1.5px solid #e2e8f0; border-radius: 10px; padding: 0.75rem 1rem; margin-bottom: 1rem; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px;">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <div style="width: 36px; height: 36px; border-radius: 50%; background: {color}; color: #ffffff; font-weight: 700; font-size: 0.9rem; display: flex; align-items: center; justify-content: center;">
                        {initials}
                    </div>
                    <div>
                        <span style="font-weight: 700; color: #0f172a; font-size: 0.95rem;">{cand_name}</span>
                        <span style="color: #64748b; font-size: 0.85rem; margin-left: 6px;">({headline} • 📍 {loc})</span>
                    </div>
                </div>
                <div style="font-size: 0.8rem; color: #166534; background: #dcfce7; padding: 3px 8px; border-radius: 6px; font-weight: 600;">
                    ✓ Dedicated Workspace Active
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("### 📝 Screen 1: Candidate Input Form & Resume Upload")
    st.markdown(
        "Upload your resume document (**PDF, Word DOCX, or Text**) or paste your work history below. "
        "The **Gemini 3.8 Flash** Agent will parse your background, extract core competencies, "
        "and synthesize recommended job search criteria."
    )

    # Feature P1-B: Multi-CV Persona Profiles & Profile Fusion
    personas = get_personas(active_id) if active_id else {}
    persona_names = list(personas.keys())
    if not persona_names:
        persona_names = ["Primary Focus"]

    p_col1, p_col2 = st.columns([2.5, 1.5], vertical_alignment="bottom")
    with p_col1:
        curr_active_persona = active_profile.get("active_persona") or persona_names[0]
        sel_idx = persona_names.index(curr_active_persona) if curr_active_persona in persona_names else 0
        selected_persona = st.selectbox(
            "🎭 Active Target Persona (P1-B):",
            options=persona_names,
            index=sel_idx,
            key="persona_selector_screen1",
            help="Switch between tailored CV personas (e.g. AI Architect vs Engineering Manager).",
        )
        if selected_persona != curr_active_persona and selected_persona in personas:
            switch_active_persona(active_id, selected_persona)
            st.toast(f"Switched to persona: {selected_persona}")
            st.rerun()

    with p_col2:
        new_persona_name = st.text_input(
            "➕ Add New Persona:",
            placeholder="e.g. Lead Architect",
            key="new_persona_input",
            help="Create a new persona profile to maintain multiple CV angles simultaneously.",
        )
        if st.button("Create Persona", key="btn_create_persona", use_container_width=True):
            if new_persona_name.strip():
                create_or_update_persona(active_id, new_persona_name.strip(), {
                    "target_role": st.session_state.get("target_role", "Target Role"),
                    "target_job_queries": st.session_state.get("target_job_queries", []),
                    "core_skills": st.session_state.get("primary_skills", []),
                    "resume_text": st.session_state.get("resume_text", ""),
                })
                switch_active_persona(active_id, new_persona_name.strip())
                st.toast(f"Created & activated persona: {new_persona_name.strip()}")
                st.rerun()

    st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

    # Initialize form version tracker for reactive widget binding
    if "form_version" not in st.session_state:
        st.session_state.form_version = 0

    fv = st.session_state.form_version

    # Tabs for Upload vs Paste
    tab_upload, tab_paste = st.tabs(["📂 Upload Resume File (.pdf, .docx, .txt)", "✍️ Paste Text / Sample Resume"])

    with tab_upload:
        uploaded_file = st.file_uploader(
            "Upload your resume document",
            type=["pdf", "docx", "txt"],
            help="Supports standard PDF, Word (.docx), and plain text documents.",
        )
        if uploaded_file is not None:
            file_key = f"parsed_file_{uploaded_file.name}_{uploaded_file.size}"
            if st.session_state.get("last_uploaded_file") != file_key:
                try:
                    with st.spinner(f"Extracting text & analyzing profile from '{uploaded_file.name}'..."):
                        extracted_text = extract_text_from_file(uploaded_file)
                        st.session_state.resume_text = extracted_text
                        st.session_state["last_uploaded_file"] = file_key

                        # Auto-fill fields from submitted CV
                        init_data = extract_initial_profile_from_text(extracted_text)
                        st.session_state.candidate_name = init_data.get("full_name") or "Candidate"
                        st.session_state.experience_level = init_data.get("experience_level") or "Senior (5+ years)"
                        st.session_state.target_job_queries = list(init_data.get("target_roles") or [])
                        if st.session_state.target_job_queries:
                            st.session_state.target_role = st.session_state.target_job_queries[0]
                        st.session_state.custom_target_role = ""
                        st.session_state.primary_skills = list(init_data.get("core_skills") or [])

                        # Target location and min salary remain blank
                        st.session_state.target_location = ""
                        st.session_state.min_salary = ""
                        st.session_state.target_companies = ""
                        st.session_state.negative_keywords = ""

                        # Increment form version and rerun to immediately re-render widgets with extracted data
                        st.session_state.form_version += 1
                        st.rerun()
                except Exception as e:
                    st.error(f"Error reading file: {e}")

    with tab_paste:
        toolbar_col1, toolbar_col2 = st.columns([1.5, 1])
        with toolbar_col1:
            if st.button("⚡ Auto-Fill Fields from Current Text", use_container_width=True, help="Extract Candidate Name, Core Competencies & Skills, and Target Queries from the text below"):
                current_text = st.session_state.get("resume_text", "")
                if current_text.strip():
                    init_data = extract_initial_profile_from_text(current_text)
                    st.session_state.candidate_name = init_data.get("full_name") or "Candidate"
                    st.session_state.experience_level = init_data.get("experience_level") or "Senior (5+ years)"
                    st.session_state.target_job_queries = list(init_data.get("target_roles") or [])
                    if st.session_state.target_job_queries:
                        st.session_state.target_role = st.session_state.target_job_queries[0]
                    st.session_state.custom_target_role = ""
                    st.session_state.primary_skills = list(init_data.get("core_skills") or [])
                    st.session_state.target_location = ""
                    st.session_state.min_salary = ""
                    st.session_state.target_companies = ""
                    st.session_state.negative_keywords = ""
                    st.session_state.form_version += 1
                    st.toast("Auto-filled Candidate Name as per Profile and Competencies as per Core Competencies & Skills!")
                    st.rerun()
                else:
                    st.warning("Please paste resume text below first.")
        with toolbar_col2:
            if st.button("✨ Load Sample Resume", use_container_width=True, help="Autofill with Alex Mercer AI Engineer sample resume"):
                st.session_state.resume_text = SAMPLE_RESUME
                # Candidate name filled as per Profile
                st.session_state.candidate_name = SAMPLE_PARSED_PROFILE.get("full_name", "Alex Mercer")
                # Primary competency focus filled as per Core Competencies & Skills
                st.session_state.primary_skills = list(SAMPLE_PARSED_PROFILE.get("core_skills", []))
                # Target job queries
                sample_queries = list(SAMPLE_PARSED_PROFILE.get("target_roles", [
                    "Senior AI / Agentic Systems Engineer",
                    "Lead Agentic Systems Architect",
                    "LLM Platform Engineer",
                    "Applied AI Research Engineer",
                ]))
                st.session_state.target_job_queries = sample_queries
                st.session_state.target_role = sample_queries[0]
                st.session_state.custom_target_role = ""
                st.session_state.experience_level = "Senior (5+ years)"
                # Target location and min salary remain blank
                st.session_state.target_location = ""
                st.session_state.min_salary = ""
                st.session_state.remote_pref = "Remote Only"
                st.session_state.target_companies = "Linear, Stripe, Databricks, Figma"
                st.session_state.negative_keywords = "Clearance, Crypto, Unpaid"
                st.session_state.form_version += 1
                st.rerun()

    # Form with widgets keyed to form_version for reactive auto-fill
    with st.form("resume_input_form"):
        # Resume input text area displaying extracted/pasted text
        resume_input = st.text_area(
            "Resume / Work History Text (Extracted or Pasted)",
            value=st.session_state.get("resume_text", ""),
            height=250,
            key=f"resume_text_area_{fv}",
            placeholder="Upload a document above or paste your resume text here...",
            help="Include your past roles, tech stack, key projects, and accomplishments.",
        )

        st.markdown("---")
        st.markdown("#### Search Preferences & Target Criteria (Auto-filled from CV)")

        col1, col2 = st.columns(2)
        with col1:
            # Candidate Name filled as per Profile
            name = st.text_input(
                "Candidate Name (as per Profile)",
                value=st.session_state.get("candidate_name", ""),
                key=f"candidate_name_input_{fv}",
                placeholder="Auto-filled as per Profile (e.g. Alex Mercer)...",
                help="Automatically filled as per Profile from your submitted CV or sample resume.",
            )

            # Target Role: Dropdown of Target Job queries + Manual Input Option
            CUSTOM_ROLE_PROMPT = "✍️ Enter custom target role manually (specify below)..."
            target_queries = st.session_state.get("target_job_queries", [])
            if not target_queries:
                dropdown_options = [
                    "Please submit CV or load sample to generate target job queries",
                    "Senior AI / Agentic Systems Engineer",
                    "Senior Product Manager",
                    "Senior Marketing Manager",
                    "Financial Analyst",
                    "Operations Manager",
                    "Software Engineer",
                    CUSTOM_ROLE_PROMPT,
                ]
            else:
                dropdown_options = list(target_queries)
                if CUSTOM_ROLE_PROMPT not in dropdown_options:
                    dropdown_options.append(CUSTOM_ROLE_PROMPT)

            current_role = st.session_state.get("target_role", "")
            role_idx = 0
            if current_role in dropdown_options:
                role_idx = dropdown_options.index(current_role)
            elif current_role and current_role != CUSTOM_ROLE_PROMPT:
                dropdown_options.insert(0, current_role)
                role_idx = 0

            target_role = st.selectbox(
                "Target Role (Select from Target Job Queries)",
                options=dropdown_options,
                index=role_idx,
                key=f"target_role_select_{fv}",
                help="Dropdown list of Target Job queries auto-populated from your submitted CV or sample resume. Choose an option, or enter a custom role below.",
            )

            manual_role = st.text_input(
                "✍️ Or Desired Target Role (Manual Input)",
                value=st.session_state.get("custom_target_role", ""),
                key=f"manual_role_input_{fv}",
                placeholder="e.g. Lead AI Systems Architect, VP of Marketing...",
                help="Enter your desired target role manually if not listed above or to specify a custom role title. If entered, this manual role will be prioritized.",
            )

            # Experience Level: Auto-filled according to submitted CV or sample resume
            current_exp = st.session_state.get("experience_level", "")
            exp_matched = match_experience_level(current_exp)
            exp_idx = EXP_LEVEL_OPTIONS.index(exp_matched) if exp_matched in EXP_LEVEL_OPTIONS else 2

            exp_level = st.selectbox(
                "Experience Level (Auto-filled)",
                options=EXP_LEVEL_OPTIONS,
                index=exp_idx,
                key=f"exp_level_select_{fv}",
                help="Auto-filled according to your submitted CV or sample resume.",
            )

        with col2:
            # Target Location: Blank and Mandatory
            location = st.text_input(
                "Target Location & Countries * (Mandatory)",
                value=st.session_state.get("target_location", ""),
                key=f"target_location_input_{fv}",
                placeholder="e.g. Germany, UK, United States, Berlin, London, Remote",
                help="Mandatory: Specify target country, city, or Remote. On-site and hybrid roles will strictly match the countries/cities specified here.",
            )

            work_mode_options = [
                "Remote Only",
                "Hybrid Preferred (Remote + Hybrid in Target Countries)",
                "Open to On-site (Remote, Hybrid & On-site in Target Countries)",
                "On-site Only (Target Countries)",
                "No Preference",
            ]
            current_mode = st.session_state.get("remote_pref", work_mode_options[0])
            mode_idx = 0
            for i, opt in enumerate(work_mode_options):
                if current_mode.lower() in opt.lower() or opt.lower() in current_mode.lower():
                    mode_idx = i
                    break

            remote_pref = st.selectbox(
                "Work Mode Preference",
                options=work_mode_options,
                index=mode_idx,
                key=f"work_mode_select_{fv}",
                help="Choose whether you want remote-only positions, or to include on-site/hybrid jobs in your target countries.",
            )

            # Desired Minimum Salary: Blank and Optional
            min_salary = st.text_input(
                "Desired Minimum Salary (Optional)",
                value=st.session_state.get("min_salary", ""),
                key=f"min_salary_input_{fv}",
                placeholder="Optional: e.g. $150,000 or €120,000 (leave blank for no restriction)",
                help="Optional: Leave blank to search all salary ranges without restriction.",
            )

        # Primary Competency Focus: Auto-filled as per Core Competencies & Skills
        current_skills = st.session_state.get("primary_skills", [])
        base_pool = [
            "Agentic AI Frameworks", "Gemini API / LLMs", "Multi-Agent Orchestration",
            "Python", "FastAPI", "Streamlit", "Docker", "PostgreSQL", "Vector Databases",
            "Project Management", "Financial Modeling", "Strategic Planning",
            "Digital Marketing", "Product Strategy", "Data Analysis", "SQL", "Cloud Platforms",
        ]
        all_skills_pool = list(dict.fromkeys(current_skills + base_pool))

        selected_skills = st.multiselect(
            "Primary Competency Focus (as per Core Competencies & Skills)",
            options=all_skills_pool,
            default=current_skills,
            key=f"skills_multiselect_{fv}",
            help="Automatically filled as per Core Competencies & Skills from your submitted CV or sample resume. You can add or remove tags as desired.",
        )

        st.markdown("---")
        st.markdown("#### 🎯 Advanced Target Filters: Dream Companies & Exclusions")

        adv_col1, adv_col2 = st.columns(2)
        with adv_col1:
            target_companies_input = st.text_input(
                "🏢 Target Dream Companies (Optional)",
                value=st.session_state.get("target_companies", ""),
                key=f"target_companies_input_{fv}",
                placeholder="e.g. Linear, Stripe, Databricks, Figma, OpenAI, Ramp",
                help="Specify priority companies separated by commas. The system dynamically queries their live Ashby, Greenhouse, Lever, and SmartRecruiters ATS job feeds.",
            )
        with adv_col2:
            negative_keywords_input = st.text_input(
                "🚫 Negative Keywords / Exclusions (Optional)",
                value=st.session_state.get("negative_keywords", ""),
                key=f"negative_keywords_input_{fv}",
                placeholder="e.g. Clearance, Crypto, Staffing Agency, C2C, Unpaid",
                help="Comma-separated terms to exclude. Any job containing these words in the title, company name, or description will be filtered out automatically.",
            )

        adv_col3, adv_col4 = st.columns(2)
        with adv_col3:
            github_input = st.text_input(
                "🐙 Public GitHub Profile / Handle (Optional - P1-A)",
                value=st.session_state.get("github_url", ""),
                key=f"github_input_{fv}",
                placeholder="e.g. github.com/username or @username",
                help="Inspects public code repositories to verify programming languages, top starred projects, and generate Code-Verified badges.",
            )
        with adv_col4:
            st.markdown("<div style='height: 1.6rem;'></div>", unsafe_allow_html=True)
            dealbreakers_active = st.checkbox(
                "⚡ Enforce Strict Hard Deal-Breakers (P2-A)",
                value=st.session_state.get("strict_dealbreakers_enabled", True),
                key=f"dealbreaker_chk_{fv}",
                help="Strictly disqualifies requisitions violating visa sponsorship, salary floor, or strict work mode.",
            )

        if dealbreakers_active:
            db_c1, db_c2, db_c3 = st.columns(3)
            with db_c1:
                req_visa = st.checkbox(
                    "Require Visa Sponsorship",
                    value=st.session_state.get("requires_visa_sponsorship", False),
                    key=f"req_visa_chk_{fv}",
                    help="Disqualifies postings explicitly stating 'No Visa Sponsorship / Citizen Only'.",
                )
            with db_c2:
                strict_mode = st.checkbox(
                    "Strict Work Mode Only",
                    value=st.session_state.get("strict_work_mode", True),
                    key=f"strict_mode_chk_{fv}",
                    help="If Remote Only, strictly excludes On-Site and Hybrid roles.",
                )
            with db_c3:
                strict_salary = st.checkbox(
                    "Strict Salary Floor",
                    value=st.session_state.get("strict_salary_floor", False),
                    key=f"strict_salary_chk_{fv}",
                    help="Disqualifies postings with stated compensation strictly below your minimum preference.",
                )
        else:
            req_visa = False
            strict_mode = False
            strict_salary = False

        st.markdown("<br>", unsafe_allow_html=True)
        submit_btn = st.form_submit_button(
            "🤖 Parse Resume with Agent & Review Profile →",
            use_container_width=True,
            type="primary",
        )

        if submit_btn:
            # 1. Validate Resume Text
            if not resume_input.strip():
                st.error("⚠️ Please upload a resume file or paste your work history before proceeding.")
                return

            # 2. Validate Mandatory Target Location
            if not location.strip():
                st.error("⚠️ 'Target Location & Countries' is mandatory. Please enter your target country, city, or 'Remote' before proceeding.")
                return

            # 3. Validate Target Role if manual option selected in dropdown but left blank
            manual_role_clean = manual_role.strip()
            if target_role == CUSTOM_ROLE_PROMPT and not manual_role_clean:
                st.error("⚠️ You selected 'Enter custom target role manually'. Please enter your desired target role title in the text field.")
                return

            selected_model = st.session_state.get("gemini_model", "Auto")
            clean_pref_model = "Auto" if "Auto" in selected_model else selected_model

            with st.spinner("🤖 ProfileAgent (Stages 1 & 2) analyzing resume structure, extracting competencies & target queries (with auto-retry)..."):
                try:
                    from src.pipeline import run_profile_stage
                    from src.schemas import ProfileAgentInput
                    profile_out = run_profile_stage(
                        ProfileAgentInput(raw_resume_text=resume_input, file_type="txt"),
                        api_key=st.session_state.get("gemini_api_key"),
                    )
                    parsed_data = profile_out.profile.to_dict()
                    status_msg = profile_out.status_message
                    st.session_state.recruiter_gap_analysis = profile_out.recruiter_gap_analysis
                except Exception:
                    parsed_data, is_live_ai, status_msg = parse_resume_with_gemini(
                        resume_input,
                        api_key=st.session_state.get("gemini_api_key"),
                        preferred_model=clean_pref_model,
                    )

            # Store in session state
            st.session_state.resume_text = resume_input
            st.session_state.parsed_profile = parsed_data
            st.session_state.parser_status = status_msg
            st.session_state.target_companies = target_companies_input.strip()
            st.session_state.negative_keywords = negative_keywords_input.strip()

            # Update session state with attributes
            # Candidate name filled as per Profile
            profile_name = parsed_data.get("full_name")
            if profile_name and profile_name != "Candidate":
                st.session_state.candidate_name = profile_name
            elif name.strip():
                st.session_state.candidate_name = name.strip()
            else:
                st.session_state.candidate_name = profile_name or "Candidate"

            # Primary competency focus filled as per Core Competencies & Skills
            profile_skills = parsed_data.get("core_skills", [])
            if profile_skills:
                st.session_state.primary_skills = profile_skills
            elif selected_skills:
                st.session_state.primary_skills = selected_skills

            # Target job queries
            gemini_queries = parsed_data.get("target_roles", [])
            if gemini_queries:
                st.session_state.target_job_queries = list(gemini_queries)
            elif not st.session_state.get("target_job_queries"):
                st.session_state.target_job_queries = [
                    "Senior AI / Agentic Systems Engineer",
                    "Senior Product Manager",
                    "Software Engineer",
                ]

            # Determine final active target role: Manual input takes precedence, then dropdown selection
            if manual_role_clean:
                final_role = manual_role_clean
                st.session_state.custom_target_role = final_role
                if final_role not in st.session_state.target_job_queries:
                    st.session_state.target_job_queries.insert(0, final_role)
            elif target_role and not target_role.startswith("Please submit") and target_role != CUSTOM_ROLE_PROMPT:
                final_role = target_role
                st.session_state.custom_target_role = ""
                if final_role not in st.session_state.target_job_queries:
                    st.session_state.target_job_queries.insert(0, final_role)
            else:
                final_role = (
                    st.session_state.target_job_queries[0]
                    if st.session_state.target_job_queries
                    else (parsed_data.get("headline") or "Target Profession")
                )
                st.session_state.custom_target_role = ""

            st.session_state.target_role = final_role
            parsed_data["headline"] = final_role
            parsed_data["target_role"] = final_role

            st.session_state.experience_level = exp_level
            st.session_state.target_location = location.strip()
            st.session_state.remote_pref = remote_pref
            st.session_state.min_salary = min_salary.strip()
            parsed_data["location"] = location.strip()
            parsed_data["target_location"] = location.strip()
            if min_salary.strip():
                parsed_data["preferred_min_salary"] = min_salary.strip()
            parsed_data["work_mode"] = remote_pref

            # Dealbreakers (P2-A)
            st.session_state.github_url = github_input.strip()
            st.session_state.strict_dealbreakers_enabled = dealbreakers_active
            st.session_state.requires_visa_sponsorship = req_visa
            st.session_state.strict_work_mode = strict_mode
            st.session_state.strict_salary_floor = strict_salary

            parsed_data["requires_visa_sponsorship"] = req_visa
            parsed_data["strict_work_mode"] = strict_mode
            parsed_data["strict_salary_floor"] = strict_salary
            parsed_data["strict_dealbreakers_enabled"] = dealbreakers_active

            # P1-A: GitHub Deep Inspection
            if github_input.strip():
                with st.spinner("🐙 GitHub Deep Inspector inspecting public repositories & verifying competencies..."):
                    gh_data = inspect_github_profile(github_input.strip())
                    st.session_state.github_summary = gh_data.get("archetype_summary", "")
                    st.session_state.github_verified_skills = gh_data.get("verified_competencies", [])
                    st.session_state.github_top_projects = gh_data.get("top_projects", [])
                    parsed_data["github_url"] = github_input.strip()
                    parsed_data["github_summary"] = gh_data.get("archetype_summary", "")
                    parsed_data["github_verified_skills"] = gh_data.get("verified_competencies", [])
                    for v_sk in gh_data.get("verified_competencies", []):
                        if v_sk not in st.session_state.primary_skills:
                            st.session_state.primary_skills.append(v_sk)

            # P1-C: Hierarchical Competency Graph
            tiers = categorize_competencies(st.session_state.primary_skills, exp_level)
            parsed_data["competency_tiers"] = tiers
            st.session_state.competency_tiers = tiers

            # P1-B: Multi-CV Persona Sync
            active_persona_key = st.session_state.get("persona_selector_screen1") or "Primary Focus"
            create_or_update_persona(active_id, active_persona_key, {
                "target_role": final_role,
                "target_job_queries": st.session_state.target_job_queries,
                "core_skills": st.session_state.primary_skills,
                "resume_text": resume_input,
                "experience_level": exp_level,
                "work_mode": remote_pref,
                "min_salary": min_salary.strip(),
                "competency_tiers": tiers,
                "github_url": github_input.strip(),
            })

            flush_session_to_user_workspace()
            go_to_screen(SCREEN_REVIEW)
