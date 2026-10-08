"""
Tier 3: Aggregator APIs & Cloud Actors.
Integrates Apify Multi-ATS & Cloud Actors (with Wellfound & Glassdoor bot mitigation),
JobSpy Multi-Board Engine, JSearch / RapidAPI (Google Jobs), and Jooble.

Adheres strictly to the Tier 3 Ingestion Hierarchy:
- BaseScraper polymorphic inheritance with fetch_jobs() -> List[JobPosting].
- Pure cloud-actor scaffolding for anti-bot protected targets (Wellfound, Glassdoor).
- Resilient API key handling and fallback graceful degradation.
"""

from __future__ import annotations

import logging
import os
import urllib.parse
from typing import Any, Dict, List, Optional, Sequence, Union

from src.agents.scrapers.base import (
    BaseScraper,
    JobPosting,
    WorkType,
    clean_html_text,
    generate_job_id,
    get_browser_headers,
)

logger = logging.getLogger("Hyrd.Scrapers.Tier3Aggregators")


# ============================================================================
# 1. JOBSPY LOGGER SILENCING
# ============================================================================

def silence_jobspy_loggers() -> None:
    """Mute JobSpy's internal error loggers so anti-bot responses do not pollute logs."""
    for scraper_name in ["ZipRecruiter", "Indeed", "Glassdoor", "Google", "LinkedIn", "Bayt", "BDJobs", "Naukri"]:
        lg = logging.getLogger(f"JobSpy:{scraper_name}")
        lg.setLevel(logging.CRITICAL)
        lg.propagate = False
        if not lg.handlers:
            lg.addHandler(logging.NullHandler())


silence_jobspy_loggers()


# ============================================================================
# 2. JOBSPY MULTI-BOARD ENGINE SCRAPER
# ============================================================================

class JobSpyScraper(BaseScraper):
    """
    Multi-board job scraper powered by python-jobspy.
    Aggregates postings directly from Indeed and ZipRecruiter with anti-blocking heuristics.
    """

    SOURCE_NAME = "jobspy"

    def fetch_jobs(
        self,
        query: str = "",
        location: str = "Remote",
        is_remote: bool = True,
        limit: int = 25,
        site_names: Optional[List[str]] = None,
        country: str = "usa",
    ) -> List[JobPosting]:
        """Scrape live positions across multi-board engines using python-jobspy."""
        silence_jobspy_loggers()
        postings: List[JobPosting] = []

        try:
            from jobspy import scrape_jobs
            search_kw = query.strip() if query and query.strip() else "Professional"
            loc_str = location.strip() if location and location.strip() and "remote" not in location.lower() else "Remote"
            target_sites = site_names or ["indeed", "zip_recruiter"]

            df = scrape_jobs(
                site_name=target_sites,
                search_term=search_kw,
                location=loc_str,
                is_remote=is_remote,
                results_wanted=min(limit, 25),
                country_indeed=country,
            )

            if df is not None and not df.empty:
                for idx, row in df.iterrows():
                    if len(postings) >= limit:
                        break
                    row_dict = row.to_dict()
                    title = str(row_dict.get("title") or "").strip()
                    if not title or title.lower() == "nan":
                        continue

                    company = str(row_dict.get("company") or "Verified Employer").strip()
                    site_name = str(row_dict.get("site") or "Indeed").title()
                    job_url = str(row_dict.get("job_url") or row_dict.get("job_url_direct") or "https://indeed.com")
                    loc = str(row_dict.get("location") or "Remote, US")
                    desc = str(row_dict.get("description") or "")
                    clean_desc = clean_html_text(desc)

                    min_amt = row_dict.get("min_amount")
                    max_amt = row_dict.get("max_amount")
                    salary_str = None
                    if min_amt and str(min_amt) != "nan" and max_amt and str(max_amt) != "nan":
                        salary_str = f"${int(float(min_amt)):,} - ${int(float(max_amt)):,}"
                    elif min_amt and str(min_amt) != "nan":
                        salary_str = f"From ${int(float(min_amt)):,}"

                    work_type = WorkType.REMOTE if is_remote or "remote" in loc.lower() else self.normalize_work_type(loc)
                    posted_date = self.parse_posted_date(row_dict.get("date_posted"))
                    item_id = f"{site_name.lower()}_{idx}_{abs(hash(job_url)) % 10000000}"

                    posting = JobPosting(
                        job_id=self.generate_job_id(item_id),
                        title=title,
                        company_name=company,
                        location=loc,
                        work_type=work_type,
                        url=job_url,
                        description_text=clean_desc or f"{title} at {company}. Sourced via JobSpy from {site_name}.",
                        posted_date=posted_date,
                        source=f"JobSpy ({site_name})",
                        metadata={
                            "site": site_name,
                            "salary": salary_str,
                            "min_amount": min_amt,
                            "max_amount": max_amt,
                        },
                    )
                    postings.append(posting)

        except Exception as exc:
            logger.warning(f"[JobSpy] Scraper encountered error: {exc}")

        return postings


