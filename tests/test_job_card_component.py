"""Tests for Job Card component resilience and key containment."""

from unittest.mock import MagicMock, patch
import pytest

from src.views.dashboard.job_card import render_job_card


@patch("streamlit.container")
@patch("streamlit.markdown")
@patch("streamlit.divider")
@patch("streamlit.columns")
@patch("streamlit.write")
@patch("streamlit.expander")
@patch("streamlit.link_button")
@patch("streamlit.button")
def test_render_job_card_resilience(
    mock_btn,
    mock_link,
    mock_exp,
    mock_write,
    mock_cols,
    mock_div,
    mock_md,
    mock_cont,
):
    """Verify render_job_card renders without KeyError even with minimal or missing keys."""
    # Mock Streamlit layout returns
    mock_cols.return_value = (MagicMock(), MagicMock())
    mock_cont.return_value.__enter__ = MagicMock()
    mock_cont.return_value.__exit__ = MagicMock()
    mock_exp.return_value.__enter__ = MagicMock()
    mock_exp.return_value.__exit__ = MagicMock()

    profile = {"location": "Remote", "headline": "Developer"}

    # 1. Standard job with NO company_size (the exact user error scenario)
    job_no_size = {
        "id": "job_test_1",
        "title": "Software Engineer",
        "company": "Tech Corp",
        "location": "Remote",
        "salary": "$120k",
        "description": "Python job.",
    }

    # Must execute smoothly without KeyError
    render_job_card(job_no_size, profile)

    # 2. Bare minimum dictionary
    job_bare = {
        "title": "Data Scientist",
    }
    render_job_card(job_bare, profile)

    # 3. Completely empty dictionary
    render_job_card({}, profile)


@patch("streamlit.container")
@patch("streamlit.markdown")
@patch("streamlit.divider")
@patch("streamlit.columns")
@patch("streamlit.write")
@patch("streamlit.expander")
@patch("streamlit.link_button")
@patch("streamlit.button")
def test_render_job_card_strategic_decision_matrix_badges(
    mock_btn,
    mock_link,
    mock_exp,
    mock_write,
    mock_cols,
    mock_div,
    mock_md,
    mock_cont,
):
    """Verify Strategic Decision Matrix badges display correct name and status colors instead of raw quadrant."""
    mock_cols.return_value = (MagicMock(), MagicMock())
    mock_cont.return_value.__enter__ = MagicMock()
    mock_cont.return_value.__exit__ = MagicMock()
    mock_exp.return_value.__enter__ = MagicMock()
    mock_exp.return_value.__exit__ = MagicMock()

    profile = {"location": "Remote"}

    test_cases = [
        ("QI", "🟢 Priority Fast-Track", "#047857", "#ecfdf5"),
        ("QII", "🟡 Referral Outreach", "#b45309", "#fffbeb"),
        ("QIII", "🔵 Stretch Role", "#1d4ed8", "#eff6ff"),
        ("QIV", "🔴 Low Viability", "#b91c1c", "#fef2f2"),
    ]

    for quad_code, expected_name, expected_color, expected_bg in test_cases:
        mock_md.reset_mock()
        job = {
            "title": "Software Engineer",
            "company": "Test Org",
            "strategic_quadrant": quad_code,
            "fit_score": 85,
        }
        render_job_card(job, profile)

        # Inspect all calls to st.markdown
        all_md_calls = " ".join([str(call.args[0]) for call in mock_md.call_args_list if call.args])
        assert expected_name in all_md_calls, f"Expected {expected_name} in markdown output for {quad_code}"
        assert expected_color in all_md_calls, f"Expected color {expected_color} for {quad_code}"
        assert expected_bg in all_md_calls, f"Expected bg {expected_bg} for {quad_code}"

