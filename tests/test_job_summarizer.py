"""
Unit tests for Job Description Summarizer & Synthesizer.
Tests HTML parsing, boilerplate filtering, executive overview extraction,
and bullet point isolation.
"""

from unittest.mock import MagicMock, patch
import pytest

from src.utils.job_summarizer import (
    clean_job_text,
    remove_boilerplate,
    extract_bullet_points,
    extract_executive_overview,
    summarize_job_description,
    render_summary_html,
)
from src.views.dashboard.job_card import render_job_card
from src.schemas import JobPosting


SAMPLE_RAW_HTML_JOB = """
<div>
  <h2>About Acme Corp</h2>
  <p>Acme Corp is a world-class technology company revolutionizing developer productivity.</p>
  
  <h2>What you'll do:</h2>
  <ul>
    <li>Design and build scalable distributed systems using Python and FastAPI.</li>
    <li>Collaborate with cross-functional product and frontend engineering teams.</li>
    <li>Optimize cloud infrastructure and reduce latency on high-throughput microservices.</li>
  </ul>

  <h2>Requirements:</h2>
  <ul>
    <li>5+ years of software engineering experience in Python or Go.</li>
    <li>Bachelor's degree in Computer Science or equivalent practical experience.</li>
    <li>Strong understanding of PostgreSQL and Redis caching.</li>
  </ul>

  <h2>Perks & Benefits:</h2>
  <p>We offer 401(k) matching, comprehensive health, dental, and vision insurance, and unlimited PTO.</p>

  <h2>Equal Opportunity Employer</h2>
  <p>Acme Corp is proud to be an Equal Opportunity Employer. We celebrate diversity and are committed to creating an inclusive environment for all employees. All employment decisions are made without regard to race, religion, color, national origin, gender, sexual orientation, age, or disability.</p>
  <p>Notice to staffing agencies: We do not accept unsolicited resumes from third-party recruiters.</p>
</div>
"""

SAMPLE_PLAIN_TEXT_JOB = """
Company Overview:
Beta Labs is seeking a Lead Data Scientist to direct our predictive modeling and machine learning initiatives.

Core Responsibilities:
• Lead the architecture and deployment of real-time machine learning pipelines.
• Partner with executive leadership to translate business OKRs into quantitative models.
• Mentor junior data scientists and establish ML engineering best practices.

Qualifications:
• 7+ years of experience with PyTorch, Scikit-Learn, and BigQuery.
• Master's or PhD in Statistics, Computer Science, or Mathematics.

Benefits:
• Competitive salary, health/dental coverage, and home office stipend.

Equal Employment Opportunity Employer.
"""


def test_clean_job_text_html_conversion():
    """Verify HTML tags are stripped while bullet lists and line breaks are preserved."""
    cleaned = clean_job_text(SAMPLE_RAW_HTML_JOB)
    assert "<div" not in cleaned
    assert "</ul>" not in cleaned
    assert "• Design and build scalable distributed systems" in cleaned
    assert "• 5+ years of software engineering experience" in cleaned
    assert "\n" in cleaned


def test_clean_job_text_entity_unescaping():
    """Verify HTML entities like &amp; and &quot; are cleanly unescaped."""
    raw = "<p>Design &amp; develop high-speed &quot;edge&quot; microservices.</p>"
    cleaned = clean_job_text(raw)
    assert cleaned == "Design & develop high-speed \"edge\" microservices."


def test_remove_boilerplate():
    """Verify EEO, benefits, and staffing agency disclaimers are removed."""
    cleaned = clean_job_text(SAMPLE_RAW_HTML_JOB)
    filtered = remove_boilerplate(cleaned)
    assert "Equal Opportunity Employer" not in filtered
    assert "unsolicited resumes" not in filtered
    assert "401(k)" not in filtered
    # Role content must be retained
    assert "Design and build scalable distributed systems" in filtered


def test_extract_bullet_points_responsibilities():
    """Verify bullets under responsibility headers are extracted while requirements are filtered out."""
    cleaned = clean_job_text(SAMPLE_RAW_HTML_JOB)
    filtered = remove_boilerplate(cleaned)
    bullets = extract_bullet_points(filtered, max_bullets=3)

    assert len(bullets) == 3
    assert any("Design and build scalable distributed systems" in b for b in bullets)
    assert any("Collaborate with cross-functional" in b for b in bullets)
    assert any("Optimize cloud infrastructure" in b for b in bullets)

    # Verify requirements were NOT extracted as responsibility bullets
    for b in bullets:
        assert "5+ years" not in b
        assert "Bachelor's degree" not in b