# ============================================================================
# 3. APIFY CLOUD ACTOR SCRAPER (Anti-Bot Scaffolding for Wellfound & Glassdoor)
# ============================================================================

class ApifyScraper(BaseScraper):
    """
    Cloud Actor Ingestion via Apify Client.
    Protects against aggressive Cloudflare & IP bans for high-friction targets:
    - LinkedIn: apify/linkedin-jobs-scraper
    - Wellfound / AngelList: anchor/wellfound-angel-jobs-scraper
    - Glassdoor: canadesk/glassdoor-jobs-scraper
    - Multi-ATS Aggregator: apify/multi-ats-scraper
    """

    SOURCE_NAME = "apify"

    ACTOR_REGISTRY: Dict[str, str] = {
        "linkedin": "apify/linkedin-jobs-scraper",
        "wellfound": "anchor/wellfound-angel-jobs-scraper",
        "glassdoor": "canadesk/glassdoor-jobs-scraper",
        "multi_ats": "apify/multi-ats-scraper",
    }

    def __init__(
        self,
        api_token: Optional[str] = None,
        timeout: float = 30.0,
        max_retries: int = 2,
    ):
        super().__init__(timeout=timeout, max_retries=max_retries)
        self.api_token = api_token or os.environ.get("APIFY_API_TOKEN") or os.environ.get("APIFY_TOKEN")

    def fetch_jobs(
        self,
        query: str = "",
        location: str = "Remote",
        limit: int = 15,
        target_platform: str = "linkedin",
        custom_actor_id: Optional[str] = None,
    ) -> List[JobPosting]:
        """Execute specified Apify Cloud Actor and normalize output dataset."""
        if not self.api_token or not self.api_token.strip():
            logger.debug("[Apify] No API token available. Skipping cloud actor run.")
            return []

        actor_id = custom_actor_id or self.ACTOR_REGISTRY.get(target_platform.lower(), "apify/linkedin-jobs-scraper")
        postings: List[JobPosting] = []

        try:
            from apify_client import ApifyClient
            client = ApifyClient(self.api_token.strip())

            # Configure actor input payload according to target platform
            run_input: Dict[str, Any] = {
                "title": query or "Software Engineer",
                "location": location or "Remote",
                "rows": min(limit, 25),
                "maxItems": min(limit, 25),
            }
            if target_platform == "wellfound":
                run_input = {
                    "search": query or "Software Engineer",
                    "location": location or "Remote",
                    "limit": min(limit, 20),
                }

            logger.info(f"[Apify] Triggering cloud actor '{actor_id}' for query='{query}', location='{location}'...")
            actor_call = client.actor(actor_id).call(
                run_input=run_input,
                timeout_secs=int(self.timeout),
                memory_mbytes=1024,
            )

            if actor_call and "defaultDatasetId" in actor_call:
                dataset = client.dataset(actor_call["defaultDatasetId"])
                for idx, item in enumerate(dataset.iterate_items()):
                    if len(postings) >= limit:
                        break

                    title = item.get("title") or item.get("jobTitle") or item.get("position")
                    company = item.get("companyName") or item.get("company") or "Verified Employer"
                    if not title:
                        continue

                    job_url = item.get("jobUrl") or item.get("url") or item.get("applyUrl") or "https://apify.com"
                    loc = item.get("location") or location or "Remote"
                    clean_desc = clean_html_text(item.get("description") or item.get("snippet") or "")
                    work_type = WorkType.REMOTE if "remote" in loc.lower() else self.normalize_work_type(loc)
                    posted_date = self.parse_posted_date(item.get("postedDate") or item.get("postedAt"))

                    posting = JobPosting(
                        job_id=self.generate_job_id(f"{target_platform}_{idx}_{abs(hash(job_url)) % 1000000}"),
                        title=title,
                        company_name=company,
                        location=loc,
                        work_type=work_type,
                        url=job_url,
                        description_text=clean_desc or f"{title} at {company}. Harvested via Apify Cloud Actor ({actor_id}).",
                        posted_date=posted_date,
                        source=f"Apify ({target_platform.capitalize()})",
                        metadata={
                            "actor_id": actor_id,
                            "dataset_id": actor_call["defaultDatasetId"],
                            "target_platform": target_platform,
                        },
                    )
                    postings.append(posting)

        except Exception as exc:
            logger.warning(f"[Apify] Cloud actor '{actor_id}' run failed: {exc}")

        return postings

    def scrape_wellfound(self, query: str = "", location: str = "Remote", limit: int = 15) -> List[JobPosting]:
        """Cloud bot mitigation: trigger Apify Wellfound actor instead of local DOM scraping."""
        return self.fetch_jobs(query=query, location=location, limit=limit, target_platform="wellfound")

    def scrape_glassdoor(self, query: str = "", location: str = "Remote", limit: int = 15) -> List[JobPosting]:
        """Cloud bot mitigation: trigger Apify Glassdoor actor instead of local DOM scraping."""
        return self.fetch_jobs(query=query, location=location, limit=limit, target_platform="glassdoor")


