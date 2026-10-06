"""
Application Pipeline & Kanban Tracker Manager.
Handles tracking of applications through stages:
Saved -> Applied -> Interviewing -> Offer Received -> Archived.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
import streamlit as st


STAGE_SAVED = "saved"
STAGE_APPLIED = "applied"
STAGE_INTERVIEWING = "interviewing"
STAGE_OFFER = "offer"
STAGE_ARCHIVED = "archived"

STAGE_ORDER = [
    STAGE_SAVED,
    STAGE_APPLIED,
    STAGE_INTERVIEWING,
    STAGE_OFFER,
    STAGE_ARCHIVED,
]

STAGE_CONFIG: Dict[str, Dict[str, str]] = {
    STAGE_SAVED: {
        "label": "Saved / To Review",
        "icon": "📌",
        "color": "#475569",
        "bg": "#f8fafc",
        "border": "#cbd5e1",
        "badge_bg": "#f1f5f9",
    },
    STAGE_APPLIED: {
        "label": "Applied",
        "icon": "📤",
        "color": "#2563eb",
        "bg": "#eff6ff",
        "border": "#bfdbfe",
        "badge_bg": "#dbeafe",
    },
    STAGE_INTERVIEWING: {
        "label": "Interviewing",
        "icon": "💬",
        "color": "#d97706",
        "bg": "#fffbeb",
        "border": "#fde68a",
        "badge_bg": "#fef3c7",
    },
    STAGE_OFFER: {
        "label": "Offer Received",
        "icon": "🏆",
        "color": "#16a34a",
        "bg": "#f0fdf4",
        "border": "#bbf7d0",
        "badge_bg": "#dcfce7",
    },
    STAGE_ARCHIVED: {
        "label": "Archived / Inactive",
        "icon": "📁",
        "color": "#64748b",
        "bg": "#f8fafc",
        "border": "#e2e8f0",
        "badge_bg": "#f1f5f9",
    },
}


def get_pipeline() -> Dict[str, Dict[str, Any]]:
    """Return the active application pipeline dictionary from session state."""
    if "application_pipeline" not in st.session_state or not isinstance(st.session_state.application_pipeline, dict):
        st.session_state.application_pipeline = {}
    return st.session_state.application_pipeline


def add_or_update_pipeline(
    job: Dict[str, Any],
    stage: str = STAGE_SAVED,
    notes: str = "",
    interview_date: str = "",
    recruiter_contact: str = "",
    salary_offered: str = "",
    applied_date: str = "",
    **kwargs: Any,
) -> None:
    """Add a job to the application pipeline or update its existing attributes."""
    pipeline = get_pipeline()
    job_id = job.get("id") or job.get("job_id")
    if not job_id:
        return

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    auto_applied = datetime.now().strftime("%Y-%m-%d") if stage != STAGE_SAVED else ""
    applied_date_val = applied_date or auto_applied

    existing = pipeline.get(job_id, {})
    pipeline[job_id] = {
        "id": job_id,
        "job_id": job_id,
        "title": job.get("title", "Target Role"),
        "company": job.get("company", "Company"),
        "location": job.get("location", "Remote"),
        "job_type": job.get("job_type", "Full-time (Remote)"),
        "salary": job.get("salary", "Competitive"),
        "fit_score": job.get("fit_score", 85),
        "badge_color": job.get("badge_color", "#2563eb"),
        "apply_url": job.get("apply_url", "https://www.google.com/search?q=jobs"),
        "description": job.get("description", ""),
        "matched_skills": job.get("matched_skills", []),
        "key_reasons": job.get("key_reasons", []),
        "source": job.get("source", "Live ATS"),
        "stage": stage or existing.get("stage", STAGE_SAVED),
        "updated_at": now_str,
        "applied_date": applied_date_val or existing.get("applied_date", ""),
        "notes": notes or existing.get("notes", ""),
        "interview_date": interview_date or existing.get("interview_date", ""),
        "recruiter_contact": recruiter_contact or existing.get("recruiter_contact", ""),
        "salary_offered": salary_offered or existing.get("salary_offered", ""),
    }

    # Synchronize session state sets
    if "saved_jobs" in st.session_state:
        st.session_state.saved_jobs.add(job_id)
    if stage in [STAGE_APPLIED, STAGE_INTERVIEWING, STAGE_OFFER]:
        if "applied_jobs" in st.session_state:
            st.session_state.applied_jobs.add(job_id)

    try:
        from src.utils.user_manager import flush_session_to_user_workspace
        flush_session_to_user_workspace()
    except Exception:
        pass


def set_job_stage(job_id: str, new_stage: str) -> None:
    """Transition a job to a new Kanban stage and update timestamps."""
    pipeline = get_pipeline()
    if job_id in pipeline:
        pipeline[job_id]["stage"] = new_stage
        pipeline[job_id]["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        if new_stage in [STAGE_APPLIED, STAGE_INTERVIEWING, STAGE_OFFER] and not pipeline[job_id].get("applied_date"):
            pipeline[job_id]["applied_date"] = datetime.now().strftime("%Y-%m-%d")

        # Synchronize applied_jobs
        if "applied_jobs" in st.session_state:
            if new_stage in [STAGE_APPLIED, STAGE_INTERVIEWING, STAGE_OFFER]:
                st.session_state.applied_jobs.add(job_id)
            elif new_stage == STAGE_SAVED and job_id in st.session_state.applied_jobs:
                st.session_state.applied_jobs.remove(job_id)

        try:
            from src.utils.user_manager import flush_session_to_user_workspace
            flush_session_to_user_workspace()
        except Exception:
            pass


def remove_from_pipeline(job_id: str) -> None:
    """Remove a job entirely from the pipeline and saved/applied sets."""
    pipeline = get_pipeline()
    if job_id in pipeline:
        del pipeline[job_id]
    if "saved_jobs" in st.session_state and job_id in st.session_state.saved_jobs:
        st.session_state.saved_jobs.remove(job_id)
    if "applied_jobs" in st.session_state and job_id in st.session_state.applied_jobs:
        st.session_state.applied_jobs.remove(job_id)

    try:
        from src.utils.user_manager import flush_session_to_user_workspace
        flush_session_to_user_workspace()
    except Exception:
        pass


def update_job_notes(
    job_id: str,
    notes: str,
    interview_date: str = "",
    recruiter_contact: str = "",
    salary_offered: str = "",
) -> None:
    """Update notes and interview metadata for a tracked job."""
    pipeline = get_pipeline()
    if job_id in pipeline:
        pipeline[job_id]["notes"] = notes
        if interview_date is not None:
            pipeline[job_id]["interview_date"] = interview_date
        if recruiter_contact is not None:
            pipeline[job_id]["recruiter_contact"] = recruiter_contact
        if salary_offered is not None:
            pipeline[job_id]["salary_offered"] = salary_offered
        pipeline[job_id]["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")

        try:
            from src.utils.user_manager import flush_session_to_user_workspace
            flush_session_to_user_workspace()
        except Exception:
            pass


def initialize_sample_pipeline_if_empty(jobs_source: List[Dict[str, Any]]) -> None:
    """If the pipeline is empty, pre-populate with 3 jobs across stages for a clean demo."""
    pipeline = get_pipeline()
    if pipeline or not jobs_source:
        return

    # Seed 3 distinct jobs
    if len(jobs_source) >= 1:
        add_or_update_pipeline(
            jobs_source[0],
            stage=STAGE_INTERVIEWING,
            notes="Completed screening with recruiter Sarah Chen. Technical interview scheduled.",
            interview_date="Next Thursday 2:00 PM EST",
            recruiter_contact="sarah.chen@cognitiveflow.ai",
        )
    if len(jobs_source) >= 2:
        add_or_update_pipeline(
            jobs_source[1],
            stage=STAGE_APPLIED,
            notes="Tailored CV and cover letter submitted via Greenhouse ATS link.",
            applied_date=datetime.now().strftime("%Y-%m-%d"),
        )
    if len(jobs_source) >= 3:
        add_or_update_pipeline(
            jobs_source[2],
            stage=STAGE_SAVED,
            notes="High fit score for multi-agent architecture. Tailoring CV before applying.",
        )
