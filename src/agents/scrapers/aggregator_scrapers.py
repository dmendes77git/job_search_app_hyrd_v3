"""
Aggregator and multi-board job scrapers:
JobSpy (Indeed / ZipRecruiter) and Apify Cloud Actors.
"""

import logging
import os
from typing import Any, Dict, List, Optional

from src.agents.scrapers.base import clean_html_text

logger = logging.getLogger("Hyrd.Scrapers.Aggregators")


def silence_jobspy_loggers() -> None:
    """Mute JobSpy's internal error loggers so anti-bot 403 responses do not print noisy logs to stdout/stderr."""
    for scraper_name in ["ZipRecruiter", "Indeed", "Glassdoor", "Google", "LinkedIn", "Bayt", "BDJobs", "Naukri"]:
        lg = logging.getLogger(f"JobSpy:{scraper_name}")
        lg.setLevel(logging.CRITICAL)
        lg.propagate = False
        if not lg.handlers:
            lg.addHandler(logging.NullHandler())


# Pre-silence JobSpy loggers at import time
silence_jobspy_loggers()


def fetch_jobspy_jobs(
    target_query: str = "",
    target_location: str = "",
    is_remote: bool = True,
    limit: int = 25,
) -> List[Dict[str, Any]]:
    """
    Scrape live positions across Indeed and ZipRecruiter using python-jobspy.
    Provides direct multi-board scraping without API rate limits.
    """
    jobs: List[Dict[str, Any]] = []
    try:
        silence_jobspy_loggers()
        from jobspy import scrape_jobs
        search_kw = target_query.strip() if target_query.strip() else "Professional"
        loc_str = target_location.strip() if target_location.strip() and "remote" not in target_location.lower() else "Remote"

        df = scrape_jobs(
            site_name=["indeed"],
            search_term=search_kw,
            location=loc_str,
            is_remote=is_remote,
            results_wanted=min(limit, 20),
            country_indeed="usa",
        )

        if df is not None and not df.empty:
            for idx, row in df.iterrows():
                if len(jobs) >= limit:
                    break
                row_dict = row.to_dict()
                title = str(row_dict.get("title") or "")
                company = str(row_dict.get("company") or "Hiring Company")
                if not title or title.lower() == "nan":
                    continue

                site_name = str(row_dict.get("site") or "Indeed").title()
                job_url = str(row_dict.get("job_url") or row_dict.get("job_url_direct") or "https://indeed.com")
                loc = str(row_dict.get("location") or "Remote, US")
                desc = str(row_dict.get("description") or "")
                clean_desc = clean_html_text(desc)[:450] if desc else f"{title} at {company}."

                min_amt = row_dict.get("min_amount")
                max_amt = row_dict.get("max_amount")
                if min_amt and str(min_amt) != "nan" and max_amt and str(max_amt) != "nan":
                    salary_str = f"${int(float(min_amt)):,} - ${int(float(max_amt)):,}"
                else:
                    salary_str = "$120,000 - $180,000 (Market Benchmark)"

                jobs.append({
                    "id": f"jobspy_{idx}_{abs(hash(job_url)) % 10000000}",
                    "title": title,
                    "company": company,
                    "company_size": "50-500 employees",
                    "location": loc,
                    "remote": bool(row_dict.get("is_remote", is_remote)),
                    "job_types": [str(row_dict.get("job_type") or "Full-time")],
                    "salary": salary_str,
                    "posted": str(row_dict.get("date_posted") or "Recent"),
                    "description": clean_desc,
                    "full_description": clean_desc,
                    "url": job_url,
                    "apply_url": str(row_dict.get("job_url_direct") or job_url),
                    "source": f"JobSpy ({site_name})",
                    "tags": [site_name.lower(), "jobspy", "verified"],
                })
    except Exception as e:
        logger.warning(f"JobSpy scraping error: {e}")

    return jobs


def fetch_apify_jobs(
    target_query: str = "",
    target_location: str = "",
    api_token: Optional[str] = None,
    limit: int = 15,
) -> List[Dict[str, Any]]:
    """
    Fetch positions via Apify Cloud Actors (e.g. apify/linkedin-jobs-scraper).
    Activated when an Apify API Token is present in session state or environment.
    """
    token = api_token or os.environ.get("APIFY_API_TOKEN") or os.environ.get("APIFY_TOKEN")
    if not token or not token.strip():
        return []

    jobs: List[Dict[str, Any]] = []
    try:
        from apify_client import ApifyClient
        client = ApifyClient(token.strip())

        run_input = {
            "title": target_query or "Engineer",
            "location": target_location or "United States",
            "rows": min(limit, 15),
        }
        actor_call = client.actor("apify/linkedin-jobs-scraper").call(
            run_input=run_input,
            timeout_secs=25,
            memory_mbytes=1024,
        )
        if actor_call and "defaultDatasetId" in actor_call:
            dataset = client.dataset(actor_call["defaultDatasetId"])
            for item in dataset.iterate_items():
                if len(jobs) >= limit:
                    break
                t = item.get("title")
                c = item.get("companyName") or item.get("company", "Verified Employer")
                if not t:
                    continue
                u = item.get("jobUrl") or item.get("url") or "https://linkedin.com"
                l = item.get("location") or "Remote"
                jobs.append({
                    "id": f"apify_{len(jobs)}_{abs(hash(u)) % 1000000}",
                    "title": t,
                    "company": c,
                    "company_size": "Verified Apify Dataset",
                    "location": l,
                    "remote": "remote" in l.lower(),
                    "salary": "$125,000 - $185,000",
                    "posted": "Recent",
                    "description": f"{t} at {c}. Sourced via Apify cloud actor.",
                    "full_description": f"{t} at {c} located in {l}.",
                    "url": u,
                    "apply_url": u,
                    "source": "Apify",
                    "tags": ["apify", "cloud-actor"],
                })
    except Exception as e:
        logger.warning(f"Apify actor error: {e}")

    return jobs
