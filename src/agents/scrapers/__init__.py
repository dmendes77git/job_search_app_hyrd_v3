"""Scrapers package for Hyrd job discovery.

Contains specialized scrapers organized by category:
- ats_scrapers: Ashby, Greenhouse, Lever, SmartRecruiters direct ATS APIs
- aggregator_scrapers: JobSpy multi-board engine, Apify actor
- remote_scrapers: Arbeitnow, Jobicy, RemoteOK, Remotive, LinkedIn, WeWorkRemotely, TelecomCrossing, ZipRecruiter
- base: Common HTTP headers, text normalization, and resilience wrappers
"""

from .base import (
    DEFAULT_HEADERS,
    clean_html_text,
    normalize_company_slug,
    safe_fetch_json,
    safe_scrape,
)
from .ats_scrapers import (
    fetch_ashby_jobs,
    fetch_greenhouse_jobs,
    fetch_lever_jobs,
    fetch_smartrecruiters_jobs,
)
from .aggregator_scrapers import (
    silence_jobspy_loggers,
    fetch_jobspy_jobs,
    fetch_apify_jobs,
)
from .remote_scrapers import (
    fetch_arbeitnow_jobs,
    fetch_jobicy_jobs,
    fetch_remoteok_jobs,
    fetch_remotive_jobs,
    fetch_linkedin_jobs,
    fetch_weworkremotely_jobs,
    fetch_telecomcrossing_jobs,
    fetch_ziprecruiter_jobs,
)

__all__ = [
    "DEFAULT_HEADERS",
    "clean_html_text",
    "normalize_company_slug",
    "safe_fetch_json",
    "safe_scrape",
    "fetch_ashby_jobs",
    "fetch_greenhouse_jobs",
    "fetch_lever_jobs",
    "fetch_smartrecruiters_jobs",
    "silence_jobspy_loggers",
    "fetch_jobspy_jobs",
    "fetch_apify_jobs",
    "fetch_arbeitnow_jobs",
    "fetch_jobicy_jobs",
    "fetch_remoteok_jobs",
    "fetch_remotive_jobs",
    "fetch_linkedin_jobs",
    "fetch_weworkremotely_jobs",
    "fetch_telecomcrossing_jobs",
    "fetch_ziprecruiter_jobs",
]
