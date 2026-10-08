"""
Autonomous Agentic AI Job Search Platform (Hyrd v4)
Core System Data Schemas and Agent Specifications (Pydantic v2 / v1 Compatible)

This module defines the authoritative, typed data models that govern:
1. Candidate Profiles & Intake State (UserProfile)
2. Scraped & Normalized Opportunities (JobPosting)
3. Multi-Factor Match Evaluations (MatchReport)
4. Executive Scouting Reports & Market Telemetry (FinalReportPayload)
5. On-Demand Document Tailoring (TailoredDocsRequest & TailoredDocsResponse)
6. Agent Role Specifications & Multi-Agent Orchestration Contracts
"""

from __future__ import annotations

import hashlib
import re
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Union

try:
    from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator
    PYDANTIC_V2 = True
except ImportError:
    from pydantic import BaseModel, Field, validator as field_validator  # type: ignore
    ConfigDict = dict  # type: ignore
    model_validator = None  # type: ignore
    PYDANTIC_V2 = False


# ============================================================================
# 1. ENUMS & VALUE OBJECTS
# ============================================================================

class WorkType(str, Enum):
    """Universal normalized work arrangement enum for scrapers and job ingestion."""
    REMOTE = "remote"
    HYBRID = "hybrid"
    ONSITE = "onsite"


def generate_job_id(source: str, raw_id: str) -> str:
    """Generate deterministic, collision-resistant job ID from source and identifier."""
    src = (source or "job").strip().lower()
    raw = str(raw_id or "").strip()
    if not raw:
        raw = str(uuid.uuid4())
    digest = hashlib.sha256(f"{src}:{raw}".encode("utf-8")).hexdigest()[:16]
    return f"{src}_{digest}"


class WorkModeEnum(str, Enum):
    REMOTE_ONLY = "Remote Only"
    HYBRID = "Hybrid"
    ON_SITE = "On-site"
    OPEN_TO_ALL = "Open to Remote & Hybrid"


class SeniorityLevelEnum(str, Enum):
    ENTRY = "Entry Level"
    MID = "Mid Level"
    SENIOR = "Senior"
    LEAD_STAFF = "Lead / Staff"
    DIRECTOR_EXECUTIVE = "Director / Executive"


class ApplicationStatusEnum(str, Enum):
    SAVED = "Saved"
    READY_TO_APPLY = "Ready to Apply"
    APPLIED = "Applied"
    INTERVIEWING = "Interviewing"
    OFFER_RECEIVED = "Offer Received"
    ARCHIVED = "Archived"


class AgentLifecycleState(str, Enum):
    IDLE = "IDLE"
    INITIALIZING = "INITIALIZING"
    RUNNING = "RUNNING"
    AWAITING_INPUT = "AWAITING_INPUT"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    DEGRADED = "DEGRADED"


# ============================================================================
# 2. SUB-MODELS (CANDIDATE & RESUME STRUCTURE)
# ============================================================================

class EducationEntry(BaseModel):
    """Structured academic credential or degree."""
    degree: str = Field(description="Degree title, e.g. B.S. in Computer Science or Mestrado em Engenharia")
    institution: str = Field(description="University, college, or issuing academic organization")
    graduation_year: Optional[str] = Field(default=None, description="Year of graduation or expected date")
    field_of_study: Optional[str] = Field(default=None, description="Academic specialization or major")
    honors_or_gpa: Optional[str] = Field(default=None, description="Academic distinctions or GPA if provided")

    if PYDANTIC_V2:
        model_config = ConfigDict(extra="ignore")


class WorkExperience(BaseModel):
    """Chronological career milestone and accomplishment record."""
    job_title: str = Field(description="Role title held at the organization")
    company_name: str = Field(description="Employing organization name")
    duration: Optional[str] = Field(default=None, description="Tenure interval, e.g. '2021 - Present' or '3 years'")
    location: Optional[str] = Field(default=None, description="Work location or Remote status")
    highlights: List[str] = Field(default_factory=list, description="Quantified accomplishments and outcomes")
    technologies_used: List[str] = Field(default_factory=list, description="Specific tech stack tools utilized")

    if PYDANTIC_V2:
        model_config = ConfigDict(extra="ignore")


class SalaryEvaluation(BaseModel):
    """Detailed geographic and seniority-adjusted compensation benchmarking."""
    currency: str = Field(default="USD", description="Currency symbol or 3-letter ISO code")
    benchmark_min: float = Field(description="Statistical P25 compensation benchmark")
    benchmark_mid: float = Field(description="Statistical P50 median compensation benchmark")
    benchmark_max: float = Field(description="Statistical P75 high-tier compensation benchmark")
    source_market: str = Field(description="Geographic labor market reference, e.g. US Tech, Portugal Tech")
    cost_of_living_multiplier: float = Field(default=1.0, description="Cost of Living relative to baseline US market")
    competitiveness_score: int = Field(ge=0, le=100, default=75, description="Salary rating score 0-100")
    analysis_narrative: str = Field(default="", description="Executive breakdown of salary positioning")

    if PYDANTIC_V2:
        model_config = ConfigDict(extra="ignore")


# ============================================================================
# 3. CORE DOMAIN MODEL: UserProfile
# ============================================================================