# ============================================================================
# 4. JSEARCH / RAPIDAPI (GOOGLE JOBS AGGREGATOR)
# ============================================================================

class JSearchScraper(BaseScraper):
    """
    Direct Aggregator Ingestion via JSearch / RapidAPI (Google Jobs aggregator).
    Endpoint: https://jsearch.p.rapidapi.com/search
    """

    SOURCE_NAME = "jsearch"

    def __init__(
        self,
        rapidapi_key: Optional[str] = None,
        timeout: float = 12.0,
        max_retries: int = 3,
    ):
        super().__init__(timeout=timeout, max_retries=max_retries)
        self.rapidapi_key = rapidapi_key or os.environ.get("RAPIDAPI_KEY") or os.environ.get("JSEARCH_API_KEY")

    def fetch_jobs(
        self,
        query: str = "",
        location: str = "Remote",
        limit: int = 20,
    ) -> List[JobPosting]:
        """Query JSearch RapidAPI for Google Jobs aggregated postings."""
        if not self.rapidapi_key or not self.rapidapi_key.strip():
            logger.debug("[JSearch] No RapidAPI key provided. Skipping JSearch query.")
            return []

        url = "https://jsearch.p.rapidapi.com/search"
        search_query = f"{query or 'Software Engineer'} in {location or 'Remote'}".strip()
        params = {
            "query": search_query,
            "page": "1",
            "num_pages": "1",
        }
        headers = {
            "x-rapidapi-host": "jsearch.p.rapidapi.com",
            "x-rapidapi-key": self.rapidapi_key.strip(),
            "Accept": "application/json",
        }

        data = self.fetch_json(url, params=params, headers=headers)
        if not data or not isinstance(data, dict):
            return []

        raw_items = data.get("data", [])
        postings: List[JobPosting] = []

        for item in raw_items:
            if len(postings) >= limit:
                break
            if not isinstance(item, dict):
                continue

            title = (item.get("job_title") or "").strip()
            if not title:
                continue

            company = item.get("employer_name") or "Global Employer"
            job_url = item.get("job_apply_link") or item.get("job_google_link") or "https://google.com"
            clean_desc = clean_html_text(item.get("job_description") or "")

            city = item.get("job_city") or ""
            country = item.get("job_country") or ""
            loc = f"{city}, {country}".strip(", ") or location or "Remote"
            is_remote = bool(item.get("job_is_remote", False)) or "remote" in loc.lower()
            work_type = WorkType.REMOTE if is_remote else self.normalize_work_type(loc)

            min_sal = item.get("job_min_salary")
            max_sal = item.get("job_max_salary")
            salary_str = None
            if min_sal and max_sal:
                salary_str = f"${int(min_sal):,} - ${int(max_sal):,}"

            job_id_raw = item.get("job_id") or str(len(postings))
            posted_date = self.parse_posted_date(item.get("job_posted_at_datetime_utc"))

            posting = JobPosting(
                job_id=self.generate_job_id(job_id_raw),
                title=title,
                company_name=company,
                location=loc,
                work_type=work_type,
                url=job_url,
                description_text=clean_desc or f"{title} at {company}. Aggregated via JSearch Google Jobs.",
                posted_date=posted_date,
                source=self.SOURCE_NAME,
                metadata={
                    "salary": salary_str,
                    "publisher": item.get("job_publisher"),
                    "employment_type": item.get("job_employment_type"),
                },
            )
            postings.append(posting)

        return postings


# ============================================================================
# 5. JOOBLE JOB SEARCH API
# ============================================================================

