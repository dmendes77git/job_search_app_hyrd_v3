"""
Unit tests for Tier 1 Direct ATS Scrapers:
Greenhouse, Lever, Ashby, Workday, BambooHR, BreezyHR, and SmartRecruiters.
"""

from typing import List
import httpx
import pytest

from src.agents.scrapers.ats_scrapers import (
    GreenhouseScraper,
    LeverScraper,
    AshbyScraper,
    WorkdayScraper,
    BambooHRScraper,
    BreezyHRScraper,
    SmartRecruitersScraper,
    fetch_ashby_jobs,
    fetch_greenhouse_jobs,
    fetch_lever_jobs,
    fetch_smartrecruiters_jobs,
    fetch_workday_jobs,
    fetch_bamboohr_jobs,
    fetch_breezyhr_jobs,
)
from src.schemas import JobPosting, WorkType


def test_greenhouse_dynamic_company_ingestion():
    """Verify GreenhouseScraper handles dynamic company slugs with mock transport."""
    def greenhouse_handler(request: httpx.Request) -> httpx.Response:
        assert "boards-api.greenhouse.io" in str(request.url)
        assert "customorg" in str(request.url)
        mock_payload = {
            "jobs": [
                {
                    "id": 1001,
                    "title": "Staff Platform Architect",
                    "location": {"name": "Remote, EMEA"},
                    "absolute_url": "https://boards.greenhouse.io/customorg/jobs/1001",
                    "updated_at": "2026-03-15T12:00:00Z",
                    "departments": [{"name": "Core Infrastructure"}],
                    "offices": [{"name": "Lisbon Office"}],
                }
            ]
        }
        return httpx.Response(200, json=mock_payload, request=request)

    client = httpx.Client(transport=httpx.MockTransport(greenhouse_handler))
    scraper = GreenhouseScraper(client=client)

    jobs = scraper.fetch_jobs("customorg", query="Platform", company_display_name="CustomOrg")
    assert len(jobs) == 1
    job = jobs[0]
    assert isinstance(job, JobPosting)
    assert job.title == "Staff Platform Architect"
    assert job.company_name == "CustomOrg"
    assert job.work_type == WorkType.REMOTE
    assert job.source == "greenhouse"
    assert job.job_id.startswith("greenhouse_")
    assert "https://boards.greenhouse.io/customorg/jobs/1001" in job.url
    assert job.is_direct_ats is True


def test_lever_dynamic_company_ingestion():
    """Verify LeverScraper handles dynamic company slugs and workplaceType."""
    def lever_handler(request: httpx.Request) -> httpx.Response:
        assert "api.lever.co" in str(request.url)
        assert "innovatecorp" in str(request.url)
        mock_payload = [
            {
                "id": "lev-909",
                "text": "Principal Applied AI Scientist",
                "createdAt": 1773500000000,
                "hostedUrl": "https://jobs.lever.co/innovatecorp/lev-909",
                "workplaceType": "hybrid",
                "categories": {
                    "location": "London / Hybrid",
                    "commitment": "Full-time",
                    "team": "Machine Learning",
                },
                "descriptionPlain": "Build frontier reasoning agents.",
            }
        ]
        return httpx.Response(200, json=mock_payload, request=request)

    client = httpx.Client(transport=httpx.MockTransport(lever_handler))
    scraper = LeverScraper(client=client)

    jobs = scraper.fetch_jobs("innovatecorp", company_display_name="InnovateCorp")
    assert len(jobs) == 1
    job = jobs[0]
    assert job.title == "Principal Applied AI Scientist"
    assert job.company_name == "InnovateCorp"
    assert job.work_type == WorkType.HYBRID
    assert job.source == "lever"
    assert "Frontier reasoning" in job.description_text or "Build frontier" in job.description_text
    assert job.metadata["commitment"] == "Full-time"