class UserProfile(BaseModel):
    """
    Candidate Profile & Intake State.
    Contains full professional background, extracted skills, target criteria,
    and workspace calibration parameters. Fully backwards compatible with
    Hyrd v4 session state and CandidateProfile dicts.
    """
    candidate_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique candidate workspace ID")
    full_name: str = Field(default="Alex Mercer", description="Candidate's full name")
    email: Optional[str] = Field(default="", description="Email contact address")
    phone: Optional[str] = Field(default="", description="Phone contact number")
    location_preference: str = Field(default="Remote", description="Preferred geographic location or target countries")
    location: str = Field(default="Remote", description="Current location or target work region")
    headline: str = Field(default="Senior Software Engineer", description="Target professional role title")
    
    # Quantitative & Extracted Experience
    experience_years: float = Field(default=5.0, description="Numerical years of professional experience")
    years_of_experience: str = Field(default="5+ years", description="Formatted string of experience tenure")
    seniority_level: SeniorityLevelEnum = Field(default=SeniorityLevelEnum.SENIOR, description="Calibrated seniority level")
    
    # Skills & Accomplishments
    extracted_skills: List[str] = Field(default_factory=list, description="Extracted technical and functional skills")
    core_skills: List[str] = Field(default_factory=list, description="Primary technical skills (v4 backward compatibility)")
    summary: str = Field(default="", description="Executive career summary synthesizing strengths")
    experience_highlights: List[str] = Field(default_factory=list, description="Key quantifiable career highlights")
    
    # Target Job Criteria & Filters
    target_roles: List[str] = Field(default_factory=list, description="Target job titles or recommended disciplines")
    selected_roles: List[str] = Field(default_factory=list, description="Active curated roles selected for crawler fan-out")
    work_mode: WorkModeEnum = Field(default=WorkModeEnum.REMOTE_ONLY, description="Preferred work mode")
    target_companies: List[str] = Field(default_factory=list, description="Dream target companies for direct ATS crawls")
    negative_keywords: List[str] = Field(default_factory=list, description="Keywords to strictly filter out from search results")
    
    # Compensation Preferences
    preferred_min_salary: str = Field(default="$150,000", description="Salary floor string representation")
    preferred_salary_min: Optional[float] = Field(default=150000.0, description="Numeric minimum annual compensation")
    preferred_salary_max: Optional[float] = Field(default=220000.0, description="Numeric maximum target compensation")
    preferred_currency: str = Field(default="USD", description="Preferred compensation currency")
    
    # Education, History & Social
    education: List[EducationEntry] = Field(default_factory=list, description="Academic background entries")
    work_experiences: List[WorkExperience] = Field(default_factory=list, description="Detailed career history milestones")
    certifications: List[str] = Field(default_factory=list, description="Professional certifications (e.g. AWS, GCP, PMP)")
    languages: List[str] = Field(default_factory=lambda: ["English (Fluent)"], description="Spoken languages and proficiencies")
    linkedin_url: Optional[str] = Field(default="", description="Personal LinkedIn profile URL")
    
    # Telemetry & Sync State
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    raw_resume_text: Optional[str] = Field(default=None, description="Original raw text extracted from uploaded resume")
    gemini_api_key: Optional[str] = Field(default=None, description="Per-user optional Gemini API Key override")

    if PYDANTIC_V2:
        model_config = ConfigDict(extra="ignore", populate_by_name=True)

        @model_validator(mode="before")
        @classmethod
        def synchronize_fields(cls, values: Any) -> Any:
            if not isinstance(values, dict):
                return values
            # Sync extracted_skills <-> core_skills
            skills = values.get("extracted_skills") or values.get("core_skills") or []
            values["extracted_skills"] = list(dict.fromkeys(skills))
            values["core_skills"] = values["extracted_skills"]

            # Sync location_preference <-> location
            loc = values.get("location_preference") or values.get("location") or "Remote"
            values["location_preference"] = loc
            values["location"] = loc

            # Sync years_of_experience <-> experience_years
            if "experience_years" in values and values["experience_years"] is not None:
                try:
                    num_yrs = float(values["experience_years"])
                    values["experience_years"] = num_yrs
                    if not values.get("years_of_experience"):
                        values["years_of_experience"] = f"{int(num_yrs)}+ years"
                except (ValueError, TypeError):
                    pass
            elif "years_of_experience" in values and values["years_of_experience"]:
                match = re.search(r"(\d+(?:\.\d+)?)", str(values["years_of_experience"]))
                if match:
                    values["experience_years"] = float(match.group(1))

            # Normalize seniority_level
            sen = values.get("seniority_level")
            if sen is not None:
                sen_str = str(sen).strip()
                sen_lower = sen_str.lower()
                if any(k in sen_lower for k in ["executive", "vp", "director", "c-level"]):
                    values["seniority_level"] = SeniorityLevelEnum.DIRECTOR_EXECUTIVE
                elif any(k in sen_lower for k in ["lead", "staff", "principal"]):
                    values["seniority_level"] = SeniorityLevelEnum.LEAD_STAFF
                elif "senior" in sen_lower:
                    values["seniority_level"] = SeniorityLevelEnum.SENIOR
                elif "mid" in sen_lower:
                    values["seniority_level"] = SeniorityLevelEnum.MID
                elif any(k in sen_lower for k in ["entry", "junior", "intern"]):
                    values["seniority_level"] = SeniorityLevelEnum.ENTRY
                else:
                    try:
                        values["seniority_level"] = SeniorityLevelEnum(sen_str)
                    except ValueError:
                        values["seniority_level"] = SeniorityLevelEnum.SENIOR

            # Normalize target_companies (string -> List[str])
            tc = values.get("target_companies")
            if isinstance(tc, str):
                values["target_companies"] = [c.strip() for c in tc.split(",") if c.strip()]
            elif isinstance(tc, list):
                values["target_companies"] = [str(c).strip() for c in tc if str(c).strip()]

            # Normalize negative_keywords (string -> List[str])
            nk = values.get("negative_keywords")
            if isinstance(nk, str):
                values["negative_keywords"] = [k.strip() for k in nk.split(",") if k.strip()]
            elif isinstance(nk, list):
                values["negative_keywords"] = [str(k).strip() for k in nk if str(k).strip()]

            # Sync target_roles <-> selected_roles
            roles = values.get("target_roles") or values.get("selected_roles") or []
            if isinstance(roles, str):
                roles = [r.strip() for r in roles.split(",") if r.strip()]
            elif isinstance(roles, list):
                roles = [str(r).strip() for r in roles if str(r).strip()]
            target_role_sing = values.get("target_role")
            if target_role_sing and isinstance(target_role_sing, str):
                sing_str = target_role_sing.strip()
                if sing_str and sing_str not in roles:
                    roles.insert(0, sing_str)
            values["target_roles"] = list(dict.fromkeys(roles))
            if not values.get("selected_roles"):
                values["selected_roles"] = list(values["target_roles"])

            # Normalize work_mode
            wm = values.get("work_mode") or values.get("remote_pref")
            if wm is not None:
                wm_str = str(wm).strip()
                wm_lower = wm_str.lower()
                if "open" in wm_lower or ("remote" in wm_lower and "hybrid" in wm_lower):
                    values["work_mode"] = WorkModeEnum.OPEN_TO_ALL
                elif "hybrid" in wm_lower:
                    values["work_mode"] = WorkModeEnum.HYBRID
                elif "site" in wm_lower or "onsite" in wm_lower:
                    values["work_mode"] = WorkModeEnum.ON_SITE
                elif "remote" in wm_lower:
                    values["work_mode"] = WorkModeEnum.REMOTE_ONLY
                else:
                    try:
                        values["work_mode"] = WorkModeEnum(wm_str)
                    except ValueError:
                        values["work_mode"] = WorkModeEnum.REMOTE_ONLY

            # Normalize min_salary
            sal = values.get("preferred_min_salary") or values.get("min_salary")
            if sal:
                values["preferred_min_salary"] = str(sal)
                if not values.get("preferred_salary_min"):
                    digits = re.sub(r"[^\d.]", "", str(sal))
                    if digits:
                        try:
                            values["preferred_salary_min"] = float(digits)
                        except ValueError:
                            pass

            # Adapt education entries (e.g. 'year' -> 'graduation_year')
            if "education" in values and isinstance(values["education"], list):
                adapted_edu = []
                for edu_item in values["education"]:
                    if isinstance(edu_item, dict):
                        edu_copy = dict(edu_item)
                        if "year" in edu_copy and "graduation_year" not in edu_copy:
                            edu_copy["graduation_year"] = str(edu_copy.pop("year"))
                        adapted_edu.append(edu_copy)
                    else:
                        adapted_edu.append(edu_item)
                values["education"] = adapted_edu

            # Adapt work experience entries
            if "experience" in values and not values.get("work_experiences"):
                raw_exp = values.get("experience")
                if isinstance(raw_exp, list):
                    adapted_exp = []
                    for exp_item in raw_exp:
                        if isinstance(exp_item, dict):
                            dur = exp_item.get("duration")
                            if not dur and (exp_item.get("start_date") or exp_item.get("end_date")):
                                dur = f"{exp_item.get('start_date', '')} - {exp_item.get('end_date', '')}".strip(" -")
                            adapted_exp.append({
                                "job_title": exp_item.get("job_title") or exp_item.get("role") or "Professional Role",
                                "company_name": exp_item.get("company_name") or exp_item.get("company") or "Company",
                                "duration": dur,
                                "location": exp_item.get("location") or "Remote",
                                "highlights": exp_item.get("highlights") or exp_item.get("bullet_points") or [],
                                "technologies_used": exp_item.get("technologies_used") or [],
                            })
                    values["work_experiences"] = adapted_exp

            if "linkedin" in values and not values.get("linkedin_url"):
                values["linkedin_url"] = str(values.get("linkedin") or "")
            if "resume_text" in values and not values.get("raw_resume_text"):
                values["raw_resume_text"] = str(values.get("resume_text") or "")

            return values

    def to_dict(self) -> Dict[str, Any]:
        """Produce clean dictionary representation matching Hyrd v4 session format."""
        if hasattr(self, "model_dump"):
            data = self.model_dump()
        else:
            data = self.dict()  # type: ignore
        return data