class JoobleScraper(BaseScraper):
    """
    Direct Aggregator Ingestion via Jooble REST API.
    Endpoint: https://jooble.org/api/{api_key}
    """

    SOURCE_NAME = "jooble"

    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout: float = 12.0,
        max_retries: int = 3,
    ):
        super().__init__(timeout=timeout, max_retries=max_retries)
        self.api_key = api_key or os.environ.get("JOOBLE_API_KEY")

    def fetch_jobs(
        self,
        query: str = "",
        location: str = "Remote",
        limit: int = 20,
    ) -> List[JobPosting]:
        """Query Jooble API for aggregated job requisitions."""
        if not self.api_key or not self.api_key.strip():
            logger.debug("[Jooble] No Jooble API key provided. Skipping Jooble query.")
            return []

        url = f"https://jooble.org/api/{self.api_key.strip()}"
        payload = {
            "keywords": query or "Software Engineer",
            "location": location or "Remote",
            "page": 1,
        }
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        try:
            resp = self.post(url, json_body=payload, headers=headers)
            if resp.status_code != 200:
                logger.debug(f"[Jooble] API returned status {resp.status_code}")
                return []
            data = resp.json()
        except Exception as exc:
            logger.debug(f"[Jooble] Request failed: {exc}")
            return []

        raw_items = data.get("jobs", [])
        postings: List[JobPosting] = []

        for item in raw_items:
            if len(postings) >= limit:
                break
            if not isinstance(item, dict):
                continue

            title = clean_html_text(item.get("title") or "")
            if not title:
                continue

            company = item.get("company") or "Verified Employer"
            job_url = item.get("link") or "https://jooble.org"
            loc = item.get("location") or location or "Remote"
            clean_desc = clean_html_text(item.get("snippet") or "")
            work_type = WorkType.REMOTE if "remote" in loc.lower() else self.normalize_work_type(loc)
            posted_date = self.parse_posted_date(item.get("updated"))
            item_id = str(item.get("id") or len(postings))

            posting = JobPosting(
                job_id=self.generate_job_id(item_id),
                title=title,
                company_name=company,
                location=loc,
                work_type=work_type,
                url=job_url,
                description_text=clean_desc or f"{title} at {company}. Sourced via Jooble.",
                posted_date=posted_date,
                source=self.SOURCE_NAME,
                metadata={
                    "salary": item.get("salary"),
                    "jooble_id": item_id,
                },
            )
            postings.append(posting)

        return postings


# ============================================================================
# 6. BACKWARD-COMPATIBLE FUNCTIONAL INTERFACES
# ============================================================================

def fetch_jobspy_jobs(
    target_query: str = "",
    target_location: str = "",
    is_remote: bool = True,
    limit: int = 25,
) -> List[Dict[str, Any]]:
    """Legacy functional runner for JobSpy Multi-Board Engine."""
    with JobSpyScraper() as scraper:
        jobs = scraper.fetch_jobs(
            query=target_query,
            location=target_location,
            is_remote=is_remote,
            limit=limit,
        )
        return [j.to_dict() for j in jobs]


def fetch_apify_jobs(
    target_query: str = "",
    target_location: str = "",
    api_token: Optional[str] = None,
    limit: int = 15,
) -> List[Dict[str, Any]]:
    """Legacy functional runner for Apify Cloud Actors."""
    with ApifyScraper(api_token=api_token) as scraper:
        jobs = scraper.fetch_jobs(
            query=target_query,
            location=target_location,
            limit=limit,
            target_platform="linkedin",
        )
        return [j.to_dict() for j in jobs]


def fetch_jsearch_jobs(
    target_query: str = "",
    target_location: str = "Remote",
    api_key: Optional[str] = None,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """Functional runner for JSearch / RapidAPI Google Jobs."""
    with JSearchScraper(rapidapi_key=api_key) as scraper:
        jobs = scraper.fetch_jobs(query=target_query, location=target_location, limit=limit)
        return [j.to_dict() for j in jobs]


def fetch_jooble_jobs(
    target_query: str = "",
    target_location: str = "Remote",
    api_key: Optional[str] = None,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """Functional runner for Jooble Job Search API."""
    with JoobleScraper(api_key=api_key) as scraper:
        jobs = scraper.fetch_jobs(query=target_query, location=target_location, limit=limit)
        return [j.to_dict() for j in jobs]


def fetch_wellfound_apify_jobs(
    target_query: str = "",
    target_location: str = "Remote",
    api_token: Optional[str] = None,
    limit: int = 15,
) -> List[Dict[str, Any]]:
    """Cloud bot mitigation functional runner for Wellfound / AngelList via Apify Actor."""
    with ApifyScraper(api_token=api_token) as scraper:
        jobs = scraper.scrape_wellfound(query=target_query, location=target_location, limit=limit)
        return [j.to_dict() for j in jobs]


def fetch_glassdoor_apify_jobs(
    target_query: str = "",
    target_location: str = "Remote",
    api_token: Optional[str] = None,
    limit: int = 15,
) -> List[Dict[str, Any]]:
    """Cloud bot mitigation functional runner for Glassdoor via Apify Actor."""
    with ApifyScraper(api_token=api_token) as scraper:
        jobs = scraper.scrape_glassdoor(query=target_query, location=target_location, limit=limit)
        return [j.to_dict() for j in jobs]
