"""
Recruiter Cold Outreach & LinkedIn Message Drafter Agent.
Synthesizes high-conversion, multi-channel outreach campaigns targeted at hiring managers,
recruiters, and company insiders.

Features:
1. LinkedIn Connection Request Note (strictly <= 300 characters with live budget counter).
2. Hiring Manager Direct Cold Email (concise, value-first, problem-solving focus).
3. Talent Acquisition / Recruiter InMail (requisition match, key skills, clear CTA).
4. Warm Alumni & Internal Referral Request (respectful, advice-seeking, culture inquiry).
5. Post-Interview Follow-Up & Thank You Note (reiteration of excitement, value reinforcement).
6. Microsoft Word (.docx) export for the entire campaign.
"""

import io
import os
import re
from src.utils.document_exporter import _add_formatted_runs, create_outreach_docx
from src.utils.gemini_client import generate_gemini_content


TONE_OPTIONS = [
    "Direct & Value-Focused",
    "Professional & Authoritative",
    "Warm, Enthusiastic & Conversational",
]


def generate_outreach_campaign(
    job: Dict[str, Any],
    profile: Dict[str, Any],
    recipient_name: str = "Hiring Manager",
    recipient_title: str = "Team Leader",
    custom_hook: str = "",
    tone: str = "Direct & Value-Focused",
    api_key: Optional[str] = None,
    preferred_model: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generate a full set of outreach templates for a target job opportunity.
    Uses Gemini API when configured, with rich, role-specific deterministic fallback.
    """
    candidate_name = (profile.get("full_name") or "Candidate").strip()
    job_title = job.get("title", "Target Role")
    company = job.get("company", "Target Company")
    location = job.get("location", "Remote")
    matched_skills = job.get("matched_skills", [])
    skills_str = ", ".join(matched_skills[:4]) if matched_skills else "distributed systems, cloud architecture"
    exp_level = profile.get("years_of_experience", "Senior")

    r_name = recipient_name.strip() if recipient_name.strip() else "Hiring Manager"
    r_title = recipient_title.strip() if recipient_title.strip() else "Hiring Manager"
    hook_str = f"Personal context / hook: {custom_hook.strip()}" if custom_hook.strip() else "No specific hook provided."

    prompt = f"""You are an elite executive career strategist specializing in high-response cold outreach.
Draft a comprehensive 5-part cold outreach campaign for a candidate reaching out regarding this role:

TARGET POSITION & COMPANY:
- Job Title: {job_title}
- Company: {company}
- Location: {location}
- Key Required Competencies: {skills_str}

RECIPIENT & CONTEXT:
- Recruiter / Contact Name: {r_name}
- Recruiter / Contact Title: {r_title}
- {hook_str}
- Desired Tone: {tone}

CANDIDATE:
- Candidate Name: {candidate_name}
- Seniority: {exp_level}
- Core Skills: {skills_str}

Please generate the following 5 distinct outreach messages in clean Markdown with the exact section headings below:

## 1. LinkedIn Connection Request Note
CRITICAL CONSTRAINT: The text must be UNDER 280 CHARACTERS total (LinkedIn hard limit is 300 characters).
Make it punchy, personalized, and mention the target role.

## 2. Hiring Manager Direct Cold Email
- Subject: [Punchy, high-open-rate subject line]
- Body: 100-140 words. Focus on solving team pain points, 1 key measurable achievement, and a low-friction 10-minute chat call to action.

## 3. Recruiter & Talent Acquisition InMail
- Subject: [Requisition reference subject line]
- Body: 120-160 words. Clear alignment with {company}'s requirements, mention of application submission, core qualifications, and timeline inquiry.

## 4. Warm Internal Referral / Insider Request
- Subject: [Informational coffee / quick question subject line]
- Body: 100-130 words. Respectful outreach to an existing team member or alumnus asking for 5 minutes of advice on engineering culture or team direction.

## 5. Post-Interview Follow-Up & Thank You Note
- Subject: [Thank you & follow-up subject line]
- Body: 120-150 words. Sent within 24 hours of an interview. Reiterate excitement, reference a specific topic discussed, and reinforce fit.
"""

    gemini_response = generate_gemini_content(
        prompt, api_key=api_key, preferred_model=preferred_model
    )

    if gemini_response and "## 1." in gemini_response:
        parsed = _parse_outreach_response(
            gemini_response, candidate_name, company, job_title, r_name
        )
        parsed["raw_markdown"] = gemini_response
        return parsed

    # Deterministic domain-tailored fallback
    return _build_fallback_outreach_campaign(
        job, profile, r_name, r_title, custom_hook, tone
    )


def _parse_outreach_response(
    text: str, candidate_name: str, company: str, job_title: str, r_name: str
) -> Dict[str, Any]:
    """Parse Gemini markdown output into structured message objects."""
    sections = {
        "linkedin_note": "",
        "hiring_manager_email": {"subject": "", "body": ""},
        "recruiter_inmail": {"subject": "", "body": ""},
        "referral_request": {"subject": "", "body": ""},
        "thank_you_note": {"subject": "", "body": ""},
    }

    # Extract sections by header
    s1 = _extract_section(text, "## 1. LinkedIn Connection Request Note", "## 2.")
    s2 = _extract_section(text, "## 2. Hiring Manager Direct Cold Email", "## 3.")
    s3 = _extract_section(text, "## 3. Recruiter & Talent Acquisition InMail", "## 4.")
    s4 = _extract_section(text, "## 4. Warm Internal Referral / Insider Request", "## 5.")
    s5 = _extract_section(text, "## 5. Post-Interview Follow-Up & Thank You Note", None)

    # Process LinkedIn note and enforce strict <= 300 chars
    clean_li = s1.replace("```", "").strip()
    clean_li = re.sub(r"^(Note|Text|Message):\s*", "", clean_li, flags=re.IGNORECASE)
    if len(clean_li) > 298:
        clean_li = clean_li[:295].rsplit(" ", 1)[0] + "..."

    sections["linkedin_note"] = {
        "text": clean_li,
        "char_count": len(clean_li),
    }

    sections["hiring_manager_email"] = _parse_subject_and_body(
        s2, f"Quick question re: {company} {job_title} - {candidate_name}"
    )
    sections["recruiter_inmail"] = _parse_subject_and_body(
        s3, f"Application: {job_title} at {company} - {candidate_name}"
    )
    sections["referral_request"] = _parse_subject_and_body(
        s4, f"Quick question about {company} & engineering culture - {candidate_name}"
    )
    sections["thank_you_note"] = _parse_subject_and_body(
        s5, f"Thank you - {job_title} interview follow-up - {candidate_name}"
    )

    return sections


def _extract_section(text: str, start_header: str, end_header: Optional[str]) -> str:
    """Extract markdown text between two headers."""
    if start_header not in text:
        return ""
    start_pos = text.find(start_header) + len(start_header)
    if end_header and end_header in text[start_pos:]:
        end_pos = text.find(end_header, start_pos)
        return text[start_pos:end_pos].strip()
    return text[start_pos:].strip()


def _parse_subject_and_body(section_text: str, default_subject: str) -> Dict[str, str]:
    """Parse out Subject: line and Body text from a markdown block."""
    lines = section_text.splitlines()
    subject = default_subject
    body_lines: List[str] = []
    subject_found = False

    for line in lines:
        line_s = line.strip()
        if not subject_found and re.match(r"^[-*#\s]*Subject:\s*", line_s, re.IGNORECASE):
            subject = re.sub(r"^[-*#\s]*Subject:\s*", "", line_s, flags=re.IGNORECASE).strip()
            subject = subject.replace("**", "").replace('"', "").replace("`", "")
            subject_found = True
        else:
            body_lines.append(line)

    body = "\n".join(body_lines).strip()
    word_count = len(body.split())
    return {
        "subject": subject,
        "body": body,
        "word_count": word_count,
    }


def _build_fallback_outreach_campaign(
    job: Dict[str, Any],
    profile: Dict[str, Any],
    r_name: str,
    r_title: str,
    custom_hook: str,
    tone: str,
) -> Dict[str, Any]:
    """High-quality deterministic fallback campaign."""
    cand_name = (profile.get("full_name") or "Candidate").strip()
    company = job.get("company", "Target Company")
    title = job.get("title", "Target Role")
    skills = job.get("matched_skills", [])
    skill_lead = skills[0] if skills else "scalable architecture"
    skill_secondary = skills[1] if len(skills) > 1 else "production engineering"
    first_name = r_name.split()[0] if r_name and r_name != "Hiring Manager" else "there"

    hook_prefix = f"I've been closely following {company}'s growth, especially {custom_hook}. " if custom_hook else f"I've been following {company}'s impressive engineering developments. "

    # 1. LinkedIn Note (<300 chars)
    li_text = (
        f"Hi {first_name}—saw your work leading {r_title} at {company}. "
        f"I'm a {title.split()[0]} specialist focused on {skill_lead} & {skill_secondary}. "
        f"Just applied for the {title} opening and would love to connect and follow your team's work!"
    )
    if len(li_text) > 298:
        li_text = (
            f"Hi {first_name}—saw your work at {company}. I'm a specialist in {skill_lead} "
            f"and just applied for the {title} opening. Would love to connect and follow your team's work!"
        )
    if len(li_text) > 298:
        li_text = li_text[:295].rsplit(" ", 1)[0] + "..."

    # 2. Hiring Manager Cold Email
    hm_subj = f"Question regarding {title} & {company}'s {skill_lead} initiatives"
    hm_body = f"""Hi {first_name},

{hook_prefix}I noticed the team is hiring for the {title} position and wanted to reach out directly.

Over the past several years, I've specialized in {skill_lead} and {skill_secondary}—most recently designing high-availability systems that improved operational efficiency and reduced latency across critical workloads.

Given {company}'s current trajectory, I'm particularly interested in how your team is tackling scale in this area. I've formally submitted my application, but I wanted to share a quick hello.

Do you have 10 minutes next week for a brief conversation on the team's roadmap and where someone with my background could hit the ground running?

Best regards,

{cand_name}
LinkedIn / Portfolio: linkedin.com/in/{cand_name.lower().replace(' ', '')}"""

    # 3. Recruiter InMail
    rec_subj = f"Application follow-up: {title} ({cand_name})"
    rec_body = f"""Hi {first_name},

Hope you are having a productive week.

I recently submitted my application for the {title} role at {company} and wanted to reach out to introduce myself.

My background centers on {skill_lead}, {skill_secondary}, and cross-functional execution. I have a proven track record delivering mission-critical projects that match {company}'s current requirements.

I've attached my tailored resume for convenience. Could you let me know if the team is actively reviewing candidates for this opening, or who the best person to connect with would be?

Thank you for your time and guidance!

Warmly,

{cand_name}"""

    # 4. Warm Internal Referral / Insider Request
    ref_subj = f"Quick question about life & engineering at {company} - {cand_name}"
    ref_body = f"""Hi {first_name},

Hope you're doing well! I came across your profile while researching {company} and was really impressed by your team's work.

I'm currently exploring the {title} opening at {company}. Given your experience there, I would be immensely grateful for 5–10 minutes of your perspective on the team culture, day-to-day challenges, and what leadership values most.

No pressure at all if you're swamped, but any brief insights would be invaluable as I go through the interview process.

Thanks so much,

{cand_name}"""

    # 5. Thank You Note
    ty_subj = f"Thank you for our conversation - {title} at {company}"
    ty_body = f"""Hi {first_name},

Thank you very much for taking the time to speak with me today about the {title} role at {company}.

I truly enjoyed learning more about the team's upcoming milestones, particularly our discussion around {skill_lead} and operational scaling. Our conversation reinforced my strong enthusiasm for joining {company} and contributing to these initiatives.

Please let me know if there are any additional materials, work samples, or references I can provide to support the evaluation.

Looking forward to the next steps!

Best regards,

{cand_name}"""

    full_md = f"""# Recruiter Cold Outreach & LinkedIn Campaign
**Target Role:** {title} at {company}
**Target Recipient:** {r_name} ({r_title})
**Tone:** {tone}

---

## 1. LinkedIn Connection Request Note ({len(li_text)}/300 chars)
{li_text}

---

## 2. Hiring Manager Direct Cold Email
**Subject:** {hm_subj}

{hm_body}

---

## 3. Recruiter & Talent Acquisition InMail
**Subject:** {rec_subj}

{rec_body}

---

## 4. Warm Internal Referral / Insider Request
**Subject:** {ref_subj}

{ref_body}

---

## 5. Post-Interview Follow-Up & Thank You Note
**Subject:** {ty_subj}

{ty_body}
"""

    return {
        "linkedin_note": {"text": li_text, "char_count": len(li_text)},
        "hiring_manager_email": {"subject": hm_subj, "body": hm_body, "word_count": len(hm_body.split())},
        "recruiter_inmail": {"subject": rec_subj, "body": rec_body, "word_count": len(rec_body.split())},
        "referral_request": {"subject": ref_subj, "body": ref_body, "word_count": len(ref_body.split())},
        "thank_you_note": {"subject": ty_subj, "body": ty_body, "word_count": len(ty_body.split())},
        "raw_markdown": full_md,
    }
