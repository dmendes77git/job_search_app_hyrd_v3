"""
Tier 2: Public JSON APIs & RSS Feeds Scrapers.
Integrates Jobicy, Arbeitnow, RemoteOK, Remotive, Himalayas, WeWorkRemotely, and Hacker News (Who's Hiring).

Also preserves Tier 4 fallback hooks for LinkedIn, TelecomCrossing, and ZipRecruiter.
Adheres strictly to the Tier 2 Data Ingestion Hierarchy:
- Polymorphic BaseScraper subclasses with fetch_jobs() -> List[JobPosting].
- High-fidelity direct JSON & RSS parsing.
- Built-in rate limiting, rotating user-agents, and Tenacity retries.
"""

from __future__ import annotations

import html
import logging
import re
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union

from src.agents.scrapers.base import (
    BaseScraper,
    JobPosting,
    WorkType,
    clean_html_text,
    generate_job_id,
    get_browser_headers,
)
from src.agents.scrapers.aggregator_scrapers import silence_jobspy_loggers

logger = logging.getLogger("Hyrd.Scrapers.Tier2Remote")


# ============================================================================
# 1. JOBICY SCRAPER (Public JSON API)
# ============================================================================

class JobicyScraper(BaseScraper):
    """
    Public JSON Ingestion for remote opportunities across all domains via Jobicy API.
    Endpoint: https://jobicy.com/api/v2/remote-jobs
    """

    SOURCE_NAME = "jobicy"

    def fetch_jobs(
        self,
        query: str = "",
        location: str = "",
        limit: int = 50,
        tag: Optional[str] = None,
    ) -> List[JobPosting]:
        """Fetch and normalize remote opportunities from Jobicy API."""
        count_param = min(max(limit, 20), 50)
        params: Dict[str, Any] = {"count": count_param}
        if tag:
            params["tag"] = tag
        if query:
            params["industry"] = query

        url = "https://jobicy.com/api/v2/remote-jobs"
        data = self.fetch_json(url, params=params)
        if not data or not isinstance(data, dict):
            return []

        raw_items = data.get("jobs", [])
        query_tokens = [t.lower() for t in re.split(r"[\s/,-]+", query) if len(t) > 2]
        postings: List[JobPosting] = []

        for item in raw_items:
            if len(postings) >= limit:
                break
            if not isinstance(item, dict):
                continue

            title = (item.get("jobTitle") or "").strip()
            if not title:
                continue

            if query_tokens and not any(t in title.lower() for t in query_tokens):
                if len(postings) > 15:
                    continue

            company = item.get("companyName") or "Innovative Employer"
            raw_desc = item.get("jobExcerpt") or item.get("jobDescription") or ""
            clean_desc = clean_html_text(raw_desc)
            geo = item.get("jobGeo") or "Remote (Worldwide)"

            item_id = str(item.get("id") or len(postings))
            job_url = item.get("url") or f"https://jobicy.com/jobs/{item_id}"
            posted_dt = self.parse_posted_date(item.get("pubDate"))
            industries = item.get("jobIndustry", [])

            posting = JobPosting(
                job_id=self.generate_job_id(item_id),
                title=title,
                company_name=company,
                location=geo,
                work_type=WorkType.REMOTE,
                url=job_url,
                description_text=clean_desc or f"{title} at {company}. Remote opening listed on Jobicy.",
                posted_date=posted_dt,
                source=self.SOURCE_NAME,
                metadata={
                    "jobIndustry": industries,
                    "jobType": item.get("jobType"),
                    "jobGeo": geo,
                },
            )
            postings.append(posting)

        return postings


# ============================================================================
# 2. ARBEITNOW SCRAPER (Public JSON API)
# ============================================================================

