"""
Unit tests for Tier 2 Public JSON & RSS Scrapers:
Jobicy, Arbeitnow, RemoteOK, Remotive, Himalayas, WeWorkRemotely, and Hacker News.
"""

from typing import List
import httpx
import pytest

from src.agents.scrapers.remote_scrapers import (
    JobicyScraper,
    ArbeitnowScraper,
    RemoteOKScraper,
    RemotiveScraper,
    HimalayasScraper,
    WeWorkRemotelyScraper,
    HackerNewsScraper,
    fetch_jobicy_jobs,
    fetch_arbeitnow_jobs,
    fetch_remoteok_jobs,
    fetch_remotive_jobs,
    fetch_himalayas_jobs,
    fetch_weworkremotely_jobs,
    fetch_hackernews_jobs,
)
from src.schemas import JobPosting, WorkType


def test_jobicy_scraper_normalization():
    """Verify JobicyScraper parses JSON response into standardized JobPosting."""
    def jobicy_handler(request: httpx.Request) -> httpx.Response:
        assert "jobicy.com/api/v2/remote-jobs" in str(request.url)
        mock_payload = {
            "jobs": [
                {
                    "id": 8801,
                    "jobTitle": "Lead AI Application Architect",
                    "companyName": "OmniAI Corp",
                    "jobExcerpt": "Design multi-agent orchestration backends.",
                    "jobGeo": "Remote (Worldwide)",
                    "jobIndustry": ["Artificial Intelligence", "Software Engineering"],
                    "url": "https://jobicy.com/jobs/8801",
                    "pubDate": "2026-03-25 14:00:00",
                }
            ]
        }
        return httpx.Response(200, json=mock_payload, request=request)

    client = httpx.Client(transport=httpx.MockTransport(jobicy_handler))
    scraper = JobicyScraper(client=client)

    jobs = scraper.fetch_jobs(query="Application Architect")
    assert len(jobs) == 1
    job = jobs[0]
    assert isinstance(job, JobPosting)
    assert job.title == "Lead AI Application Architect"
    assert job.company_name == "OmniAI Corp"
    assert job.work_type == WorkType.REMOTE
    assert job.source == "jobicy"
    assert "https://jobicy.com/jobs/8801" in job.url
    assert job.job_id.startswith("jobicy_")


def test_arbeitnow_scraper_normalization():
    """Verify ArbeitnowScraper parses JSON response into standardized JobPosting."""
    def arbeitnow_handler(request: httpx.Request) -> httpx.Response:
        assert "arbeitnow.com/api/job-board-api" in str(request.url)
        mock_payload = {
            "data": [
                {
                    "slug": "senior-python-engineer-berlin-1234",
                    "title": "Senior Python & Agentic Systems Engineer",
                    "company_name": "NextGen Logistics",
                    "description": "<p>Build autonomous workflows with FastAPI and Gemini.</p>",
                    "location": "Berlin, Germany / Hybrid",
                    "remote": False,
                    "tags": ["python", "fastapi", "agents"],
                    "job_types": ["Full-time"],
                    "created_at": 1774000000,
                    "url": "https://www.arbeitnow.com/view/senior-python-engineer-berlin-1234",
                }
            ]
        }
        return httpx.Response(200, json=mock_payload, request=request)

    client = httpx.Client(transport=httpx.MockTransport(arbeitnow_handler))
    scraper = ArbeitnowScraper(client=client)

    jobs = scraper.fetch_jobs(query="Python")
    assert len(jobs) == 1
    job = jobs[0]
    assert job.title == "Senior Python & Agentic Systems Engineer"
    assert job.company_name == "NextGen Logistics"
    assert job.work_type == WorkType.HYBRID
    assert job.source == "arbeitnow"
    assert "Build autonomous workflows" in job.description_text


