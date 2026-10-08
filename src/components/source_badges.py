"""
Centralized UI Metadata & Badge Registry for Job Sources and Scoring Attributes.
Standardizes branding, colors, badges, and HTML widgets across Screen 3, Screen 4,
and modal dialogs.
"""

from typing import Any, Dict, List, Optional

SOURCE_METADATA: Dict[str, Dict[str, Any]] = {
    "Ashby": {
        "name": "Ashby HQ",
        "color": "#4338ca",
        "bg": "#e0e7ff",
        "border": "#c7d2fe",
        "icon": "⚡",
        "is_direct_ats": True,
    },
    "Greenhouse": {
        "name": "Greenhouse Direct",
        "color": "#15803d",
        "bg": "#dcfce7",
        "border": "#bbf7d0",
        "icon": "🌱",
        "is_direct_ats": True,
    },
    "Lever": {
        "name": "Lever Direct",
        "color": "#0369a1",
        "bg": "#e0f2fe",
        "border": "#bae6fd",
        "icon": "💼",
        "is_direct_ats": True,
    },
    "SmartRecruiters": {
        "name": "SmartRecruiters Direct",
        "color": "#7c2d12",
        "bg": "#ffedd5",
        "border": "#fed7aa",
        "icon": "🎯",
        "is_direct_ats": True,
    },
    "Workable": {
        "name": "Workable Direct",
        "color": "#065f46",
        "bg": "#d1fae5",
        "border": "#a7f3d0",
        "icon": "👔",
        "is_direct_ats": True,
    },
    "ITJobs.pt": {
        "name": "ITJobs Portugal",
        "color": "#0f766e",
        "bg": "#ccfbf1",
        "border": "#99f6e4",
        "icon": "🇵🇹",
        "is_direct_ats": False,
    },
    "Net-Empregos": {
        "name": "Net-Empregos",
        "color": "#9a3412",
        "bg": "#ffedd5",
        "border": "#fed7aa",
        "icon": "🇵🇹",
        "is_direct_ats": False,
    },
    "Landing.jobs": {
        "name": "Landing.jobs",
        "color": "#0369a1",
        "bg": "#e0f2fe",
        "border": "#bae6fd",
        "icon": "🇵🇹",
        "is_direct_ats": False,
    },
    "LinkedIn": {
        "name": "LinkedIn SyndiFeed",
        "color": "#0a66c2",
        "bg": "#e8f4fd",
        "border": "#bee3f8",
        "icon": "🌐",
        "is_direct_ats": False,
    },
    "ZipRecruiter": {
        "name": "ZipRecruiter Network",
        "color": "#166534",
        "bg": "#f0fdf4",
        "border": "#bbf7d0",
        "icon": "🌐",
        "is_direct_ats": False,
    },
    "Arbeitnow": {
        "name": "Arbeitnow EU",
        "color": "#6b21a8",
        "bg": "#f3e8ff",
        "border": "#e9d5ff",
        "icon": "🇪🇺",
        "is_direct_ats": False,
    },
    "WeWorkRemotely": {
        "name": "WeWorkRemotely",
        "color": "#c2410c",
        "bg": "#ffedd5",
        "border": "#fed7aa",
        "icon": "🌍",
        "is_direct_ats": False,
    },
    "RemoteOK": {
        "name": "RemoteOK Global",
        "color": "#b91c1c",
        "bg": "#fee2e2",
        "border": "#fecaca",
        "icon": "🚀",
        "is_direct_ats": False,
    },
    "Remotive": {
        "name": "Remotive Tech",
        "color": "#1e40af",
        "bg": "#dbeafe",
        "border": "#bfdbfe",
        "icon": "📡",
        "is_direct_ats": False,
    },
    "Jobicy": {
        "name": "Jobicy Worldwide",
        "color": "#0d9488",
        "bg": "#ccfbf1",
        "border": "#99f6e4",
        "icon": "🗺️",
        "is_direct_ats": False,
    },
    "TelecomCrossing": {
        "name": "TelecomCrossing",
        "color": "#475569",
        "bg": "#f1f5f9",
        "border": "#cbd5e1",
        "icon": "🗼",
        "is_direct_ats": False,
    },
    "JobSpy": {
        "name": "Multi-Board Metasearch",
        "color": "#334155",
        "bg": "#f8fafc",
        "border": "#e2e8f0",
        "icon": "🔍",
        "is_direct_ats": False,
    },
    "Apify": {
        "name": "Apify Cloud Actor",
        "color": "#4338ca",
        "bg": "#e0e7ff",
        "border": "#c7d2fe",
        "icon": "☁️",
        "is_direct_ats": False,
    },
}