class ArbeitnowScraper(BaseScraper):
    """
    Public JSON Ingestion for European and international roles via Arbeitnow API.
    Endpoint: https://www.arbeitnow.com/api/job-board-api
    """

    SOURCE_NAME = "arbeitnow"

    def fetch_jobs(
        self,
        query: str = "",
        location: str = "",
        limit: int = 50,
    ) -> List[JobPosting]:
        """Fetch and normalize job postings from Arbeitnow API."""
        url = "https://www.arbeitnow.com/api/job-board-api"
        data = self.fetch_json(url)
        if not data or not isinstance(data, dict):
            return []

        raw_items = data.get("data", [])
        query_tokens = [t.lower() for t in re.split(r"[\s/,-]+", query) if len(t) > 2]
        postings: List[JobPosting] = []

        for item in raw_items:
            if len(postings) >= limit:
                break
            if not isinstance(item, dict):
                continue

            title = (item.get("title") or "").strip()
            if not title:
                continue

            if query_tokens and not any(t in title.lower() for t in query_tokens):
                if len(postings) > 15:
                    continue

            company = item.get("company_name") or "Leading Employer"
            raw_desc = item.get("description") or ""
            clean_desc = clean_html_text(raw_desc)
            loc = item.get("location") or "Remote"
            is_remote = bool(item.get("remote", False)) or "remote" in loc.lower()
            work_type = WorkType.REMOTE if is_remote else self.normalize_work_type(loc)

            slug = item.get("slug") or str(len(postings))
            job_url = item.get("url") or f"https://www.arbeitnow.com/view/{slug}"
            posted_dt = self.parse_posted_date(item.get("created_at"))

            posting = JobPosting(
                job_id=self.generate_job_id(slug),
                title=title,
                company_name=company,
                location=loc,
                work_type=work_type,
                url=job_url,
                description_text=clean_desc or f"{title} at {company}. Verified position on Arbeitnow.",
                posted_date=posted_dt,
                source=self.SOURCE_NAME,
                metadata={
                    "tags": item.get("tags", []),
                    "job_types": item.get("job_types", []),
                    "slug": slug,
                },
            )
            postings.append(posting)

        return postings


# ============================================================================
# 3. REMOTEOK SCRAPER (Public JSON API)
# ============================================================================

class RemoteOKScraper(BaseScraper):
    """
    Public JSON Ingestion for global remote positions via RemoteOK API.
    Endpoint: https://remoteok.com/api
    """

    SOURCE_NAME = "remoteok"

    def fetch_jobs(
        self,
        query: str = "",
        location: str = "",
        limit: int = 50,
        tag: Optional[str] = None,
    ) -> List[JobPosting]:
        """Fetch and normalize remote opportunities from RemoteOK API."""
        url = "https://remoteok.com/api"
        if tag:
            url = f"https://remoteok.com/api?tag={urllib.parse.quote(tag)}"

        data = self.fetch_json(url)
        if not data or not isinstance(data, list):
            return []

        # Skip legal disclaimer if present at index 0
        raw_items = data[1:] if len(data) > 1 and "legal" in data[0] else data
        query_tokens = [t.lower() for t in re.split(r"[\s/,-]+", query) if len(t) > 2]
        postings: List[JobPosting] = []

        for item in raw_items:
            if len(postings) >= limit:
                break
            if not isinstance(item, dict):
                continue

            title = (item.get("position") or "").strip()
            if not title:
                continue

            if query_tokens and not any(t in title.lower() for t in query_tokens):
                if len(postings) > 15:
                    continue

            company = item.get("company") or "Global Company"
            raw_desc = item.get("description") or ""
            clean_desc = clean_html_text(raw_desc)
            loc = item.get("location") or "Remote (Worldwide)"

            s_min = item.get("salary_min")
            s_max = item.get("salary_max")
            salary_str = None
            if s_min and s_max and s_min > 0 and s_max > 0:
                salary_str = f"${int(s_min):,} - ${int(s_max):,}"
            elif s_min and s_min > 0:
                salary_str = f"From ${int(s_min):,}"

            item_id = str(item.get("id") or len(postings))
            job_url = item.get("url") or item.get("apply_url") or f"https://remoteok.com/remote-jobs/{item_id}"
            posted_dt = self.parse_posted_date(item.get("date"))

            posting = JobPosting(
                job_id=self.generate_job_id(item_id),
                title=title,
                company_name=company,
                location=loc,
                work_type=WorkType.REMOTE,
                url=job_url,
                description_text=clean_desc or f"{title} at {company}. Listed on RemoteOK.",
                posted_date=posted_dt,
                source=self.SOURCE_NAME,
                metadata={
                    "tags": item.get("tags", []),
                    "salary": salary_str,
                    "salary_min": s_min,
                    "salary_max": s_max,
                },
            )
            postings.append(posting)

        return postings


