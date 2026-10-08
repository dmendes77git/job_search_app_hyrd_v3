"""
ProfileAgent (Stages 1 & 2): Candidate Intake, Resume Parsing & Entity Extraction.
Built using the google-antigravity framework with strict Pydantic v2 contracts.
"""

from __future__ import annotations

import logging
import re
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
# RECRUITER READINESS & REAL-TIME RADAR ENGINE (Feature P1-D)
# ============================================================================

POWER_VERBS = {
    "architected", "spearheaded", "accelerated", "orchestrated", "engineered",
    "deployed", "scaled", "overhauled", "optimized", "championed", "pioneered",
    "designed", "streamlined", "automated", "built", "developed", "executed",
    "mentored", "drove", "delivered", "transformed", "established", "instituted",
    "modernized", "founded", "led", "directed", "authored", "implemented",
    "consolidated", "maximized", "revamped", "reduced", "boosted", "negotiated",
}

PASSIVE_VERBS = {
    "assisted", "helped", "worked on", "responsible for", "participated in",
    "contributed to", "involved in", "handled", "supported", "tasked with",
    "aided", "served as", "duties included",
}

METRIC_PATTERNS = [
    re.compile(r"\b\d+(?:\.\d+)?%"),
    re.compile(r"[\$€£]\s*\d+(?:[,\.]\d+)?\s*(?:k|m|b|million|billion)?", re.IGNORECASE),
    re.compile(r"\b\d+[\.,]?\d*\s*(?:k|m|b|million|billion|users|customers|clients|queries|qps|rps|req/s|tps)\b", re.IGNORECASE),
    re.compile(r"\b\d+\s*(?:ms|s|sec|seconds|minutes|hours|days|weeks|months|years)\b", re.IGNORECASE),
    re.compile(r"\b\d+x\b", re.IGNORECASE),
    re.compile(r"\b(?:reduced|increased|boosted|saved|scaled|improved)\s+by\s+\d+", re.IGNORECASE),
    re.compile(r"\bteam of \d+|\b\d+\s*(?:engineers|developers|direct reports|people|members)\b", re.IGNORECASE),
]


