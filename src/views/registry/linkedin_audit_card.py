"""
LinkedIn Profile Audit Card Component for Candidate Registry.
Renders an interactive 5-pillar scorecard, grade badge, rewritten headlines,
optimized executive bio, and missing keyword chips.
"""

from typing import Any, Dict
import streamlit as st


def render_linkedin_audit_card(audit: Dict[str, Any], prefix: str = "reg") -> None:
    """Render rich, interactive scorecard and improvement suggestions for LinkedIn profile."""
    if not audit:
        return

    score = audit.get("overall_score", 80)
    grade = audit.get("grade", "A")
    tier = audit.get("tier", "Professional Presence")
    badge_color = audit.get("badge_color", "#2563eb")
    badge_bg = audit.get("badge_bg", "#eff6ff")
    slug_feedback = audit.get("slug_feedback", "")

    st.markdown(
        f"""
        <div style="background: {badge_bg}; border: 1.5px solid {badge_color}45; border-radius: 12px; padding: 1.1rem 1.35rem; margin-top: 0.85rem; margin-bottom: 1rem;">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
                <div>
                    <div style="font-size: 1.25rem; font-weight: 800; color: {badge_color}; display: flex; align-items: center; gap: 8px;">
                        <span>🎯 LinkedIn Optimization Rating: {score}/100</span>
                        <span style="background: {badge_color}; color: #ffffff; padding: 2px 9px; border-radius: 9999px; font-size: 0.82rem; font-weight: 700;">Grade {grade}</span>
                    </div>
                    <div style="font-size: 0.88rem; color: #1e293b; font-weight: 600; margin-top: 3px;">
                        Profile Tier: <strong>{tier}</strong>
                    </div>
                    <div style="font-size: 0.82rem; color: #475569; margin-top: 3px;">
                        {slug_feedback}
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 5-Pillar Score Metrics
    p1, p2, p3, p4, p5 = st.columns(5)
    with p1:
        st.metric("📢 Headline", f"{audit.get('headline_score', 80)}/100")
    with p2:
        st.metric("📖 About Bio", f"{audit.get('about_score', 80)}/100")
    with p3:
        st.metric("🧠 Skills Fit", f"{audit.get('skills_score', 80)}/100")
    with p4:
        st.metric("💼 Experience", f"{audit.get('experience_score', 80)}/100")
    with p5:
        st.metric("🔗 URL Branding", f"{audit.get('slug_score', 80)}/100")

    st.markdown("<div style='height: 0.4rem;'></div>", unsafe_allow_html=True)

    tab_h, tab_a, tab_k, tab_p = st.tabs([
        "💡 3 Optimized Headlines",
        "📝 Rewritten About Bio",
        "🏷️ Missing Keywords",
        "📋 Profile Action Plan",
    ])

    with tab_h:
        st.markdown("##### 🚀 High-Impact Headline Alternatives")
        st.caption("Recruiters scan headlines first. Choose an optimized formula that maximizes Boolean search matching:")
        headlines = audit.get("headline_alternatives", [])
        for i, h in enumerate(headlines, 1):
            st.markdown(f"**Option {i}:**")
            st.code(h, language=None)
            if st.button(f"👉 Apply Headline Option {i} to Form", key=f"apply_hl_{prefix}_{i}"):
                st.session_state[f"{prefix}_headline"] = h
                st.toast(f"Headline Option {i} applied to form!")
                st.rerun()

    with tab_a:
        st.markdown("##### 📝 Optimized 3-Section Executive Bio")
        st.caption("Hooks recruiters in the first 3 lines, showcases quantifiable achievements, and ends with a contact call-to-action:")
        about_text = audit.get("about_rewrite", "")
        st.text_area("Suggested About Bio", value=about_text, height=220, key=f"preview_about_{prefix}", disabled=True)
        if st.button("👉 Apply Rewritten Bio to Form", key=f"apply_about_{prefix}"):
            st.session_state[f"{prefix}_summary"] = about_text
            st.toast("Executive Summary updated with optimized bio!")
            st.rerun()

    with tab_k:
        st.markdown("##### 🏷️ High-Demand Missing Keywords for LinkedIn Recruiter & ATS")
        st.caption("Talent Acquisition systems index these keywords. Incorporate them into your skills, headline, and experience:")
        missing_kw = audit.get("missing_keywords", [])
        kw_html = " ".join([
            f"<span style='background:#f1f5f9; color:#0f172a; border:1px solid #cbd5e1; padding:4px 10px; border-radius:14px; font-size:0.82rem; font-weight:600; display:inline-block; margin:3px;'>+ {kw}</span>"
            for kw in missing_kw
        ])
        st.markdown(f"<div style='margin-bottom: 0.8rem;'>{kw_html}</div>", unsafe_allow_html=True)

    with tab_p:
        st.markdown("##### 📋 Actionable Checklist to Boost Recruiter Conversion")
        for item in audit.get("action_items", []):
            st.markdown(f"- {item}")