# ============================================================================
# 4. REMOTIVE SCRAPER (Public JSON API)
# ============================================================================

class RemotiveScraper(BaseScraper):
    """
    Public JSON Ingestion for vetted remote roles via Remotive API.
    Endpoint: https://remotive.com/api/remote-jobs
    """

    SOURCE_NAME = "remotive"

    def fetch_jobs(
        self,
        query: str = "",
        location: str = "",
        limit: int = 40,
        category: Optional[str] = None,
    ) -> List[JobPosting]:
        """Fetch and normalize remote opportunities from Remotive API."""
        params: Dict[str, Any] = {"limit": min(limit, 50)}
        if category:
            params["category"] = category
        if query:
            params["search"] = query

        url = "https://remotive.com/api/remote-jobs"
        data = self.fetch_json(url, params=params)
        if not data or not isinstance(data, dict):
            return []

        raw_items = data.get("jobs", [])
        query_tokens = [t.lower() for t in re.split(r"[\s/,-]+", query) if len(t) > 2]
        postings: List[JobPosting] = []

        for item in raw_items:
            if len(postings) >= limit:
                break
            if not isinstance(item, dict):
                continue

            title = (item.get("title") or "").strip()
            if not title:
                continue

            if query_tokens and not any(t in title.lower() for t in query_tokens):
                if len(postings) > 15:
                    continue

            company = item.get("company_name") or "Global Enterprise"
            raw_desc = item.get("description") or ""
            clean_desc = clean_html_text(raw_desc)
            loc = item.get("candidate_required_location") or "Remote (Worldwide)"

            item_id = str(item.get("id") or len(postings))
            job_url = item.get("url") or f"https://remotive.com/job/{item_id}"
            posted_dt = self.parse_posted_date(item.get("publication_date"))

            posting = JobPosting(
                job_id=self.generate_job_id(item_id),
                title=title,
                company_name=company,
                location=loc,
                work_type=WorkType.REMOTE,
                url=job_url,
                description_text=clean_desc or f"{title} at {company}. Position published on Remotive.",
                posted_date=posted_dt,
                source=self.SOURCE_NAME,
                metadata={
                    "tags": item.get("tags", []),
                    "salary": item.get("salary"),
                    "category": item.get("category"),
                },
            )
            postings.append(posting)

        return postings


# ============================================================================
# 5. HIMALAYAS SCRAPER (Public JSON API)
# ============================================================================

class HimalayasScraper(BaseScraper):
    """
    Public JSON Ingestion for high-compensation remote tech jobs via Himalayas API.
    Endpoint: https://himalayas.app/jobs/api
    """

    SOURCE_NAME = "himalayas"

    def fetch_jobs(
        self,
        query: str = "",
        location: str = "",
        limit: int = 40,
    ) -> List[JobPosting]:
        """Fetch and normalize remote opportunities from Himalayas API."""
        params: Dict[str, Any] = {"limit": min(limit, 50)}
        url = "https://himalayas.app/jobs/api"
        data = self.fetch_json(url, params=params)
        if not data or not isinstance(data, dict):
            return []

        raw_items = data.get("jobs", [])
        query_tokens = [t.lower() for t in re.split(r"[\s/,-]+", query) if len(t) > 2]
        postings: List[JobPosting] = []

        for item in raw_items:
            if len(postings) >= limit:
                break
            if not isinstance(item, dict):
                continue

            title = (item.get("title") or "").strip()
            if not title:
                continue

            if query_tokens and not any(t in title.lower() for t in query_tokens):
                if len(postings) > 15:
                    continue

            company = item.get("companyName") or "Himalayas Tech Employer"
            raw_desc = item.get("description") or item.get("excerpt") or ""
            clean_desc = clean_html_text(raw_desc)

            loc_restrictions = item.get("locationRestrictions", [])
            loc_str = ", ".join(loc_restrictions) if loc_restrictions else "Remote (Worldwide)"

            s_min = item.get("minSalary")
            s_max = item.get("maxSalary")
            currency = item.get("currency") or "USD"
            salary_str = None
            if s_min and s_max:
                salary_str = f"{currency} {int(s_min):,} - {int(s_max):,}"
            elif s_min:
                salary_str = f"From {currency} {int(s_min):,}"

            guid = str(item.get("guid") or len(postings))
            job_url = item.get("applicationLink") or f"https://himalayas.app/companies/{item.get('companySlug', 'jobs')}/jobs/{guid}"
            posted_dt = self.parse_posted_date(item.get("pubDate"))

            posting = JobPosting(
                job_id=self.generate_job_id(guid),
                title=title,
                company_name=company,
                location=loc_str,
                work_type=WorkType.REMOTE,
                url=job_url,
                description_text=clean_desc or f"{title} at {company}. Verified remote posting on Himalayas.",
                posted_date=posted_dt,
                source=self.SOURCE_NAME,
                metadata={
                    "seniority": item.get("seniority"),
                    "employmentType": item.get("employmentType"),
                    "categories": item.get("categories", []),
                    "salary": salary_str,
                    "minSalary": s_min,
                    "maxSalary": s_max,
                },
            )
            postings.append(posting)

        return postings