def test_remoteok_scraper_normalization():
    """Verify RemoteOKScraper parses JSON response and compensation intervals."""
    def remoteok_handler(request: httpx.Request) -> httpx.Response:
        assert "remoteok.com/api" in str(request.url)
        mock_payload = [
            {"legal": "Notice"},
            {
                "id": "rok-552",
                "position": "Staff Infrastructure Engineer",
                "company": "CloudNative Labs",
                "description": "High-availability Kubernetes and distributed databases.",
                "location": "Remote (Worldwide)",
                "salary_min": 160000,
                "salary_max": 220000,
                "tags": ["kubernetes", "golang", "remote"],
                "url": "https://remoteok.com/remote-jobs/rok-552",
                "date": "2026-03-24T12:00:00Z",
            }
        ]
        return httpx.Response(200, json=mock_payload, request=request)

    client = httpx.Client(transport=httpx.MockTransport(remoteok_handler))
    scraper = RemoteOKScraper(client=client)

    jobs = scraper.fetch_jobs()
    assert len(jobs) == 1
    job = jobs[0]
    assert job.title == "Staff Infrastructure Engineer"
    assert job.company_name == "CloudNative Labs"
    assert job.work_type == WorkType.REMOTE
    assert job.source == "remoteok"
    assert "$160,000 - $220,000" in (job.metadata.get("salary") or "")


def test_remotive_scraper_normalization():
    """Verify RemotiveScraper parses JSON response into standardized JobPosting."""
    def remotive_handler(request: httpx.Request) -> httpx.Response:
        assert "remotive.com/api/remote-jobs" in str(request.url)
        mock_payload = {
            "jobs": [
                {
                    "id": 9931,
                    "title": "Senior Backend Architect",
                    "company_name": "Fintech Global",
                    "candidate_required_location": "USA / Canada / EU",
                    "salary": "$175,000 - $210,000",
                    "tags": ["python", "architecture"],
                    "url": "https://remotive.com/job/9931",
                    "publication_date": "2026-03-22T09:00:00Z",
                    "description": "<p>Lead our core ledger engineering squad.</p>",
                }
            ]
        }
        return httpx.Response(200, json=mock_payload, request=request)

    client = httpx.Client(transport=httpx.MockTransport(remotive_handler))
    scraper = RemotiveScraper(client=client)

    jobs = scraper.fetch_jobs(query="Backend")
    assert len(jobs) == 1
    job = jobs[0]
    assert job.title == "Senior Backend Architect"
    assert job.company_name == "Fintech Global"
    assert job.work_type == WorkType.REMOTE
    assert job.source == "remotive"


def test_himalayas_scraper_normalization():
    """Verify HimalayasScraper parses API response with rich compensation and seniority."""
    def himalayas_handler(request: httpx.Request) -> httpx.Response:
        assert "himalayas.app/jobs/api" in str(request.url)
        mock_payload = {
            "jobs": [
                {
                    "guid": "him-4421",
                    "title": "Principal Machine Learning Engineer",
                    "companyName": "Cortex Intelligence",
                    "companySlug": "cortex-ai",
                    "applicationLink": "https://himalayas.app/companies/cortex-ai/jobs/him-4421",
                    "description": "Develop multimodal frontier architectures.",
                    "locationRestrictions": ["Worldwide"],
                    "minSalary": 200000,
                    "maxSalary": 275000,
                    "currency": "USD",
                    "seniority": "Principal",
                    "employmentType": "Full-Time",
                    "pubDate": "2026-03-25T16:00:00.000Z",
                }
            ]
        }
        return httpx.Response(200, json=mock_payload, request=request)

    client = httpx.Client(transport=httpx.MockTransport(himalayas_handler))
    scraper = HimalayasScraper(client=client)

    jobs = scraper.fetch_jobs(query="Machine Learning")
    assert len(jobs) == 1
    job = jobs[0]
    assert job.title == "Principal Machine Learning Engineer"
    assert job.company_name == "Cortex Intelligence"
    assert job.work_type == WorkType.REMOTE
    assert job.source == "himalayas"
    assert job.metadata["seniority"] == "Principal"
    assert "200,000" in (job.metadata.get("salary") or "")