# ============================================================================
# 3B. GRANULAR MATCH AUDIT & VIABILITY MODELS (03_MATCH_LOGIC_BLUEPRINT)
# ============================================================================

class CapabilityMatch(BaseModel):
    """Detailed competency evaluation for a specific skill requirement."""
    skill_name: str = Field(description="Name of evaluated technical or functional competency")
    is_must_have: bool = Field(default=True, description="True if mandatory core pillar requirement")
    matched: bool = Field(default=False, description="True if candidate profile satisfies requirement")
    candidate_tenure_years: Optional[float] = Field(default=None, description="Candidate verified experience tenure")
    required_tenure_years: Optional[float] = Field(default=None, description="Tenure required by posting")
    mastery_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Calibrated proficiency score (0.0 to 1.0)")
    evidence_snippet: Optional[str] = Field(default=None, description="Quantified proof-point from candidate CV")

    if PYDANTIC_V2:
        model_config = ConfigDict(extra="ignore")


class LevelingAnalysis(BaseModel):
    """Seniority and organizational scope calibration."""
    candidate_level: str = Field(default="Senior", description="Candidate seniority classification")
    role_level: str = Field(default="Senior", description="Job requisition seniority classification")
    level_delta: int = Field(default=0, description="Index difference: L_cand - L_job")
    score: float = Field(default=100.0, ge=0.0, le=100.0, description="Calibrated leveling score (0-100)")
    assessment: str = Field(default="Aligned with career trajectory", description="Leveling diagnostic rationale")

    if PYDANTIC_V2:
        model_config = ConfigDict(extra="ignore")


class GatekeeperAudit(BaseModel):
    """Hard disqualification and dealbreaker audit."""
    work_auth_pass: bool = Field(default=True, description="Passes citizenship / work authorization checks")
    geo_radius_pass: bool = Field(default=True, description="Passes geographic physical residency / country checks")
    mandatory_cert_pass: bool = Field(default=True, description="Passes mandatory certifications / bar licenses")
    overall_gate_factor: float = Field(default=1.0, ge=0.0, le=1.0, description="Binary or fractional gatekeeper multiplier")
    disqualification_reason: Optional[str] = Field(default=None, description="Primary disqualification reason if failed")

    if PYDANTIC_V2:
        model_config = ConfigDict(extra="ignore")


