"""
Session State Manager and Navigation Machine for Agentic AI Job Search.
"""

from typing import Any, Dict
import streamlit as st

# Screen step definitions
SCREEN_REGISTRY = 0
SCREEN_INPUT = 1
SCREEN_REVIEW = 2
SCREEN_SEARCHING = 3
SCREEN_DASHBOARD = 4
SCREEN_PIPELINE = 5

SCREEN_INFO = {
    SCREEN_REGISTRY: {
        "title": "User Registry",
        "subtitle": "Manage & switch candidate workspaces",
        "icon": "👤",
        "step_num": 0,
    },
    SCREEN_INPUT: {
        "title": "Input Profile",
        "subtitle": "Provide your resume & job preferences",
        "icon": "📝",
        "step_num": 1,
    },
    SCREEN_REVIEW: {
        "title": "Review Profile",
        "subtitle": "Verify extracted skills & search criteria",
        "icon": "🔍",
        "step_num": 2,
    },
    SCREEN_SEARCHING: {
        "title": "Agentic Search",
        "subtitle": "Antigravity agents scraping & matching roles",
        "icon": "⚡",
        "step_num": 3,
    },
    SCREEN_DASHBOARD: {
        "title": "Job Dashboard",
        "subtitle": "Ranked matches, fit scores & recommendations",
        "icon": "📊",
        "step_num": 4,
    },
    SCREEN_PIPELINE: {
        "title": "Application Kanban",
        "subtitle": "Track applications, stages & tailored assets",
        "icon": "📋",
        "step_num": 5,
    },
}


def init_session_state() -> None:
    """Initialize all session state keys with sensible defaults and load active user workspace."""
    from src.utils.user_manager import get_active_user_id, load_user_into_session

    defaults: Dict[str, Any] = {
        "current_screen": SCREEN_REGISTRY,
        "active_user_id": "",
        "resume_text": "",
        "candidate_name": "",
        "target_role": "",
        "custom_target_role": "",
        "target_job_queries": [],
        "target_location": "",
        "experience_level": "",
        "remote_pref": "Remote Only",
        "min_salary": "",
        "primary_skills": [],
        "target_companies": "",
        "negative_keywords": "",
        "parsed_profile": None,
        "scrape_progress": 0,
        "scrape_completed": False,
        "saved_jobs": set(),
        "applied_jobs": set(),
        "application_pipeline": {},
        "customized_cvs": {},
        "customized_cover_letters": {},
        "interview_prep_packs": {},
        "outreach_campaigns": {},
        "gemini_api_key": "",
        "apify_api_token": "",
        "parser_status": "",
        "discovered_jobs": [],
        "total_scraped_count": 0,
        "live_scrape_logs": [],
    }

    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

    # Load active user profile and dedicated workspace if not already loaded
    if not st.session_state.active_user_id or st.session_state.parsed_profile is None:
        active_id = get_active_user_id()
        if active_id:
            load_user_into_session(active_id)


def go_to_screen(screen_num: int) -> None:
    """Transition to the specified screen and trigger a rerun."""
    if screen_num in SCREEN_INFO:
        st.session_state.current_screen = screen_num
        st.rerun()


def reset_wizard() -> None:
    """Reset the wizard flow back to Screen 1 while preserving the active user's dedicated profile."""
    from src.utils.user_manager import get_active_user_id, load_user_into_session

    st.session_state.current_screen = SCREEN_INPUT
    st.session_state.scrape_progress = 0
    st.session_state.scrape_completed = False
    st.session_state.discovered_jobs = []
    st.session_state.total_scraped_count = 0
    st.session_state.live_scrape_logs = []
    active_id = get_active_user_id()
    if active_id:
        load_user_into_session(active_id)
    st.rerun()