_DEFAULT_SOURCE_META = {
    "name": "Verified Channel",
    "color": "#334155",
    "bg": "#f8fafc",
    "border": "#e2e8f0",
    "icon": "📌",
    "is_direct_ats": False,
}


def get_source_metadata(source_name: str) -> Dict[str, Any]:
    """Retrieve metadata styling and attributes for a job source."""
    if not source_name:
        return _DEFAULT_SOURCE_META
    for key, meta in SOURCE_METADATA.items():
        if key.lower() in source_name.lower():
            return meta
    return {
        "name": source_name,
        "color": "#334155",
        "bg": "#f8fafc",
        "border": "#e2e8f0",
        "icon": "🌐",
        "is_direct_ats": False,
    }


def render_source_badge(source_name: str, is_direct_ats: bool = False) -> str:
    """Render HTML badge for job source and partner tier."""
    meta = get_source_metadata(source_name)
    color = meta["color"]
    bg = meta["bg"]
    border = meta["border"]
    icon = meta["icon"]
    display = meta["name"]

    badge_html = (
        f"<span style='background: {bg}; color: {color}; border: 1px solid {border}; "
        f"padding: 0.15rem 0.55rem; border-radius: 9999px; font-size: 0.78rem; font-weight: 700; "
        f"display: inline-flex; align-items: center; gap: 4px; white-space: nowrap;'>"
        f"{icon} {display}</span>"
    )

    if is_direct_ats or meta["is_direct_ats"]:
        ats_tag = (
            "<span style='background: #f0fdf4; color: #166534; border: 1px solid #bbf7d0; "
            "padding: 0.15rem 0.55rem; border-radius: 9999px; font-size: 0.75rem; font-weight: 700; "
            "white-space: nowrap;'>🏢 Direct ATS Partner</span>"
        )
        return f"{badge_html} {ats_tag}"

    return badge_html


def render_freshness_badge(days_count: int, days_label: str) -> str:
    """Render HTML widget for days since posted."""
    day_unit = "day" if days_count == 1 else "days"
    if days_count <= 3:
        f_bg, f_color, f_border, f_icon = "#ecfdf5", "#047857", "#a7f3d0", "🔥 New"
    elif days_count <= 14:
        f_bg, f_color, f_border, f_icon = "#eff6ff", "#1d4ed8", "#bfdbfe", "⏱️ Recent"
    else:
        f_bg, f_color, f_border, f_icon = "#f8fafc", "#475569", "#e2e8f0", "📅 Active"

    return (
        f"<div style='margin-top: 0.15rem; margin-bottom: 0.35rem; display: flex; align-items: center; gap: 0.45rem; flex-wrap: wrap; font-size: 0.95rem;'>"
        f"<span>📅 <strong>Days since posted:</strong> <strong>{days_count} {day_unit}</strong></span>"
        f"<span style='background: {f_bg}; color: {f_color}; border: 1px solid {f_border}; padding: 0.12rem 0.55rem; border-radius: 9999px; font-size: 0.78rem; font-weight: 600; white-space: nowrap;'>"
        f"{f_icon} ({days_label})</span>"
        f"</div>"
    )


