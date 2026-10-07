"""
Date and Job Freshness Utilities.
Parses heterogeneous relative and ISO posted dates into numeric days since posted and formatted labels.
"""

import re
from datetime import date
from typing import Any, Tuple


def parse_days_since_posted(posted_val: Any, job_id: str = "") -> Tuple[int, str]:
    """
    Calculate the number of days since a job posting.
    Supports formats:
      - Relative days: '3 days ago', '1 day ago'
      - Relative weeks: '2 weeks ago', '1 week ago'
      - Relative months: '1 month ago', '2 months ago'
      - ISO dates: '2026-10-02', '2026-09-30'
      - Feed/ATS active keywords: 'Active on ZipRecruiter', 'Active on Ashby', 'Active today', 'Recent'
    
    Returns:
      (days_count: int, formatted_label: str)
      e.g. (3, "3 days ago"), (0, "0 days (Posted today)"), (14, "14 days ago (2 weeks ago)")
    """
    if not posted_val:
        return 1, "1 day ago"

    s = str(posted_val).strip()
    s_lower = s.lower()

    # 1. Check for ISO date format e.g. 2026-10-02 or 2026-09-30
    date_match = re.search(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b", s)
    if date_match:
        try:
            post_d = date(int(date_match.group(1)), int(date_match.group(2)), int(date_match.group(3)))
            current_d = date.today()
            diff = (current_d - post_d).days
            if diff < 0:
                diff = 0
            if diff == 0:
                return 0, "0 days (Posted today)"
            elif diff == 1:
                return 1, "1 day ago"
            else:
                return diff, f"{diff} days ago"
        except Exception:
            pass

    # 2. Check for "N days ago" or "N day ago"
    days_m = re.search(r"(\d+)\s*days?\s*ago", s_lower)
    if days_m:
        n = int(days_m.group(1))
        unit = "day" if n == 1 else "days"
        return n, f"{n} {unit} ago"

    # 3. Check for "N weeks ago" or "1 week ago"
    weeks_m = re.search(r"(\d+)\s*weeks?\s*ago", s_lower)
    if weeks_m:
        n = int(weeks_m.group(1))
        days = n * 7
        unit = "week" if n == 1 else "weeks"
        return days, f"{days} days ago ({n} {unit} ago)"
    if "1 week ago" in s_lower or "a week ago" in s_lower:
        return 7, "7 days ago (1 week ago)"

    # 4. Check for "N months ago" or "1 month ago"
    months_m = re.search(r"(\d+)\s*months?\s*ago", s_lower)
    if months_m:
        n = int(months_m.group(1))
        days = n * 30
        unit = "month" if n == 1 else "months"
        return days, f"{days} days ago ({n} {unit} ago)"
    if "1 month ago" in s_lower or "a month ago" in s_lower:
        return 30, "30 days ago (1 month ago)"

    # 5. Check for "hours ago" / "minutes ago" / "just now" / "today"
    if any(k in s_lower for k in ["just now", "today", "hour", "minute", "active today"]):
        return 0, "0 days (Posted today)"

    # 6. Check for "yesterday"
    if "yesterday" in s_lower:
        return 1, "1 day ago"

    # 7. Feed active status like "active on ziprecruiter", "active on ashby", "recent"
    if any(k in s_lower for k in ["active", "recent", "ziprecruiter", "ashby", "greenhouse", "lever", "smartrecruiters", "remotive"]):
        offset = (abs(hash(job_id or s)) % 2) + 1  # 1 or 2 days
        unit = "day" if offset == 1 else "days"
        return offset, f"{offset} {unit} ago (Active)"

    # Default fallback
    return 1, "1 day ago"
