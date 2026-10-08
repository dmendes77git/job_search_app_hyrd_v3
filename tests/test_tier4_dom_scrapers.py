"""Unit tests for Tier 4: Regional, Portuguese, and Niche DOM Scrapers."""

from __future__ import annotations

import json
from unittest.mock import patch
import httpx
import pytest

from src.schemas import JobPosting, WorkType
from src.agents.scrapers.regional_scrapers import (
    ITJobsScraper,
    NetEmpregosScraper,
    LandingJobsScraper,
    TeamlyzerScraper,
    InfoJobsScraper,
    fetch_itjobs_jobs,
    fetch_netempregos_jobs,
    fetch_landingjobs_jobs,
    fetch_teamlyzer_jobs,
    fetch_infojobs_jobs,
)
from src.agents.scrapers.niche_scrapers import (
    LinkedInGuestScraper,
    BuiltInScraper,
    TelecomCrossingScraper,
    ZipRecruiterDOMScraper,
    WellfoundScraper,
    fetch_builtin_jobs,
    fetch_wellfound_jobs,
)


# ============================================================================
# 1. ITJOBS.PT TESTS
# ============================================================================

SAMPLE_ITJOBS_HTML = """
<html>
<body>
    <ul class="listing">
        <li>
            <div class="list-title"><a class="title" href="/oferta/123456/senior-python-engineer">Senior Python Engineer</a></div>
            <div class="list-name"><a href="/empresa/techcorp">TechCorp Portugal</a></div>
            <div class="list-details">Lisboa, Portugal • Remoto</div>
        </li>
        <li>
            <div class="list-title"><a class="title" href="/oferta/789101/devops-lead">DevOps Lead</a></div>
            <div class="list-name"><a href="/empresa/cloudsystems">CloudSystems</a></div>
            <div class="list-details">Porto • Híbrido</div>
        </li>
    </ul>
</body>
</html>
"""

def test_itjobs_scraper_parsing():
    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=SAMPLE_ITJOBS_HTML)

    scraper = ITJobsScraper(transport=httpx.MockTransport(mock_handler))
    jobs = scraper.fetch_jobs(query="Python", limit=10)

    assert len(jobs) == 2
    j1 = jobs[0]
    assert j1.title == "Senior Python Engineer"
    assert j1.company_name == "TechCorp Portugal"
    assert j1.work_type == WorkType.REMOTE
    assert j1.source == "ITJobs.pt"
    assert j1.job_id.startswith("itjobs.pt_")
    assert j1.metadata.get("itjobs_id") == "123456"
    assert j1.url == "https://www.itjobs.pt/oferta/123456/senior-python-engineer"

    j2 = jobs[1]
    assert j2.title == "DevOps Lead"
    assert j2.company_name == "CloudSystems"
    assert j2.work_type == WorkType.HYBRID


# ============================================================================
# 2. NET-EMPREGOS (ISO-8859-1) TESTS
# ============================================================================

SAMPLE_NETEMPREGOS_RAW_BYTES = """
<html>
<body>
    <div class="job-item">
        <h2><a class="oferta-link" href="/9876543/engenheiro-de-software-senior/">Engenheiro de Software Sénior</a></h2>
        <li class="flaticon-work">Inovação Tech Lda</li>
        <li class="flaticon-pin">Braga (Teletrabalho)</li>
        <li class="flaticon-calendar">Hoje</li>
        <li class="fa-tags">Informática / TI</li>
    </div>
</body>
</html>
""".encode("iso-8859-1")

def test_netempregos_scraper_iso_encoding():
    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=SAMPLE_NETEMPREGOS_RAW_BYTES,
            headers={"Content-Type": "text/html; charset=iso-8859-1"},
        )

    scraper = NetEmpregosScraper(transport=httpx.MockTransport(mock_handler))
    jobs = scraper.fetch_jobs(query="Software", limit=5)

    assert len(jobs) == 1
    job = jobs[0]
    assert "Sénior" in job.title or "Senior" in job.title
    assert "Inovação" in job.company_name or "Inovacao" in job.company_name
    assert job.work_type == WorkType.REMOTE
    assert job.source == "Net-Empregos"
    assert job.job_id.startswith("net-empregos_")
    assert job.metadata.get("netempregos_id") == "9876543"


# ============================================================================
# 3. LANDING.JOBS TESTS
# ============================================================================

SAMPLE_LANDINGJOBS_HTML = """
<html>
<body>
    <article class="lj-jobcard-static">
        <h2 class="lj-jobcard-static__title"><a href="/jobs/backend-architect-101">Backend Architect</a></h2>
        <div class="lj-jobcard-static__company"><a href="/co/fintech">Fintech Scaleup</a></div>
        <div class="lj-jobcard-static__location">Lisbon, Portugal</div>
        <span class="lj-jobcard-static__badge">Remote in Europe</span>
        <span class="lj-jobcard-static__salary">€65.000 - €85.000</span>
        <span class="lj-jobcard-static__skill">Python</span>
        <span class="lj-jobcard-static__skill">FastAPI</span>
    </article>
</body>
</html>
"""

