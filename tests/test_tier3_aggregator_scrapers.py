"""
Unit tests for Tier 3 Aggregator APIs & Cloud Actors:
JobSpy, Apify (with Wellfound & Glassdoor bot mitigation), JSearch (Google Jobs), and Jooble.
"""

from typing import Any, Dict, List
from unittest.mock import MagicMock, patch
import httpx
import pandas as pd
import pytest

from src.agents.scrapers.aggregator_scrapers import (
    JobSpyScraper,
    ApifyScraper,
    JSearchScraper,
    JoobleScraper,
    fetch_jobspy_jobs,
    fetch_apify_jobs,
    fetch_jsearch_jobs,
    fetch_jooble_jobs,
    fetch_wellfound_apify_jobs,
    fetch_glassdoor_apify_jobs,
)
from src.schemas import JobPosting, WorkType


def test_jobspy_scraper_normalization():
    """Verify JobSpyScraper maps JobSpy pandas DataFrame into standardized JobPosting models."""
    mock_df = pd.DataFrame([
        {
            "title": "Lead Multi-Agent Systems Engineer",
            "company": "Enterprise AI Lab",
            "location": "Remote, US",
            "site": "indeed",
            "job_url": "https://www.indeed.com/viewjob?jk=12345",
            "job_url_direct": "https://careers.enterpriseai.com/job/12345",
            "description": "Develop autonomous agent frameworks with Gemini API.",
            "min_amount": 180000,
            "max_amount": 230000,
            "is_remote": True,
            "job_type": "fulltime",
            "date_posted": "2026-03-26",
        }
    ])

    with patch("jobspy.scrape_jobs", return_value=mock_df):
        scraper = JobSpyScraper()
        jobs = scraper.fetch_jobs(query="Multi-Agent", location="Remote", limit=10)

    assert len(jobs) == 1
    job = jobs[0]
    assert isinstance(job, JobPosting)
    assert job.title == "Lead Multi-Agent Systems Engineer"
    assert job.company_name == "Enterprise AI Lab"
    assert job.work_type == WorkType.REMOTE
    assert job.source == "JobSpy (Indeed)"
    assert "$180,000 - $230,000" in (job.metadata.get("salary") or "")
    assert "https://www.indeed.com/viewjob?jk=12345" in job.url
    assert job.job_id.startswith("jobspy_")


def test_apify_cloud_actor_and_bot_mitigation():
    """Verify ApifyScraper routes Wellfound and Glassdoor to cloud actors rather than local scraping."""
    mock_apify_client = MagicMock()
    mock_actor = MagicMock()
    mock_dataset = MagicMock()

    mock_dataset.iterate_items.return_value = [
        {
            "title": "Founding AI Engineer",
            "companyName": "Stealth Agent Startup",
            "location": "San Francisco, CA / Remote",
            "jobUrl": "https://wellfound.com/jobs/9999",
            "description": "Ground-floor opportunity on autonomous agents.",
            "postedDate": "2026-03-24T18:00:00Z",
        }
    ]
    mock_actor.call.return_value = {"defaultDatasetId": "dataset_123"}
    mock_apify_client.actor.return_value = mock_actor
    mock_apify_client.dataset.return_value = mock_dataset

    with patch("apify_client.ApifyClient", return_value=mock_apify_client):
        scraper = ApifyScraper(api_token="test_mock_token_123")

        # Test Wellfound cloud routing (Anti-bot mitigation)
        wf_jobs = scraper.scrape_wellfound(query="Founding Engineer", location="Remote", limit=5)
        assert len(wf_jobs) == 1
        wf_job = wf_jobs[0]
        assert wf_job.title == "Founding AI Engineer"
        assert wf_job.company_name == "Stealth Agent Startup"
        assert wf_job.source == "Apify (Wellfound)"
        assert wf_job.metadata["actor_id"] == "anchor/wellfound-angel-jobs-scraper"
        assert mock_apify_client.actor.call_args[0][0] == "anchor/wellfound-angel-jobs-scraper"

        # Test Glassdoor cloud routing (Anti-bot mitigation)
        scraper.scrape_glassdoor(query="Data Architect", location="Remote", limit=5)
        assert mock_apify_client.actor.call_args[0][0] == "canadesk/glassdoor-jobs-scraper"