def analyze_recruiter_gaps(profile: UserProfile) -> Dict[str, Any]:
    """Perform a 100% Recruiter Readiness benchmark audit against the extracted profile.
    Checks contact completeness, experience quantification, technical depth,
    action verb power ratio, metric density, and ATS formatting hygiene (Feature P1-D).
    """
    score = 100
    missing_elements: List[str] = []
    strengths: List[str] = []
    recommendations: List[str] = []

    # 1. Contact Info Audit
    contact_score = 100
    if not profile.email:
        score -= 15
        contact_score -= 35
        missing_elements.append("Email contact address missing")
        recommendations.append("Provide a direct professional email address for recruiter reachout.")
    else:
        strengths.append(f"Direct contact email verified ({profile.email}).")

    if not profile.phone:
        score -= 10
        contact_score -= 25
        missing_elements.append("Phone number missing")
        recommendations.append("Add a direct phone number to facilitate recruiter scheduling.")
    else:
        strengths.append("Direct phone number available.")

    if not profile.linkedin_url:
        score -= 10
        contact_score -= 20
        missing_elements.append("LinkedIn profile link not detected")
        recommendations.append("Include your public LinkedIn profile link for social proof validation.")
    else:
        strengths.append("LinkedIn profile detected.")
    contact_score = max(20.0, float(contact_score))

    # 2. Skills & Technical Depth
    skills_count = len(profile.extracted_skills)
    if skills_count < 4:
        score -= 20
        competency_score = 45.0
        missing_elements.append("Low technical skills density (< 4 detected)")
        recommendations.append("List at least 6-8 core technical competencies to improve ATS searchability.")
    else:
        competency_score = min(100.0, 60.0 + skills_count * 4.5)
        strengths.append(f"Strong competency footprint with {skills_count} recognized core skills.")

    # 3. Bullets, Action Verbs & Metric Quantification Analysis
    bullets = list(profile.experience_highlights or [])
    if not bullets and profile.raw_resume_text:
        # Extract potential bullets from raw resume text
        for line in profile.raw_resume_text.splitlines():
            sline = line.strip()
            if sline.startswith(("-", "*", "•", "–")) and len(sline) > 15:
                bullets.append(sline.lstrip("-*•– "))

    # 3a. Experience Quantification
    if not bullets:
        score -= 15
        quantification_density_pct = 0.0
        action_verb_power_index = 50.0
        missing_elements.append("Missing quantified career accomplishments")
        recommendations.append("Add 3-5 bullet points with metrics (e.g. '% reduction', '$ savings', 'users served').")
    else:
        quantified_count = sum(1 for b in bullets if any(p.search(b) for p in METRIC_PATTERNS))
        quantification_density_pct = round((quantified_count / len(bullets)) * 100.0, 1)

        if quantification_density_pct >= 60.0:
            strengths.append(f"High metric density: {quantification_density_pct}% of accomplishments feature hard numbers.")
        elif quantification_density_pct >= 30.0:
            strengths.append(f"Moderate metric quantification: {quantification_density_pct}% with KPI evidence.")
        else:
            score -= 10
            missing_elements.append(f"Low metric density ({quantification_density_pct}%). Recruiters favor quantified impact.")
            recommendations.append("Use 1-Click Auto-Quantify to inject metric benchmarks into your experience statements.")

        # 3b. Action Verb Power Index
        power_hits = 0
        passive_hits = 0
        for b in bullets:
            words = [w.strip(".,;:()[]\"'").lower() for w in b.split()[:8]]
            for w in words:
                if w in POWER_VERBS:
                    power_hits += 1
                elif w in PASSIVE_VERBS:
                    passive_hits += 1

        if (power_hits + passive_hits) > 0:
            power_ratio = power_hits / (power_hits + passive_hits)
            action_verb_power_index = round(min(100.0, max(25.0, power_ratio * 100.0)), 1)
        else:
            action_verb_power_index = 75.0

        if action_verb_power_index >= 75.0:
            strengths.append(f"Strong leadership voice: {action_verb_power_index}% Action Verb Power Index.")
        else:
            recommendations.append("Upgrade passive verbs ('worked on', 'assisted') to executive power verbs ('architected', 'spearheaded').")

    # 4. ATS Formatting Hygiene
    raw = profile.raw_resume_text or ""
    ats_issues: List[str] = []
    hygiene_score = 100

    special_glyphs = [c for c in raw if c in "★●■➔✔►◆§▲▼◈✓✕"]
    if special_glyphs:
        hygiene_score -= 15
        ats_issues.append(f"Non-standard Unicode symbols detected ({len(special_glyphs)} instances e.g. '{special_glyphs[0]}'). These can corrupt older ATS parsers.")

    if "|---" in raw or raw.count(" | ") > 8:
        hygiene_score -= 15
        ats_issues.append("Complex multi-column or table formatting detected. Tables often break ATS parsers (Taleo, iCIMS).")

    if "\t\t" in raw:
        hygiene_score -= 10
        ats_issues.append("Heavy tab character indentation detected; single space formatting is recommended.")

    non_ascii_chars = [c for c in raw if ord(c) > 127 and c not in "éáíóúñãõç€£•—–“”‘’"]
    if len(non_ascii_chars) > 6:
        hygiene_score -= 10
        ats_issues.append("Unusual non-ASCII encoding artifacts detected in resume text.")

    if not ats_issues:
        ats_issues.append("No ATS formatting friction detected. Resume text is clean and parser-safe.")

    ats_hygiene_score = max(30, hygiene_score)

    readiness_score = max(20, min(100, score))
    readiness_label = (
        "100% Market Ready" if readiness_score >= 90
        else "Strong Contender" if readiness_score >= 75
        else "Calibration Needed"
    )

    radar_metrics = {
        "Action Verb Power": action_verb_power_index,
        "Metric Quantification": quantification_density_pct,
        "ATS Formatting Hygiene": float(ats_hygiene_score),
        "Contact Completeness": contact_score,
        "Technical Competency Depth": competency_score,
    }

    # Actionable 1-Click Remediations
    actionable_remediations: List[Dict[str, str]] = []
    if not profile.email:
        actionable_remediations.append({
            "gap": "Missing Email",
            "category": "contact",
            "action": "Add Contact Email",
            "suggested_fix": "Provide a clean personal email in profile header.",
        })
    if not profile.linkedin_url:
        actionable_remediations.append({
            "gap": "Missing LinkedIn",
            "category": "social",
            "action": "Add LinkedIn Link",
            "suggested_fix": "Add https://linkedin.com/in/username to boost recruiter credibility.",
        })
    if quantification_density_pct < 60.0:
        actionable_remediations.append({
            "gap": f"Low Metric Density ({quantification_density_pct}%)",
            "category": "quantification",
            "action": "⚡ 1-Click Auto-Quantify Bullet",
            "suggested_fix": "Transform passive bullets into STAR-quantified statements.",
        })
    if action_verb_power_index < 70.0:
        actionable_remediations.append({
            "gap": f"Passive Voice ({action_verb_power_index}% Power Index)",
            "category": "verbs",
            "action": "Upgrade to Leadership Action Verbs",
            "suggested_fix": "Replace 'worked on' or 'assisted' with 'architected', 'spearheaded', or 'engineered'.",
        })

    return {
        "readiness_score": readiness_score,
        "readiness_label": readiness_label,
        "missing_elements": missing_elements,
        "strengths": strengths,
        "recommendations": recommendations,
        "action_verb_power_index": action_verb_power_index,
        "quantification_density_pct": quantification_density_pct,
        "ats_hygiene_score": ats_hygiene_score,
        "ats_hygiene_issues": ats_issues,
        "radar_metrics": radar_metrics,
        "actionable_remediations": actionable_remediations,
    }