def test_landingjobs_scraper_parsing():
    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=SAMPLE_LANDINGJOBS_HTML)

    scraper = LandingJobsScraper(transport=httpx.MockTransport(mock_handler))
    jobs = scraper.fetch_jobs(query="Backend", limit=5)

    assert len(jobs) == 1
    job = jobs[0]
    assert job.title == "Backend Architect"
    assert job.company_name == "Fintech Scaleup"
    assert job.work_type == WorkType.REMOTE
    assert job.source == "Landing.jobs"
    assert "€65.000 - €85.000" in job.metadata.get("salary", "")
    assert "Python" in job.metadata.get("skills", [])


# ============================================================================
# 4. TEAMLYZER TESTS
# ============================================================================

SAMPLE_TEAMLYZER_HTML = """
<html>
<body>
    <a href="/companies/intellias/job/lead-platform-engineer-up-to-65k">Lead Platform Engineer (up to 65k) - Remote</a>
    <a href="/companies/farfetch/job/staff-ml-engineer-80k">Staff ML Engineer - 80k - Hybrid</a>
</body>
</html>
"""

def test_teamlyzer_scraper_parsing():
    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=SAMPLE_TEAMLYZER_HTML)

    scraper = TeamlyzerScraper(transport=httpx.MockTransport(mock_handler))
    jobs = scraper.fetch_jobs(query="Engineer", limit=5)

    assert len(jobs) == 2
    j1 = jobs[0]
    assert "Lead Platform Engineer" in j1.title
    assert j1.company_name == "Intellias"
    assert j1.work_type == WorkType.REMOTE
    assert j1.source == "Teamlyzer"
    assert "65K" in j1.metadata.get("salary", "")

    j2 = jobs[1]
    assert j2.company_name == "Farfetch"
    assert j2.work_type == WorkType.HYBRID


# ============================================================================
# 5. INFOJOBS TESTS
# ============================================================================

SAMPLE_INFOJOBS_HTML = """
<html>
<body>
    <li class="ij-OfferCard">
        <h2><a class="ij-OfferCardTitle-link" href="/ofertas-trabajo/ingeniero-datos-of-abc12345">Ingeniero de Datos Cloud</a></h2>
        <a class="ij-OfferCardContent-description-list-link">Telefónica Tech</a>
        <div class="ij-OfferCardProperty-description">Madrid (Teletrabajo)</div>
        <div class="ij-OfferCardProperty-salary">€45.000 - €55.000 Bruto/año</div>
    </li>
</body>
</html>
"""

def test_infojobs_scraper_parsing():
    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=SAMPLE_INFOJOBS_HTML)

    scraper = InfoJobsScraper(transport=httpx.MockTransport(mock_handler))
    jobs = scraper.fetch_jobs(query="Datos", limit=5)

    assert len(jobs) == 1
    job = jobs[0]
    assert job.title == "Ingeniero de Datos Cloud"
    assert job.company_name == "Telefónica Tech"
    assert job.work_type == WorkType.REMOTE
    assert job.source == "InfoJobs"
    assert job.job_id.startswith("infojobs_")
    assert job.metadata.get("infojobs_id") == "abc12345"
    assert "€45.000 - €55.000" in job.metadata.get("salary", "")


# ============================================================================
# 6. LINKEDIN GUEST SCRAPER TESTS
# ============================================================================

SAMPLE_LINKEDIN_GUEST_HTML = """
<ul class="jobs-search__results-list">
    <li>
        <div class="base-search-card">
            <h3 class="base-search-card__title">Senior Staff Engineer</h3>
            <h4 class="base-search-card__subtitle">Stripe</h4>
            <span class="job-search-card__location">Dublin, Ireland (Remote)</span>
            <a class="base-card__full-link" href="https://ie.linkedin.com/jobs/view/senior-staff-engineer-at-stripe-33445566?refId=123"></a>
        </div>
    </li>
</ul>
"""

def test_linkedin_guest_scraper_parsing():
    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=SAMPLE_LINKEDIN_GUEST_HTML)

    scraper = LinkedInGuestScraper(transport=httpx.MockTransport(mock_handler))
    jobs = scraper.fetch_jobs(query="Engineer", location="Dublin", work_mode="Remote Only", limit=5)

    assert len(jobs) == 1
    job = jobs[0]
    assert job.title == "Senior Staff Engineer"
    assert job.company_name == "Stripe"
    assert job.work_type == WorkType.REMOTE
    assert job.source == "LinkedIn"
    assert job.url == "https://ie.linkedin.com/jobs/view/senior-staff-engineer-at-stripe-33445566"


# ============================================================================
# 7. BUILTIN (NEXT.JS __NEXT_DATA__ EXTRACTION) TESTS
# ============================================================================