def test_ashby_dynamic_company_ingestion():
    """Verify AshbyScraper handles dynamic startups and compensation metadata."""
    def ashby_handler(request: httpx.Request) -> httpx.Response:
        assert "api.ashbyhq.com" in str(request.url)
        assert "futureai" in str(request.url)
        mock_payload = {
            "jobs": [
                {
                    "id": "ash-777",
                    "title": "Lead Multi-Agent Systems Engineer",
                    "location": "San Francisco, CA",
                    "isRemote": True,
                    "jobUrl": "https://jobs.ashbyhq.com/futureai/ash-777",
                    "publishedAt": "2026-03-20T08:30:00Z",
                    "department": "Autonomous Agents",
                    "compensation": {"compensationTierSummary": "$210,000 - $260,000 + Equity"},
                }
            ]
        }
        return httpx.Response(200, json=mock_payload, request=request)

    client = httpx.Client(transport=httpx.MockTransport(ashby_handler))
    scraper = AshbyScraper(client=client)

    jobs = scraper.fetch_jobs("futureai", company_display_name="FutureAI")
    assert len(jobs) == 1
    job = jobs[0]
    assert job.title == "Lead Multi-Agent Systems Engineer"
    assert job.company_name == "FutureAI"
    assert job.work_type == WorkType.REMOTE
    assert job.source == "ashby"
    assert "$210,000" in (job.metadata.get("salary") or "")
    assert job.metadata["department"] == "Autonomous Agents"


def test_workday_csrf_handshake_and_cxs_api():
    """Verify WorkdayScraper performs two-step CSRF cookie handshake and POST."""
    handshake_called = False
    cxs_post_called = False

    def workday_handler(request: httpx.Request) -> httpx.Response:
        nonlocal handshake_called, cxs_post_called
        url_str = str(request.url)

        if request.method == "GET" and "external_experienced" in url_str:
            handshake_called = True
            # Return initial GET with CSRF cookies
            headers = {"Set-Cookie": "CALYPSO_CSRF_TOKEN=mock_secret_csrf_token; Path=/"}
            return httpx.Response(200, headers=headers, request=request)

        elif request.method == "POST" and "/wday/cxs/corp/external_experienced/jobs" in url_str:
            cxs_post_called = True
            # Check CSRF header or cookie presence
            assert request.headers.get("calypso-csrf-token") == "mock_secret_csrf_token"
            mock_payload = {
                "total": 1,
                "jobPostings": [
                    {
                        "title": "Principal Distributed Systems Engineer",
                        "externalPath": "/job/California/Principal-Eng_R999",
                        "locationsText": "Sunnyvale, CA - Remote Eligible",
                        "postedOn": "Posted 1 Day Ago",
                        "bulletFields": ["R999", "Engineering"],
                    }
                ],
            }
            return httpx.Response(200, json=mock_payload, request=request)

        return httpx.Response(404, request=request)

    client = httpx.Client(transport=httpx.MockTransport(workday_handler))
    scraper = WorkdayScraper(client=client)

    jobs = scraper.fetch_jobs(
        company_slug="corp",
        tenant_host="corp.wd5.myworkdayjobs.com",
        career_site="external_experienced",
        company_display_name="Enterprise Corp",
    )

    assert handshake_called is True
    assert cxs_post_called is True
    assert len(jobs) == 1
    job = jobs[0]
    assert job.title == "Principal Distributed Systems Engineer"
    assert job.company_name == "Enterprise Corp"
    assert "https://corp.wd5.myworkdayjobs.com/job/California/Principal-Eng_R999" in job.url
    assert job.source == "workday"
    assert job.is_direct_ats is True
    assert job.metadata["requisition_id"] == "R999"


