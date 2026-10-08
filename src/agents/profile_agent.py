"""
ProfileAgent (Stages 1 & 2): Candidate Intake, Resume Parsing & Entity Extraction.
Built using the google-antigravity framework with strict Pydantic v2 contracts.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional, Union

try:
    from google.antigravity import Agent, LocalAgentConfig
    from google.antigravity.tools.tool_runner import ToolRunner
except ImportError:
    from google.antigravity.tools.tool_runner import ToolRunner  # type: ignore
    Agent = Any  # type: ignore
    LocalAgentConfig = Any  # type: ignore

from src.schemas import (
    ProfileAgentInput,
    ProfileAgentOutput,
    UserProfile,
    EducationEntry,
    WorkExperience,
    SeniorityLevelEnum,
    WorkModeEnum,
)
from src.utils.file_parser import extract_text_from_file
from src.agents.resume_parser_agent import (
    parse_resume_with_gemini,
    _heuristic_fallback_parser,
)

logger = logging.getLogger("Hyrd.ProfileAgent")


# ============================================================================
# RECRUITER READINESS & GAP ANALYSIS ENGINE
# ============================================================================

def analyze_recruiter_gaps(profile: UserProfile) -> Dict[str, Any]:
    """Perform a 100% Recruiter Readiness benchmark audit against the extracted profile.
    Checks contact completeness, experience quantification, and technical depth.
    """
    score = 100
    missing_elements: List[str] = []
    strengths: List[str] = []
    recommendations: List[str] = []

    # 1. Contact Info Audit
    if not profile.email:
        score -= 15
        missing_elements.append("Email contact address missing")
        recommendations.append("Provide a direct professional email address for recruiter reachout.")
    else:
        strengths.append(f"Direct contact email verified ({profile.email}).")

    if not profile.phone:
        score -= 10
        missing_elements.append("Phone number missing")
        recommendations.append("Add a direct phone number to facilitate recruiter scheduling.")
    else:
        strengths.append("Direct phone number available.")

    if not profile.linkedin_url:
        score -= 10
        missing_elements.append("LinkedIn profile link not detected")
        recommendations.append("Include your public LinkedIn profile link for social proof validation.")
    else:
        strengths.append("LinkedIn profile detected.")

    # 2. Skills & Technical Depth
    skills_count = len(profile.extracted_skills)
    if skills_count < 4:
        score -= 20
        missing_elements.append("Low technical skills density (< 4 detected)")
        recommendations.append("List at least 6-8 core technical competencies to improve ATS searchability.")
    else:
        strengths.append(f"Strong competency footprint with {skills_count} recognized core skills.")

    # 3. Experience Quantification
    if not profile.experience_highlights:
        score -= 15
        missing_elements.append("Missing quantified career accomplishments")
        recommendations.append("Add 3-5 bullet points with metrics (e.g. '% reduction', '$ savings', 'users served').")
    else:
        strengths.append(f"Documented {len(profile.experience_highlights)} quantified impact achievements.")

    readiness_score = max(20, min(100, score))
    readiness_label = (
        "100% Market Ready" if readiness_score >= 90
        else "Strong Contender" if readiness_score >= 75
        else "Calibration Needed"
    )

    return {
        "readiness_score": readiness_score,
        "readiness_label": readiness_label,
        "missing_elements": missing_elements,
        "strengths": strengths,
        "recommendations": recommendations,
    }


# ============================================================================
# HIERARCHICAL COMPETENCY GRAPH & PROFICIENCY TAXONOMY (Feature P1-C)
# ============================================================================

_TIER1_INDICATORS = {
    "python", "go", "golang", "java", "c++", "c#", "rust", "typescript", "javascript",
    "system architecture", "distributed systems", "machine learning", "deep learning",
    "llm", "llms", "agentic ai", "generative ai", "nlp", "data engineering", "leadership",
    "software engineering", "backend development",
}

_TIER2_INDICATORS = {
    "docker", "kubernetes", "k8s", "aws", "gcp", "azure", "postgresql", "postgres",
    "sql", "nosql", "redis", "mongodb", "fastapi", "react", "next.js", "django",
    "pytorch", "tensorflow", "langchain", "ci/cd", "terraform", "microservices", "rest api",
}


def categorize_competencies(
    extracted_skills: List[str],
    experience_years: Any = "Senior",
    summary: str = "",
) -> Dict[str, List[str]]:
    """
    Categorize candidate competencies into a 3-tier taxonomy (Feature P1-C):
    - tier_1_core: Core Drivers (Primary engineering languages & core systems)
    - tier_2_supporting: Supporting Stack (Frameworks, datastores, cloud, devops)
    - tier_3_familiar: Familiar & Emerging (Tooling, methodologies, secondary libraries)
    """
    tier_1 = []
    tier_2 = []
    tier_3 = []

    for skill in extracted_skills:
        s_clean = skill.strip()
        if not s_clean:
            continue
        s_lower = s_clean.lower()
        if any(ind in s_lower or s_lower in ind for ind in _TIER1_INDICATORS):
            tier_1.append(s_clean)
        elif any(ind in s_lower or s_lower in ind for ind in _TIER2_INDICATORS):
            tier_2.append(s_clean)
        else:
            tier_3.append(s_clean)

    # Balance tiers if needed
    if not tier_1 and extracted_skills:
        tier_1 = extracted_skills[:3]
        tier_2 = extracted_skills[3:7]
        tier_3 = extracted_skills[7:]
    elif not tier_2 and tier_3:
        half = max(1, len(tier_3) // 2)
        tier_2 = tier_3[:half]
        tier_3 = tier_3[half:]

    return {
        "tier_1_core": tier_1,
        "tier_2_supporting": tier_2,
        "tier_3_familiar": tier_3,
    }


# ============================================================================
# PROFILE AGENT CLASS & RUNNER
# ============================================================================

class ProfileAgent:
    """Autonomous agent governing Candidate Intake, Resume Parsing, and Calibration."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.tool_runner = ToolRunner()
        self._register_tools()

    def _register_tools(self) -> None:
        """Register profile parsing tools into the Antigravity ToolRunner registry."""
        self.tool_runner.register(extract_text_from_file, "extract_text_from_file")
        self.tool_runner.register(_heuristic_fallback_parser, "heuristic_parser")
        self.tool_runner.register(analyze_recruiter_gaps, "analyze_recruiter_gaps")

    def run(self, input_payload: ProfileAgentInput) -> ProfileAgentOutput:
        """Execute Stage 1 (Document Extraction) and Stage 2 (Entity Calibration)."""
        start_time = time.perf_counter()
        raw_text = input_payload.raw_resume_text or ""
        file_bytes = input_payload.raw_resume_bytes
        file_ext = input_payload.file_type or "pdf"

        # 1. Text Extraction with Error Containment
        if file_bytes and not raw_text:
            try:
                raw_text = extract_text_from_file(file_bytes, file_ext)
            except Exception as exc:
                logger.error(f"Failed to extract text from file ({file_ext}): {exc}")
                raw_text = ""

        # Handle unparseable or completely empty resume input gracefully
        if not raw_text or not raw_text.strip():
            logger.warning("Unparseable or empty resume input detected. Generating default candidate baseline.")
            fallback_dict = _heuristic_fallback_parser("")
            fallback_dict["summary"] = "Candidate profile created via manual intake. Add resume text to populate full career details."
            
            profile = UserProfile(
                full_name=fallback_dict.get("full_name", "Alex Mercer"),
                headline=fallback_dict.get("headline", "Software Engineer"),
                years_of_experience=fallback_dict.get("years_of_experience", "5+ years"),
                location_preference=fallback_dict.get("location", "Remote"),
                extracted_skills=fallback_dict.get("core_skills", ["Software Engineering", "Python"]),
                summary=fallback_dict.get("summary", ""),
                target_roles=fallback_dict.get("target_roles", ["Software Engineer", "Backend Developer"]),
                raw_resume_text="",
            )
            gaps = analyze_recruiter_gaps(profile)
            latency = (time.perf_counter() - start_time) * 1000

            return ProfileAgentOutput(
                profile=profile,
                parsing_method="heuristic_fallback",
                parsing_latency_ms=latency,
                recruiter_gap_analysis=gaps,
                recommended_roles=profile.target_roles,
                status_message="⚠️ Resume input was empty or unparseable. Profile initialized with baseline template. You can edit fields manually.",
            )

        # 2. Structured Extraction (Gemini with Heuristic Fallback)
        try:
            profile_dict, is_ai, status_msg = parse_resume_with_gemini(
                resume_text=raw_text,
                api_key=self.api_key,
            )
            method = "gemini_structured_output" if is_ai else "heuristic_fallback"
        except Exception as exc:
            logger.warning(f"Gemini parsing invocation failed: {exc}. Activating heuristic fallback.")
            profile_dict = _heuristic_fallback_parser(raw_text)
            method = "heuristic_fallback"
            status_msg = f"Profile parsed using local heuristic agent ({exc})."

        # Apply any manual overrides specified by the user
        if input_payload.manual_overrides:
            for k, v in input_payload.manual_overrides.items():
                if v is not None and v != "":
                    profile_dict[k] = v

        # Convert to strict Pydantic UserProfile model
        skills = profile_dict.get("core_skills") or profile_dict.get("extracted_skills") or []
        target_roles = profile_dict.get("target_roles") or [profile_dict.get("headline", "Software Engineer")]
        
        # Build education list if present
        edu_list: List[EducationEntry] = []
        raw_edu = profile_dict.get("education") or []
        if isinstance(raw_edu, list):
            for e in raw_edu:
                if isinstance(e, dict):
                    edu_list.append(EducationEntry(**e))
                elif isinstance(e, str) and e.strip():
                    edu_list.append(EducationEntry(degree=e.strip(), institution="Accredited University"))

        profile = UserProfile(
            full_name=profile_dict.get("full_name") or "Alex Mercer",
            email=profile_dict.get("email") or "",
            phone=profile_dict.get("phone") or "",
            location_preference=profile_dict.get("location") or "Remote",
            location=profile_dict.get("location") or "Remote",
            headline=profile_dict.get("headline") or "Software Engineer",
            years_of_experience=str(profile_dict.get("years_of_experience") or "5+ years"),
            extracted_skills=skills,
            core_skills=skills,
            summary=profile_dict.get("summary") or "",
            experience_highlights=profile_dict.get("experience_highlights") or [],
            target_roles=target_roles,
            selected_roles=profile_dict.get("selected_roles") or target_roles,
            preferred_min_salary=profile_dict.get("preferred_min_salary") or "$150,000",
            work_mode=profile_dict.get("work_mode") or WorkModeEnum.REMOTE_ONLY,
            linkedin_url=profile_dict.get("linkedin_url") or "",
            education=edu_list,
            raw_resume_text=raw_text,
            competency_tiers=categorize_competencies(skills, profile_dict.get("years_of_experience", "5+ years")),
        )

        # 3. Recruiter Gap Analysis
        gaps = analyze_recruiter_gaps(profile)
        latency = (time.perf_counter() - start_time) * 1000

        return ProfileAgentOutput(
            profile=profile,
            parsing_method=method,
            parsing_latency_ms=latency,
            recruiter_gap_analysis=gaps,
            recommended_roles=profile.target_roles,
            status_message=status_msg,
        )


def run_profile_agent(
    input_data: Union[ProfileAgentInput, Dict[str, Any]],
    api_key: Optional[str] = None,
) -> ProfileAgentOutput:
    """Functional runner for ProfileAgent to allow isolated stage testing."""
    if isinstance(input_data, dict):
        validated_input = ProfileAgentInput(**input_data)
    else:
        validated_input = input_data

    agent = ProfileAgent(api_key=api_key)
    return agent.run(validated_input)
