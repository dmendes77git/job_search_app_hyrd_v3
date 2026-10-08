"""
Multi-User Profile Registry & Workspace Isolation Manager.
Provides persistent storage, profile management, and dedicated workspace isolation
for multiple candidate accounts across the application.
"""

from datetime import date, datetime
from enum import Enum
import json
import logging
import os
from pathlib import Path
import re
import shutil
from typing import Any, Dict, List, Optional, Tuple
import uuid
import streamlit as st


BASE_DATA_DIR = Path("data/users")
REGISTRY_FILE = BASE_DATA_DIR / "registry.json"

AVATAR_COLORS = {
    "#2563eb": "🔵 Royal Blue",
    "#7c3aed": "🟣 Electric Purple",
    "#059669": "🟢 Emerald Green",
    "#d97706": "🟠 Warm Amber",
    "#dc2626": "🔴 Crimson Red",
    "#0891b2": "🩵 Ocean Cyan",
    "#4f46e5": "🔷 Deep Indigo",
    "#be123c": "🌺 Rose Magenta",
    "#0284c7": "🌐 Sky Blue",
    "#0f172a": "⚫ Slate Charcoal",
}

AVATAR_PALETTE = list(AVATAR_COLORS.keys())


def make_json_serializable(obj: Any) -> Any:
    """
    Recursively convert datetime, date, set, UUID, Enum, Path, and custom models
    to clean JSON-serializable primitives.
    """
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, uuid.UUID):
        return str(obj)
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, (set, list, tuple)):
        return [make_json_serializable(item) for item in obj]
    if isinstance(obj, dict):
        return {str(k): make_json_serializable(v) for k, v in obj.items()}
    if hasattr(obj, "model_dump"):
        try:
            return make_json_serializable(obj.model_dump(mode="json"))
        except Exception:
            return make_json_serializable(obj.model_dump())
    if hasattr(obj, "to_dict"):
        return make_json_serializable(obj.to_dict())
    if hasattr(obj, "dict"):
        return make_json_serializable(obj.dict())
    return str(obj)


