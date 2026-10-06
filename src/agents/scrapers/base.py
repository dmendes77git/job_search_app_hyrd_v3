"""
Base utilities, HTTP configurations, and resilience helpers for job scrapers.
"""

import html
import json
import logging
import re
import urllib.parse
import urllib.request
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("Hyrd.Scrapers")

# Standard HTTP headers mimicking a modern browser
HTTP_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
}
DEFAULT_HEADERS = HTTP_HEADERS


_HTML_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")
_NON_WORD_SLUG_RE = re.compile(r"[^\w\-]")


def clean_html_text(raw_text: str) -> str:
    """Strip HTML tags, decode entities, and normalize whitespace."""
    if not raw_text:
        return ""
    text = html.unescape(raw_text)
    clean = _HTML_TAG_RE.sub(" ", text)
    clean = _WHITESPACE_RE.sub(" ", clean).strip()
    return clean


def normalize_company_slug(comp: str) -> str:
    """Normalize user input company name to an ATS URL slug (e.g. 'Perplexity AI' -> 'perplexityai')."""
    clean = comp.lower().strip()
    clean = clean.replace("&", "and")
    clean = _NON_WORD_SLUG_RE.sub("", clean.replace(" ", ""))
    return clean


def safe_fetch_json(
    url: str,
    headers: Optional[Dict[str, str]] = None,
    timeout: int = 8,
) -> Optional[Any]:
    """Safely fetch and parse a JSON endpoint with timeout and exception containment."""
    hdrs = headers or HTTP_HEADERS
    try:
        req = urllib.request.Request(url, headers=hdrs)
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw)
    except Exception as exc:
        logger.debug(f"Fetch failed for {url}: {exc}")
        return None


def safe_scrape(
    name: str,
    fn: Callable[[], List[Dict[str, Any]]],
) -> Tuple[str, List[Dict[str, Any]]]:
    """Execute a scraper function safely, preventing any single failure from crashing the pipeline."""
    try:
        return name, fn()
    except Exception as exc:
        logger.warning(f"Scraper '{name}' encountered error: {exc}")
        return name, []
