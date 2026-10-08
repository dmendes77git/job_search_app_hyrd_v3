"""
Unit tests for BaseScraper ABC, universal JobPosting schema, and session resilience.
"""

from datetime import datetime, timezone
from typing import List
import httpx
import pytest

from src.agents.scrapers.base import (
    BaseScraper,
    JobPosting,
    WorkType,
    generate_job_id,
    get_random_user_agent,
    get_browser_headers,
    USER_AGENTS,
    clean_html_text,
    normalize_company_slug,
)


class MockSuccessScraper(BaseScraper):
    """Concrete scraper implementation for testing polymorphic contract."""
    SOURCE_NAME = "mock_ats"

    def fetch_jobs(self, company_slug: str = "acme", limit: int = 10) -> List[JobPosting]:
        return [
            JobPosting(
                job_id=self.generate_job_id("req-101"),
                title="Senior Distributed Systems Engineer",
                company_name=company_slug.capitalize(),
                location="Remote - Europe",
                work_type=WorkType.REMOTE,
                url=f"https://jobs.example.com/{company_slug}/101",
                description_text="Build low-latency streaming services.",
                posted_date=datetime(2026, 4, 1, 10, 0, tzinfo=timezone.utc),
                source=self.SOURCE_NAME,
                metadata={"department": "Engineering", "salary": "$170k - $200k"},
            )
        ]


class MockFailingScraper(BaseScraper):
    """Concrete scraper that intentionally raises an exception to test error containment."""
    SOURCE_NAME = "failing_portal"

    def fetch_jobs(self, *args, **kwargs) -> List[JobPosting]:
        raise ConnectionResetError("Remote server terminated connection unexpectedly.")


def test_universal_job_posting_schema():
    """Verify strict adherence to universal JobPosting attributes and types."""
    now = datetime.now(timezone.utc)
    job = JobPosting(
        job_id="greenhouse_abcdef1234567890",
        title="Staff AI Research Scientist",
        company_name="DeepMind",
        location="London / Remote",
        work_type=WorkType.HYBRID,
        url="https://boards.greenhouse.io/deepmind/jobs/999",
        description_text="Pioneer next-generation foundation models.",
        posted_date=now,
        source="greenhouse",
        metadata={"experience_years": 8, "equity": "0.1%"},
    )

    # 1. Primary universal contract fields
    assert job.job_id == "greenhouse_abcdef1234567890"
    assert job.title == "Staff AI Research Scientist"
    assert job.company_name == "DeepMind"
    assert job.location == "London / Remote"
    assert job.work_type == WorkType.HYBRID
    assert job.url == "https://boards.greenhouse.io/deepmind/jobs/999"
    assert job.description_text == "Pioneer next-generation foundation models."
    assert job.posted_date == now
    assert job.source == "greenhouse"
    assert job.metadata["experience_years"] == 8

    # 2. Downstream / legacy bidirectional synchronization
    assert job.company == "DeepMind"
    assert job.full_description == job.description_text
    assert job.source_url == job.url
    assert job.job_type == "Hybrid"
    assert job.id == "greenhouse_abcdef1234567890"

    # 3. to_dict serialization contains all required keys
    d = job.to_dict()
    assert d["job_id"] == job.job_id
    assert d["company_name"] == "DeepMind"
    assert d["company"] == "DeepMind"
    assert d["work_type"] == "hybrid"
    assert d["job_type"] == "Hybrid"
    assert d["description_text"] == job.description_text
    assert d["full_description"] == job.description_text
    assert d["url"] == job.url


def test_job_posting_auto_id_and_hashing():
    """Verify deterministic hash generation when job_id is computed."""
    h1 = generate_job_id("ashby", "job-12345")
    h2 = generate_job_id("ashby", "job-12345")
    h3 = generate_job_id("greenhouse", "job-12345")

    assert h1 == h2
    assert h1 != h3
    assert h1.startswith("ashby_")
    assert len(h1) > 10

    # Auto-generation inside JobPosting
    job = JobPosting(
        title="MLOps Engineer",
        company="Stripe",
        source="stripe_ats",
    )
    assert job.job_id.startswith("stripe_ats_")
    assert job.id is not None


def test_work_type_normalization():
    """Verify various string inputs map correctly to WorkType enum."""
    assert BaseScraper.normalize_work_type("Remote Only") == WorkType.REMOTE
    assert BaseScraper.normalize_work_type("Totalmente Remoto") == WorkType.REMOTE
    assert BaseScraper.normalize_work_type("Hybrid (2 days onsite)") == WorkType.HYBRID
    assert BaseScraper.normalize_work_type("Regime Híbrido") == WorkType.HYBRID
    assert BaseScraper.normalize_work_type("On-site / Presencial") == WorkType.ONSITE
    assert BaseScraper.normalize_work_type("Lisboa - Presencial") == WorkType.ONSITE


def test_base_scraper_polymorphism_and_safe_execution():
    """Verify BaseScraper abstract subclassing and exception containment."""
    scraper = MockSuccessScraper()
    jobs = scraper.safe_fetch_jobs(company_slug="openai")
    assert len(jobs) == 1
    assert jobs[0].company_name == "Openai"
    assert jobs[0].work_type == WorkType.REMOTE

    # Failing scraper must not raise an unhandled exception
    failing_scraper = MockFailingScraper()
    safe_results = failing_scraper.safe_fetch_jobs()
    assert safe_results == []


def test_user_agent_rotation_and_headers():
    """Verify random User-Agent selection and browser header construction."""
    ua = get_random_user_agent()
    assert ua in USER_AGENTS

    headers_json = get_browser_headers(accept_json=True)
    assert "application/json" in headers_json["Accept"]
    assert "User-Agent" in headers_json

    headers_html = get_browser_headers(accept_json=False)
    assert "text/html" in headers_html["Accept"]


def test_base_scraper_session_context_manager():
    """Verify session initialization and clean teardown in context manager."""
    with MockSuccessScraper(timeout=5.0) as scraper:
        assert isinstance(scraper.client, httpx.Client)
        assert not scraper.client.is_closed

    # Client must be closed after exiting context block
    assert scraper.client.is_closed


def test_tenacity_retry_mechanism():
    """Verify request_with_retry retries transient HTTP failures with Tenacity."""
    call_count = 0

    def mock_transport_handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            # Simulate transient 503 Service Unavailable
            return httpx.Response(503, request=request)
        return httpx.Response(200, json={"status": "ok"}, request=request)

    transport = httpx.MockTransport(mock_transport_handler)
    mock_client = httpx.Client(transport=transport)

    scraper = MockSuccessScraper(client=mock_client, max_retries=4, rate_limit_delay=0.01)
    resp = scraper.get("https://api.mockats.com/v1/jobs")

    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
    assert call_count == 3  # Failed twice with 503, succeeded on 3rd attempt
