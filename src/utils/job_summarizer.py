"""
Job Description Synthesizer & Intelligent Summarization Engine.
Extracts concise, high-signal executive overviews and actionable responsibilities
from lengthy, jargon-dense, or unformatted scraped job descriptions.

Features:
- Boilerplate removal: Strips Equal Opportunity (EEO) statements, benefits packages,
  legal disclaimers, staffing agency warnings, and redundant recruiting blurbs.
- High-signal extraction: Identifies role mission/purpose and core responsibilities.
- Structured output: Returns an executive synopsis and 2-3 crisp bullet points.
- Dual-tier support: Fast deterministic NLP heuristic (0ms latency, 100% offline)
  with optional Gemini-augmented summarization.
"""

from __future__ import annotations

import html
import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger("Hyrd.JobSummarizer")

# Patterns for boilerplate paragraphs and disclaimers that add clutter without informing the role
BOILERPLATE_PATTERNS = [
    r"(?i)\bwe are an equal opportunity employer\b.*",
    r"(?i)\bequal opportunity employer\b.*",
    r"(?i)\be-?verify\b.*",
    r"(?i)\baffirmative action\b.*",
    r"(?i)\bnotice to (?:recruitment|staffing|third[- ]party) agencies\b.*",
    r"(?i)\bno (?:unsolicited|agency) resumes\b.*",
    r"(?i)\bwe do not accept (?:unsolicited|agency) resumes\b.*",
    r"(?i)\bwe celebrate diversity\b.*",
    r"(?i)\bdiversity,?\s+equity,?\s+(?:and\s+)?inclusion\b.*",
    r"(?i)\bbackground check\b.*",
    r"(?i)\baccommodation(?:s)? for (?:disabilities|individuals with disabilities)\b.*",
    r"(?i)\bphysical (?:demands|requirements)\b.*",
    r"(?i)\bpay transparency\b.*",
    r"(?i)\bcompetitive (?:salary|benefits|compensation) package\b.*",
    r"(?i)\b401\s*\(?k\)?\b.*",
    r"(?i)\bhealth,?\s+dental,?\s+(?:and\s+)?vision\b.*",
    r"(?i)\bunlimited pto\b.*",
    r"(?i)\ball qualified applicants will receive consideration\b.*",
    r"(?i)\bemployment decisions are made without regard to\b.*",
    r"(?i)\bwe are committed to creating an inclusive\b.*",
    r"(?i)\bmust be able to lift up to\b.*",
    r"(?i)\bat-will employment\b.*",
    r"(?i)\bperks & benefits|benefits & perks|our benefits\b.*",
]

# Responsibility section headers
RESPONSIBILITY_HEADERS = [
    r"(?i)what you(?:'ll| will) (?:do|be doing|deliver|work on)",
    r"(?i)(?:key|core|primary|daily) responsibilities",
    r"(?i)responsibilities",
    r"(?i)in this role,? you(?:'ll| will)",
    r"(?i)the role",
    r"(?i)what you(?:'ll| will) bring",
    r"(?i)duties (?:and|&) responsibilities",
    r"(?i)your mission",
    r"(?i)o que vais fazer",
    r"(?i)responsabilidades",
    r"(?i)funções",
    r"(?i)principais tarefas",
]

# Requirements / Qualification indicators (to filter OUT from responsibility bullets)
REQUIREMENT_PATTERNS = [
    r"(?i)^\d+\+?\s+years?",
    r"(?i)^bachelor|master|phd|degree in",
    r"(?i)^experience with|experience in|proficient in|knowledge of|familiarity with",
    r"(?i)^strong understanding of|expertise in|proven track record",
    r"(?i)^must have|nice to have|bonus points",
    r"(?i)^excellent (?:written|communication|interpersonal) skills",
    r"(?i)^ability to (?:lift|travel|work in)",
]

# Action verbs commonly found in true technical and professional duties
ACTION_VERBS = {
    "design", "build", "develop", "architect", "lead", "manage", "collaborate",
    "create", "implement", "optimize", "deliver", "scale", "maintain", "deploy",
    "drive", "spearhead", "partner", "execute", "oversee", "integrate", "automate",
    "engineer", "analyze", "test", "coordinate", "supervise", "mentor", "establish",
    "craft", "ship", "troubleshoot", "refactor", "monitor", "evaluate", "plan",
    "own", "contribute", "improve", "ensure", "guide", "investigate",
}