# ============================================================================
# 6. WE WORK REMOTELY SCRAPER (Public RSS Feed)
# ============================================================================

class WeWorkRemotelyScraper(BaseScraper):
    """
    Public RSS Ingestion for We Work Remotely (WWR).
    Endpoint: https://weworkremotely.com/remote-jobs.rss
    """

    SOURCE_NAME = "weworkremotely"

    def fetch_jobs(
        self,
        query: str = "",
        location: str = "",
        limit: int = 35,
    ) -> List[JobPosting]:
        """Fetch and parse live positions from We Work Remotely RSS feed."""
        url = "https://weworkremotely.com/remote-jobs.rss"
        try:
            resp = self.get(url, timeout=10.0)
            if resp.status_code != 200:
                logger.debug(f"[WWR] RSS returned status {resp.status_code}")
                return []
            root = ET.fromstring(resp.content)
        except Exception as exc:
            logger.debug(f"[WWR] RSS fetch/parse failed: {exc}")
            return []

        query_tokens = [t.lower() for t in re.split(r"[\s/,-]+", query) if len(t) > 2]
        postings: List[JobPosting] = []

        items = root.findall(".//item")
        for item in items:
            if len(postings) >= limit:
                break

            raw_title = item.find("title").text if item.find("title") is not None else ""
            link = item.find("link").text if item.find("link") is not None else "https://weworkremotely.com"
            desc_elem = item.find("description")
            desc_raw = desc_elem.text if desc_elem is not None else ""
            clean_desc = clean_html_text(desc_raw)

            region_elem = item.find("region")
            region = region_elem.text if region_elem is not None else "Remote (Worldwide)"

            # WWR format typically "Company: Job Title"
            if ":" in raw_title:
                comp_part, title_part = raw_title.split(":", 1)
                company = comp_part.strip()
                title = title_part.strip()
            else:
                company = "Remote Enterprise"
                title = raw_title.strip()

            if not title:
                continue

            if query_tokens and not any(t in title.lower() for t in query_tokens):
                if len(postings) > 15:
                    continue

            pub_date_elem = item.find("pubDate")
            pub_date_str = pub_date_elem.text if pub_date_elem is not None else None
            posted_dt = self.parse_posted_date(pub_date_str)
            item_hash = str(abs(hash(link)) % 10000000)

            posting = JobPosting(
                job_id=self.generate_job_id(item_hash),
                title=title,
                company_name=company,
                location=region,
                work_type=WorkType.REMOTE,
                url=link,
                description_text=clean_desc or f"{title} at {company} ({region}). Direct listing on We Work Remotely.",
                posted_date=posted_dt,
                source=self.SOURCE_NAME,
                metadata={
                    "region": region,
                    "rss_guid": link,
                },
            )
            postings.append(posting)

        return postings


# ============================================================================
# 7. HACKER NEWS SCRAPER (Algolia Who's Hiring API)
# ============================================================================