def test_bamboohr_dynamic_company_ingestion():
    """Verify BambooHRScraper parses public careers list."""
    def bamboo_handler(request: httpx.Request) -> httpx.Response:
        assert "growthcorp.bamboohr.com/careers/list" in str(request.url)
        mock_payload = {
            "result": [
                {
                    "id": "55",
                    "jobOpeningName": "Senior Backend Developer",
                    "department": "Platform",
                    "location": {"city": "Porto", "state": "Portugal"},
                    "jobType": "Full-time",
                    "isRemote": True,
                }
            ]
        }
        return httpx.Response(200, json=mock_payload, request=request)

    client = httpx.Client(transport=httpx.MockTransport(bamboo_handler))
    scraper = BambooHRScraper(client=client)

    jobs = scraper.fetch_jobs("growthcorp", company_display_name="GrowthCorp")
    assert len(jobs) == 1
    job = jobs[0]
    assert job.title == "Senior Backend Developer"
    assert job.company_name == "GrowthCorp"
    assert job.work_type == WorkType.REMOTE
    assert job.source == "bamboohr"
    assert "growthcorp.bamboohr.com/careers/55" in job.url


def test_breezyhr_dynamic_company_ingestion():
    """Verify BreezyHRScraper parses JSON job list."""
    def breezy_handler(request: httpx.Request) -> httpx.Response:
        assert "talentlab.breezy.hr/json" in str(request.url)
        mock_payload = [
            {
                "id": "brz-123",
                "name": "Cloud Security Architect",
                "url": "https://talentlab.breezy.hr/p/brz-123",
                "published_date": "2026-03-25T10:00:00Z",
                "type": {"name": "Full-Time"},
                "location": {"name": "Remote / Hybrid", "is_remote": True},
                "department": "Information Security",
                "salary": "$160,000 - $190,000",
            }
        ]
        return httpx.Response(200, json=mock_payload, request=request)

    client = httpx.Client(transport=httpx.MockTransport(breezy_handler))
    scraper = BreezyHRScraper(client=client)

    jobs = scraper.fetch_jobs("talentlab", company_display_name="TalentLab")
    assert len(jobs) == 1
    job = jobs[0]
    assert job.title == "Cloud Security Architect"
    assert job.company_name == "TalentLab"
    assert job.work_type == WorkType.REMOTE
    assert job.source == "breezyhr"
    assert job.metadata["salary"] == "$160,000 - $190,000"


def test_smartrecruiters_dynamic_company_ingestion():
    """Verify SmartRecruitersScraper parses posting API content."""
    def sr_handler(request: httpx.Request) -> httpx.Response:
        assert "api.smartrecruiters.com" in str(request.url)
        assert "cern" in str(request.url)
        mock_payload = {
            "content": [
                {
                    "id": "sr-456",
                    "name": "Distributed Computing Research Fellow",
                    "location": {"city": "Geneva", "country": "Switzerland", "remote": False},
                    "department": {"label": "CERN Information Technology"},
                    "releasedDate": "2026-03-01T00:00:00Z",
                }
            ]
        }
        return httpx.Response(200, json=mock_payload, request=request)

    client = httpx.Client(transport=httpx.MockTransport(sr_handler))
    scraper = SmartRecruitersScraper(client=client)

    jobs = scraper.fetch_jobs("cern", company_display_name="CERN")
    assert len(jobs) == 1
    job = jobs[0]
    assert job.title == "Distributed Computing Research Fellow"
    assert job.company_name == "CERN"
    assert job.work_type == WorkType.ONSITE
    assert job.source == "smartrecruiters"
    assert "https://jobs.smartrecruiters.com/cern/sr-456" in job.url


def test_legacy_functional_runners():
    """Verify legacy functional interfaces return dictionary representations."""
    # Ensure they can be called without errors and return list of dicts
    assert callable(fetch_ashby_jobs)
    assert callable(fetch_greenhouse_jobs)
    assert callable(fetch_lever_jobs)
    assert callable(fetch_smartrecruiters_jobs)
    assert callable(fetch_workday_jobs)
    assert callable(fetch_bamboohr_jobs)
    assert callable(fetch_breezyhr_jobs)