def auto_quantify_bullet(
    bullet: str,
    context: Optional[str] = None,
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    1-Click Auto-Remediation (Feature P1-D):
    Transforms passive, vague bullet points into active, quantified STAR accomplishments.
    Uses Gemini when api_key is available, with deterministic STAR heuristic transformer fallback.
    """
    cleaned = (bullet or "").strip()
    if not cleaned:
        return {
            "original": "",
            "quantified": "",
            "verb_upgraded": "",
            "metrics_added": [],
            "star_components": {"situation_task": "", "action": "", "result": ""},
            "status": "empty_input",
        }

    # Attempt Gemini call if API key provided
    if api_key:
        try:
            from google import genai
            client = genai.Client(api_key=api_key)
            prompt = (
                "You are an executive tech resume writer. Rewrite the following resume bullet into a high-impact, "
                "STAR-quantified statement. Begin with an executive power verb (e.g. Architected, Spearheaded, Engineered). "
                "Incorporate realistic quantified metrics (percentage improvement, latency cut, dollar savings, or scale). "
                "Return ONLY the rewritten bullet sentence without markdown formatting or commentary.\n\n"
                f"Original bullet: {cleaned}\n"
                f"Context: {context or 'Software Engineering'}"
            )
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
            )
            rewritten = response.text.strip().lstrip("-*• ")
            if rewritten and len(rewritten) > 20:
                first_word = rewritten.split()[0].rstrip(":,.")
                return {
                    "original": cleaned,
                    "quantified": rewritten,
                    "verb_upgraded": first_word,
                    "metrics_added": ["AI-calibrated quantified impact"],
                    "star_components": {
                        "situation_task": context or "Production engineering demand",
                        "action": rewritten,
                        "result": "Quantified efficiency & reliability gain",
                    },
                    "status": "success_gemini",
                }
        except Exception as exc:
            logger.warning(f"Live Gemini auto-quantify failed ({exc}), falling back to deterministic transformer.")

    # Deterministic STAR Transformer Fallback
    b_lower = cleaned.lower()
    metrics_added = []

    # Detect domain & action
    if any(k in b_lower for k in ["api", "backend", "fastapi", "python", "service", "microservice", "database", "sql"]):
        power_verb = "Architected and deployed high-throughput backend services"
        metric_str = "reducing p99 API response latency by 45% while scaling transaction volume to 3.2M daily queries"
        metrics_added = ["45% p99 latency reduction", "3.2M daily queries"]
    elif any(k in b_lower for k in ["cloud", "k8s", "kubernetes", "docker", "infra", "aws", "gcp", "devops"]):
        power_verb = "Spearheaded cloud infrastructure automation"
        metric_str = "slashing deployment cycle times by 60% and reducing monthly cloud compute expenses by $24,000"
        metrics_added = ["60% faster deployments", "$24,000 monthly cloud cost savings"]
    elif any(k in b_lower for k in ["ai", "llm", "ml", "model", "pipeline", "agent", "deep learning"]):
        power_verb = "Engineered autonomous AI inference pipelines"
        metric_str = "improving prompt-completion throughput by 3.4x with 99.95% availability across production workloads"
        metrics_added = ["3.4x throughput boost", "99.95% system availability"]
    elif any(k in b_lower for k in ["lead", "manage", "team", "mentor", "agile", "sprint", "hiring"]):
        power_verb = "Orchestrated cross-functional engineering initiatives"
        metric_str = "increasing sprint delivery velocity by 32% and mentoring 6 junior engineers to senior promotions"
        metrics_added = ["32% sprint velocity gain", "6 engineers mentored"]
    elif any(k in b_lower for k in ["frontend", "ui", "ux", "react", "streamlit", "web", "css"]):
        power_verb = "Designed and shipped responsive user interfaces"
        metric_str = "accelerating user onboarding conversion by 28% and eliminating clientside UI render latency"
        metrics_added = ["28% conversion lift", "sub-100ms render speeds"]
    else:
        power_verb = "Spearheaded core technical initiatives"
        metric_str = "driving a 35% improvement in operational throughput and saving 15+ engineering hours weekly"
        metrics_added = ["35% operational throughput boost", "15 hrs/week saved"]

    # Strip passive prefixes if present
    stripped = cleaned
    for prefix in [
        "assisted with", "assisted", "helped to", "helped with", "helped",
        "worked on", "responsible for", "participated in", "contributed to",
        "involved in", "tasked with", "handled", "managed", "supported", "aided",
        "served as", "duties included",
    ]:
        if stripped.lower().startswith(prefix):
            stripped = stripped[len(prefix):].strip(" ,;:-")
            break

    stripped = stripped.rstrip(".,;:- ")
    quantified_bullet = f"{power_verb} for {stripped}, {metric_str}."

    return {
        "original": cleaned,
        "quantified": quantified_bullet,
        "verb_upgraded": power_verb.split()[0],
        "metrics_added": metrics_added,
        "star_components": {
            "situation_task": stripped,
            "action": power_verb,
            "result": metric_str,
        },
        "status": "success_deterministic",
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
        self.tool_runner.register(auto_quantify_bullet, "auto_quantify_bullet")

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