class ViabilityMetrics(BaseModel):
    """Market dynamics and pipeline viability indicators."""
    days_since_posted: int = Field(default=1, description="Days elapsed since publication")
    decay_multiplier: float = Field(default=1.0, ge=0.0, le=1.0, description="Temporal decay multiplier Lambda")
    channel_type: str = Field(default="Direct ATS", description="Scraper origin channel type")
    channel_multiplier: float = Field(default=1.0, description="Ingestion channel competitive advantage factor Omega")
    ats_keyword_density_pct: float = Field(default=100.0, ge=0.0, le=100.0, description="Keyword screening density factor Psi")

    if PYDANTIC_V2:
        model_config = ConfigDict(extra="ignore")


# ============================================================================
# 4. CORE DOMAIN MODEL: JobPosting
# ============================================================================

class JobPosting(BaseModel):
    """
    Standardized, normalized job opportunity record aggregated across
    Tier 1-4 scrapers (Direct ATS APIs, public feeds, aggregator engines, and DOM portals).
    Conforms strictly to universal data ingestion contract with bidirectional backward compatibility.
    """
    # Universal Ingestion Contract Fields (Tier 1-4 Standard)
    job_id: str = Field(default="", description="Unique hash of source + id (e.g. 'greenhouse_a1b2c3d4e5f67890')")
    title: str = Field(description="Job title requisition, e.g. Senior Machine Learning Engineer")
    company_name: str = Field(default="", description="Employing organization or hiring company name")
    location: str = Field(default="Remote", description="Job location string or remote indicator")
    work_type: WorkType = Field(default=WorkType.REMOTE, description="Normalized work arrangement: remote, hybrid, onsite")
    url: str = Field(default="", description="Direct application or job post URL")
    description_text: str = Field(default="", description="Sanitized full job description text")
    posted_date: Optional[Union[datetime, str]] = Field(default=None, description="Publication timestamp or date string")
    source: str = Field(default="Aggregator", description="Scraper endpoint origin (e.g. 'greenhouse', 'itjobs_pt')")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata dictionary for salary, tags, and source quirks")

    # Core System Legacy & Downstream Aliases
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Internal unique opportunity ID")
    company: str = Field(default="", description="Employer name (synced with company_name)")
    full_description: str = Field(default="", description="Full description text (synced with description_text)")
    requirements: List[str] = Field(default_factory=list, description="Extracted requirements, competencies, or bullet points")
    salary_range: Optional[str] = Field(default=None, description="Disclosed or estimated salary interval string")
    source_url: str = Field(default="", description="Direct application URL (synced with url)")
    job_type: str = Field(default="Remote", description="Operational work mode label: Remote, Hybrid, or On-site")
    is_direct_ats: bool = Field(default=False, description="True if scraped directly from an employer ATS API")
    is_target_company: bool = Field(default=False, description="True if company matches candidate's target list")
    company_size: str = Field(default="Scale-up / Enterprise", description="Company size classification or scale")
    short_summary: Optional[str] = Field(default=None, description="Concise executive role summary and key responsibilities")

    # Semantic & Algorithmic Fit Metrics (0–100 scale)
    fit_score: int = Field(ge=0, le=100, default=0, description="Overall calibrated Match Fit Score")
    role_fit_score: Optional[int] = Field(default=None, description="Role title and domain alignment sub-score")
    profile_fit_score: float = Field(default=0.0, ge=0.0, le=100.0, description="Intrinsic capability fit score (0-100)")
    interview_likelihood_pct: float = Field(default=0.0, ge=0.0, le=100.0, description="Real-world interview callback probability (0-100%)")
    strategic_quadrant: str = Field(default="QI", description="Strategic decision quadrant (QI, QII, QIII, QIV)")
    badge_color: str = Field(default="#2563eb", description="Hex UI status badge indicator color")
    matched_skills: List[str] = Field(default_factory=list, description="Candidate skills directly matching this job")
    missing_skills: List[str] = Field(default_factory=list, description="Critical job requirements missing from profile")
    key_reasons: List[str] = Field(default_factory=list, description="Analytical rationale statements explaining the match")
    
    # Salary Analysis & Calibration
    salary_min: Optional[float] = Field(default=None, description="Numerical minimum annual compensation")
    salary_max: Optional[float] = Field(default=None, description="Numerical maximum annual compensation")
    salary_currency: Optional[str] = Field(default="USD", description="Currency symbol or ISO code")
    salary_score: Optional[int] = Field(default=None, ge=0, le=100, description="Compensation competitiveness score")
    salary_evaluation: Optional[Dict[str, Any]] = Field(default=None, description="Detailed salary benchmark breakdown")

    # Workflow & Kanban Tracking
    application_status: ApplicationStatusEnum = Field(default=ApplicationStatusEnum.SAVED, description="Kanban stage")
    notes: Optional[str] = Field(default=None, description="Personal candidate notes regarding this opportunity")

    if PYDANTIC_V2:
        model_config = ConfigDict(extra="ignore", populate_by_name=True)

        @model_validator(mode="before")
        @classmethod
        def normalize_job_fields(cls, values: Any) -> Any:
            if not isinstance(values, dict):
                return values

            # 1. Normalize title
            if "job_title" in values and not values.get("title"):
                values["title"] = values["job_title"]

            # 2. Normalize company & company_name
            comp = values.get("company_name") or values.get("company") or ""
            values["company_name"] = comp
            values["company"] = comp

            # 3. Normalize description_text, full_description, description
            desc = values.get("description_text") or values.get("full_description") or values.get("description") or ""
            values["description_text"] = desc
            values["full_description"] = desc

            # 4. Normalize url, source_url
            u = values.get("url") or values.get("source_url") or ""
            values["url"] = u
            values["source_url"] = u

            # 5. Normalize job_id & id
            src = str(values.get("source") or "job").strip().lower()
            raw_id = values.get("job_id") or values.get("id")
            if not raw_id:
                raw_uuid = str(uuid.uuid4())
                values["id"] = raw_uuid
                digest = hashlib.sha256(f"{src}:{raw_uuid}".encode("utf-8")).hexdigest()[:16]
                values["job_id"] = f"{src}_{digest}"
            else:
                raw_str = str(raw_id)
                values["id"] = raw_str
                if not values.get("job_id"):
                    if "_" in raw_str and any(raw_str.startswith(p) for p in [src, "job", "ats", "gh", "ashby"]):
                        values["job_id"] = raw_str
                    else:
                        digest = hashlib.sha256(f"{src}:{raw_str}".encode("utf-8")).hexdigest()[:16]
                        values["job_id"] = f"{src}_{digest}"
                else:
                    values["job_id"] = str(values["job_id"])

            # 6. Normalize work_type & job_type
            raw_work = values.get("work_type") or values.get("job_type")
            if isinstance(raw_work, WorkType):
                values["work_type"] = raw_work
                values["job_type"] = "Remote" if raw_work == WorkType.REMOTE else ("Hybrid" if raw_work == WorkType.HYBRID else "On-site")
            elif isinstance(raw_work, str):
                rw_lower = raw_work.lower()
                if "hybrid" in rw_lower or "híbrido" in rw_lower:
                    values["work_type"] = WorkType.HYBRID
                    values["job_type"] = "Hybrid"
                elif "onsite" in rw_lower or "on-site" in rw_lower or "presencial" in rw_lower:
                    values["work_type"] = WorkType.ONSITE
                    values["job_type"] = "On-site"
                else:
                    values["work_type"] = WorkType.REMOTE
                    values["job_type"] = "Remote"
            else:
                values["work_type"] = WorkType.REMOTE
                values["job_type"] = "Remote"

            # 7. Normalize metadata
            if values.get("metadata") is None or not isinstance(values.get("metadata"), dict):
                values["metadata"] = {}
            if "salary_range" in values and values["salary_range"] and "salary" not in values["metadata"]:
                values["metadata"]["salary"] = values["salary_range"]

            # 8. Sync fit_score <-> profile_fit_score
            if "profile_fit_score" in values and values["profile_fit_score"]:
                values["fit_score"] = int(round(values["profile_fit_score"]))
            elif "fit_score" in values and values["fit_score"]:
                values["profile_fit_score"] = float(values["fit_score"])

            return values

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation matching Hyrd dashboard format."""
        if hasattr(self, "model_dump"):
            try:
                d = self.model_dump(mode="json")
            except Exception:
                d = self.model_dump()
        else:
            d = self.dict()  # type: ignore
        # Provide aliases expected by both legacy views and universal schemas
        d["job_id"] = self.job_id
        d["id"] = self.id
        d["title"] = self.title
        d["company"] = self.company
        d["company_name"] = self.company_name or self.company
        d["description"] = self.full_description or self.description_text
        d["full_description"] = self.full_description or self.description_text
        d["description_text"] = self.description_text or self.full_description
        d["url"] = self.source_url or self.url
        d["source_url"] = self.source_url or self.url
        d["work_type"] = self.work_type.value if hasattr(self.work_type, "value") else str(self.work_type)
        d["job_type"] = self.job_type
        d["company_size"] = getattr(self, "company_size", None) or self.metadata.get("company_size") or "Scale-up / Enterprise"
        d["short_summary"] = getattr(self, "short_summary", None) or self.metadata.get("short_summary")
        if hasattr(self, "posted_date") and self.posted_date is not None:
            if hasattr(self.posted_date, "isoformat"):
                d["posted_date"] = self.posted_date.isoformat()
            else:
                d["posted_date"] = str(self.posted_date)
        d["posted"] = d.get("posted_date") or "Recent"
        d["metadata"] = self.metadata or {}
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "JobPosting":
        """Instantiate JobPosting model from a dictionary payload."""
        return cls(**data)



# ============================================================================
# 5. CORE DOMAIN MODEL: MatchReport
# ============================================================================

class MatchReport(BaseModel):
    """
    Multi-Dimensional Evaluation Dossier for a specific Job-Candidate pair.
    Computes deterministic match scores, recruiter response probability,
    and granular skill gap diagnostics.
    """
    job_id: str = Field(description="Unique reference ID of evaluated JobPosting")
    job_title: str = Field(description="Job title of evaluated opportunity")
    company: str = Field(description="Employer organization")
    
    # Core Prescribed Metrics (Decoupled Dual-Engine Architecture)
    match_score: float = Field(default=0.0, ge=0.0, le=100.0, description="Overall Match Score on 0-100 scale")
    profile_fit_score: float = Field(default=0.0, ge=0.0, le=100.0, description="Intrinsic capability fit score (0-100)")
    probability_of_recruiter_response: float = Field(
        default=0.0, ge=0.0, le=1.0, 
        description="Statistical likelihood (0.0 to 1.0) of receiving a recruiter response or interview callback"
    )
    interview_likelihood_pct: float = Field(
        default=0.0, ge=0.0, le=100.0,
        description="Real-world interview callback probability percentage (0-100%)"
    )
    strategic_quadrant: str = Field(
        default="QI", 
        description="Strategic decision quadrant: QI (Priority), QII (Outreach), QIII (Stretch), QIV (Filter)"
    )
    key_skill_gaps: List[str] = Field(default_factory=list, description="High-priority missing skills or qualifications")
    alignment_summary: str = Field(default="", description="Executive narrative summarizing candidate suitability")
    
    # Granular Scoring Breakdown & Multi-Dimensional Audits
    matching_skills: List[str] = Field(default_factory=list, description="Skills present in both candidate and job")
    dimension_scores: Dict[str, float] = Field(
        default_factory=dict,
        description="Decomposed sub-scores: skill, role, level, pref, semantic_fit, compensation"
    )
    capability_matches: List[CapabilityMatch] = Field(
        default_factory=list, 
        description="Granular requirement-level capability matches and gaps"
    )
    leveling_analysis: Optional[LevelingAnalysis] = Field(
        default=None, 
        description="Seniority delta and scope leveling calibration"
    )
    gatekeeper_audit: Optional[GatekeeperAudit] = Field(
        default=None, 
        description="Hard dealbreakers: visa, citizenship, clearances, location radius"
    )
    viability_metrics: Optional[ViabilityMetrics] = Field(
        default=None, 
        description="Requisition age decay and channel competition dynamics"
    )
    recruiter_reasoning: List[str] = Field(
        default_factory=list, 
        description="Key observations that human recruiters will flag during screening"
    )
    interview_readiness_score: Optional[float] = Field(
        default=None, ge=0.0, le=100.0, 
        description="Readiness index for technical and behavioral interviews"
    )
    recommended_action: str = Field(
        default="Apply Immediately", 
        description="Actionable directive (e.g. Priority Fast-Track, Referral Outreach, Apply with Bridge Narrative, Archive)"
    )

    if PYDANTIC_V2:
        model_config = ConfigDict(extra="ignore")

        @model_validator(mode="before")
        @classmethod
        def synchronize_match_metrics(cls, values: Any) -> Any:
            if not isinstance(values, dict):
                return values
            # Sync match_score <-> profile_fit_score
            if "profile_fit_score" in values and values.get("profile_fit_score") is not None:
                if "match_score" not in values or values.get("match_score") is None:
                    values["match_score"] = float(values["profile_fit_score"])
            elif "match_score" in values and values.get("match_score") is not None:
                values["profile_fit_score"] = float(values["match_score"])

            # Sync probability_of_recruiter_response <-> interview_likelihood_pct
            if "interview_likelihood_pct" in values and values.get("interview_likelihood_pct") is not None:
                if "probability_of_recruiter_response" not in values or values.get("probability_of_recruiter_response") is None:
                    values["probability_of_recruiter_response"] = round(float(values["interview_likelihood_pct"]) / 100.0, 4)
            elif "probability_of_recruiter_response" in values and values.get("probability_of_recruiter_response") is not None:
                values["interview_likelihood_pct"] = round(float(values["probability_of_recruiter_response"]) * 100.0, 1)

            return values


# ============================================================================
# 6. CORE DOMAIN MODEL: FinalReportPayload
# ============================================================================

class FinalReportPayload(BaseModel):
    """
    Comprehensive aggregated intelligence payload summarizing the complete
    scouting cycle, ranked opportunities, and market insights.
    """
    report_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique report cycle identifier")
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    candidate_id: str = Field(description="Reference candidate identifier")
    candidate_name: str = Field(description="Candidate full name")
    target_role: str = Field(description="Primary targeted discipline")
    
    # Pipeline Execution Metrics
    total_jobs_scouted: int = Field(default=0, description="Total raw positions retrieved from all scrapers")
    total_jobs_evaluated: int = Field(default=0, description="Total positions that passed geographic and negative filters")
    
    # Ranked Opportunities & Diagnostics
    top_matches: List[JobPosting] = Field(
        default_factory=list, 
        description="Sorted list of top job matches with scores (descending order)"
    )
    detailed_match_reports: List[MatchReport] = Field(
        default_factory=list, 
        description="Associated MatchReport objects for top matches"
    )
    
    # Market & Labor Telemetry
    market_intelligence_summary: Dict[str, Any] = Field(
        default_factory=dict, 
        description="Aggregated market insights: median compensation, top in-demand skills, hiring hubs"
    )
    search_channels_telemetry: Dict[str, int] = Field(
        default_factory=dict, 
        description="Scraper breakdown of yields per channel (e.g. Ashby: 40, LinkedIn: 25)"
    )
    executive_takeaway: str = Field(
        default="", 
        description="Strategic recommendation for maximizing interview callback velocity"
    )

    if PYDANTIC_V2:
        model_config = ConfigDict(extra="ignore")


# ============================================================================
# 7. DOCUMENT TAILORING SCHEMAS: TailoredDocsRequest & TailoredDocsResponse
# ============================================================================

class DocumentTypeEnum(str, Enum):
    CV = "cv"
    COVER_LETTER = "cover_letter"
    INTERVIEW_PREP = "interview_prep"
    OUTREACH = "outreach"


class TailoredDocsRequest(BaseModel):
    """
    Input payload for on-demand application document synthesis
    (ATS-optimized CV and customized Cover Letter).
    """
    user_profile: UserProfile = Field(description="Complete candidate profile and background state")
    job_posting: JobPosting = Field(description="Target opportunity to calibrate documents against")
    document_types: List[DocumentTypeEnum] = Field(
        default_factory=lambda: [DocumentTypeEnum.CV, DocumentTypeEnum.COVER_LETTER],
        description="Requested document artifacts to generate"
    )
    language: str = Field(
        default="en", 
        description="Target linguistic locale: 'en' for English or 'pt-pt' for European Portuguese"
    )
    tone: str = Field(default="executive", description="Stylistic tone: executive, technical, or conversational")
    target_keywords_override: Optional[List[str]] = Field(
        default=None, 
        description="Explicit keywords to force into the ATS optimization matrix"
    )
    model_override: Optional[str] = Field(
        default=None, 
        description="Optional Gemini model override (e.g. gemini-3.8-flash)"
    )
    custom_instructions: Optional[str] = Field(
        default=None, 
        description="User-specified constraints or highlights to emphasize"
    )

    if PYDANTIC_V2:
        model_config = ConfigDict(extra="ignore")


class TailoredDocsResponse(BaseModel):
    """
    Output payload delivering synthesized, ATS-calibrated documents
    and audit metrics.
    """
    job_id: str = Field(description="Opportunity reference ID")
    job_title: str = Field(description="Job title of target opening")
    company: str = Field(description="Company name")
    
    # Document Payloads (Markdown formatted)
    cv_markdown: Optional[str] = Field(default=None, description="Synthesized ATS-compliant CV in Markdown")
    cover_letter_markdown: Optional[str] = Field(default=None, description="Personalized formal Cover Letter")
    
    # ATS Validation & Keywords
    ats_compatibility_score: Optional[int] = Field(
        default=None, ge=0, le=100, 
        description="Objective ATS audit score evaluating heading and keyword compliance"
    )
    ats_keywords_targeted: List[str] = Field(
        default_factory=list, 
        description="High-frequency requisition keywords successfully woven into text"
    )
    ats_audit_summary: Optional[Dict[str, Any]] = Field(
        default=None, 
        description="Checklist audit results across sections, metrics, and formatting"
    )
    
    # Generation Metadata
    language: str = Field(default="en", description="Output linguistic locale ('en' or 'pt-pt')")
    generated_model: str = Field(default="gemini-3.8-flash", description="Model engine that produced the documents")
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    export_ready: bool = Field(default=True, description="Flag indicating documents are ready for DOCX/PDF export")

    if PYDANTIC_V2:
        model_config = ConfigDict(extra="ignore")


# ============================================================================
# 8. AGENT ROLE SPECIFICATIONS & INTERFACES
# ============================================================================

# --- ProfileAgent (Stages 1 & 2) ---

class ProfileAgentInput(BaseModel):
    """Input payload for Candidate Intake & Calibration Agent."""
    raw_resume_bytes: Optional[bytes] = None
    raw_resume_text: Optional[str] = None
    file_type: Optional[str] = Field(default="pdf", description="File extension: pdf, docx, or txt")
    manual_overrides: Optional[Dict[str, Any]] = Field(default=None, description="Manual edits made by user in UI")
    preferred_language: str = Field(default="en", description="Default user language")

    if PYDANTIC_V2:
        model_config = ConfigDict(extra="ignore")


class ProfileAgentOutput(BaseModel):
    """Output payload from ProfileAgent after parsing and calibration."""
    profile: UserProfile
    parsing_method: str = Field(description="'gemini_structured_output' or 'heuristic_fallback'")
    parsing_latency_ms: float = Field(default=0.0)
    recruiter_gap_analysis: Dict[str, Any] = Field(
        default_factory=dict,
        description="Strengths, missing sections, and advice to reach 100% recruiter readiness"
    )
    recommended_roles: List[str] = Field(default_factory=list, description="Curated target titles for job search")
    status_message: str = Field(default="")

    if PYDANTIC_V2:
        model_config = ConfigDict(extra="ignore")


# --- ScoutAgent (Stage 3) ---

class ScoutAgentInput(BaseModel):
    """Input parameters for multi-source autonomous crawler."""
    profile: UserProfile
    channels_enabled: Optional[List[str]] = Field(
        default=None, 
        description="List of scrapers to activate (defaults to all 17 available)"
    )
    max_workers: int = Field(default=22, ge=1, le=32, description="Concurrency thread limit")
    target_job_limit_per_source: int = Field(default=35, description="Upper bound fetch limit per channel")
    apify_api_token: Optional[str] = None

    if PYDANTIC_V2:
        model_config = ConfigDict(extra="ignore")


class ScoutAgentOutput(BaseModel):
    """Output containing all scraped, deduplicated, and mode-filtered opportunities."""
    raw_jobs_found: int = Field(default=0)
    filtered_jobs: List[JobPosting] = Field(default_factory=list)
    channel_telemetry: Dict[str, int] = Field(default_factory=dict)
    failures_by_source: Dict[str, str] = Field(default_factory=dict)
    execution_time_seconds: float = Field(default=0.0)

    if PYDANTIC_V2:
        model_config = ConfigDict(extra="ignore")


# --- MatchAgent (Stages 4 & 5) ---

class MatchAgentInput(BaseModel):
    """Input parameters for multi-dimensional matching and reranking."""
    profile: UserProfile
    candidate_jobs: List[JobPosting]
    enable_gemini_rerank: bool = Field(default=True, description="Perform Pass-2 deep semantic reranking")
    geographic_factors: Optional[Dict[str, float]] = None

    if PYDANTIC_V2:
        model_config = ConfigDict(extra="ignore")


class MatchAgentOutput(BaseModel):
    """Output containing fully evaluated, scored, and calibrated opportunities."""
    ranked_jobs: List[JobPosting] = Field(default_factory=list)
    match_reports: Dict[str, MatchReport] = Field(default_factory=dict)
    total_evaluated: int = Field(default=0)
    average_fit_score: float = Field(default=0.0)
    top_tier_count: int = Field(default=0, description="Jobs scoring >= 90")

    if PYDANTIC_V2:
        model_config = ConfigDict(extra="ignore")


# --- ReportAgent (Stage 6) ---

class ReportAgentInput(BaseModel):
    """Input payload for generating the executive final report and morning digest."""
    profile: UserProfile
    ranked_jobs: List[JobPosting]
    match_reports: Dict[str, MatchReport]
    telemetry: Dict[str, Any]

    if PYDANTIC_V2:
        model_config = ConfigDict(extra="ignore")


class ReportAgentOutput(BaseModel):
    """Executive scouting report and multi-channel publication payload."""
    payload: FinalReportPayload
    morning_digest_markdown: str = Field(description="Formatted morning briefing ready for reading or email")
    top_recommendations: List[JobPosting] = Field(default_factory=list)

    if PYDANTIC_V2:
        model_config = ConfigDict(extra="ignore")


# --- DocAgent (On-Demand UI Trigger) ---

class DocAgentInput(TailoredDocsRequest):
    """DocAgent uses TailoredDocsRequest as its formal input contract."""
    pass


class DocAgentOutput(TailoredDocsResponse):
    """DocAgent uses TailoredDocsResponse as its formal output contract."""
    pass


# ============================================================================
# 9. AGENT ROLE SPECIFICATION REGISTRY
# ============================================================================

class AgentSpec(BaseModel):
    """Formal architectural specification metadata for an orchestration agent."""
    name: str
    phase_stages: str
    description: str
    lifecycle_state: AgentLifecycleState = AgentLifecycleState.IDLE
    input_schema: str
    output_schema: str
    assigned_tools: List[str]
    primary_llm: str
    fallback_strategy: str

    if PYDANTIC_V2:
        model_config = ConfigDict(extra="ignore")


AGENT_ROLE_SPECS: Dict[str, AgentSpec] = {
    "ProfileAgent": AgentSpec(
        name="ProfileAgent",
        phase_stages="Stages 1 & 2 (Candidate Intake, Document Parsing, Role Calibration)",
        description="Ingests raw PDF/DOCX resumes, extracts structured career profiles with Gemini Flash, and benchmarks recruiter match readiness.",
        input_schema="ProfileAgentInput",
        output_schema="ProfileAgentOutput",
        assigned_tools=[
            "file_parser.extract_text_from_file",
            "gemini_client.generate_gemini_content",
            "ats_optimizer.format_ats_contact_block",
            "resume_parser._heuristic_fallback_parser",
            "user_manager.save_user_profile"
        ],
        primary_llm="gemini-3.8-flash",
        fallback_strategy="Deterministic Regex Heuristic Parser + Rule-based Keyword Extractor"
    ),
    "ScoutAgent": AgentSpec(
        name="ScoutAgent",
        phase_stages="Stage 3 (Concurrent Async Multi-Source Crawling)",
        description="Dispatches parallel crawler tasks across 17 live ATS, aggregator, and regional job portals with query sanitization and exclusion filtering.",
        input_schema="ScoutAgentInput",
        output_schema="ScoutAgentOutput",
        assigned_tools=[
            "scrapers.ats.fetch_ashby_jobs",
            "scrapers.ats.fetch_greenhouse_jobs",
            "scrapers.ats.fetch_lever_jobs",
            "scrapers.ats.fetch_smartrecruiters_jobs",
            "scrapers.aggregator.fetch_jobspy_jobs",
            "scrapers.aggregator.fetch_apify_jobs",
            "scrapers.remote.fetch_remoteok_jobs",
            "scrapers.remote.fetch_remotive_jobs",
            "scrapers.remote.fetch_arbeitnow_jobs",
            "scrapers.remote.fetch_weworkremotely_jobs",
            "scrapers.portuguese.fetch_itjobs_jobs",
            "scrapers.portuguese.fetch_netempregos_jobs",
            "scrapers.portuguese.fetch_landingjobs_jobs",
            "concurrent.futures.ThreadPoolExecutor"
        ],
        primary_llm="None (I/O HTTP & API Orchestration)",
        fallback_strategy="Graceful per-channel exception isolation (safe_scrape) + Mock Data Fallback"
    ),
    "MatchAgent": AgentSpec(
        name="MatchAgent",
        phase_stages="Stages 4 & 5 (Semantic Scoring, Salary Calibration & Kanban Tracking)",
        description="Evaluates candidate-opportunity pairs across multi-dimensional criteria, executes Pass-2 Gemini Flash reranking, and benchmarks compensation.",
        input_schema="MatchAgentInput",
        output_schema="MatchAgentOutput",
        assigned_tools=[
            "matching.scoring.calculate_semantic_fit",
            "matching.reranker.rerank_top_jobs_with_gemini",
            "utils.salary_evaluator.evaluate_salary",
            "utils.salary_benchmarks.get_benchmark",
            "utils.pipeline_manager.update_job_status"
        ],
        primary_llm="gemini-3.8-flash (Pass-2 Reranking)",
        fallback_strategy="Deterministic Weighted Keyword Overlap + Geographic Matrix Calibration"
    ),
    "ReportAgent": AgentSpec(
        name="ReportAgent",
        phase_stages="Stage 6 (Executive Intelligence & Morning Digest Aggregation)",
        description="Synthesizes market intelligence, compiles final ranked opportunity payloads, and authors personalized executive morning digests.",
        input_schema="ReportAgentInput",
        output_schema="ReportAgentOutput",
        assigned_tools=[
            "gemini_client.generate_gemini_content",
            "job_scout_agent.generate_morning_digest",
            "utils.document_exporter.export_to_json"
        ],
        primary_llm="gemini-3.8-flash",
        fallback_strategy="Deterministic Executive Summary Templating"
    ),
    "DocAgent": AgentSpec(
        name="DocAgent",
        phase_stages="On-Demand UI Trigger (Tailored CV, Cover Letter, Prep Pack, Outreach)",
        description="Generates ATS-optimized CVs, bespoke Cover Letters, and interview battlecards in English and Portuguese with direct Word (.docx) and PDF export.",
        input_schema="DocAgentInput",
        output_schema="DocAgentOutput",
        assigned_tools=[
            "application_agent.generate_customized_cv",
            "application_agent.generate_cover_letter",
            "interview_prep_agent.generate_interview_prep",
            "outreach_agent.generate_cold_outreach",
            "company_intelligence_agent.generate_company_dossier",
            "ats_optimizer.audit_ats_cv_compatibility",
            "ats_optimizer.detect_job_language",
            "document_exporter.generate_tailored_cv_docx",
            "document_exporter.generate_cover_letter_docx",
            "document_exporter.generate_tailored_cv_pdf"
        ],
        primary_llm="gemini-3.8-flash (Primary) -> gemini-2.5-flash (Cascade)",
        fallback_strategy="Strict ATS Standard Template Fallbacks (100% Parser Safe, zero-AI dependency)"
    )
}
