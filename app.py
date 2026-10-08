"""
Hyrd — Autonomous Multi-Agent Career Platform (v3.0.0-dev)
Tagline: Don't just search. Get Hyrd!
Powered by google-antigravity framework and Gemini AI.
"""

from __future__ import annotations

APP_VERSION = "v3.0.0-dev"

import os
import logging
import warnings
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

# Silence noisy third-party internal SDK warnings & scraper 403 logs
logging.getLogger("google_genai.models").setLevel(logging.ERROR)
for name in ["ZipRecruiter", "Indeed", "Glassdoor", "Google", "LinkedIn", "Bayt", "BDJobs", "Naukri"]:
    lg = logging.getLogger(f"JobSpy:{name}")
    lg.setLevel(logging.CRITICAL)
    lg.propagate = False
    if not lg.handlers:
        lg.addHandler(logging.NullHandler())

import streamlit as st

# Configure page before any other Streamlit calls
st.set_page_config(
    page_title="Hyrd — Don't just search. Get Hyrd!",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling for polished card-based UI
st.markdown(
    """
    <style>
        /* Global typography & spacing */
        .main .block-container {
            padding-top: 1.8rem;
            padding-bottom: 3rem;
            max-width: 1200px;
        }

        /* Clean Card UI */
        .metric-card {
            background-color: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 10px;
            padding: 1.2rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.03);
        }

        /* App Banner */
        .app-banner {
            background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
            color: #f8fafc;
            padding: 1.25rem 1.75rem;
            border-radius: 12px;
            margin-bottom: 1.5rem;
            border: 1px solid #334155;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 1rem;
        }

        .badge-module {
            background: #2563eb;
            color: #ffffff;
            padding: 0.3rem 0.75rem;
            border-radius: 9999px;
            font-size: 0.78rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

from src.state import (
    SCREEN_REGISTRY,
    SCREEN_INPUT,
    SCREEN_REVIEW,
    SCREEN_SEARCHING,
    SCREEN_DASHBOARD,
    SCREEN_PIPELINE,
    SCREEN_INFO,
    init_session_state,
    go_to_screen,
    reset_wizard,
)
from src.components.stepper import render_stepper
from src.views.screen0_registry import render_screen0
from src.views.screen1_input import render_screen1
from src.views.screen2_review import render_screen2
from src.views.screen3_loading import render_screen3
from src.views.screen4_dashboard import render_screen4
from src.views.screen5_pipeline import render_screen5
from src.components.job_scout_dialog import show_job_scout_dialog
from src.components.dialogs.company_dialog import show_company_dossier_dialog
from src.tools.dossier_exporter import build_dossier_docx, build_dossier_pdf
from src.utils.user_manager import (
    get_active_user_id,
    get_user_profile,
    flush_session_to_user_workspace,
)
from src.pipeline import (
    MultiAgentJobPipeline,
    run_profile_stage,
    run_scout_stage,
    run_match_stage,
    run_report_stage,
    run_doc_stage,
)


def main() -> None:
    # 1. Initialize State Machine and Multi-User Session
    init_session_state()

    active_id = get_active_user_id()
    active_profile = st.session_state.get("active_user_profile")
    if not active_profile or st.session_state.get("_cached_active_id") != active_id:
        active_profile = get_user_profile(active_id) if active_id else {}
        st.session_state.active_user_profile = active_profile
        st.session_state._cached_active_id = active_id

    cand_name = active_profile.get("full_name") or st.session_state.get("candidate_name") or "Candidate"
    cand_headline = active_profile.get("headline", "Professional")
    cand_color = active_profile.get("avatar_color", "#2563eb")
    cand_initials = "".join([part[0].upper() for part in cand_name.split() if part][:2]) or "U"

    # 2. Render App Header Banner
    st.markdown(
        f"""
        <div class="app-banner">
            <div>
                <div style="display: flex; align-items: center; gap: 0.6rem; margin-bottom: 0.25rem;">
                    <span style="font-size: 1.5rem;">⚡</span>
                    <h1 style="margin: 0; font-size: 1.65rem; color: #ffffff; font-weight: 800; letter-spacing: -0.02em;">
                        Hyrd
                    </h1>
                    <span style="font-size: 0.72rem; background: rgba(59, 130, 246, 0.25); border: 1px solid rgba(147, 197, 253, 0.4); color: #93c5fd; padding: 2px 7px; border-radius: 9999px; font-weight: 600; letter-spacing: 0.03em;">{APP_VERSION}</span>
                </div>
                <div style="font-size: 0.95rem; color: #94a3b8; font-weight: 500;">
                    Don't just search. Get Hyrd!
                </div>
            </div>
            <div style="display: flex; align-items: center; gap: 0.75rem;">
                <div style="background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2); border-radius: 9999px; padding: 0.35rem 0.85rem; display: flex; align-items: center; gap: 0.5rem; color: #f8fafc; font-size: 0.85rem; font-weight: 600;">
                    <div style="width: 22px; height: 22px; border-radius: 50%; background: {cand_color}; color: #fff; font-size: 0.7rem; font-weight: 700; display: flex; align-items: center; justify-content: center;">
                        {cand_initials}
                    </div>
                    <span>{cand_name}</span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 3. Render Top Stepper
    render_stepper(current_step=st.session_state.current_screen)

    # 4. Sidebar: Active Workspace Card, Navigation & Settings
    with st.sidebar:
        # Active User Workspace Box
        st.markdown(
            f"""
            <div style="background: #f8fafc; border: 1.5px solid #cbd5e1; border-radius: 10px; padding: 0.75rem 0.85rem; margin-bottom: 0.85rem;">
                <div style="display: flex; align-items: center; gap: 0.6rem;">
                    <div style="width: 38px; height: 38px; border-radius: 50%; background: {cand_color}; color: #ffffff; font-weight: 700; font-size: 0.95rem; display: flex; align-items: center; justify-content: center; flex-shrink: 0;">
                        {cand_initials}
                    </div>
                    <div style="overflow: hidden;">
                        <div style="font-weight: 700; font-size: 0.9rem; color: #0f172a; white-space: nowrap; text-overflow: ellipsis; overflow: hidden;">{cand_name}</div>
                        <div style="font-size: 0.76rem; color: #64748b; white-space: nowrap; text-overflow: ellipsis; overflow: hidden;">{cand_headline}</div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.button("👥 Switch Candidate / Hub", key="sidebar_btn_switch_hub", use_container_width=True, help="Switch between registered candidate workspaces"):
            flush_session_to_user_workspace()
            go_to_screen(SCREEN_REGISTRY)

        if st.button("🔭 Scout & Morning Digest", key="sidebar_btn_scout", use_container_width=True, help="Open Autonomous Job Scout & Daily Intelligence Digest"):
            active_p = st.session_state.get("parsed_profile") or active_profile or get_user_profile(active_id) or {}
            show_job_scout_dialog(active_p)

        st.markdown("---")
        st.markdown("### 🎛️ Wizard State Machine")
        st.markdown(f"**Current State**: `Screen {st.session_state.current_screen}`")
        st.markdown(f"**Screen Name**: `{SCREEN_INFO[st.session_state.current_screen]['title']}`")

        st.markdown("---")
        st.markdown("#### ⚡ Quick Jump")
        for s_id, s_info in SCREEN_INFO.items():
            is_curr = s_id == st.session_state.current_screen
            label = f"{'👉 ' if is_curr else ''}Screen {s_id}: {s_info['title']}"
            if st.button(label, key=f"nav_btn_{s_id}", use_container_width=True, disabled=is_curr):
                flush_session_to_user_workspace()
                go_to_screen(s_id)

        st.markdown("---")
        if st.button("🔄 Reset Current Search", use_container_width=True, help="Reset search results while keeping this user's profile and pipeline intact"):
            reset_wizard()

        with st.expander("🔑 Gemini API Settings", expanded=False):
            current_key = st.session_state.get("gemini_api_key") or os.environ.get("GEMINI_API_KEY", "")
            entered_key = st.text_input(
                "Gemini API Key",
                value=current_key,
                type="password",
                placeholder="AIzaSy...",
                help="Set your Google Gemini API key to activate live Gemini AI reasoning.",
            )
            if entered_key != current_key:
                st.session_state.gemini_api_key = entered_key.strip()
                os.environ["GEMINI_API_KEY"] = entered_key.strip()
                st.toast("Gemini API key updated!")

            # Dynamic model options
            discovered = st.session_state.get("discovered_models", [])
            base_options = ["Auto (Dynamic Discovery & Smart Cascade)"]
            if discovered:
                model_options = base_options + discovered
            else:
                model_options = base_options + [
                    "gemini-2.0-flash",
                    "gemini-2.5-flash",
                    "gemini-3.8-flash",
                    "gemini-1.5-flash",
                ]

            current_model = st.session_state.get("gemini_model", model_options[0])
            idx = model_options.index(current_model) if current_model in model_options else 0
            selected_model = st.selectbox(
                "Model Strategy",
                options=model_options,
                index=idx,
                help="Auto dynamically fetches authorized models for your key and automatically handles 503 capacity failovers.",
            )
            st.session_state.gemini_model = selected_model

            if entered_key.strip():
                col_test, col_save = st.columns([1, 1])
                with col_test:
                    if st.button("🔍 Test Key", use_container_width=True, help="Verify key and query authorized models from Google"):
                        try:
                            from google import genai
                            client = genai.Client(api_key=entered_key.strip())
                            found = []
                            for m in client.models.list():
                                acts = getattr(m, "supported_actions", []) or []
                                if "generateContent" in acts:
                                    clean_m = m.name.replace("models/", "")
                                    if not any(x in clean_m.lower() for x in ["embed", "tts", "image", "live", "transcribe", "banana"]):
                                        found.append(clean_m)
                            if found:
                                st.session_state.discovered_models = found
                                st.success(f"✓ Valid key! {len(found)} models authorized: {', '.join(found[:3])}...")
                            else:
                                st.warning("Key accepted, but no generateContent models returned.")
                        except Exception as test_err:
                            st.error(f"Key test failed: {str(test_err)[:120]}")

                with col_save:
                    if st.button("💾 Save to .env", use_container_width=True, help="Save to local .env so you don't need to retype it"):
                        env_path = os.path.join(os.path.dirname(__file__), ".env")
                        with open(env_path, "w", encoding="utf-8") as f:
                            f.write(f"GEMINI_API_KEY={entered_key.strip()}\n")
                        st.toast("Saved GEMINI_API_KEY to local .env file!")

            st.caption(
                "⚡ **Dynamic Discovery & Resilience**: Automatically queries your account's authorized endpoints and retries with backoff on 503 capacity spikes."
            )

        with st.expander("☁️ Apify Cloud Scraper Settings", expanded=False):
            curr_apify = st.session_state.get("apify_api_token") or os.environ.get("APIFY_API_TOKEN", "")
            entered_apify = st.text_input(
                "Apify API Token (Optional)",
                value=curr_apify,
                type="password",
                placeholder="apify_api_...",
                help="Optional: Enter your Apify API Token to run cloud Apify Actors (LinkedIn/Indeed scrapers). Leave blank to use local JobSpy and direct ATS scrapers.",
            )
            if entered_apify != curr_apify:
                st.session_state.apify_api_token = entered_apify.strip()
                os.environ["APIFY_API_TOKEN"] = entered_apify.strip()
                st.toast("Apify API Token updated!")
            st.caption("ℹ️ When blank, Hyrd uses JobSpy (Indeed, Google Jobs, ZipRecruiter) & direct ATS APIs (Ashby, Greenhouse, Lever, SmartRecruiters) without requiring Apify tokens.")

        with st.expander("🛠️ Session State Inspector", expanded=False):
            st.json(
                {
                    "current_screen": st.session_state.current_screen,
                    "candidate_name": st.session_state.get("candidate_name"),
                    "target_role": st.session_state.get("target_role"),
                    "target_job_queries": st.session_state.get("target_job_queries"),
                    "target_location": st.session_state.get("target_location"),
                    "experience_level": st.session_state.get("experience_level"),
                    "primary_skills": st.session_state.get("primary_skills"),
                    "remote_pref": st.session_state.get("remote_pref"),
                    "min_salary": st.session_state.get("min_salary"),
                    "resume_chars": len(st.session_state.get("resume_text", "")),
                    "scrape_completed": st.session_state.get("scrape_completed", False),
                    "saved_jobs_count": len(st.session_state.get("saved_jobs", set())),
                    "has_gemini_key": bool(st.session_state.get("gemini_api_key") or os.environ.get("GEMINI_API_KEY")),
                }
            )

        st.markdown(
            """
            ---
            <div style="font-size: 0.78rem; color: #64748b;">
                <strong>google-antigravity Pipeline Active:</strong><br>
                • ProfileAgent (Stages 1 & 2 Intake & Audit)<br>
                • ScoutAgent (Stage 3 Multi-Source Crawlers)<br>
                • MatchAgent (Stages 4 & 5 Semantic Scoring)<br>
                • ReportAgent (Stage 6 Morning Intelligence)<br>
                • DocAgent (On-Demand ATS CV & Cover Letter)
            </div>
            """,
            unsafe_allow_html=True,
        )

    # 5. Screen Router / State Machine Dispatcher
    current_screen = st.session_state.current_screen

    if current_screen == SCREEN_REGISTRY:
        render_screen0()
    elif current_screen == SCREEN_INPUT:
        render_screen1()
    elif current_screen == SCREEN_REVIEW:
        render_screen2()
    elif current_screen == SCREEN_SEARCHING:
        render_screen3()
    elif current_screen == SCREEN_DASHBOARD:
        render_screen4()
    elif current_screen == SCREEN_PIPELINE:
        render_screen5()
    else:
        st.session_state.current_screen = SCREEN_REGISTRY
        render_screen0()


if __name__ == "__main__":
    main()