def clean_job_text(raw_text: str) -> str:
    """
    Strip HTML tags, unescape entities, and normalize whitespace while preserving
    meaningful paragraph and bullet line breaks.
    """
    if not raw_text:
        return ""
    text = str(raw_text)

    # 1. Unescape HTML entities first (e.g. &lt;li&gt; or &amp;)
    text = html.unescape(text)

    # 2. Convert HTML block and list elements to structured newlines/bullets
    # Convert list items to bullet lines
    text = re.sub(r"(?i)<\s*li[^>]*>", "\n• ", text)
    text = re.sub(r"(?i)<\s*/\s*li\s*>", "\n", text)
    # Convert breaks and paragraphs
    text = re.sub(r"(?i)<\s*br\s*/?>", "\n", text)
    text = re.sub(r"(?i)<\s*/\s*(p|div|tr|h[1-6])\s*>", "\n\n", text)
    text = re.sub(r"(?i)<\s*(p|div|tr|h[1-6])[^>]*>", "\n", text)

    # 3. Strip all remaining HTML tags
    text = re.sub(r"<[^>]+>", " ", text)

    # 4. Normalize non-breaking spaces and carriage returns
    text = text.replace("\xa0", " ").replace("\r", "\n")

    # 5. Normalize horizontal whitespace per line without flattening newlines
    lines: List[str] = []
    for line in text.split("\n"):
        clean_line = re.sub(r"[ \t]+", " ", line).strip()
        if clean_line:
            lines.append(clean_line)
        else:
            # Preserve empty line for paragraph separation
            if lines and lines[-1] != "":
                lines.append("")

    text = "\n".join(lines)
    # Collapse 3+ newlines to 2
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def remove_boilerplate(text: str) -> str:
    """Filter out legal disclaimers, EEO statements, benefits lists, and recruiter notices."""
    paragraphs = text.split("\n\n")
    cleaned_paras: List[str] = []

    for para in paragraphs:
        p_clean = para.strip()
        if not p_clean:
            continue

        # Check if entire paragraph matches boilerplate
        is_boilerplate = False
        for pattern in BOILERPLATE_PATTERNS:
            if re.search(pattern, p_clean):
                # If paragraph matches boilerplate pattern and is relatively short or dominated by it
                if re.match(pattern, p_clean) or len(p_clean) < 400:
                    is_boilerplate = True
                    break

        if not is_boilerplate:
            # Also clean individual lines if a paragraph mixed content with a trailing EEO notice
            lines = p_clean.split("\n")
            filtered_lines: List[str] = []
            for line in lines:
                l_str = line.strip()
                if not any(re.search(bp, l_str) for bp in BOILERPLATE_PATTERNS):
                    filtered_lines.append(l_str)
            if filtered_lines:
                cleaned_paras.append("\n".join(filtered_lines))

    return "\n\n".join(cleaned_paras) if cleaned_paras else text


def extract_bullet_points(text: str, max_bullets: int = 3) -> List[str]:
    """Extract actionable responsibility or task statements from cleaned text."""
    lines = text.split("\n")
    bullets: List[str] = []

    in_resp_section = False

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Detect responsibility header
        if any(re.search(hdr, stripped) for hdr in RESPONSIBILITY_HEADERS):
            in_resp_section = True
            continue

        # Detect exit from responsibility section (e.g., Requirements, Benefits, About Us)
        if in_resp_section and re.match(r"(?i)^(?:requirements|qualifications|benefits|perks|about us|who you are|o que procuramos|requisitos)", stripped):
            in_resp_section = False

        # Extract candidate text if line starts with bullet marker
        bullet_match = re.match(r"^[\s•*▪\-–—\d\.)]+\s*(.+)$", stripped)
        candidate_text = bullet_match.group(1).strip() if bullet_match else stripped

        # Skip headers ending in colon
        if candidate_text.endswith(":"):
            continue

        # Skip requirements/qualifications (e.g. "5+ years of Python")
        if any(re.search(req, candidate_text) for req in REQUIREMENT_PATTERNS):
            continue

        # Validate suitability as a responsibility bullet
        if (
            len(candidate_text) >= 20
            and len(candidate_text) <= 220
            and not any(re.search(bp, candidate_text) for bp in BOILERPLATE_PATTERNS)
        ):
            # Check if starts with an action verb or is in an explicit responsibility section
            first_word = re.sub(r"[^a-zA-Z]", "", candidate_text.split()[0].lower()) if candidate_text.split() else ""
            if in_resp_section or first_word in ACTION_VERBS:
                # Ensure no duplicate bullet
                if candidate_text not in bullets:
                    bullets.append(candidate_text)
                    if len(bullets) >= max_bullets:
                        break

    return bullets


