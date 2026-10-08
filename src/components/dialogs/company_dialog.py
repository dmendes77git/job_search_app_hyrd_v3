"""Company Intelligence Dossier Dialog component."""

import json
import streamlit as st
from src.agents.company_intelligence_agent import generate_company_dossier
from src.utils.user_manager import flush_session_to_user_workspace


@st.dialog("🏢 Company Intelligence Dossier", width="large")
def show_company_dossier_dialog(job: dict, profile: dict) -> None:
    """Render executive intelligence dossier: funding, tech stack, leadership, and interview talking points."""
    if "company_dossiers" not in st.session_state:
        st.session_state.company_dossiers = {}

    company_name = job.get("company", "Target Company").strip()
    cache_key = company_name.lower()
    job_id = job.get("id") or job.get("job_id", "job_custom")
    job_title = job.get("title", "Software Engineer")
    job_desc = job.get("description") or job.get("full_description", "")
    api_key = st.session_state.get("gemini_api_key")
    pref_model = st.session_state.get("gemini_model")

    if cache_key not in st.session_state.company_dossiers:
        with st.spinner(f"🕵️ Hyrd Agent gathering corporate intelligence on {company_name}..."):
            dossier = generate_company_dossier(
                company_name=company_name,
                job_title=job_title,
                job_description=job_desc,
                api_key=api_key,
                preferred_model=pref_model,
            )
            st.session_state.company_dossiers[cache_key] = dossier
            flush_session_to_user_workspace()
    else:
        dossier = st.session_state.company_dossiers[cache_key]

    stage_info = dossier.get("stage_and_funding", {})
    tech_info = dossier.get("tech_stack", {})
    culture_info = dossier.get("engineering_culture", {})
    leaders = dossier.get("leadership_team", [])
    talking_points = dossier.get("strategic_interview_questions", [])
    sentiment = dossier.get("culture_and_sentiment", {})

    # Header Card
    st.markdown(
        f"""<div style='background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); color: #f8fafc; border-radius: 10px; padding: 1.25rem 1.4rem; margin-bottom: 1.2rem; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);'>
            <div style='display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 10px;'>
                <div>
                    <h3 style='margin: 0; color: #ffffff; font-size: 1.4rem; font-weight: 700;'>🏢 {dossier.get('company_name', company_name)}</h3>
                    <div style='color: #94a3b8; font-size: 0.88rem; margin-top: 4px;'>Target Role: <strong>{job_title}</strong></div>
                </div>
                <div style='display: flex; gap: 8px; flex-wrap: wrap;'>
                    <span style='background: #3b82f625; color: #93c5fd; border: 1px solid #3b82f650; padding: 4px 10px; border-radius: 6px; font-size: 0.8rem; font-weight: 600;'>{stage_info.get('stage', 'Growth Stage')}</span>
                    <span style='background: #10b98125; color: #6ee7b7; border: 1px solid #10b98150; padding: 4px 10px; border-radius: 6px; font-size: 0.8rem; font-weight: 600;'>{dossier.get('ats_system', 'Ashby / Greenhouse')}</span>
                </div>
            </div>
            <div style='margin-top: 0.85rem; font-size: 0.92rem; line-height: 1.5; color: #cbd5e1;'>
                {dossier.get('summary', '')}
            </div>
        </div>""",
        unsafe_allow_html=True,
    )

    tab_biz, tab_tech, tab_cult, tab_q = st.tabs([
        "💼 Business & Funding",
        "⚙️ Tech Stack & Infra",
        "🚀 Culture & Leadership",
        "💡 Interview Talking Points",
    ])

    with tab_biz:
        b1, b2, b3, b4 = st.columns(4)
        b1.metric("Funding Stage", stage_info.get("stage", "Private"))
        b2.metric("Valuation / Cap", stage_info.get("valuation", "N/A"))
        b3.metric("Total Raised", stage_info.get("total_raised", "N/A"))
        b4.metric("Team Size", stage_info.get("headcount", "50-200"))

        st.markdown("---")
        st.markdown("#### 🏛️ Notable Venture Capital & Strategic Investors")
        investors = stage_info.get("notable_investors", [])
        if investors:
            tags_html = " ".join([f"<span style='background: #e0f2fe; color: #0369a1; border: 1px solid #bae6fd; padding: 4px 10px; border-radius: 6px; font-size: 0.85rem; font-weight: 600;'>{inv}</span>" for inv in investors])
            st.markdown(f"<div style='margin-top: 6px;'>{tags_html}</div>", unsafe_allow_html=True)
        else:
            st.write("Independent / Private")

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("#### 📈 Recent Momentum & Milestones")
        for mom in dossier.get("recent_momentum", []):
            st.markdown(f"- 🚀 {mom}")

    with tab_tech:
        st.markdown("#### 🛠️ Known Architecture & Tooling Stack")
        
        tcol1, tcol2 = st.columns(2)
        with tcol1:
            st.markdown("**Core Programming Languages:**")
            langs = tech_info.get("core_languages", [])
            l_html = " ".join([f"<span style='background: #f1f5f9; color: #334155; border: 1px solid #cbd5e1; padding: 3px 8px; border-radius: 4px; font-size: 0.82rem; font-weight: 600;'>{l}</span>" for l in langs])
            st.markdown(l_html, unsafe_allow_html=True)

            st.markdown("<br>**Frontend & Applications:**", unsafe_allow_html=True)
            front = tech_info.get("frontend_and_apps", [])
            f_html = " ".join([f"<span style='background: #fdf4ff; color: #86198f; border: 1px solid #f5d0fe; padding: 3px 8px; border-radius: 4px; font-size: 0.82rem; font-weight: 600;'>{f}</span>" for f in front])
            st.markdown(f_html, unsafe_allow_html=True)

        with tcol2:
            st.markdown("**Backend, Storage & Pipelines:**")
            back = tech_info.get("backend_and_data", [])
            bk_html = " ".join([f"<span style='background: #ecfdf5; color: #047857; border: 1px solid #a7f3d0; padding: 3px 8px; border-radius: 4px; font-size: 0.82rem; font-weight: 600;'>{b}</span>" for b in back])
            st.markdown(bk_html, unsafe_allow_html=True)

            st.markdown("<br>**Cloud Infrastructure & DevOps:**", unsafe_allow_html=True)
            cloud = tech_info.get("cloud_and_infra", [])
            c_html = " ".join([f"<span style='background: #eff6ff; color: #1d4ed8; border: 1px solid #bfdbfe; padding: 3px 8px; border-radius: 4px; font-size: 0.82rem; font-weight: 600;'>{c}</span>" for c in cloud])
            st.markdown(c_html, unsafe_allow_html=True)

        ai_tools = tech_info.get("ai_and_ml", [])
        if ai_tools:
            st.markdown("<br>**AI / ML & LLM Tooling:**", unsafe_allow_html=True)
            ai_html = " ".join([f"<span style='background: #fff7ed; color: #c2410c; border: 1px solid #fed7aa; padding: 3px 8px; border-radius: 4px; font-size: 0.82rem; font-weight: 600;'>{a}</span>" for a in ai_tools])
            st.markdown(ai_html, unsafe_allow_html=True)

    with tab_cult:
        st.markdown("#### 👥 Key Engineering & Company Leaders")
        lcols = st.columns(len(leaders) if leaders else 1)
        for idx, leader in enumerate(leaders):
            with lcols[idx]:
                st.markdown(
                    f"<div style='background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px 12px; margin-bottom: 8px;'>"
                    f"<div style='font-size: 0.8rem; color: #64748b; font-weight: 600;'>{leader.get('role', 'Executive')}</div>"
                    f"<div style='font-size: 0.95rem; color: #0f172a; font-weight: 700;'>{leader.get('name', 'N/A')}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

        st.markdown("---")
        st.markdown("#### ⚡ Engineering Operating Style")
        st.markdown(f"- 🧭 **Working Philosophy:** {culture_info.get('style', 'Autonomous, high-velocity')}")
        st.markdown(f"- 🌍 **Remote Policy:** {culture_info.get('remote_policy', 'Distributed')}")
        st.markdown(f"- 🚀 **Release Cadence:** {culture_info.get('release_frequency', 'Continuous Deployment')}")

        for h in culture_info.get("highlights", []):
            st.markdown(f"  • {h}")

        st.markdown("---")
        st.markdown(f"#### 💬 Culture & Glassdoor Sentiment ({sentiment.get('overall_rating', '4.5/5.0')})")
        col_pro, col_con = st.columns(2)
        with col_pro:
            st.markdown("<span style='color: #15803d; font-weight: 700;'>✅ Culture Strengths:</span>", unsafe_allow_html=True)
            for p in sentiment.get("pros", []):
                st.markdown(f"- {p}")
        with col_con:
            st.markdown("<span style='color: #b45309; font-weight: 700;'>⚠️ Practical Trade-offs:</span>", unsafe_allow_html=True)
            for w in sentiment.get("watch_outs", []):
                st.markdown(f"- {w}")

    with tab_q:
        st.markdown("#### 🎯 Strategic Interview Questions to Ask the Hiring Team")
        st.caption("Asking questions grounded in their specific business context signals senior acumen and separates you from 95% of candidates.")

        for idx, q in enumerate(talking_points, 1):
            st.markdown(
                f"""<div style='background: #f8fafc; border-left: 4px solid #3b82f6; border-radius: 4px; padding: 0.85rem 1rem; margin-bottom: 12px;'>
                    <div style='font-weight: 700; color: #1e3a8a; font-size: 0.88rem; margin-bottom: 4px;'>Question #{idx}</div>
                    <div style='color: #1e293b; font-size: 0.95rem; line-height: 1.45;'>"{q}"</div>
                </div>""",
                unsafe_allow_html=True,
            )

    st.markdown("---")
    d1, d2 = st.columns([1, 1])
    with d1:
        st.download_button(
            label="📥 Export Dossier (.json)",
            data=json.dumps(dossier, indent=2, default=str),
            file_name=f"Dossier_{company_name.replace(' ', '_').lower()}.json",
            mime="application/json",
            use_container_width=True,
        )
    with d2:
        if st.button("🔄 Refresh / Re-analyze Employer", key=f"refresh_dossier_{cache_key}", use_container_width=True):
            with st.spinner(f"Re-analyzing corporate intelligence for {company_name}..."):
                st.session_state.company_dossiers[cache_key] = generate_company_dossier(
                    company_name=company_name,
                    job_title=job_title,
                    job_description=job_desc,
                    api_key=api_key,
                    preferred_model=pref_model,
                )
                flush_session_to_user_workspace()
                st.toast("Company Dossier updated with latest intelligence!")
                st.rerun()