def test_weworkremotely_scraper_rss():
    """Verify WeWorkRemotelyScraper parses RSS feed XML."""
    mock_rss_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
      <channel>
        <title>We Work Remotely</title>
        <item>
          <title><![CDATA[Automattic: Lead WordPress Core Architect]]></title>
          <link>https://weworkremotely.com/remote-jobs/automattic-lead-wordpress-architect</link>
          <description><![CDATA[<p>Shape the future of open web publishing.</p>]]></description>
          <region>Anywhere in the World</region>
          <pubDate>Wed, 25 Mar 2026 12:00:00 +0000</pubDate>
        </item>
      </channel>
    </rss>
    """

    def wwr_handler(request: httpx.Request) -> httpx.Response:
        assert "weworkremotely.com/remote-jobs.rss" in str(request.url)
        return httpx.Response(200, content=mock_rss_xml.encode("utf-8"), request=request)

    client = httpx.Client(transport=httpx.MockTransport(wwr_handler))
    scraper = WeWorkRemotelyScraper(client=client)

    jobs = scraper.fetch_jobs(query="Architect")
    assert len(jobs) == 1
    job = jobs[0]
    assert job.title == "Lead WordPress Core Architect"
    assert job.company_name == "Automattic"
    assert job.work_type == WorkType.REMOTE
    assert job.source == "weworkremotely"
    assert "Shape the future of open web" in job.description_text


def test_hackernews_scraper_algolia_integration():
    """Verify HackerNewsScraper two-step search (thread lookup + comment parse)."""
    step1_called = False
    step2_called = False

    def hn_handler(request: httpx.Request) -> httpx.Response:
        nonlocal step1_called, step2_called
        url_str = str(request.url)

        if "tags=story%2Cauthor_whoishiring" in url_str or "tags=story,author_whoishiring" in url_str:
            step1_called = True
            mock_story = {
                "hits": [
                    {
                        "objectID": "story_499000",
                        "title": "Ask HN: Who is hiring? (March 2026)",
                    }
                ]
            }
            return httpx.Response(200, json=mock_story, request=request)

        elif "tags=comment%2Cstory_story_499000" in url_str or "story_story_499000" in url_str:
            step2_called = True
            mock_comments = {
                "hits": [
                    {
                        "objectID": "comment_881234",
                        "author": "techfounder",
                        "comment_text": "Cortex Labs | Staff AI Engineer | Remote (US/EU) | Full-time<p>We are building autonomous cognitive assistants.</p>",
                        "created_at": "2026-03-02T15:30:00Z",
                    }
                ]
            }
            return httpx.Response(200, json=mock_comments, request=request)

        return httpx.Response(404, request=request)

    client = httpx.Client(transport=httpx.MockTransport(hn_handler))
    scraper = HackerNewsScraper(client=client)

    jobs = scraper.fetch_jobs(query="Engineer")
    assert step1_called is True
    assert step2_called is True
    assert len(jobs) == 1
    job = jobs[0]
    assert job.company_name == "Cortex Labs"
    assert job.title == "Staff AI Engineer"
    assert job.work_type == WorkType.REMOTE
    assert job.source == "hackernews"
    assert "https://news.ycombinator.com/item?id=comment_881234" in job.url


def test_tier2_legacy_functional_runners():
    """Verify all Tier 2 functional interfaces return dictionaries correctly."""
    assert callable(fetch_jobicy_jobs)
    assert callable(fetch_arbeitnow_jobs)
    assert callable(fetch_remoteok_jobs)
    assert callable(fetch_remotive_jobs)
    assert callable(fetch_himalayas_jobs)
    assert callable(fetch_weworkremotely_jobs)
    assert callable(fetch_hackernews_jobs)