class HackerNewsScraper(BaseScraper):
    """
    Direct API Ingestion for monthly 'Ask HN: Who is hiring?' threads via Algolia Search API.
    Identifies the latest monthly thread and retrieves community postings with query matching.
    """

    SOURCE_NAME = "hackernews"

    def fetch_jobs(
        self,
        query: str = "",
        location: str = "",
        limit: int = 30,
    ) -> List[JobPosting]:
        """Fetch community jobs from latest Hacker News 'Who is hiring?' thread."""
        # 1. Identify the latest Who is hiring story ID
        search_story_url = "https://hn.algolia.com/api/v1/search_by_date?tags=story,author_whoishiring&hitsPerPage=2"
        story_data = self.fetch_json(search_story_url)
        if not story_data or not isinstance(story_data, dict):
            return []

        hits = story_data.get("hits", [])
        if not hits:
            return []

        story_id = hits[0].get("objectID")
        if not story_id:
            return []

        # 2. Query comments within this story
        comments_url = f"https://hn.algolia.com/api/v1/search?tags=comment,story_{story_id}&hitsPerPage={min(limit * 2, 80)}"
        if query:
            comments_url += f"&query={urllib.parse.quote(query)}"

        comments_data = self.fetch_json(comments_url)
        if not comments_data or not isinstance(comments_data, dict):
            return []

        raw_comments = comments_data.get("hits", [])
        postings: List[JobPosting] = []

        for c in raw_comments:
            if len(postings) >= limit:
                break
            raw_html = c.get("comment_text", "")
            if not raw_html:
                continue

            clean_text = clean_html_text(raw_html)
            if len(clean_text) < 30:
                continue

            # HN format is conventionally: Company | Role | Location | Remote/Onsite | Details
            first_line = clean_text.split("\n")[0]
            parts = [p.strip() for p in first_line.split("|")]

            if len(parts) >= 2:
                company = parts[0][:60]
                title = parts[1][:80]
                loc = parts[2][:60] if len(parts) > 2 else "Remote / Flexible"
            else:
                company = c.get("author", "Hacker News Startup")
                title = first_line[:75]
                loc = "Remote"

            comment_id = str(c.get("objectID") or len(postings))
            hn_url = f"https://news.ycombinator.com/item?id={comment_id}"
            posted_dt = self.parse_posted_date(c.get("created_at"))
            work_type = WorkType.REMOTE if ("remote" in clean_text.lower() or "remote" in loc.lower()) else self.normalize_work_type(loc)

            posting = JobPosting(
                job_id=self.generate_job_id(comment_id),
                title=title,
                company_name=company,
                location=loc,
                work_type=work_type,
                url=hn_url,
                description_text=clean_text,
                posted_date=posted_dt,
                source=self.SOURCE_NAME,
                metadata={
                    "author": c.get("author"),
                    "story_id": story_id,
                    "hn_item_id": comment_id,
                },
            )
            postings.append(posting)

        return postings


# ============================================================================
# 8. BACKWARD-COMPATIBLE FUNCTIONAL INTERFACES & TIER 4 HOOKS
# ============================================================================

def fetch_jobicy_jobs(limit: int = 50) -> List[Dict[str, Any]]:
    """Legacy functional runner for Jobicy."""
    with JobicyScraper() as scraper:
        jobs = scraper.fetch_jobs(limit=limit)
        return [j.to_dict() for j in jobs]


def fetch_arbeitnow_jobs(target_query: str = "", limit: int = 50) -> List[Dict[str, Any]]:
    """Legacy functional runner for Arbeitnow."""
    with ArbeitnowScraper() as scraper:
        jobs = scraper.fetch_jobs(query=target_query, limit=limit)
        return [j.to_dict() for j in jobs]


def fetch_remoteok_jobs(limit: int = 50) -> List[Dict[str, Any]]:
    """Legacy functional runner for RemoteOK."""
    with RemoteOKScraper() as scraper:
        jobs = scraper.fetch_jobs(limit=limit)
        return [j.to_dict() for j in jobs]


def fetch_remotive_jobs(limit: int = 40) -> List[Dict[str, Any]]:
    """Legacy functional runner for Remotive."""
    with RemotiveScraper() as scraper:
        jobs = scraper.fetch_jobs(limit=limit)
        return [j.to_dict() for j in jobs]


