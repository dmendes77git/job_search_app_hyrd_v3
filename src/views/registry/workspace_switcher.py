"""
Workspace Switcher Component for Candidate Registry.
Renders the grid of registered candidate workspaces, active indicators, and workspace switcher actions.
"""

from typing import Any, Dict, List, Optional
import streamlit as st

from src.state import SCREEN_INPUT, SCREEN_PIPELINE, go_to_screen
from src.utils.user_manager import (
    AVATAR_PALETTE,
    delete_user,
    flush_session_to_user_workspace,
    get_active_user_id,
    get_user_workspace,
    load_user_into_session,
)


def render_workspace_switcher(
    all_users: List[Dict[str, Any]], active_id: Optional[str] = None
) -> None:
    """Render registered candidate cards and workspace navigation triggers."""
    st.markdown("### 👥 Registered Candidate Workspaces")
    st.caption(
        "Select a candidate to enter their dedicated workspace. All saved roles, "
        "custom CVs, cover letters, and Kanban pipeline cards are fully isolated."
    )

    if not all_users:
        st.info("No candidates registered yet. Switch to the '➕ Register New Candidate' tab to create your first profile!")
        return

    for u in all_users:
        u_id = u.get("id")
        is_active = (u_id == active_id)
        u_name = u.get("name", "Candidate")
        u_headline = u.get("headline", "Professional")
        u_loc = u.get("location", "Remote")
        u_color = u.get("avatar_color", AVATAR_PALETTE[0])
        u_initials = "".join([part[0].upper() for part in u_name.split() if part][:2]) or "U"
        u_role = u.get("target_role", "")

        u_workspace = get_user_workspace(u_id)
        u_saved = len(u_workspace.get("saved_jobs", []))
        u_pipeline = len(u_workspace.get("application_pipeline", {}))

        card_border = "#2563eb" if is_active else "#e2e8f0"
        card_bg = "#f8faff" if is_active else "#ffffff"

        with st.container():
            st.markdown(
                f"""
                <div style="background: {card_bg}; border: 1.5px solid {card_border}; border-radius: 12px; padding: 1.1rem 1.25rem; margin-bottom: 0.75rem;">
                    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
                        <div style="display: flex; align-items: center; gap: 12px;">
                            <div style="width: 44px; height: 44px; border-radius: 50%; background: {u_color}; color: #ffffff; font-size: 1.05rem; font-weight: 700; display: flex; align-items: center; justify-content: center;">
                                {u_initials}
                            </div>
                            <div>
                                <div style="font-size: 1.05rem; font-weight: 700; color: #0f172a;">
                                    {u_name} {'<span style="background:#2563eb; color:#fff; font-size:0.7rem; font-weight:600; padding:2px 7px; border-radius:10px; margin-left:6px;">ACTIVE</span>' if is_active else ''}
                                </div>
                                <div style="font-size: 0.85rem; color: #475569;">
                                    {u_headline} • 📍 {u_loc}
                                </div>
                            </div>
                        </div>
                        <div style="display: flex; align-items: center; gap: 12px; font-size: 0.82rem; color: #64748b;">
                            {f'<span>🎯 Target: <strong>{u_role}</strong></span>' if u_role else ''}
                            <span>📋 Pipeline: <strong>{u_pipeline}</strong></span>
                            <span>📌 Saved: <strong>{u_saved}</strong></span>
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            btn_c1, btn_c2, btn_c3, btn_c4 = st.columns([1.5, 1.2, 1, 0.8])
            with btn_c1:
                if st.button(
                    f"🚀 Enter {u_name}'s Workspace",
                    key=f"btn_enter_{u_id}",
                    use_container_width=True,
                    type="primary" if is_active else "secondary",
                ):
                    flush_session_to_user_workspace()
                    load_user_into_session(u_id)
                    st.toast(f"Switched to {u_name}'s dedicated workspace!")
                    go_to_screen(SCREEN_INPUT)

            with btn_c2:
                if st.button(f"📋 Open Kanban Pipeline", key=f"btn_kanban_{u_id}", use_container_width=True):
                    flush_session_to_user_workspace()
                    load_user_into_session(u_id)
                    go_to_screen(SCREEN_PIPELINE)

            with btn_c3:
                if st.button(f"👁️ View Details", key=f"btn_edit_sel_{u_id}", use_container_width=True):
                    flush_session_to_user_workspace()
                    load_user_into_session(u_id)
                    st.toast(f"Loaded {u_name} for inspection.")
                    st.rerun()

            with btn_c4:
                if len(all_users) > 1:
                    if st.button(
                        f"🗑️ Delete",
                        key=f"btn_del_{u_id}",
                        use_container_width=True,
                        help="Permanently delete this user profile and dedicated workspace",
                    ):
                        if delete_user(u_id):
                            st.toast(f"Deleted {u_name}'s profile and workspace.")
                            remaining_id = get_active_user_id()
                            if remaining_id:
                                load_user_into_session(remaining_id)
                            st.rerun()
                else:
                    st.caption("(Primary User)")

            st.markdown("<div style='height: 0.5rem;'></div>", unsafe_allow_html=True)
