"""
Wizard Stepper Component displaying the 4-screen state machine progression.
"""

import streamlit as st
from src.state import SCREEN_INFO, go_to_screen


def render_stepper(current_step: int) -> None:
    """Render a visual, modern horizontal step tracker."""
    cols = st.columns(len(SCREEN_INFO))

    for idx, (step_id, info) in enumerate(SCREEN_INFO.items()):
        with cols[idx]:
            is_active = step_id == current_step
            is_done = step_id < current_step

            if is_done:
                status_icon = "✓"
                status_class = "step-done"
                badge_bg = "#16a34a"
                badge_text = "#ffffff"
                border_color = "#16a34a"
            elif is_active:
                status_icon = "👤" if step_id == 0 else f"{step_id}"
                status_class = "step-active"
                badge_bg = "#2563eb"
                badge_text = "#ffffff"
                border_color = "#2563eb"
            else:
                status_icon = "👤" if step_id == 0 else f"{step_id}"
                status_class = "step-pending"
                badge_bg = "#e4e4e7"
                badge_text = "#71717a"
                border_color = "#d4d4d8"

            step_label = "Account Hub" if step_id == 0 else f"Step {step_id}"

            st.markdown(
                f"""
                <div style="
                    background: {'#f0fdf4' if is_done else ('#eff6ff' if is_active else '#fafafa')};
                    border: 1.5px solid {border_color};
                    border-radius: 10px;
                    padding: 0.85rem 1rem;
                    display: flex;
                    align-items: center;
                    gap: 0.75rem;
                    box-shadow: {'0 2px 8px rgba(37, 99, 235, 0.12)' if is_active else 'none'};
                ">
                    <div style="
                        width: 28px;
                        height: 28px;
                        border-radius: 50%;
                        background: {badge_bg};
                        color: {badge_text};
                        font-weight: 700;
                        font-size: 0.85rem;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        flex-shrink: 0;
                    ">{status_icon}</div>
                    <div style="overflow: hidden;">
                        <div style="
                            font-size: 0.75rem;
                            font-weight: 600;
                            text-transform: uppercase;
                            letter-spacing: 0.05em;
                            color: {'#15803d' if is_done else ('#1d4ed8' if is_active else '#71717a')};
                        ">{step_label}</div>
                        <div style="
                            font-size: 0.92rem;
                            font-weight: 600;
                            color: #18181b;
                            white-space: nowrap;
                            text-overflow: ellipsis;
                            overflow: hidden;
                        ">{info['title']}</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("<div style='height: 1.5rem;'></div>", unsafe_allow_html=True)