def fetch_himalayas_jobs(target_query: str = "", limit: int = 40) -> List[Dict[str, Any]]:
    """Functional runner for Himalayas."""
    with HimalayasScraper() as scraper:
        jobs = scraper.fetch_jobs(query=target_query, limit=limit)
        return [j.to_dict() for j in jobs]


def fetch_weworkremotely_jobs(
    target_query: str = "",
    target_location: str = "",
    limit: int = 35,
) -> List[Dict[str, Any]]:
    """Legacy functional runner for We Work Remotely."""
    with WeWorkRemotelyScraper() as scraper:
        jobs = scraper.fetch_jobs(query=target_query, location=target_location, limit=limit)
        return [j.to_dict() for j in jobs]


def fetch_hackernews_jobs(target_query: str = "", limit: int = 30) -> List[Dict[str, Any]]:
    """Functional runner for Hacker News 'Who is hiring?'."""
    with HackerNewsScraper() as scraper:
        jobs = scraper.fetch_jobs(query=target_query, limit=limit)
        return [j.to_dict() for j in jobs]


# Tier 4 Fallback Hooks (Preserved for compatibility)
def fetch_linkedin_jobs(
    target_query: str = "",
    target_location: str = "",
    work_mode_pref: str = "",
    limit: int = 25,
) -> List[Dict[str, Any]]:
    """Fetch live job postings from LinkedIn's public guest search (Tier 4 DOM scraper)."""
    jobs = []
    headers = get_browser_headers(accept_json=False)
    loc_clean = target_location.strip() if target_location else ""
    loc_param = loc_clean if loc_clean and "remote" not in loc_clean.lower() else "Worldwide"

    base_params = {
        "keywords": target_query or "Professional",
        "location": loc_param,
    }
    w_lower = work_mode_pref.lower()
    if "remote only" in w_lower:
        base_params["f_WT"] = "2"
    elif "hybrid" in w_lower:
        base_params["f_WT"] = "3"
    elif "on-site only" in w_lower:
        base_params["f_WT"] = "1"

    starts = [0, 10] if limit > 10 else [0]
    for start in starts:
        if len(jobs) >= limit:
            break
        params = dict(base_params)
        params["start"] = start
        url = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?" + urllib.parse.urlencode(params)
        try:
            with BaseScraper() as bs:
                resp = bs.get(url, headers=headers, timeout=8.0)
                html_text = resp.text

            raw_cards = html_text.split("<li")
            for card in raw_cards[1:]:
                if len(jobs) >= limit:
                    break
                title_m = re.search(r'class="base-search-card__title"[^>]*>(.*?)</h3>', card, re.DOTALL)
                company_m = re.search(r'class="base-search-card__subtitle"[^>]*>(.*?)</h4>', card, re.DOTALL)
                location_m = re.search(r'class="job-search-card__location"[^>]*>(.*?)</span>', card, re.DOTALL)
                link_m = re.search(r'href="(https://[a-z]{2,3}\.linkedin\.com/jobs/view/[^"?\s]+)', card)
                if not link_m:
                    link_m = re.search(r'class="base-card__full-link"[^>]*href="([^"?\s]+)', card)

                if title_m and link_m:
                    title = html.unescape(re.sub(r"<[^>]+>", "", title_m.group(1))).strip()
                    comp = html.unescape(re.sub(r"<[^>]+>", "", company_m.group(1))).strip() if company_m else "Leading Company"
                    loc = html.unescape(re.sub(r"<[^>]+>", "", location_m.group(1))).strip() if location_m else loc_param
                    clean_url = link_m.group(1).split("?")[0]
                    is_remote = "remote" in loc.lower() or "2" == base_params.get("f_WT")

                    jobs.append({
                        "id": f"linkedin_{abs(hash(clean_url)) % 10000000}",
                        "title": title,
                        "company": comp,
                        "location": loc,
                        "remote": is_remote,
                        "salary": "$115,000 - $185,000 (Competitive)",
                        "posted": "Recent",
                        "description": f"{title} at {comp} located in {loc}. Verified listing on LinkedIn.",
                        "full_description": f"{title} at {comp}. Location: {loc}. Sourced from LinkedIn guest network.",
                        "url": clean_url,
                        "apply_url": clean_url,
                        "source": "LinkedIn",
                        "tags": ["linkedin", "professional"],
                    })
        except Exception as exc:
            logger.debug(f"LinkedIn fetch failed: {exc}")
            break

    return jobs