def _ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_registry() -> Dict[str, Any]:
    """Retrieve the global user registry index."""
    _ensure_dir(BASE_DATA_DIR)
    if not REGISTRY_FILE.exists():
        _create_default_registry()
    try:
        with open(REGISTRY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logging.warning(f"Could not read user registry ({e}). Resetting registry.")
        return _create_default_registry()


def save_registry(registry_data: Dict[str, Any]) -> None:
    """Save the global user registry index."""
    _ensure_dir(BASE_DATA_DIR)
    clean_reg = make_json_serializable(registry_data)
    with open(REGISTRY_FILE, "w", encoding="utf-8") as f:
        json.dump(clean_reg, f, indent=2, ensure_ascii=False, default=str)


def get_all_users() -> List[Dict[str, Any]]:
    """Return a list of user summary dictionaries."""
    reg = get_registry()
    users = list(reg.get("users", {}).values())
    users.sort(key=lambda u: u.get("name", "").lower())
    return users


def get_active_user_id() -> str:
    """Get the currently active user ID from session state or registry."""
    if "active_user_id" in st.session_state and st.session_state.active_user_id:
        return st.session_state.active_user_id
    reg = get_registry()
    active_id = reg.get("active_user_id", "")
    if active_id and active_id in reg.get("users", {}):
        st.session_state.active_user_id = active_id
        return active_id
    users = list(reg.get("users", {}).keys())
    if users:
        active_id = users[0]
        st.session_state.active_user_id = active_id
        return active_id
    return ""


def get_user_dir(user_id: str, create: bool = True) -> Path:
    """Return directory path for a specific user's data."""
    p = BASE_DATA_DIR / user_id
    if create:
        return _ensure_dir(p)
    return p


def get_user_profile(user_id: str) -> Dict[str, Any]:
    """Load the full LinkedIn-like profile data for a specific user."""
    p_path = BASE_DATA_DIR / user_id / "profile.json"
    if p_path.exists():
        try:
            with open(p_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Error loading profile for {user_id}: {e}")
    return {}


def save_user_profile(user_id: str, profile_data: Dict[str, Any]) -> None:
    """Save full profile data and update global registry summary."""
    udir = get_user_dir(user_id, create=True)
    p_path = udir / "profile.json"
    clean_profile = make_json_serializable(profile_data)
    with open(p_path, "w", encoding="utf-8") as f:
        json.dump(clean_profile, f, indent=2, ensure_ascii=False, default=str)

    # Update summary in registry
    reg = get_registry()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    user_name = profile_data.get("full_name") or "Unnamed Candidate"
    headline = profile_data.get("headline") or "Professional"
    loc = profile_data.get("location") or "Remote"
    color = profile_data.get("avatar_color") or AVATAR_PALETTE[0]

    if "users" not in reg:
        reg["users"] = {}

    reg["users"][user_id] = {
        "id": user_id,
        "name": user_name,
        "headline": headline,
        "location": loc,
        "email": profile_data.get("email", ""),
        "avatar_color": color,
        "years_experience": profile_data.get("years_experience") or profile_data.get("years_of_experience", ""),
        "target_role": profile_data.get("target_role", ""),
        "updated_at": now_str,
    }
    save_registry(reg)


def get_user_workspace(user_id: str) -> Dict[str, Any]:
    """Load the user's dedicated saved area / workspace."""
    w_path = BASE_DATA_DIR / user_id / "workspace.json"
    if w_path.exists():
        try:
            with open(w_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Error loading workspace for {user_id}: {e}")
    return {
        "application_pipeline": {},
        "saved_jobs": [],
        "applied_jobs": [],
        "customized_cvs": {},
        "customized_cover_letters": {},
        "interview_prep_packs": {},
        "outreach_campaigns": {},
        "discovered_jobs": [],
        "search_history": [],
    }


def save_user_workspace(user_id: str, workspace_data: Dict[str, Any]) -> None:
    """Save the user's dedicated workspace state to disk."""
    udir = get_user_dir(user_id)
    w_path = udir / "workspace.json"
    clean_workspace = make_json_serializable(workspace_data)

    with open(w_path, "w", encoding="utf-8") as f:
        json.dump(clean_workspace, f, indent=2, ensure_ascii=False, default=str)


def create_user(profile_data: Dict[str, Any], initial_workspace: Optional[Dict[str, Any]] = None) -> str:
    """
    Register a new candidate profile and initialize their dedicated workspace.
    Returns the newly created user_id.
    """
    raw_name = profile_data.get("full_name", "candidate").strip().lower()
    clean_slug = re.sub(r"[^\w]", "_", raw_name)[:20].strip("_") or "user"
    base_id = f"usr_{clean_slug}"
    user_id = base_id

    reg = get_registry()
    counter = 1
    while user_id in reg.get("users", {}):
        user_id = f"{base_id}_{counter}"
        counter += 1

    profile_data["id"] = user_id
    if not profile_data.get("avatar_color"):
        idx = len(reg.get("users", {})) % len(AVATAR_PALETTE)
        profile_data["avatar_color"] = AVATAR_PALETTE[idx]

    save_user_profile(user_id, profile_data)
    save_user_workspace(user_id, initial_workspace or {
        "application_pipeline": {},
        "saved_jobs": [],
        "applied_jobs": [],
        "customized_cvs": {},
        "customized_cover_letters": {},
        "interview_prep_packs": {},
        "outreach_campaigns": {},
        "discovered_jobs": [],
    })

    # Re-fetch latest registry to include the newly saved user profile and set as active
    reg = get_registry()
    reg["active_user_id"] = user_id
    save_registry(reg)
    try:
        st.session_state.active_user_id = user_id
    except Exception:
        pass
    return user_id


def delete_user(user_id: str) -> bool:
    """Delete a user account and purge their dedicated workspace folder."""
    reg = get_registry()
    if user_id not in reg.get("users", {}):
        return False

    del reg["users"][user_id]
    udir = BASE_DATA_DIR / user_id
    if udir.exists() and udir.is_dir():
        shutil.rmtree(udir, ignore_errors=True)

    if reg.get("active_user_id") == user_id:
        remaining = list(reg.get("users", {}).keys())
        reg["active_user_id"] = remaining[0] if remaining else ""
        st.session_state.active_user_id = reg["active_user_id"]

    save_registry(reg)
    return True


def load_user_into_session(user_id: str) -> None:
    """
    Load a candidate's complete profile and dedicated workspace into Streamlit session state.
    Isolates each candidate's applications, tailored CVs, prep packs, and pipeline.
    """
    if not user_id:
        return

    profile = get_user_profile(user_id)
    workspace = get_user_workspace(user_id)

    st.session_state.active_user_id = user_id

    # Populate profile fields
    st.session_state.candidate_name = profile.get("full_name", "")
    st.session_state.target_role = profile.get("target_role", "")
    st.session_state.custom_target_role = profile.get("target_role", "")
    st.session_state.target_job_queries = profile.get("target_roles", [profile.get("target_role", "")])
    st.session_state.target_location = profile.get("location", "")
    st.session_state.experience_level = profile.get("seniority_level", "Senior (5+ years)")
    st.session_state.remote_pref = profile.get("remote_pref", "Remote Only")
    st.session_state.min_salary = profile.get("min_salary", "$140,000")
    st.session_state.target_companies = profile.get("target_companies", "")
    st.session_state.negative_keywords = profile.get("negative_keywords", "")
    st.session_state.primary_skills = profile.get("core_skills", [])
    st.session_state.resume_text = profile.get("resume_text", "")
    st.session_state.parsed_profile = profile
    st.session_state.candidate_profile = profile

    # Populate workspace fields
    st.session_state.application_pipeline = workspace.get("application_pipeline", {})
    raw_saved = workspace.get("saved_jobs", [])
    st.session_state.saved_jobs = {
        item if isinstance(item, str) else item.get("id", str(item)) for item in raw_saved
    }
    raw_applied = workspace.get("applied_jobs", [])
    st.session_state.applied_jobs = {
        item if isinstance(item, str) else item.get("id", str(item)) for item in raw_applied
    }
    st.session_state.customized_cvs = workspace.get("customized_cvs", {})
    st.session_state.customized_cover_letters = workspace.get("customized_cover_letters", {})
    st.session_state.interview_prep_packs = workspace.get("interview_prep_packs", {})
    st.session_state.outreach_campaigns = workspace.get("outreach_campaigns", {})
    st.session_state.discovered_jobs = workspace.get("discovered_jobs", [])
    st.session_state.total_scraped_count = len(st.session_state.discovered_jobs)
    st.session_state.company_dossiers = workspace.get("company_dossiers", {})
    st.session_state.job_scout_config = workspace.get("job_scout_config", {})
    st.session_state.job_scout_digests = workspace.get("job_scout_digests", [])

    # Persist active user in registry
    reg = get_registry()
    reg["active_user_id"] = user_id
    save_registry(reg)


def flush_session_to_user_workspace() -> None:
    """Save active session state changes back into the user's dedicated workspace on disk."""
    user_id = st.session_state.get("active_user_id")
    if not user_id:
        return

    raw_saved = st.session_state.get("saved_jobs", set())
    clean_saved = [item if isinstance(item, str) else item.get("id", str(item)) for item in raw_saved]
    raw_applied = st.session_state.get("applied_jobs", set())
    clean_applied = [item if isinstance(item, str) else item.get("id", str(item)) for item in raw_applied]

    workspace_data = {
        "application_pipeline": st.session_state.get("application_pipeline", {}),
        "saved_jobs": clean_saved,
        "applied_jobs": clean_applied,
        "customized_cvs": st.session_state.get("customized_cvs", {}),
        "customized_cover_letters": st.session_state.get("customized_cover_letters", {}),
        "interview_prep_packs": st.session_state.get("interview_prep_packs", {}),
        "outreach_campaigns": st.session_state.get("outreach_campaigns", {}),
        "discovered_jobs": st.session_state.get("discovered_jobs", []),
        "company_dossiers": st.session_state.get("company_dossiers", {}),
        "job_scout_config": st.session_state.get("job_scout_config", {}),
        "job_scout_digests": st.session_state.get("job_scout_digests", []),
    }
    save_user_workspace(user_id, workspace_data)

    # Also update profile if user modified basic criteria on screens
    profile = get_user_profile(user_id)
    if profile:
        modified = False
        if st.session_state.get("candidate_name") and st.session_state.candidate_name != profile.get("full_name"):
            profile["full_name"] = st.session_state.candidate_name
            modified = True
        if st.session_state.get("target_role") and st.session_state.target_role != profile.get("target_role"):
            profile["target_role"] = st.session_state.target_role
            modified = True
        if st.session_state.get("target_companies") != profile.get("target_companies"):
            profile["target_companies"] = st.session_state.get("target_companies", "")
            modified = True
        if st.session_state.get("negative_keywords") != profile.get("negative_keywords"):
            profile["negative_keywords"] = st.session_state.get("negative_keywords", "")
            modified = True
        if modified:
            save_user_profile(user_id, profile)


def _create_default_registry() -> Dict[str, Any]:
    """Initialize default demo profiles (Alex Mercer & Elena Rostova) for instant multi-user testing."""
    _ensure_dir(BASE_DATA_DIR)

    alex_profile = {
        "id": "usr_alex_mercer",
        "full_name": "Alex Mercer",
        "email": "alex.mercer@example.com",
        "phone": "+1 (555) 019-2834",
        "location": "San Francisco, CA",
        "headline": "Senior AI & Distributed Systems Engineer",
        "industry": "Artificial Intelligence & Cloud Infrastructure",
        "avatar_color": "#2563eb",
        "seniority_level": "Senior (5+ years)",
        "years_of_experience": "7 years",
        "summary": "Senior AI & Distributed Systems Engineer with 7+ years building enterprise multi-agent swarms, RAG architectures, and high-throughput Python/FastAPI microservices. Specialized in Gemini API, LangChain, Kubernetes, and real-time inference optimization.",
        "core_skills": [
            "Python", "FastAPI", "Docker", "Kubernetes", "LLMs", "RAG", "LangChain",
            "PostgreSQL", "Google Cloud", "Distributed Systems", "CI/CD", "Redis"
        ],
        "experience_highlights": [
            "Architected enterprise multi-agent research pipelines handling 2.5M+ requests/month with 99.95% uptime.",
            "Engineered hybrid RAG retrieval pipeline with Qdrant vector database, reducing document search latency by 45%."
        ],
        "experience": [
            {
                "role": "Lead AI Platform Engineer",
                "company": "Apex Autonomous Labs",
                "start_date": "2022",
                "end_date": "Present",
                "location": "San Francisco, CA (Remote)",
                "bullet_points": [
                    "Designed scalable multi-agent AI pipeline using Python and LangChain, improving throughput by 65%.",
                    "Deployed containerized RAG service on Google Cloud Run and Kubernetes, handling 15k req/sec."
                ]
            },
            {
                "role": "Senior Software Engineer",
                "company": "DataScale Systems",
                "start_date": "2019",
                "end_date": "2022",
                "location": "San Francisco, CA",
                "bullet_points": [
                    "Built distributed ETL pipelines processing 10TB+ daily telemetry with Python and PostgreSQL.",
                    "Reduced p99 API latency from 240ms to 45ms through asynchronous caching and query optimization."
                ]
            }
        ],
        "education": [
            {
                "degree": "B.S. in Computer Science",
                "institution": "University of California, Berkeley",
                "year": "2019"
            }
        ],
        "certifications": [
            "Google Cloud Professional Machine Learning Engineer",
            "CKA: Certified Kubernetes Administrator"
        ],
        "target_role": "Senior AI Software Engineer",
        "target_roles": ["Senior AI Software Engineer", "Staff Machine Learning Engineer", "Lead AI Infrastructure Engineer"],
        "remote_pref": "Remote Only",
        "min_salary": "$160,000",
        "target_companies": "Linear, Stripe, Databricks, OpenAI, Anthropic, Figma",
        "negative_keywords": "Clearance, Crypto, Staffing Agency, C2C, Unpaid",
        "linkedin": "https://linkedin.com/in/alex-mercer-ai",
        "github": "https://github.com/alex-mercer",
        "portfolio": "https://alexmercer.dev",
        "resume_text": "Alex Mercer\nSan Francisco, CA • +1 (555) 019-2834 • alex.mercer@example.com\nSenior AI & Distributed Systems Engineer\nSkills: Python, FastAPI, Docker, Kubernetes, LLMs, RAG, LangChain, PostgreSQL, GCP.\nLead AI Platform Engineer at Apex Autonomous Labs (2022-Present).",
    }

    elena_profile = {
        "id": "usr_elena_rostova",
        "full_name": "Elena Rostova",
        "email": "elena.rostova@example.com",
        "phone": "+1 (555) 048-9122",
        "location": "New York, NY",
        "headline": "Lead Product Manager — AI & Enterprise SaaS",
        "industry": "Enterprise Software & Product Strategy",
        "avatar_color": "#7c3aed",
        "seniority_level": "Staff / Principal / Lead (8+ years)",
        "years_of_experience": "9 years",
        "summary": "Data-driven Lead Product Manager with 9+ years steering 0-to-1 enterprise B2B SaaS platforms and generative AI product roadmaps. Expert in user research, OKR execution, cross-functional leadership, and go-to-market strategies.",
        "core_skills": [
            "Product Management", "AI Product Strategy", "Roadmapping", "User Research",
            "Go-To-Market (GTM)", "Cross-Functional Leadership", "OKRs & KPIs", "Data Analytics", "SQL", "Agile/Scrum"
        ],
        "experience_highlights": [
            "Scaled AI-assisted SaaS workflow from zero to $8.5M ARR in 18 months with 120k active enterprise seats.",
            "Spearheaded enterprise customer discovery across Fortune 500 accounts, achieving a 94% retention rate."
        ],
        "experience": [
            {
                "role": "Lead Product Manager",
                "company": "Vanguard Cognitive Tech",
                "start_date": "2021",
                "end_date": "Present",
                "location": "New York, NY (Hybrid)",
                "bullet_points": [
                    "Defined 2-year product roadmap for generative AI assistant, resulting in 3.4x user adoption.",
                    "Led cross-functional team of 14 engineers, 3 designers, and data scientists across 3 sprints."
                ]
            }
        ],
        "education": [
            {
                "degree": "M.B.A. in Technology Strategy",
                "institution": "Columbia Business School",
                "year": "2018"
            },
            {
                "degree": "B.A. in Economics",
                "institution": "New York University",
                "year": "2015"
            }
        ],
        "certifications": [
            "Certified Scrum Product Owner (CSPO)",
            "Pragmatic Institute Certified (PMC-III)"
        ],
        "target_role": "Lead Product Manager",
        "target_roles": ["Lead Product Manager", "Principal Product Manager", "Director of Product"],
        "remote_pref": "Hybrid",
        "min_salary": "$175,000",
        "target_companies": "Notion, Figma, Slack, Stripe, Airtable, Miro",
        "negative_keywords": "Contract, Offshore, Relocation Required",
        "linkedin": "https://linkedin.com/in/elena-rostova-pm",
        "github": "",
        "portfolio": "https://elenarostova.product",
        "resume_text": "Elena Rostova\nNew York, NY • +1 (555) 048-9122 • elena.rostova@example.com\nLead Product Manager — AI & Enterprise SaaS\nExperience: Lead Product Manager at Vanguard Cognitive Tech (2021-Present).",
    }

    # Save both profiles and workspaces
    _ensure_dir(BASE_DATA_DIR / "usr_alex_mercer")
    _ensure_dir(BASE_DATA_DIR / "usr_elena_rostova")

    with open(BASE_DATA_DIR / "usr_alex_mercer" / "profile.json", "w", encoding="utf-8") as f:
        json.dump(alex_profile, f, indent=2, ensure_ascii=False, default=str)
    with open(BASE_DATA_DIR / "usr_alex_mercer" / "workspace.json", "w", encoding="utf-8") as f:
        json.dump({
            "application_pipeline": {},
            "saved_jobs": [],
            "applied_jobs": [],
            "customized_cvs": {},
            "customized_cover_letters": {},
            "interview_prep_packs": {},
            "outreach_campaigns": {},
            "discovered_jobs": [],
        }, f, indent=2, default=str)

    with open(BASE_DATA_DIR / "usr_elena_rostova" / "profile.json", "w", encoding="utf-8") as f:
        json.dump(elena_profile, f, indent=2, ensure_ascii=False, default=str)
    with open(BASE_DATA_DIR / "usr_elena_rostova" / "workspace.json", "w", encoding="utf-8") as f:
        json.dump({
            "application_pipeline": {},
            "saved_jobs": [],
            "applied_jobs": [],
            "customized_cvs": {},
            "customized_cover_letters": {},
            "interview_prep_packs": {},
            "outreach_campaigns": {},
            "discovered_jobs": [],
        }, f, indent=2, default=str)

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    registry_data = {
        "active_user_id": "usr_alex_mercer",
        "created_at": now_str,
        "users": {
            "usr_alex_mercer": {
                "id": "usr_alex_mercer",
                "name": "Alex Mercer",
                "headline": "Senior AI & Distributed Systems Engineer",
                "location": "San Francisco, CA",
                "email": "alex.mercer@example.com",
                "avatar_color": "#2563eb",
                "years_experience": "7 years",
                "target_role": "Senior AI Software Engineer",
                "updated_at": now_str,
            },
            "usr_elena_rostova": {
                "id": "usr_elena_rostova",
                "name": "Elena Rostova",
                "headline": "Lead Product Manager — AI & Enterprise SaaS",
                "location": "New York, NY",
                "email": "elena.rostova@example.com",
                "avatar_color": "#7c3aed",
                "years_experience": "9 years",
                "target_role": "Lead Product Manager",
                "updated_at": now_str,
            }
        }
    }

    with open(REGISTRY_FILE, "w", encoding="utf-8") as f:
        json.dump(registry_data, f, indent=2, ensure_ascii=False, default=str)

    return registry_data


# ---------------------------------------------------------
# Feature P1-B: Multi-CV Persona Profiles & Profile Fusion
# ---------------------------------------------------------

def get_personas(user_id: str) -> Dict[str, Any]:
    """Retrieve all candidate personas stored for the specified user."""
    profile = get_user_profile(user_id)
    return profile.get("personas", {})


def create_or_update_persona(user_id: str, persona_name: str, persona_data: Dict[str, Any]) -> None:
    """Store or update a specialized candidate persona in the candidate's workspace profile."""
    profile = get_user_profile(user_id)
    if "personas" not in profile:
        profile["personas"] = {}

    clean_name = persona_name.strip()
    if not clean_name:
        clean_name = "Primary Focus"

    persona_data["name"] = clean_name
    persona_data["updated_at"] = datetime.now().isoformat()
    profile["personas"][clean_name] = persona_data
    if not profile.get("active_persona"):
        profile["active_persona"] = clean_name

    save_user_profile(user_id, profile)


def switch_active_persona(user_id: str, persona_name: str) -> Dict[str, Any]:
    """
    Switch active candidate persona and populate Streamlit session state.
    Returns the loaded persona dictionary.
    """
    profile = get_user_profile(user_id)
    personas = profile.get("personas", {})
    if persona_name not in personas:
        # Default or fallback persona
        return {}

    target_persona = personas[persona_name]
    profile["active_persona"] = persona_name
    save_user_profile(user_id, profile)

    try:
        # Update session state with persona-specific attributes
        if target_persona.get("target_role"):
            st.session_state.target_role = target_persona["target_role"]
            st.session_state.custom_target_role = target_persona["target_role"]
        if target_persona.get("target_job_queries"):
            st.session_state.target_job_queries = list(target_persona["target_job_queries"])
        if target_persona.get("core_skills"):
            st.session_state.primary_skills = list(target_persona["core_skills"])
        if target_persona.get("resume_text"):
            st.session_state.resume_text = target_persona["resume_text"]
        if target_persona.get("experience_level"):
            st.session_state.experience_level = target_persona["experience_level"]
        if target_persona.get("min_salary"):
            st.session_state.min_salary = target_persona["min_salary"]
        if target_persona.get("work_mode"):
            st.session_state.remote_pref = target_persona["work_mode"]
        if "form_version" in st.session_state:
            st.session_state.form_version += 1
    except Exception:
        pass

    return target_persona


def delete_persona(user_id: str, persona_name: str) -> bool:
    """Delete a persona from the user's profile."""
    profile = get_user_profile(user_id)
    personas = profile.get("personas", {})
    if persona_name in personas:
        del personas[persona_name]
        if profile.get("active_persona") == persona_name:
            remaining = list(personas.keys())
            profile["active_persona"] = remaining[0] if remaining else None
        save_user_profile(user_id, profile)
        return True
    return False