def test_extract_bullet_points_plain_text():
    """Verify plain text bullet points with unicode bullets are extracted."""
    bullets = extract_bullet_points(SAMPLE_PLAIN_TEXT_JOB, max_bullets=3)
    assert len(bullets) >= 2
    assert any("Lead the architecture" in b for b in bullets)


def test_extract_executive_overview():
    """Verify executive overview extracts high-signal role mission statement."""
    overview = extract_executive_overview(
        SAMPLE_PLAIN_TEXT_JOB,
        title="Lead Data Scientist",
        company="Beta Labs",
    )
    assert "Beta Labs is seeking a Lead Data Scientist" in overview or "Lead Data Scientist" in overview


def test_summarize_job_description_full_pipeline():
    """Verify end-to-end summarization output structure."""
    result = summarize_job_description(
        SAMPLE_RAW_HTML_JOB,
        title="Senior Software Engineer",
        company="Acme Corp",
    )
    assert "overview" in result
    assert "bullets" in result
    assert "formatted_markdown" in result
    assert len(result["bullets"]) > 0
    assert result["is_short"] is False
    assert "Acme" in result["overview"] or "Senior Software Engineer" in result["overview"]


def test_summarize_job_description_empty_and_short():
    """Verify safe fallback for empty or very short job postings."""
    # 1. Empty string
    res_empty = summarize_job_description("", title="Fullstack Engineer", company="StartUp X")
    assert "Fullstack Engineer" in res_empty["overview"]
    assert res_empty["is_short"] is True
    assert res_empty["bullets"] == []

    # 2. Ultra-short text
    short_text = "Looking for a React developer to build our web dashboard."
    res_short = summarize_job_description(short_text, title="React Developer", company="Co")
    assert res_short["overview"] == short_text
    assert res_short["is_short"] is True


def test_render_summary_html():
    """Verify HTML rendering format and escaping."""
    summary_data = {
        "overview": "Acme Corp seeks an Engineer & Architect.",
        "bullets": ["Build APIs", "Lead sprints <fast>"],
    }
    html_out = render_summary_html(summary_data)
    assert "<p " in html_out
    assert "Acme Corp seeks an Engineer &amp; Architect." in html_out
    assert "<ul " in html_out
    assert "<li " in html_out
    assert "Build APIs</li>" in html_out
    assert "&lt;fast&gt;" in html_out


@patch("streamlit.container")
@patch("streamlit.markdown")
@patch("streamlit.divider")
@patch("streamlit.columns")
@patch("streamlit.write")
@patch("streamlit.expander")
@patch("streamlit.link_button")
@patch("streamlit.button")
def test_render_job_card_with_long_description(
    mock_btn,
    mock_link,
    mock_exp,
    mock_write,
    mock_cols,
    mock_div,
    mock_md,
    mock_cont,
):
    """Verify job card renders clean summary and expander without exception on long HTML descriptions."""
    mock_cols.return_value = (MagicMock(), MagicMock())
    mock_cont.return_value.__enter__ = MagicMock()
    mock_cont.return_value.__exit__ = MagicMock()
    mock_exp.return_value.__enter__ = MagicMock()
    mock_exp.return_value.__exit__ = MagicMock()

    job_payload = {
        "id": "job_long_html_1",
        "title": "Senior Platform Engineer",
        "company": "Acme Corp",
        "company_size": "500-1000",
        "location": "Remote",
        "salary": "$150,000",
        "description": SAMPLE_RAW_HTML_JOB,
    }
    profile = {"location": "Remote", "headline": "Engineer"}

    render_job_card(job_payload, profile)

    # Verify expander was called for the full job description
    mock_exp.assert_any_call("📄 View Full Job Description", expanded=False)


def test_job_posting_short_summary_field():
    """Verify JobPosting model schema supports short_summary."""
    job = JobPosting(
        title="ML Engineer",
        company_name="AI Corp",
        description_text=SAMPLE_RAW_HTML_JOB,
        short_summary="Summary of role",
    )
    d = job.to_dict()
    assert d["short_summary"] == "Summary of role"
