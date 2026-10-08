"""
Cross-Source Fuzzy Deduplication & Canonicalization Engine (Feature P2-B).
Detects and merges cross-posted opportunities retrieved across 17 concurrent crawling feeds.
Prioritizes official direct ATS portals (Greenhouse, Ashby, Lever, Workday) over saturated aggregators,
merging rich metadata while eliminating duplicate cards on the dashboard.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple
from src.agents.scrapers.base import DIRECT_ATS_SOURCES


_CORP_SUFFIX_RE = re.compile(
    r"\b(?:inc\.?|llc\.?|ltd\.?|gmbh|corp\.?|corporation|co\.?|s\.?a\.?|lda\.?|technologies|solutions|group)\b",
    re.IGNORECASE,
)

_TITLE_CLEANUP_RE = re.compile(
    r"[\(\[\{].*?[\)\]\}]|\b(?:remote|hybrid|onsite|on-site|full-?time|part-?time|f/m/d|m/f/d|m/w/d)\b",
    re.IGNORECASE,
)

_PUNCT_RE = re.compile(r"[^\w\s]")


def normalize_company_name(name: str) -> str:
    """Normalize employer name for cross-channel entity resolution."""
    if not name:
        return ""
    clean = _CORP_SUFFIX_RE.sub("", name)
    clean = _PUNCT_RE.sub(" ", clean)
    return " ".join(clean.lower().split())


def normalize_job_title(title: str) -> str:
    """Normalize job title removing parentheticals, remote tags, and noise tokens."""
    if not title:
        return ""
    clean = _TITLE_CLEANUP_RE.sub("", title)
    clean = _PUNCT_RE.sub(" ", clean)
    tokens = clean.lower().split()
    return " ".join(tokens)


def _get_source_authority_tier(source: str) -> int:
    """Assign priority rank (lower number = higher priority authority).
    Tier 1 (Direct ATS): 1
    Tier 2 (Specialized Portals): 2
    Tier 3 (Aggregators): 3
    """
    s_lower = (source or "").lower()
    if any(ats in s_lower for ats in DIRECT_ATS_SOURCES):
        return 1
    if any(sp in s_lower for sp in ["remoteok", "arbeitnow", "itjobs", "remotive", "landing", "net-empregos"]):
        return 2
    return 3


def deduplicate_jobs(jobs: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Deduplicate a list of raw job dictionaries by resolving company + title clusters.
    When multiple postings refer to the same requisition:
    - Selects the canonical posting with the highest source authority (Direct ATS).
    - Enriches the canonical posting with any missing fields (salary, description details) from secondary copies.
    - Annotates with cross_listed=True and merged_sources.
    
    Returns (deduplicated_jobs, metrics_dict).
    """
    if not jobs:
        return [], {"total_input": 0, "unique_output": 0, "duplicates_removed": 0, "cross_listed_clusters": 0}

    clusters: Dict[str, List[Dict[str, Any]]] = {}

    for job in jobs:
        c_norm = normalize_company_name(job.get("company", ""))
        t_norm = normalize_job_title(job.get("title", ""))

        if not c_norm or not t_norm:
            # If missing title or company, cluster by title only or fallback to unique ID
            key = f"raw_{job.get('id') or job.get('job_id') or id(job)}"
        else:
            key = f"{c_norm}::{t_norm}"

        if key not in clusters:
            clusters[key] = []
        clusters[key].append(job)

    deduped: List[Dict[str, Any]] = []
    cross_listed_count = 0
    duplicates_removed = 0

    for key, items in clusters.items():
        if len(items) == 1:
            deduped.append(items[0])
            continue

        # Sort items by source authority (Tier 1 Direct ATS first), then by length of description
        items.sort(
            key=lambda x: (
                _get_source_authority_tier(x.get("source", "")),
                -len(str(x.get("full_description") or x.get("description") or "")),
            )
        )

        canonical = dict(items[0])
        duplicates_removed += len(items) - 1
        cross_listed_count += 1

        all_sources = list(dict.fromkeys(
            [str(x.get("source", "unknown")) for x in items if x.get("source")]
        ))
        canonical["cross_listed"] = True
        canonical["merged_sources"] = all_sources
        canonical["duplicate_count"] = len(items)

        # Merge missing salary or metadata from secondary copies if canonical was missing them
        if not canonical.get("salary") or canonical.get("salary") == "Competitive":
            for secondary in items[1:]:
                sec_sal = secondary.get("salary") or secondary.get("salary_range")
                if sec_sal and sec_sal != "Competitive":
                    canonical["salary"] = sec_sal
                    if "metadata" not in canonical:
                        canonical["metadata"] = {}
                    canonical["metadata"]["salary"] = sec_sal
                    break

        deduped.append(canonical)

    metrics = {
        "total_input": len(jobs),
        "unique_output": len(deduped),
        "duplicates_removed": duplicates_removed,
        "cross_listed_clusters": cross_listed_count,
    }

    return deduped, metrics