SAMPLE_BUILTIN_NEXTJS_HTML = """
<html>
<head>
<script id="__NEXT_DATA__" type="application/json">
{
    "props": {
        "pageProps": {
            "jobs": [
                {
                    "id": 998811,
                    "title": "Principal AI Architect",
                    "company_name": "NextGen AI Lab",
                    "location": "San Francisco, CA",
                    "remote": true,
                    "alias": "principal-ai-architect-998811",
                    "body": "Design state-of-the-art transformer systems.",
                    "salary_min": 210000,
                    "salary_max": 280000
                }
            ]
        }
    }
}
</script>
</head>
<body>
</body>
</html>
"""

def test_builtin_nextjs_payload_extraction():
    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=SAMPLE_BUILTIN_NEXTJS_HTML)

    scraper = BuiltInScraper(transport=httpx.MockTransport(mock_handler))
    jobs = scraper.fetch_jobs(query="AI", limit=5)

    assert len(jobs) == 1
    job = jobs[0]
    assert job.title == "Principal AI Architect"
    assert job.company_name == "NextGen AI Lab"
    assert job.work_type == WorkType.REMOTE
    assert job.source == "BuiltIn"
    assert "210,000" in job.metadata.get("salary", "")
    assert job.job_id.startswith("builtin_")
    assert job.metadata.get("builtin_id") == "998811"


# ============================================================================
# 8. TELECOMCROSSING TESTS
# ============================================================================

SAMPLE_TELECOMCROSSING_HTML = """
<html>
<body>
    <a href="/job/id-112233/senior-fiber-network-engineer">Senior Fiber Network Engineer</a>
    <a href="/job/id-445566/rf-systems-specialist-remote">RF Systems Specialist - Remote</a>
</body>
</html>
"""

def test_telecomcrossing_scraper_parsing():
    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=SAMPLE_TELECOMCROSSING_HTML)

    scraper = TelecomCrossingScraper(transport=httpx.MockTransport(mock_handler))
    jobs = scraper.fetch_jobs(query="Network", limit=5)

    assert len(jobs) == 2
    assert jobs[0].title == "Senior Fiber Network Engineer"
    assert jobs[0].work_type == WorkType.ONSITE
    assert jobs[1].title == "RF Systems Specialist - Remote"
    assert jobs[1].work_type == WorkType.REMOTE
    assert jobs[0].source == "TelecomCrossing"


# ============================================================================
# 9. ZIPRECRUITER DOM FALLBACK TESTS
# ============================================================================

SAMPLE_ZIPRECRUITER_DOM_HTML = """
<html>
<body>
    <article class="job_result">
        <h2><a class="job_link" href="https://www.ziprecruiter.com/jobs/devops-lead-554433?lvk=123">Senior Site Reliability Engineer</a></h2>
        <div class="company_name">CloudCore Global</div>
        <div class="location">Remote, US</div>
    </article>
</body>
</html>
"""

def test_ziprecruiter_dom_fallback_parsing():
    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=SAMPLE_ZIPRECRUITER_DOM_HTML)

    scraper = ZipRecruiterDOMScraper(transport=httpx.MockTransport(mock_handler))
    jobs = scraper.fetch_jobs(query="SRE", location="Remote", limit=5)

    assert len(jobs) == 1
    job = jobs[0]
    assert job.title == "Senior Site Reliability Engineer"
    assert job.company_name == "CloudCore Global"
    assert job.work_type == WorkType.REMOTE
    assert job.source == "ZipRecruiter"


# ============================================================================
# 10. WELLFOUND (APIFY CLOUD ACTOR BOT-MITIGATION) TESTS
# ============================================================================

def test_wellfound_bot_mitigation_routing():
    # Without API token: gracefully logs warning and returns empty list
    scraper = WellfoundScraper(apify_token=None)
    jobs = scraper.fetch_jobs(query="Founder Associate", limit=5)
    assert jobs == []

    # With API token: routes to fetch_wellfound_apify_jobs
    mock_raw_jobs = [
        {
            "id": "wf_1",
            "title": "Founding Engineer",
            "company": "Stealth AI",
            "location": "San Francisco, CA",
            "remote": True,
            "source": "Wellfound",
            "url": "https://wellfound.com/jobs/123",
            "full_description": "Founding engineer opening.",
        }
    ]
    with patch("src.agents.scrapers.aggregator_scrapers.fetch_wellfound_apify_jobs", return_value=mock_raw_jobs):
        scraper_with_token = WellfoundScraper(apify_token="apify_test_token_123")
        jobs = scraper_with_token.fetch_jobs(query="Founding Engineer", limit=5)
        assert len(jobs) == 1
        assert jobs[0].title == "Founding Engineer"
        assert jobs[0].company_name == "Stealth AI"
        assert jobs[0].work_type == WorkType.REMOTE
