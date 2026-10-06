"""Recruiter Cold Outreach & LinkedIn Drafter Dialog component."""

import re
import streamlit as st
from src.agents.outreach_agent import generate_outreach_campaign, create_outreach_docx, TONE_OPTIONS
from src.utils.user_manager import flush_session_to_user_workspace


@st.dialog("📬 Recruiter Cold Outreach & LinkedIn Drafter", width="large")
def show_outreach_dialog(job: dict, profile: dict) -> None:
    """Render the multi-channel cold outreach drafter with customizable recipient details, tone, and downloads."""
    job_id = job.get("id") or job.get("job_id", "job_custom")
    if "outreach_campaigns" not in st.session_state:
        st.session_state.outreach_campaigns = {}

    cand_name = (profile.get("full_name") or st.session_state.get("candidate_name") or "Candidate").strip()
    cand_clean = re.sub(r"[^\w\-]", "_", cand_name)
    company_name = job.get("company", "Target Company")
    clean_company = company_name.replace(" ", "_").lower()
    title_name = job.get("title", "Target Role")
    api_key = st.session_state.get("gemini_api_key")
    pref_model = st.session_state.get("gemini_model")

    st.markdown(
        f"<div style='background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 8px; padding: 0.75rem 1rem; margin-bottom: 0.75rem; font-size: 0.88rem; color: #1e40af;'>"
        f"⚡ <strong>ATS & Talent CRM Multiplier:</strong> Strategic outreach formulated with exact requisition tokens, target title keywords, and Boolean search keywords for recruiters' LinkedIn and ATS talent filters at <strong>{company_name}</strong>."
        f"</div>",
        unsafe_allow_html=True,
    )

    # Outreach Customization Controls
    with st.expander("⚙️ Recruiter & Outreach Personalization Parameters", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            rec_name = st.text_input("Recipient / Recruiter Name", value="Hiring Manager", key=f"out_rec_name_{job_id}")
            rec_title = st.text_input("Recipient Title / Role", value="Engineering Leader", key=f"out_rec_title_{job_id}")
        with c2:
            rec_tone = st.selectbox("Outreach Tone", options=TONE_OPTIONS, index=0, key=f"out_tone_{job_id}")
            rec_hook = st.text_input("Custom Hook / Common Ground (Optional)", placeholder="e.g. Loved your recent post on AI infra / fellow MIT alum", key=f"out_hook_{job_id}")

        if st.button("⚡ Generate / Recalibrate Messages", key=f"btn_recal_outreach_{job_id}", type="primary"):
            with st.spinner("Generating personalized outreach sequence..."):
                campaign = generate_outreach_campaign(
                    job,
                    profile,
                    recipient_name=rec_name,
                    recipient_title=rec_title,
                    custom_hook=rec_hook,
                    tone=rec_tone,
                    api_key=api_key,
                    preferred_model=pref_model,
                )
                st.session_state.outreach_campaigns[job_id] = campaign
                flush_session_to_user_workspace()
                st.toast("Outreach messages generated!")
                st.rerun()

    # Load or generate campaign
    if job_id not in st.session_state.outreach_campaigns:
        with st.spinner(f"🤖 Hyrd Agent drafting high-conversion outreach for {company_name}..."):
            campaign = generate_outreach_campaign(
                job, profile, api_key=api_key, preferred_model=pref_model
            )
            st.session_state.outreach_campaigns[job_id] = campaign
            flush_session_to_user_workspace()
    else:
        campaign = st.session_state.outreach_campaigns[job_id]

    tab_li, tab_hm, tab_rec, tab_ref, tab_ty = st.tabs([
        "🔗 LinkedIn Note (<300 char)",
        "👔 Hiring Manager Email",
        "🎯 Recruiter InMail",
        "🤝 Referral / Insider Chat",
        "🙏 Post-Interview Thank You",
    ])

    with tab_li:
        st.markdown("#### 🔗 LinkedIn Connection Request Note")
        st.caption("LinkedIn strictly restricts connection invitation notes to 300 characters.")

        li_data = campaign.get("linkedin_note", {})
        current_li_text = li_data.get("text", "")
        char_count = len(current_li_text)

        badge_color = "#166534" if char_count <= 300 else "#dc2626"
        badge_bg = "#dcfce7" if char_count <= 300 else "#fee2e2"
        badge_status = "Within 300 Char Limit ✅" if char_count <= 300 else "EXCEEDS 300 Limit ⚠️"

        st.markdown(
            f"<div style='display:inline-block; background:{badge_bg}; color:{badge_color}; padding:4px 10px; border-radius:12px; font-size:0.82rem; font-weight:600; margin-bottom:8px;'>"
            f"Length: {char_count} / 300 Characters — {badge_status}"
            f"</div>",
            unsafe_allow_html=True,
        )

        edited_li = st.text_area(
            "Connection Note Text",
            value=current_li_text,
            height=120,
            key=f"edit_li_note_{job_id}",
        )
        if edited_li != current_li_text:
            campaign["linkedin_note"]["text"] = edited_li
            campaign["linkedin_note"]["char_count"] = len(edited_li)
            st.session_state.outreach_campaigns[job_id] = campaign
            flush_session_to_user_workspace()

        st.code(edited_li, language=None)

    with tab_hm:
        st.markdown("#### 👔 Direct Cold Email to Hiring Manager")
        st.caption("Targeted at the decision maker. Focuses on solving team challenges and quantifiable outcomes.")

        hm_data = campaign.get("hiring_manager_email", {})
        hm_subj = st.text_input("Subject Line", value=hm_data.get("subject", ""), key=f"subj_hm_{job_id}")
        hm_body = st.text_area("Email Body", value=hm_data.get("body", ""), height=220, key=f"body_hm_{job_id}")
        st.caption(f"Estimated length: {len(hm_body.split())} words (Ideal cold email: 90–140 words)")

        if hm_subj != hm_data.get("subject") or hm_body != hm_data.get("body"):
            campaign["hiring_manager_email"]["subject"] = hm_subj
            campaign["hiring_manager_email"]["body"] = hm_body
            campaign["hiring_manager_email"]["word_count"] = len(hm_body.split())
            st.session_state.outreach_campaigns[job_id] = campaign
            flush_session_to_user_workspace()

    with tab_rec:
        st.markdown("#### 🎯 Recruiter & Talent Acquisition InMail")
        st.caption("Highlights specific alignment with the job requisition, attached CV, and availability.")

        rec_data = campaign.get("recruiter_inmail", {})
        rec_subj = st.text_input("Subject Line", value=rec_data.get("subject", ""), key=f"subj_rec_{job_id}")
        rec_body = st.text_area("InMail Body", value=rec_data.get("body", ""), height=220, key=f"body_rec_{job_id}")
        st.caption(f"Estimated length: {len(rec_body.split())} words")

        if rec_subj != rec_data.get("subject") or rec_body != rec_data.get("body"):
            campaign["recruiter_inmail"]["subject"] = rec_subj
            campaign["recruiter_inmail"]["body"] = rec_body
            campaign["recruiter_inmail"]["word_count"] = len(rec_body.split())
            st.session_state.outreach_campaigns[job_id] = campaign
            flush_session_to_user_workspace()

    with tab_ref:
        st.markdown("#### 🤝 Warm Internal Referral / Insider Request")
        st.caption("Low-pressure message to team members, university alumni, or 2nd-degree connections asking for culture insights or a referral.")

        ref_data = campaign.get("referral_request", {})
        ref_subj = st.text_input("Subject Line", value=ref_data.get("subject", ""), key=f"subj_ref_{job_id}")
        ref_body = st.text_area("Message Body", value=ref_data.get("body", ""), height=220, key=f"body_ref_{job_id}")
        st.caption(f"Estimated length: {len(ref_body.split())} words")

        if ref_subj != ref_data.get("subject") or ref_body != ref_data.get("body"):
            campaign["referral_request"]["subject"] = ref_subj
            campaign["referral_request"]["body"] = ref_body
            campaign["referral_request"]["word_count"] = len(ref_body.split())
            st.session_state.outreach_campaigns[job_id] = campaign
            flush_session_to_user_workspace()

    with tab_ty:
        st.markdown("#### 🙏 Post-Interview Follow-Up & Thank You Note")
        st.caption("Send within 24 hours of completing a recruiter screen or team interview.")

        ty_data = campaign.get("thank_you_note", {})
        ty_subj = st.text_input("Subject Line", value=ty_data.get("subject", ""), key=f"subj_ty_{job_id}")
        ty_body = st.text_area("Follow-Up Body", value=ty_data.get("body", ""), height=220, key=f"body_ty_{job_id}")
        st.caption(f"Estimated length: {len(ty_body.split())} words")

        if ty_subj != ty_data.get("subject") or ty_body != ty_data.get("body"):
            campaign["thank_you_note"]["subject"] = ty_subj
            campaign["thank_you_note"]["body"] = ty_body
            campaign["thank_you_note"]["word_count"] = len(ty_body.split())
            st.session_state.outreach_campaigns[job_id] = campaign
            flush_session_to_user_workspace()

    st.markdown("---")

    d_col1, d_col2, d_col3 = st.columns([1.2, 1.2, 1])
    with d_col1:
        docx_buffer = create_outreach_docx(campaign)
        st.download_button(
            label="📥 Download Campaign (.docx)",
            data=docx_buffer.getvalue(),
            file_name=f"OutreachCampaign_{cand_clean}_{clean_company}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True,
        )
    with d_col2:
        txt_content = campaign.get("raw_markdown") or (
            f"LINKEDIN NOTE:\n{campaign.get('linkedin_note', {}).get('text')}\n\n"
            f"HIRING MANAGER EMAIL:\nSubject: {campaign.get('hiring_manager_email', {}).get('subject')}\n\n{campaign.get('hiring_manager_email', {}).get('body')}\n\n"
            f"RECRUITER INMAIL:\nSubject: {campaign.get('recruiter_inmail', {}).get('subject')}\n\n{campaign.get('recruiter_inmail', {}).get('body')}\n\n"
            f"REFERRAL REQUEST:\nSubject: {campaign.get('referral_request', {}).get('subject')}\n\n{campaign.get('referral_request', {}).get('body')}\n\n"
            f"THANK YOU NOTE:\nSubject: {campaign.get('thank_you_note', {}).get('subject')}\n\n{campaign.get('thank_you_note', {}).get('body')}"
        )
        st.download_button(
            label="📥 Download Text Pack (.txt)",
            data=txt_content,
            file_name=f"OutreachMessages_{cand_clean}_{clean_company}.txt",
            mime="text/plain",
            use_container_width=True,
        )
    with d_col3:
        if st.button("🔄 Reset / Re-run", key=f"regen_outreach_{job_id}", use_container_width=True):
            with st.spinner("Regenerating campaign messages..."):
                st.session_state.outreach_campaigns[job_id] = generate_outreach_campaign(
                    job, profile, api_key=api_key, preferred_model=pref_model
                )
                flush_session_to_user_workspace()
                st.toast("Outreach messages refreshed!")
                st.rerun()
