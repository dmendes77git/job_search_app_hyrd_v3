"""
Tier 1: Direct Applicant Tracking System (ATS) Scrapers.
Integrates Greenhouse, Lever, Ashby, Workday, BambooHR, BreezyHR, and SmartRecruiters.

Adheres strictly to the Tier 1 Direct ATS Ingestion Hierarchy:
- Subclasses BaseScraper ABC with polymorphic fetch_jobs() -> List[JobPosting].
- Pure dynamic company parameterization (accepts company_slug or tenant_id dynamically).
- Implements Workday CSRF session handshake and CXS API.
- Resilient connection pooling, rotating User-Agents, and Tenacity retries.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import logging
import re
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from src.agents.scrapers.base import (
    BaseScraper,
    JobPosting,
    WorkType,
    clean_html_text,
    generate_job_id,
    get_browser_headers,
    normalize_company_slug,
)

logger = logging.getLogger("Hyrd.Scrapers.Tier1ATS")


def _fetch_companies_concurrently(
    scraper: BaseScraper,
    merged_items: List[Tuple[str, str, bool]],
    query: str,
    location: str,
    limit: int,
    per_company_limit: int = 20,
    max_workers: int = 8,
) -> List[JobPosting]:
    """Execute multi-company scraper requests concurrently while strictly preserving company priority order."""
    if not merged_items:
        return []

    def _fetch_one(item: Tuple[str, str, bool]) -> List[JobPosting]:
        return scraper.safe_fetch_jobs(
            company_slug=item[0],
            query=query,
            location=location,
            limit=per_company_limit,
            company_display_name=item[1],
            is_custom_target=item[2],
        )

    pool_workers = min(max_workers, len(merged_items))
    if pool_workers <= 1:
        batch_results = [_fetch_one(item) for item in merged_items]
    else:
        with ThreadPoolExecutor(max_workers=pool_workers) as executor:
            batch_results = list(executor.map(_fetch_one, merged_items))

    results: List[JobPosting] = []
    for jobs in batch_results:
        for job in jobs:
            if len(results) < limit:
                results.append(job)
            else:
                break
        if len(results) >= limit:
            break

    return results


def _fetch_workday_tenants_concurrently(
    scraper: BaseScraper,
    merged_items: List[Tuple[str, str, str, str]],
    query: str,
    location: str,
    limit: int,
    per_tenant_limit: int = 15,
    max_workers: int = 6,
) -> List[JobPosting]:
    """Execute Workday multi-tenant requests concurrently preserving priority order."""
    if not merged_items:
        return []

    def _fetch_one(item: Tuple[str, str, str, str]) -> List[JobPosting]:
        return scraper.safe_fetch_jobs(
            company_slug=item[0],
            tenant_host=item[1],
            career_site=item[2],
            query=query,
            location=location,
            limit=per_tenant_limit,
            company_display_name=item[3],
        )

    pool_workers = min(max_workers, len(merged_items))
    if pool_workers <= 1:
        batch_results = [_fetch_one(item) for item in merged_items]
    else:
        with ThreadPoolExecutor(max_workers=pool_workers) as executor:
            batch_results = list(executor.map(_fetch_one, merged_items))

    results: List[JobPosting] = []
    for jobs in batch_results:
        for job in jobs:
            if len(results) < limit:
                results.append(job)
            else:
                break
        if len(results) >= limit:
            break

    return results


# ============================================================================
# 1. GREENHOUSE ATS SCRAPER
# ============================================================================

class GreenhouseScraper(BaseScraper):
    """
    Direct ATS Ingestion for companies on Greenhouse (boards-api.greenhouse.io).
    Accepts company_slug dynamically (e.g. 'stripe', 'airbnb', 'databricks', 'gitlab').
    """

    SOURCE_NAME = "greenhouse"

    DEFAULT_COMPANIES: List[Tuple[str, str]] = [
        ("stripe", "Stripe"),
        ("airbnb", "Airbnb"),
        ("databricks", "Databricks"),
        ("gitlab", "GitLab"),
        ("pinterest", "Pinterest"),
        ("canonical", "Canonical"),
        ("elastic", "Elastic"),
        ("dropbox", "Dropbox"),
    ]

    def fetch_jobs(
        self,
        company_slug: str,
        query: str = "",
        location: str = "",
        limit: int = 40,
        company_display_name: Optional[str] = None,
        is_custom_target: bool = False,
    ) -> List[JobPosting]:
        """Fetch and normalize job postings for a specific Greenhouse employer."""
        slug = normalize_company_slug(company_slug)
        if not slug:
            return []

        comp_name = company_display_name or slug.replace("-", " ").capitalize()
        url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=false"
        data = self.fetch_json(url)
        if not data or not isinstance(data, dict):
            return []

        raw_items = data.get("jobs", [])
        query_tokens = [t.lower() for t in re.split(r"[\s/,-]+", query) if len(t) > 2]
        postings: List[JobPosting] = []

        for item in raw_items:
            if len(postings) >= limit:
                break

            title = item.get("title", "").strip()
            if not title:
                continue

            title_lower = title.lower()
            if not is_custom_target and query_tokens and not any(t in title_lower for t in query_tokens):
                if len(postings) > 15:
                    continue

            loc_dict = item.get("location") or {}
            loc_name = loc_dict.get("name") or "Remote / Global"
            job_url = item.get("absolute_url") or f"https://boards.greenhouse.io/{slug}"
            item_id = str(item.get("id") or len(postings))
            work_type = self.normalize_work_type(loc_name)
            posted_dt = self.parse_posted_date(item.get("updated_at"))

            dept_names = [d.get("name") for d in item.get("departments", []) if d.get("name")]
            dept_str = ", ".join(dept_names) or "General"

            posting = JobPosting(
                job_id=self.generate_job_id(f"{slug}_{item_id}"),
                title=title,
                company_name=comp_name,
                location=loc_name,
                work_type=work_type,
                url=job_url,
                description_text=f"{title} at {comp_name} ({dept_str}). Verified position on Greenhouse ATS.",
                posted_date=posted_dt,
                source=self.SOURCE_NAME,
                metadata={
                    "departments": dept_names,
                    "offices": [o.get("name") for o in item.get("offices", []) if o.get("name")],
                    "company_slug": slug,
                    "is_target_company": is_custom_target,
                },
                is_direct_ats=True,
                is_target_company=is_custom_target,
            )
            postings.append(posting)

        return postings

    def fetch_for_companies(
        self,
        companies: Optional[Sequence[Union[str, Tuple[str, str]]]] = None,
        query: str = "",
        location: str = "",
        limit: int = 40,
    ) -> List[JobPosting]:
        """Query multiple target employers and aggregate up to limit."""
        target_list: List[Tuple[str, str, bool]] = []
        if companies:
            for item in companies:
                if isinstance(item, tuple):
                    slug = normalize_company_slug(item[0])
                    target_list.append((slug, item[1], True))
                elif isinstance(item, str) and item.strip():
                    slug = normalize_company_slug(item)
                    target_list.append((slug, item.strip(), True))

        custom_slugs = {t[0] for t in target_list}
        merged = target_list + [(s, n, False) for s, n in self.DEFAULT_COMPANIES if s not in custom_slugs]
        return _fetch_companies_concurrently(self, merged, query, location, limit, per_company_limit=20)


# ============================================================================
# 2. LEVER ATS SCRAPER
# ============================================================================

class LeverScraper(BaseScraper):
    """
    Direct ATS Ingestion for companies on Lever (api.lever.co/v0/postings/{slug}).
    Accepts company_slug dynamically (e.g. 'spotify', 'netflix', 'atlassian', 'shopify').
    """

    SOURCE_NAME = "lever"

    DEFAULT_COMPANIES: List[Tuple[str, str]] = [
        ("spotify", "Spotify"),
        ("netflix", "Netflix"),
        ("eventbrite", "Eventbrite"),
        ("atlassian", "Atlassian"),
        ("shopify", "Shopify"),
        ("carta", "Carta"),
    ]

    def fetch_jobs(
        self,
        company_slug: str,
        query: str = "",
        location: str = "",
        limit: int = 40,
        company_display_name: Optional[str] = None,
        is_custom_target: bool = False,
    ) -> List[JobPosting]:
        """Fetch and normalize job postings for a specific Lever employer."""
        slug = normalize_company_slug(company_slug)
        if not slug:
            return []

        comp_name = company_display_name or slug.replace("-", " ").capitalize()
        url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
        data = self.fetch_json(url)
        if not data or not isinstance(data, list):
            return []

        query_tokens = [t.lower() for t in re.split(r"[\s/,-]+", query) if len(t) > 2]
        postings: List[JobPosting] = []

        for item in data:
            if len(postings) >= limit:
                break

            title = item.get("text", "").strip()
            if not title:
                continue

            title_lower = title.lower()
            if not is_custom_target and query_tokens and not any(t in title_lower for t in query_tokens):
                if len(postings) > 15:
                    continue

            cats = item.get("categories") or {}
            loc = cats.get("location") or "Remote / Distributed"
            commitment = cats.get("commitment") or "Full-time"
            workplace_type = str(item.get("workplaceType") or "").lower()

            if workplace_type == "remote" or "remote" in loc.lower():
                work_type = WorkType.REMOTE
            elif workplace_type == "hybrid" or "hybrid" in loc.lower():
                work_type = WorkType.HYBRID
            elif workplace_type in ("onsite", "on-site"):
                work_type = WorkType.ONSITE
            else:
                work_type = self.normalize_work_type(loc)

            job_url = item.get("hostedUrl") or item.get("applyUrl") or f"https://jobs.lever.co/{slug}"
            item_id = str(item.get("id") or len(postings))
            desc_plain = clean_html_text(item.get("descriptionPlain") or item.get("description") or "")
            if not desc_plain:
                desc_plain = f"{title} at {comp_name} ({commitment}). Official listing hosted on Lever ATS."

            posted_dt = self.parse_posted_date(item.get("createdAt"))

            posting = JobPosting(
                job_id=self.generate_job_id(f"{slug}_{item_id}"),
                title=title,
                company_name=comp_name,
                location=loc,
                work_type=work_type,
                url=job_url,
                description_text=desc_plain,
                posted_date=posted_dt,
                source=self.SOURCE_NAME,
                metadata={
                    "commitment": commitment,
                    "team": cats.get("team"),
                    "department": cats.get("department"),
                    "company_slug": slug,
                    "is_target_company": is_custom_target,
                },
                is_direct_ats=True,
                is_target_company=is_custom_target,
            )
            postings.append(posting)

        return postings

    def fetch_for_companies(
        self,
        companies: Optional[Sequence[Union[str, Tuple[str, str]]]] = None,
        query: str = "",
        location: str = "",
        limit: int = 40,
    ) -> List[JobPosting]:
        """Query multiple target employers on Lever and aggregate up to limit."""
        target_list: List[Tuple[str, str, bool]] = []
        if companies:
            for item in companies:
                if isinstance(item, tuple):
                    slug = normalize_company_slug(item[0])
                    target_list.append((slug, item[1], True))
                elif isinstance(item, str) and item.strip():
                    slug = normalize_company_slug(item)
                    target_list.append((slug, item.strip(), True))

        custom_slugs = {t[0] for t in target_list}
        merged = target_list + [(s, n, False) for s, n in self.DEFAULT_COMPANIES if s not in custom_slugs]
        return _fetch_companies_concurrently(self, merged, query, location, limit, per_company_limit=20)


# ============================================================================
# 3. ASHBY ATS SCRAPER
# ============================================================================

class AshbyScraper(BaseScraper):
    """
    Direct ATS Ingestion for modern startups on Ashby (api.ashbyhq.com/posting-api/job-board/{slug}).
    Accepts company_slug dynamically (e.g. 'linear', 'retool', 'ramp', 'perplexity').
    """

    SOURCE_NAME = "ashby"

    DEFAULT_COMPANIES: List[Tuple[str, str]] = [
        ("linear", "Linear"),
        ("retool", "Retool"),
        ("ramp", "Ramp"),
        ("perplexity", "Perplexity AI"),
        ("synthesia", "Synthesia"),
        ("sentry", "Sentry"),
        ("elevenlabs", "ElevenLabs"),
        ("vanta", "Vanta"),
    ]

    def fetch_jobs(
        self,
        company_slug: str,
        query: str = "",
        location: str = "",
        limit: int = 40,
        company_display_name: Optional[str] = None,
        is_custom_target: bool = False,
    ) -> List[JobPosting]:
        """Fetch and normalize job postings for a specific Ashby employer."""
        slug = normalize_company_slug(company_slug)
        if not slug:
            return []

        comp_name = company_display_name or slug.replace("-", " ").capitalize()
        url = f"https://api.ashbyhq.com/posting-api/job-board/{slug}"
        data = self.fetch_json(url)
        if not data or not isinstance(data, dict):
            return []

        raw_items = data.get("jobs", [])
        query_tokens = [t.lower() for t in re.split(r"[\s/,-]+", query) if len(t) > 2]
        postings: List[JobPosting] = []

        for item in raw_items:
            if len(postings) >= limit:
                break

            title = item.get("title", "").strip()
            if not title:
                continue

            title_lower = title.lower()
            if not is_custom_target and query_tokens and not any(t in title_lower for t in query_tokens):
                if len(postings) > 15:
                    continue

            loc = item.get("location") or "Remote"
            is_remote = bool(item.get("isRemote", False)) or "remote" in loc.lower()
            work_type = WorkType.REMOTE if is_remote else self.normalize_work_type(loc)
            job_url = item.get("jobUrl") or f"https://jobs.ashbyhq.com/{slug}"
            item_id = str(item.get("id") or len(postings))
            dept = item.get("department", "Engineering")
            posted_dt = self.parse_posted_date(item.get("publishedAt"))

            compensation = item.get("compensation") or {}
            salary_str = None
            if compensation:
                min_val = compensation.get("compensationTierSummary") or compensation.get("scrapeSummary")
                if min_val:
                    salary_str = str(min_val)

            posting = JobPosting(
                job_id=self.generate_job_id(f"{slug}_{item_id}"),
                title=title,
                company_name=comp_name,
                location=loc,
                work_type=work_type,
                url=job_url,
                description_text=f"{title} at {comp_name}. Department: {dept}. Location: {loc}. Verified opening on Ashby ATS.",
                posted_date=posted_dt,
                source=self.SOURCE_NAME,
                metadata={
                    "department": dept,
                    "employmentType": item.get("employmentType"),
                    "compensation": compensation,
                    "salary": salary_str,
                    "company_slug": slug,
                    "is_target_company": is_custom_target,
                },
                is_direct_ats=True,
                is_target_company=is_custom_target,
            )
            postings.append(posting)

        return postings

    def fetch_for_companies(
        self,
        companies: Optional[Sequence[Union[str, Tuple[str, str]]]] = None,
        query: str = "",
        location: str = "",
        limit: int = 40,
    ) -> List[JobPosting]:
        """Query multiple target employers on Ashby and aggregate up to limit."""
        target_list: List[Tuple[str, str, bool]] = []
        if companies:
            for item in companies:
                if isinstance(item, tuple):
                    slug = normalize_company_slug(item[0])
                    target_list.append((slug, item[1], True))
                elif isinstance(item, str) and item.strip():
                    slug = normalize_company_slug(item)
                    target_list.append((slug, item.strip(), True))

        custom_slugs = {t[0] for t in target_list}
        merged = target_list + [(s, n, False) for s, n in self.DEFAULT_COMPANIES if s not in custom_slugs]
        return _fetch_companies_concurrently(self, merged, query, location, limit, per_company_limit=20)


# ============================================================================
# 4. WORKDAY ATS SCRAPER (Enterprise CSRF / CXS API)
# ============================================================================

class WorkdayScraper(BaseScraper):
    """
    Direct Enterprise Ingestion for Workday Career Sites (CXS API).
    Handles Workday's two-step handshake:
    1. GET to career site establishes session cookies and CALYPSO_CSRF_TOKEN.
    2. POST to /wday/cxs/{slug}/{career_site}/jobs with JSON payload and CSRF header.
    """

    SOURCE_NAME = "workday"

    DEFAULT_TENANTS: List[Tuple[str, str, str, str]] = [
        # (company_slug, tenant_host, career_site, display_name)
        ("adobe", "adobe.wd5.myworkdayjobs.com", "external_experienced", "Adobe"),
        ("nvidia", "nvidia.wd5.myworkdayjobs.com", "NVIDIAExternalCareerSite", "NVIDIA"),
    ]

    def fetch_jobs(
        self,
        company_slug: str,
        tenant_host: Optional[str] = None,
        career_site: str = "external_experienced",
        query: str = "",
        location: str = "",
        limit: int = 25,
        company_display_name: Optional[str] = None,
    ) -> List[JobPosting]:
        """Execute Workday CSRF handshake and query CXS /jobs endpoint."""
        slug = normalize_company_slug(company_slug)
        if not slug:
            return []

        host = tenant_host or f"{slug}.wd5.myworkdayjobs.com"
        comp_name = company_display_name or slug.replace("-", " ").capitalize()

        # Step 1: Handshake GET to acquire session cookies and CSRF token
        init_url = f"https://{host}/{career_site}"
        try:
            init_resp = self.get(init_url, timeout=8.0)
            if init_resp.status_code not in (200, 301, 302):
                logger.debug(f"[Workday] Initial GET failed for {init_url}: HTTP {init_resp.status_code}")
                return []
        except Exception as exc:
            logger.debug(f"[Workday] Handshake exception for {init_url}: {exc}")
            return []

        # Extract CSRF token from cookies or response headers
        csrf_token = (
            self.client.cookies.get("CALYPSO_CSRF_TOKEN")
            or self.client.cookies.get("wday-csrf")
            or init_resp.headers.get("calypso-csrf-token")
            or ""
        )

        # Step 2: POST to Workday CXS JSON endpoint
        cxs_url = f"https://{host}/wday/cxs/{slug}/{career_site}/jobs"
        post_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if csrf_token:
            post_headers["calypso-csrf-token"] = csrf_token

        payload = {
            "appliedFacets": {},
            "limit": min(limit, 50),
            "offset": 0,
            "searchText": query or "",
        }

        try:
            resp = self.post(cxs_url, json_body=payload, headers=post_headers, timeout=10.0)
            if resp.status_code != 200:
                logger.debug(f"[Workday] CXS POST failed for {cxs_url}: HTTP {resp.status_code}")
                return []
            data = resp.json()
        except Exception as exc:
            logger.debug(f"[Workday] CXS POST error for {cxs_url}: {exc}")
            return []

        postings: List[JobPosting] = []
        raw_jobs = data.get("jobPostings", [])

        for item in raw_jobs:
            if len(postings) >= limit:
                break

            title = item.get("title", "").strip()
            if not title:
                continue

            ext_path = item.get("externalPath", "")
            job_url = f"https://{host}{ext_path}" if ext_path else init_url

            loc_text = item.get("locationsText") or "Corporate Headquarters"
            work_type = self.normalize_work_type(loc_text)
            bullets = item.get("bulletFields", [])
            req_id = bullets[0] if bullets else str(len(postings))

            posting = JobPosting(
                job_id=self.generate_job_id(f"{slug}_{req_id}"),
                title=title,
                company_name=comp_name,
                location=loc_text,
                work_type=work_type,
                url=job_url,
                description_text=f"{title} at {comp_name}. Requisition ID: {req_id}. Location: {loc_text}. Official Workday posting.",
                posted_date=None,  # Workday returns relative strings like 'Posted 2 Days Ago'
                source=self.SOURCE_NAME,
                metadata={
                    "requisition_id": req_id,
                    "posted_on_text": item.get("postedOn"),
                    "bulletFields": bullets,
                    "host": host,
                    "career_site": career_site,
                },
                is_direct_ats=True,
            )
            postings.append(posting)

        return postings

    def fetch_for_companies(
        self,
        companies: Optional[List[Union[str, Tuple[str, str]]]] = None,
        query: str = "",
        location: str = "",
        limit: int = 25,
    ) -> List[JobPosting]:
        """Fetch across multiple Workday tenants or custom company slugs."""
        target_list: List[Tuple[str, str, str, str]] = []
        if companies:
            for item in companies:
                if isinstance(item, tuple):
                    slug = normalize_company_slug(item[0])
                    target_list.append((slug, f"{slug}.wd5.myworkdayjobs.com", "external_experienced", item[1]))
                elif isinstance(item, str) and item.strip():
                    slug = normalize_company_slug(item)
                    target_list.append((slug, f"{slug}.wd5.myworkdayjobs.com", "external_experienced", item.strip()))

        custom_slugs = {t[0] for t in target_list}
        merged = target_list + [t for t in self.DEFAULT_TENANTS if t[0] not in custom_slugs]
        return _fetch_workday_tenants_concurrently(self, merged, query, location, limit, per_tenant_limit=15)


# ============================================================================
# 5. BAMBOOHR ATS SCRAPER
# ============================================================================

class BambooHRScraper(BaseScraper):
    """
    Direct ATS Ingestion for companies using BambooHR (https://{slug}.bamboohr.com/careers/list).
    Accepts company_slug dynamically (e.g. 'zapier', 'change', 'invision').
    """

    SOURCE_NAME = "bamboohr"

    DEFAULT_COMPANIES: List[Tuple[str, str]] = [
        ("zapier", "Zapier"),
        ("invision", "InVision"),
        ("thoughtbot", "Thoughtbot"),
    ]

    def fetch_jobs(
        self,
        company_slug: str,
        query: str = "",
        location: str = "",
        limit: int = 25,
        company_display_name: Optional[str] = None,
    ) -> List[JobPosting]:
        """Fetch and normalize job postings from BambooHR careers endpoint."""
        slug = normalize_company_slug(company_slug)
        if not slug:
            return []

        comp_name = company_display_name or slug.replace("-", " ").capitalize()
        url = f"https://{slug}.bamboohr.com/careers/list"
        data = self.fetch_json(url)
        if not data or not isinstance(data, dict):
            return []

        raw_items = data.get("result", [])
        query_tokens = [t.lower() for t in re.split(r"[\s/,-]+", query) if len(t) > 2]
        postings: List[JobPosting] = []

        for item in raw_items:
            if len(postings) >= limit:
                break

            title = item.get("jobOpeningName") or item.get("name") or ""
            title = title.strip()
            if not title:
                continue

            if query_tokens and not any(t in title.lower() for t in query_tokens):
                if len(postings) > 10:
                    continue

            loc_dict = item.get("location") or {}
            city = loc_dict.get("city", "")
            state = loc_dict.get("state", "")
            loc = f"{city}, {state}".strip(", ") or "Remote"

            is_remote = bool(item.get("isRemote", False)) or "remote" in loc.lower()
            work_type = WorkType.REMOTE if is_remote else self.normalize_work_type(loc)

            item_id = str(item.get("id") or len(postings))
            job_url = f"https://{slug}.bamboohr.com/careers/{item_id}"
            dept = item.get("department", "Engineering")

            posting = JobPosting(
                job_id=self.generate_job_id(f"{slug}_{item_id}"),
                title=title,
                company_name=comp_name,
                location=loc,
                work_type=work_type,
                url=job_url,
                description_text=f"{title} at {comp_name}. Department: {dept}. Location: {loc}. Listed on BambooHR ATS.",
                source=self.SOURCE_NAME,
                metadata={
                    "department": dept,
                    "jobType": item.get("jobType"),
                    "company_slug": slug,
                },
                is_direct_ats=True,
            )
            postings.append(posting)

        return postings

    def fetch_for_companies(
        self,
        companies: Optional[List[Union[str, Tuple[str, str]]]] = None,
        query: str = "",
        location: str = "",
        limit: int = 25,
    ) -> List[JobPosting]:
        """Fetch across multiple BambooHR company portals."""
        target_list: List[Tuple[str, str, bool]] = []
        if companies:
            for item in companies:
                if isinstance(item, tuple):
                    slug = normalize_company_slug(item[0])
                    target_list.append((slug, item[1], True))
                elif isinstance(item, str) and item.strip():
                    slug = normalize_company_slug(item)
                    target_list.append((slug, item.strip(), True))

        custom_slugs = {t[0] for t in target_list}
        merged = target_list + [(s, n, False) for s, n in self.DEFAULT_COMPANIES if s not in custom_slugs]
        return _fetch_companies_concurrently(self, merged, query, location, limit, per_company_limit=15)


# ============================================================================
# 6. BREEZYHR ATS SCRAPER
# ============================================================================

class BreezyHRScraper(BaseScraper):
    """
    Direct ATS Ingestion for companies using BreezyHR (https://{slug}.breezy.hr/json).
    Accepts company_slug dynamically (e.g. 'duolingo', 'charitywater').
    """

    SOURCE_NAME = "breezyhr"

    DEFAULT_COMPANIES: List[Tuple[str, str]] = [
        ("duolingo", "Duolingo"),
    ]

    def fetch_jobs(
        self,
        company_slug: str,
        query: str = "",
        location: str = "",
        limit: int = 25,
        company_display_name: Optional[str] = None,
    ) -> List[JobPosting]:
        """Fetch and normalize job postings from BreezyHR JSON endpoint."""
        slug = normalize_company_slug(company_slug)
        if not slug:
            return []

        comp_name = company_display_name or slug.replace("-", " ").capitalize()
        url = f"https://{slug}.breezy.hr/json"
        data = self.fetch_json(url)
        if not data or not isinstance(data, list):
            return []

        query_tokens = [t.lower() for t in re.split(r"[\s/,-]+", query) if len(t) > 2]
        postings: List[JobPosting] = []

        for item in data:
            if len(postings) >= limit:
                break

            title = item.get("name", "").strip()
            if not title:
                continue

            if query_tokens and not any(t in title.lower() for t in query_tokens):
                if len(postings) > 10:
                    continue

            loc_dict = item.get("location") or {}
            loc_name = loc_dict.get("name") or "Remote"
            is_remote = bool(loc_dict.get("is_remote", False)) or "remote" in loc_name.lower()
            work_type = WorkType.REMOTE if is_remote else self.normalize_work_type(loc_name)

            item_id = str(item.get("id") or len(postings))
            job_url = item.get("url") or f"https://{slug}.breezy.hr/p/{item_id}"
            dept = item.get("department", "General")
            posted_dt = self.parse_posted_date(item.get("published_date"))

            salary_info = item.get("salary")
            salary_str = str(salary_info) if salary_info else None

            posting = JobPosting(
                job_id=self.generate_job_id(f"{slug}_{item_id}"),
                title=title,
                company_name=comp_name,
                location=loc_name,
                work_type=work_type,
                url=job_url,
                description_text=f"{title} at {comp_name}. Department: {dept}. Location: {loc_name}. Verified BreezyHR posting.",
                posted_date=posted_dt,
                source=self.SOURCE_NAME,
                metadata={
                    "department": dept,
                    "type": item.get("type"),
                    "salary": salary_str,
                    "company_slug": slug,
                },
                is_direct_ats=True,
            )
            postings.append(posting)

        return postings

    def fetch_for_companies(
        self,
        companies: Optional[List[Union[str, Tuple[str, str]]]] = None,
        query: str = "",
        location: str = "",
        limit: int = 25,
    ) -> List[JobPosting]:
        """Fetch across multiple BreezyHR company portals."""
        target_list: List[Tuple[str, str, bool]] = []
        if companies:
            for item in companies:
                if isinstance(item, tuple):
                    slug = normalize_company_slug(item[0])
                    target_list.append((slug, item[1], True))
                elif isinstance(item, str) and item.strip():
                    slug = normalize_company_slug(item)
                    target_list.append((slug, item.strip(), True))

        custom_slugs = {t[0] for t in target_list}
        merged = target_list + [(s, n, False) for s, n in self.DEFAULT_COMPANIES if s not in custom_slugs]
        return _fetch_companies_concurrently(self, merged, query, location, limit, per_company_limit=15)


# ============================================================================
# 7. SMARTRECRUITERS ATS SCRAPER
# ============================================================================

class SmartRecruitersScraper(BaseScraper):
    """
    Direct ATS Ingestion for companies using SmartRecruiters (api.smartrecruiters.com).
    Accepts company_slug dynamically (e.g. 'cern', 'informa', 'colt', 'epicgames').
    """

    SOURCE_NAME = "smartrecruiters"

    DEFAULT_COMPANIES: List[Tuple[str, str]] = [
        ("cern", "CERN"),
        ("informa", "Informa"),
        ("colt", "Colt Technology"),
        ("epicgames", "Epic Games"),
        ("blizzard", "Blizzard Entertainment"),
    ]

    def fetch_jobs(
        self,
        company_slug: str,
        query: str = "",
        location: str = "",
        limit: int = 25,
        company_display_name: Optional[str] = None,
        is_custom_target: bool = False,
    ) -> List[JobPosting]:
        """Fetch and normalize job postings from SmartRecruiters postings endpoint."""
        slug = normalize_company_slug(company_slug)
        if not slug:
            return []

        comp_name = company_display_name or slug.replace("-", " ").capitalize()
        url = f"https://api.smartrecruiters.com/v1/companies/{slug}/postings?limit={min(limit, 50)}"
        data = self.fetch_json(url)
        if not data or not isinstance(data, dict):
            return []

        raw_items = data.get("content", [])
        query_tokens = [t.lower() for t in re.split(r"[\s/,-]+", query) if len(t) > 2]
        postings: List[JobPosting] = []

        for item in raw_items:
            if len(postings) >= limit:
                break

            title = item.get("name", "").strip()
            if not title:
                continue

            title_lower = title.lower()
            if not is_custom_target and query_tokens and not any(t in title_lower for t in query_tokens):
                if len(postings) > 10:
                    continue

            loc_dict = item.get("location") or {}
            city = loc_dict.get("city", "")
            country = loc_dict.get("country", "")
            loc = f"{city}, {country}".strip(", ") or "Global"

            is_remote = bool(loc_dict.get("remote", False)) or "remote" in loc.lower()
            work_type = WorkType.REMOTE if is_remote else self.normalize_work_type(loc)

            item_id = str(item.get("id") or len(postings))
            job_url = f"https://jobs.smartrecruiters.com/{slug}/{item_id}"
            posted_dt = self.parse_posted_date(item.get("releasedDate"))
            dept = item.get("department", {}).get("label") if isinstance(item.get("department"), dict) else item.get("department")

            posting = JobPosting(
                job_id=self.generate_job_id(f"{slug}_{item_id}"),
                title=title,
                company_name=comp_name,
                location=loc,
                work_type=work_type,
                url=job_url,
                description_text=f"{title} at {comp_name}. Location: {loc}. Listed on SmartRecruiters enterprise talent portal.",
                posted_date=posted_dt,
                source=self.SOURCE_NAME,
                metadata={
                    "department": dept,
                    "company_slug": slug,
                    "is_target_company": is_custom_target,
                },
                is_direct_ats=True,
                is_target_company=is_custom_target,
            )
            postings.append(posting)

        return postings

    def fetch_for_companies(
        self,
        companies: Optional[Sequence[Union[str, Tuple[str, str]]]] = None,
        query: str = "",
        location: str = "",
        limit: int = 25,
    ) -> List[JobPosting]:
        """Query multiple target employers on SmartRecruiters and aggregate up to limit."""
        target_list: List[Tuple[str, str, bool]] = []
        if companies:
            for item in companies:
                if isinstance(item, tuple):
                    slug = normalize_company_slug(item[0])
                    target_list.append((slug, item[1], True))
                elif isinstance(item, str) and item.strip():
                    slug = normalize_company_slug(item)
                    target_list.append((slug, item.strip(), True))

        custom_slugs = {t[0] for t in target_list}
        merged = target_list + [(s, n, False) for s, n in self.DEFAULT_COMPANIES if s not in custom_slugs]
        return _fetch_companies_concurrently(self, merged, query, location, limit, per_company_limit=15)


# ============================================================================
# 8. BACKWARD-COMPATIBLE FUNCTIONAL INTERFACES
# ============================================================================

def fetch_ashby_jobs(
    target_query: str = "",
    target_location: str = "",
    custom_companies: Optional[List[str]] = None,
    limit: int = 40,
) -> List[Dict[str, Any]]:
    """Legacy functional runner for Ashby ATS (returns dictionaries)."""
    with AshbyScraper() as scraper:
        postings = scraper.fetch_for_companies(
            companies=custom_companies,
            query=target_query,
            location=target_location,
            limit=limit,
        )
        return [p.to_dict() for p in postings]


def fetch_greenhouse_jobs(
    target_query: str = "",
    target_location: str = "",
    custom_companies: Optional[List[str]] = None,
    limit: int = 40,
) -> List[Dict[str, Any]]:
    """Legacy functional runner for Greenhouse ATS (returns dictionaries)."""
    with GreenhouseScraper() as scraper:
        postings = scraper.fetch_for_companies(
            companies=custom_companies,
            query=target_query,
            location=target_location,
            limit=limit,
        )
        return [p.to_dict() for p in postings]


def fetch_lever_jobs(
    target_query: str = "",
    target_location: str = "",
    custom_companies: Optional[List[str]] = None,
    limit: int = 35,
) -> List[Dict[str, Any]]:
    """Legacy functional runner for Lever ATS (returns dictionaries)."""
    with LeverScraper() as scraper:
        postings = scraper.fetch_for_companies(
            companies=custom_companies,
            query=target_query,
            location=target_location,
            limit=limit,
        )
        return [p.to_dict() for p in postings]


def fetch_smartrecruiters_jobs(
    target_query: str = "",
    target_location: str = "",
    custom_companies: Optional[List[str]] = None,
    limit: int = 25,
) -> List[Dict[str, Any]]:
    """Legacy functional runner for SmartRecruiters ATS (returns dictionaries)."""
    with SmartRecruitersScraper() as scraper:
        postings = scraper.fetch_for_companies(
            companies=custom_companies,
            query=target_query,
            location=target_location,
            limit=limit,
        )
        return [p.to_dict() for p in postings]


def fetch_workday_jobs(
    target_query: str = "",
    target_location: str = "",
    company_slug: str = "adobe",
    tenant_host: Optional[str] = None,
    career_site: str = "external_experienced",
    custom_companies: Optional[List[str]] = None,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """Functional runner for Workday CXS ATS."""
    with WorkdayScraper() as scraper:
        if custom_companies:
            postings = scraper.fetch_for_companies(
                companies=custom_companies,
                query=target_query,
                location=target_location,
                limit=limit,
            )
        else:
            postings = scraper.fetch_jobs(
                company_slug=company_slug,
                tenant_host=tenant_host,
                career_site=career_site,
                query=target_query,
                location=target_location,
                limit=limit,
            )
        return [p.to_dict() for p in postings]


def fetch_bamboohr_jobs(
    company_slug: str = "zapier",
    target_query: str = "",
    target_location: str = "",
    custom_companies: Optional[List[str]] = None,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """Functional runner for BambooHR ATS."""
    with BambooHRScraper() as scraper:
        if custom_companies:
            postings = scraper.fetch_for_companies(
                companies=custom_companies,
                query=target_query,
                location=target_location,
                limit=limit,
            )
        else:
            postings = scraper.fetch_jobs(
                company_slug=company_slug,
                query=target_query,
                location=target_location,
                limit=limit,
            )
        return [p.to_dict() for p in postings]


def fetch_breezyhr_jobs(
    company_slug: str = "duolingo",
    target_query: str = "",
    target_location: str = "",
    custom_companies: Optional[List[str]] = None,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """Functional runner for BreezyHR ATS."""
    with BreezyHRScraper() as scraper:
        if custom_companies:
            postings = scraper.fetch_for_companies(
                companies=custom_companies,
                query=target_query,
                location=target_location,
                limit=limit,
            )
        else:
            postings = scraper.fetch_jobs(
                company_slug=company_slug,
                query=target_query,
                location=target_location,
                limit=limit,
            )
        return [p.to_dict() for p in postings]