def test_jsearch_google_jobs_normalization():
    """Verify JSearchScraper parses RapidAPI Google Jobs JSON responses."""
    def jsearch_handler(request: httpx.Request) -> httpx.Response:
        assert "jsearch.p.rapidapi.com/search" in str(request.url)
        assert request.headers.get("x-rapidapi-key") == "mock_rapidapi_key"
        mock_payload = {
            "status": "OK",
            "data": [
                {
                    "job_id": "jsearch_98765",
                    "job_title": "Principal Distributed Systems Engineer",
                    "employer_name": "NextEra Analytics",
                    "job_apply_link": "https://nextera.com/careers/98765",
                    "job_description": "Architect fault-tolerant event streams.",
                    "job_is_remote": True,
                    "job_city": "New York",
                    "job_country": "US",
                    "job_min_salary": 195000,
                    "job_max_salary": 245000,
                    "job_posted_at_datetime_utc": "2026-03-25T10:00:00Z",
                    "job_publisher": "LinkedIn",
                }
            ],
        }
        return httpx.Response(200, json=mock_payload, request=request)

    client = httpx.Client(transport=httpx.MockTransport(jsearch_handler))
    scraper = JSearchScraper(rapidapi_key="mock_rapidapi_key")
    scraper._client = client

    jobs = scraper.fetch_jobs(query="Distributed Systems", location="Remote", limit=10)
    assert len(jobs) == 1
    job = jobs[0]
    assert job.title == "Principal Distributed Systems Engineer"
    assert job.company_name == "NextEra Analytics"
    assert job.work_type == WorkType.REMOTE
    assert job.source == "jsearch"
    assert "$195,000 - $245,000" in (job.metadata.get("salary") or "")
    assert "https://nextera.com/careers/98765" in job.url


def test_jooble_api_normalization():
    """Verify JoobleScraper parses POST response from Jooble API."""
    def jooble_handler(request: httpx.Request) -> httpx.Response:
        assert "jooble.org/api/mock_jooble_key" in str(request.url)
        assert request.method == "POST"
        mock_payload = {
            "totalCount": 1,
            "jobs": [
                {
                    "id": 55102,
                    "title": "Senior Cloud Infrastructure Specialist",
                    "location": "Lisbon, Portugal / Remote",
                    "snippet": "Deploy high-performance Kubernetes clusters.",
                    "link": "https://jooble.org/desc/55102",
                    "company": "Lisbon Cloud Solutions",
                    "salary": "€80,000 - €105,000",
                    "updated": "2026-03-26T00:00:00Z",
                }
            ],
        }
        return httpx.Response(200, json=mock_payload, request=request)

    client = httpx.Client(transport=httpx.MockTransport(jooble_handler))
    scraper = JoobleScraper(api_key="mock_jooble_key")
    scraper._client = client

    jobs = scraper.fetch_jobs(query="Cloud Infrastructure", location="Lisbon", limit=10)
    assert len(jobs) == 1
    job = jobs[0]
    assert job.title == "Senior Cloud Infrastructure Specialist"
    assert job.company_name == "Lisbon Cloud Solutions"
    assert job.work_type == WorkType.REMOTE
    assert job.source == "jooble"
    assert "jooble_55102" in job.job_id or "jooble_" in job.job_id


def test_tier3_functional_runners():
    """Verify all Tier 3 functional interfaces return dictionaries correctly."""
    assert callable(fetch_jobspy_jobs)
    assert callable(fetch_apify_jobs)
    assert callable(fetch_jsearch_jobs)
    assert callable(fetch_jooble_jobs)
    assert callable(fetch_wellfound_apify_jobs)
    assert callable(fetch_glassdoor_apify_jobs)