def render_salary_badge(salary_eval: Dict[str, Any]) -> str:
    """Render HTML widget for salary score and market ranking."""
    score_val = salary_eval["score"]
    rank_label = salary_eval["rank"]
    rank_icon = salary_eval["rank_icon"]
    s_badge_bg = salary_eval["badge_bg"]
    s_badge_text = salary_eval["badge_text"]
    s_badge_border = salary_eval["badge_border"]
    loc_badge = salary_eval.get("location_badge") or "📍 Market Benchmark"

    imputed_tag = ""
    if salary_eval.get("is_imputed") and salary_eval.get("imputed_salary_badge"):
        badge_text = salary_eval["imputed_salary_badge"]
        imputed_tag = (
            f"<span style='background: #fdf4ff; color: #86198f; border: 1px solid #f0abfc; "
            f"padding: 0.12rem 0.5rem; border-radius: 4px; font-size: 0.74rem; font-weight: 600; white-space: nowrap;'>"
            f"🔮 {badge_text}</span>"
        )
    elif salary_eval.get("equity_breakdown"):
        eq = salary_eval["equity_breakdown"]
        imputed_tag = (
            f"<span style='background: #f0fdf4; color: #166534; border: 1px solid #bbf7d0; "
            f"padding: 0.12rem 0.5rem; border-radius: 4px; font-size: 0.74rem; font-weight: 600; white-space: nowrap;'>"
            f"📈 Equity: {eq['equity_band']} ({eq['stage']})</span>"
        )

    return (
        f"<div style='margin-top: 0.15rem; margin-bottom: 0.35rem; display: flex; align-items: center; gap: 0.45rem; flex-wrap: wrap; font-size: 0.95rem;'>"
        f"<span>📊 <strong>Salary Score:</strong> <strong>{score_val}/100</strong></span>"
        f"<span style='background: {s_badge_bg}; color: {s_badge_text}; border: 1px solid {s_badge_border}; padding: 0.12rem 0.55rem; border-radius: 9999px; font-size: 0.78rem; font-weight: 600; white-space: nowrap;'>"
        f"{rank_icon} {rank_label}</span>"
        f"<span style='background: #f8fafc; color: #475569; border: 1px solid #e2e8f0; padding: 0.12rem 0.5rem; border-radius: 4px; font-size: 0.74rem; font-weight: 500; white-space: nowrap;'>"
        f"{loc_badge}</span>"
        f"{imputed_tag}"
        f"</div>"
    )


def render_tech_stack_matrix_html(
    matched_skills: List[str], missing_skills: List[str]
) -> Optional[str]:
    """Render HTML container for Tech Stack Alignment Matrix."""
    chips_html_parts = []
    if matched_skills:
        matched_chips = " ".join([
            f"<span style='background: #dcfce7; color: #15803d; border: 1px solid #86efac; padding: 0.18rem 0.55rem; border-radius: 9999px; font-size: 0.78rem; font-weight: 600; white-space: nowrap;'>✓ {s}</span>"
            for s in matched_skills[:6]
        ])
        chips_html_parts.append(
            f"<div style='margin-bottom: 0.35rem;'><span style='font-size: 0.78rem; font-weight: 700; color: #166534; margin-right: 6px;'>🟢 MATCHED TECH:</span>{matched_chips}</div>"
        )

    if missing_skills:
        missing_chips = " ".join([
            f"<span style='background: #fff1f2; color: #be123c; border: 1px solid #fecdd3; padding: 0.18rem 0.55rem; border-radius: 9999px; font-size: 0.78rem; font-weight: 600; white-space: nowrap;'>+ {s}</span>"
            for s in missing_skills[:4]
        ])
        chips_html_parts.append(
            f"<div><span style='font-size: 0.78rem; font-weight: 700; color: #9f1239; margin-right: 6px;'>🔴 GROWTH TECH:</span>{missing_chips}</div>"
        )

    if not chips_html_parts:
        return None

    return (
        f"<div style='background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 0.5rem 0.75rem; margin-top: 0.6rem;'>"
        f"{''.join(chips_html_parts)}"
        f"</div>"
    )
