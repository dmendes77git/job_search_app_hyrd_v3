"""
Visual ATS Keyword Match Heatmap & Optimization Inspector Dialog (Feature P3-B).
Provides deep visibility into keyword alignment across CV sections, frequency density,
and actionable suggestions for missing high-impact competencies.
"""

from __future__ import annotations

import streamlit as st
from typing import Any, Dict

from src.utils.ats_optimizer import generate_ats_keyword_heatmap


@st.dialog("🔍 Visual ATS Keyword Match Heatmap & Inspector", width="large")
def show_ats_heatmap_dialog(job: Dict[str, Any], profile: Dict[str, Any], cv_text: str) -> None:
    """Render the visual ATS Keyword Heatmap and optimization inspector."""
    job_title = job.get("title", "Target Role")
    company_name = job.get("company", "Target Company")

    heatmap_data = generate_ats_keyword_heatmap(job=job, cv_markdown=cv_text, profile=profile)

    match_rate = heatmap_data["match_rate_pct"]
    total_kws = heatmap_data["total_keywords"]
    matched_cnt = heatmap_data["matched_count"]
    partial_cnt = heatmap_data["partial_count"]
    missing_cnt = heatmap_data["missing_count"]
    items = heatmap_data["items"]
    suggestions = heatmap_data["auto_inject_suggestions"]

    # Header metric banner
    if match_rate >= 85:
        banner_bg, banner_color, banner_border = "#f0fdf4", "#166534", "#bbf7d0"
        grade_text = "🟢 Optimal ATS Density"
    elif match_rate >= 70:
        banner_bg, banner_color, banner_border = "#eff6ff", "#1e40af", "#bfdbfe"
        grade_text = "🔵 Competitive ATS Alignment"
    else:
        banner_bg, banner_color, banner_border = "#fffbeb", "#92400e", "#fde68a"
        grade_text = "🟡 Keyword Gaps Detected"

    st.markdown(
        f"""
        <div style="background: {banner_bg}; border: 1.5px solid {banner_border}; border-radius: 8px; padding: 0.85rem 1.1rem; margin-bottom: 1rem; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
            <div>
                <div style="font-size: 0.8rem; font-weight: 600; text-transform: uppercase; color: {banner_color};">Role Keyword Match</div>
                <div style="font-size: 1.25rem; font-weight: 800; color: #0f172a;">{job_title} at {company_name}</div>
            </div>
            <div style="display: flex; gap: 0.75rem; align-items: center;">
                <span style="background: #ffffff; color: {banner_color}; border: 1px solid {banner_border}; padding: 4px 12px; border-radius: 9999px; font-weight: 800; font-size: 0.95rem;">
                    🎯 {match_rate}% Density
                </span>
                <span style="font-weight: 700; font-size: 0.85rem; color: {banner_color};">{grade_text}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 4-Column Stat summary
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Total Scanned", total_kws)
    with c2:
        st.metric("Exact Matches", f"{matched_cnt} (🟢)")
    with c3:
        st.metric("Partial / Synonyms", f"{partial_cnt} (🟡)")
    with c4:
        st.metric("Missing Keywords", f"{missing_cnt} (🔴)")

    st.markdown("---")

    # Filter controls
    f_col1, f_col2 = st.columns([1.5, 2.5])
    with f_col1:
        status_filter = st.selectbox(
            "Filter by Status:",
            options=["All Statuses", "🟢 Exact Matches", "🟡 Partial / Synonyms", "🔴 Missing Keywords"],
            key="ats_heatmap_filter",
        )
    with f_col2:
        search_query = st.text_input(
            "Search Keyword:",
            placeholder="Type skill or tool name...",
            key="ats_heatmap_search",
        )

    # Filter items
    filtered_items = items
    if "Exact" in status_filter:
        filtered_items = [it for it in filtered_items if it["status"] == "matched"]
    elif "Partial" in status_filter:
        filtered_items = [it for it in filtered_items if it["status"] == "partial"]
    elif "Missing" in status_filter:
        filtered_items = [it for it in filtered_items if it["status"] == "missing"]

    if search_query.strip():
        q = search_query.strip().lower()
        filtered_items = [it for it in filtered_items if q in it["keyword"].lower() or q in it["category"].lower()]

    st.caption(f"Showing {len(filtered_items)} of {total_kws} competencies:")

    # Table / Badge Layout
    for it in filtered_items:
        kw = it["keyword"]
        cat = it["category"]
        stt = it["status"]
        cnt = it["count"]
        secs = ", ".join(it["sections"])
        imp = it["importance"]

        if stt == "matched":
            badge_html = f"<span style='background: #dcfce7; color: #15803d; border: 1px solid #86efac; padding: 2px 8px; border-radius: 12px; font-size: 0.76rem; font-weight: 700;'>🟢 Exact Match ({cnt}x)</span>"
        elif stt == "partial":
            badge_html = f"<span style='background: #fef3c7; color: #b45309; border: 1px solid #fde68a; padding: 2px 8px; border-radius: 12px; font-size: 0.76rem; font-weight: 700;'>🟡 Partial / Synonym</span>"
        else:
            badge_html = f"<span style='background: #fef2f2; color: #b91c1c; border: 1px solid #fecaca; padding: 2px 8px; border-radius: 12px; font-size: 0.76rem; font-weight: 700;'>🔴 Missing</span>"

        imp_badge = (
            "<span style='background: #eff6ff; color: #1d4ed8; padding: 1px 6px; border-radius: 4px; font-size: 0.7rem; font-weight: 600; margin-left: 6px;'>★ High Impact</span>"
            if imp == "High"
            else ""
        )

        st.markdown(
            f"""
            <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 6px; padding: 0.5rem 0.8rem; margin-bottom: 0.4rem; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                <div>
                    <strong style="color: #0f172a; font-size: 0.9rem;">{kw}</strong>
                    <span style="color: #64748b; font-size: 0.76rem; margin-left: 8px;">({cat})</span>
                    {imp_badge}
                    <div style="font-size: 0.75rem; color: #475569; margin-top: 2px;">📍 Found in: <em>{secs}</em></div>
                </div>
                <div>{badge_html}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Auto-inject suggestions
    if suggestions:
        st.markdown("---")
        with st.expander("💡 1-Click Auto-Inject Suggestions (Non-Stuffing Compliance)", expanded=True):
            st.caption(
                "Incorporate these high-impact impact statements into your CV to bridge detected gaps without triggering ATS keyword-stuffing penalties:"
            )
            for sug in suggestions:
                st.markdown(f"**Target Section:** `{sug['target_section']}` — Keyword: **{sug['keyword']}**")
                st.code(sug["suggested_bullet"], language="markdown")