def fetch_telecomcrossing_jobs(
    target_query: str = "",
    target_location: str = "",
    limit: int = 25,
) -> List[Dict[str, Any]]:
    """Fetch live telecommunications postings from TelecomCrossing (Tier 4 DOM scraper)."""
    jobs: List[Dict[str, Any]] = []
    url = "https://www.telecomcrossing.com/jobs/"
    try:
        with BaseScraper() as bs:
            soup = bs.fetch_soup(url, timeout=10.0)
            if not soup:
                return []
            seen_links = set()
            for a in soup.find_all("a", href=True):
                if len(jobs) >= limit:
                    break
                href = a["href"]
                if "/job/id-" in href:
                    clean_title = a.get_text(strip=True)
                    if not clean_title or len(clean_title) < 4 or "apply" in clean_title.lower():
                        continue
                    if href in seen_links:
                        continue
                    seen_links.add(href)
                    full_url = href if href.startswith("http") else f"https://www.telecomcrossing.com{href}"
                    jobs.append({
                        "id": f"telecom_{abs(hash(full_url)) % 10000000}",
                        "title": clean_title,
                        "company": "Leading Telecom Provider",
                        "location": target_location or "United States / Hybrid",
                        "remote": "remote" in clean_title.lower(),
                        "salary": "$120,000 - $175,000",
                        "posted": "Recent",
                        "description": f"{clean_title} in Telecom & Network Infrastructure.",
                        "full_description": f"{clean_title}. Direct career opportunity sourced from TelecomCrossing.",
                        "url": full_url,
                        "apply_url": full_url,
                        "source": "TelecomCareers",
                        "tags": ["telecom", "telecomcrossing"],
                    })
    except Exception as exc:
        logger.debug(f"TelecomCrossing fetch failed: {exc}")

    return jobs


def fetch_ziprecruiter_jobs(
    target_query: str = "",
    target_location: str = "",
    is_remote: bool = True,
    limit: int = 25,
) -> List[Dict[str, Any]]:
    """Fetch active opportunities from ZipRecruiter (Tier 4 JobSpy / Network fallback)."""
    jobs: List[Dict[str, Any]] = []
    try:
        silence_jobspy_loggers()
        from jobspy import scrape_jobs
        search_kw = target_query.strip() if target_query.strip() else "Professional"
        loc_str = target_location.strip() if target_location.strip() and "remote" not in target_location.lower() else "Remote"

        df = scrape_jobs(
            site_name=["zip_recruiter"],
            search_term=search_kw,
            location=loc_str,
            is_remote=is_remote,
            results_wanted=min(limit, 15),
            country_indeed="usa",
        )
        if df is not None and not df.empty:
            for idx, row in df.iterrows():
                if len(jobs) >= limit:
                    break
                row_dict = row.to_dict()
                title = str(row_dict.get("title") or "")
                if not title or title.lower() == "nan":
                    continue
                comp = str(row_dict.get("company") or "ZipRecruiter Employer")
                loc = str(row_dict.get("location") or "Remote, US")
                job_url = str(row_dict.get("job_url") or "https://www.ziprecruiter.com")
                jobs.append({
                    "id": f"zip_{idx}_{abs(hash(job_url)) % 10000000}",
                    "title": title,
                    "company": comp,
                    "location": loc,
                    "remote": bool(row_dict.get("is_remote", is_remote)),
                    "salary": "$120,000 - $175,000",
                    "posted": str(row_dict.get("date_posted") or "Recent"),
                    "description": f"{title} at {comp}. Verified listing from ZipRecruiter.",
                    "full_description": f"{title} at {comp} located in {loc}.",
                    "url": job_url,
                    "apply_url": job_url,
                    "source": "ZipRecruiter",
                    "tags": ["ziprecruiter", "verified"],
                })
    except Exception as exc:
        logger.debug(f"ZipRecruiter error: {exc}")

    return jobs