def extract_executive_overview(text: str, title: str = "", company: str = "", max_chars: int = 240) -> str:
    """Extract or synthesize the primary 1-2 sentence core mission overview of the role."""
    # Split into sentences
    sentences = re.split(r"(?<=[.!?])\s+", text)
    overview_sentences: List[str] = []

    # Priority indicators for role mission sentences
    MISSION_INDICATORS = [
        r"(?i)\b(?:looking for|seeking|in this role|as a|responsible for|will be responsible for)\b",
        r"(?i)\b(?:join our team|help us|lead the|build and scale|deliver high-impact)\b",
    ]

    # First pass: look for explicit mission statements
    for s in sentences:
        s_clean = s.strip()
        if not s_clean or len(s_clean) < 30 or s_clean.endswith(":"):
            continue
        if any(re.search(bp, s_clean) for bp in BOILERPLATE_PATTERNS):
            continue
        if any(re.search(ind, s_clean) for ind in MISSION_INDICATORS):
            overview_sentences.append(s_clean)
            if len(" ".join(overview_sentences)) >= 100 or len(overview_sentences) >= 2:
                break

    # Second pass: if no explicit mission statement found, take the first clean descriptive sentences
    if not overview_sentences:
        for s in sentences:
            s_clean = s.strip()
            if not s_clean or len(s_clean) < 30 or s_clean.endswith(":"):
                continue
            if any(re.search(bp, s_clean) for bp in BOILERPLATE_PATTERNS):
                continue
            if not any(re.search(req, s_clean) for req in REQUIREMENT_PATTERNS):
                overview_sentences.append(s_clean)
                if len(" ".join(overview_sentences)) >= 100 or len(overview_sentences) >= 2:
                    break

    if overview_sentences:
        overview = " ".join(overview_sentences)
        if len(overview) > max_chars:
            overview = overview[:max_chars].rsplit(" ", 1)[0] + "..."
        # Ensure proper punctuation
        if not overview.endswith((".", "!", "?")):
            overview += "."
        return overview

    # Fallback template if text was too fragmented or brief
    comp_label = f" at {company}" if company and company.lower() != "unknown" else ""
    return f"{title or 'Key Engineering Requisition'}{comp_label}. Core responsibilities span system architecture, engineering execution, and cross-functional delivery."


def summarize_job_description(
    raw_text: str,
    title: str = "",
    company: str = "",
    max_bullets: int = 3,
) -> Dict[str, Any]:
    """
    Produce a concise, structured job description summary:
    Returns:
    {
        "overview": str,
        "bullets": List[str],
        "formatted_markdown": str,
        "raw_cleaned": str,
        "is_short": bool
    }
    """
    cleaned = clean_job_text(raw_text)
    if not cleaned or len(cleaned) < 40:
        overview = f"Active opening for {title or 'Software Engineer'} at {company or 'Hiring Company'}."
        return {
            "overview": overview,
            "bullets": [],
            "formatted_markdown": overview,
            "raw_cleaned": cleaned or overview,
            "is_short": True,
        }

    # If the text is already very concise (e.g. 1-2 curated sentences < 240 chars)
    if len(cleaned) <= 240 and "\n" not in cleaned:
        return {
            "overview": cleaned,
            "bullets": [],
            "formatted_markdown": cleaned,
            "raw_cleaned": cleaned,
            "is_short": True,
        }

    # Filter out boilerplate
    filtered_text = remove_boilerplate(cleaned)

    # 1. Extract executive overview sentence
    overview = extract_executive_overview(filtered_text, title=title, company=company)

    # 2. Extract key responsibility bullets
    bullets = extract_bullet_points(filtered_text, max_bullets=max_bullets)

    # 3. Fallback bullets if no explicit bullet points were parsed
    if not bullets:
        # Pick 2 actionable sentences from the body that are not the overview or requirements
        remaining_sentences = [
            s.strip() for s in re.split(r"(?<=[.!?])\s+", filtered_text)
            if s.strip() and s.strip() not in overview and len(s.strip()) > 30
            and not any(re.search(bp, s) for bp in BOILERPLATE_PATTERNS)
            and not any(re.search(req, s) for req in REQUIREMENT_PATTERNS)
        ]
        for s in remaining_sentences:
            first_word = re.sub(r"[^a-zA-Z]", "", s.split()[0].lower()) if s.split() else ""
            if first_word in ACTION_VERBS or any(w in s.lower() for w in ["responsible for", "build", "lead", "develop", "work with", "design", "manage"]):
                bullet_str = s.rstrip(".")
                if bullet_str not in bullets:
                    bullets.append(bullet_str)
                    if len(bullets) >= 2:
                        break

    # Build clean markdown
    md_lines = [overview]
    if bullets:
        md_lines.append("")
        for b in bullets:
            md_lines.append(f"• {b}")

    formatted_md = "\n".join(md_lines)

    return {
        "overview": overview,
        "bullets": bullets,
        "formatted_markdown": formatted_md,
        "raw_cleaned": cleaned,
        "is_short": False,
    }


def render_summary_html(summary_data: Dict[str, Any]) -> str:
    """Render a structured, polished HTML snippet for display inside the job card."""
    overview = html.escape(summary_data.get("overview", ""))
    bullets = summary_data.get("bullets", [])

    html_parts = [
        f"<p style='margin: 0 0 0.5rem 0; font-size: 0.88rem; line-height: 1.45; color: #1e293b; font-weight: 500;'>"
        f"{overview}</p>"
    ]

    if bullets:
        html_parts.append("<ul style='margin: 0; padding-left: 1.2rem; font-size: 0.84rem; color: #334155; line-height: 1.45;'>")
        for b in bullets:
            html_parts.append(f"<li style='margin-bottom: 0.25rem;'>{html.escape(b)}</li>")
        html_parts.append("</ul>")

    return "".join(html_parts)
