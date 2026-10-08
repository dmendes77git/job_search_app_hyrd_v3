"""
Enterprise-Grade Scraper Base Infrastructure, BaseScraper ABC, and Session Management.
Adheres strictly to the Tier 1-4 Job Ingestion Hierarchy.
"""

from __future__ import annotations

import hashlib
import html
import json
import logging
import random
import re
import time
import urllib.parse
import urllib.request
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import httpx
from tenacity import (
    Retrying,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BeautifulSoup = None  # type: ignore
    BS4_AVAILABLE = False

from src.schemas import JobPosting, WorkType, generate_job_id

logger = logging.getLogger("Hyrd.Scrapers")

# ============================================================================
# 1. ROTATING USER-AGENTS & BROWSER HEADERS
# ============================================================================

USER_AGENTS: List[str] = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.4; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]


def get_random_user_agent() -> str:
    """Return a randomized modern desktop browser User-Agent string."""
    return random.choice(USER_AGENTS)


def get_browser_headers(accept_json: bool = True, custom_ua: Optional[str] = None) -> Dict[str, str]:
    """Generate realistic browser request headers with rotating User-Agent."""
    accept_val = (
        "application/json, text/plain, */*"
        if accept_json
        else "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
    )
    return {
        "User-Agent": custom_ua or get_random_user_agent(),
        "Accept": accept_val,
        "Accept-Language": "en-US,en;q=0.9,pt-PT;q=0.8,pt;q=0.7",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1" if not accept_json else "0",
    }


# Standard HTTP headers (preserved for backward compatibility)
HTTP_HEADERS = {
    "User-Agent": USER_AGENTS[0],
    "Accept": "application/json, text/plain, */*",
}
DEFAULT_HEADERS = HTTP_HEADERS

# Authoritative set of direct ATS endpoints (unmediated employer portals)
DIRECT_ATS_SOURCES = {
    "ashby",
    "greenhouse",
    "lever",
    "smartrecruiters",
    "workday",
    "bamboohr",
    "breezyhr",
}


# ============================================================================
# 2. STRING NORMALIZATION & REGEX HELPERS
# ============================================================================

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


# ============================================================================
# 3. LEGACY RESILIENCE HELPERS (Preserved for backward compatibility)
# ============================================================================

_SHARED_JSON_CLIENT: Optional[httpx.Client] = None


def get_shared_json_client() -> httpx.Client:
    """Provide a thread-safe pooled httpx.Client for fast JSON fetches."""
    global _SHARED_JSON_CLIENT
    if _SHARED_JSON_CLIENT is None or _SHARED_JSON_CLIENT.is_closed:
        _SHARED_JSON_CLIENT = httpx.Client(
            timeout=8.0,
            follow_redirects=True,
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=40),
            headers=HTTP_HEADERS,
        )
    return _SHARED_JSON_CLIENT


def safe_fetch_json(
    url: str,
    headers: Optional[Dict[str, str]] = None,
    timeout: int = 8,
) -> Optional[Any]:
    """Safely fetch and parse a JSON endpoint with keep-alive pooling, timeout and exception containment."""
    hdrs = headers or HTTP_HEADERS
    try:
        client = get_shared_json_client()
        resp = client.get(url, headers=hdrs, timeout=timeout)
        if resp.status_code == 200:
            return resp.json()
    except Exception as exc:
        logger.debug(f"HTTPX fetch failed for {url}: {exc}, falling back to urllib")

    try:
        req = urllib.request.Request(url, headers=hdrs)
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw)
    except Exception as exc:
        logger.debug(f"Legacy fetch failed for {url}: {exc}")
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


# ============================================================================
# 4. HTTP RETRY PREDICATE FOR TENACITY
# ============================================================================

def _is_transient_http_error(exc: BaseException) -> bool:
    """Evaluate whether an exception qualifies for automated retry."""
    if isinstance(exc, (httpx.TimeoutException, httpx.NetworkError, httpx.ConnectError, httpx.ReadTimeout)):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        # 429: Too Many Requests; 5xx: Server Errors
        return exc.response.status_code in (429, 500, 502, 503, 504)
    return False


# ============================================================================
# 5. ABSTRACT BASE CLASS: BaseScraper
# ============================================================================

class BaseScraper(ABC):
    """
    Abstract Base Class for all job scrapers across Tiers 1-4.

    Core capabilities:
    - Standardized `fetch_jobs()` polymorphic contract returning `List[JobPosting]`.
    - Resilient connection pooling and session management via `httpx.Client`.
    - Tenacity-based exponential backoff retry with jitter on network/transient failures.
    - User-Agent rotation and anti-bot headers.
    - Uniform error containment via `safe_fetch_jobs()`.
    """

    SOURCE_NAME: str = "base"

    def __init__(
        self,
        timeout: float = 8.0,
        max_retries: int = 2,
        rate_limit_delay: float = 0.15,
        client: Optional[httpx.Client] = None,
        transport: Optional[httpx.BaseTransport] = None,
        **kwargs: Any,
    ):
        self.timeout = timeout
        self.max_retries = max_retries
        self.rate_limit_delay = rate_limit_delay
        self._external_client = client is not None
        self._client = client
        self._transport = transport

    @property
    def is_closed(self) -> bool:
        """Return True if the scraper's HTTP client is closed or not initialized."""
        return self._client is None or self._client.is_closed

    @property
    def client(self) -> httpx.Client:
        """Provide or lazily initialize an active httpx.Client session."""
        if self._client is None:
            client_kwargs: Dict[str, Any] = {
                "timeout": self.timeout,
                "follow_redirects": True,
                "headers": get_browser_headers(accept_json=True),
            }
            if self._transport is not None:
                client_kwargs["transport"] = self._transport
            self._client = httpx.Client(**client_kwargs)
        return self._client

    def __enter__(self) -> "BaseScraper":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    def close(self) -> None:
        """Close the managed httpx client session if owned by this instance."""
        if self._client and not self._external_client and not self._client.is_closed:
            self._client.close()

    # ------------------------------------------------------------------------
    # HTTP Resilience Layer (Tenacity Retries & Exponential Backoff)
    # ------------------------------------------------------------------------

    def request_with_retry(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        json_body: Optional[Any] = None,
        data: Optional[Any] = None,
        timeout: Optional[float] = None,
        **kwargs: Any,
    ) -> httpx.Response:
        """
        Execute an HTTP request with Tenacity exponential backoff retries.
        Rotates User-Agent per attempt if headers are not explicitly fixed.
        """
        req_timeout = timeout or self.timeout
        retrying = Retrying(
            stop=stop_after_attempt(self.max_retries),
            wait=wait_exponential(multiplier=0.6, min=0.5, max=2.5),
            retry=retry_if_exception(_is_transient_http_error),
            reraise=True,
        )

        for attempt in retrying:
            with attempt:
                if self.rate_limit_delay > 0:
                    time.sleep(self.rate_limit_delay)

                active_headers = dict(headers) if headers else get_browser_headers()
                resp = self.client.request(
                    method=method.upper(),
                    url=url,
                    headers=active_headers,
                    params=params,
                    json=json_body,
                    data=data,
                    timeout=req_timeout,
                    **kwargs,
                )
                if resp.status_code in (429, 500, 502, 503, 504):
                    resp.raise_for_status()
                return resp

        raise RuntimeError(f"Request to {url} failed after {self.max_retries} retries.")

    def get(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
        **kwargs: Any,
    ) -> httpx.Response:
        """Perform HTTP GET request with retries."""
        return self.request_with_retry("GET", url, headers=headers, params=params, timeout=timeout, **kwargs)

    def post(
        self,
        url: str,
        json_body: Optional[Any] = None,
        data: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
        **kwargs: Any,
    ) -> httpx.Response:
        """Perform HTTP POST request with retries."""
        return self.request_with_retry("POST", url, headers=headers, json_body=json_body, data=data, timeout=timeout, **kwargs)

    def fetch_json(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs: Any,
    ) -> Optional[Any]:
        """Safely fetch and parse a JSON endpoint. Returns None on 4xx/5xx or parsing failure."""
        try:
            hdrs = headers or get_browser_headers(accept_json=True)
            resp = self.get(url, params=params, headers=hdrs, **kwargs)
            if resp.status_code == 200:
                return resp.json()
            logger.debug(f"[{self.SOURCE_NAME}] JSON fetch {url} returned HTTP {resp.status_code}")
            return None
        except Exception as exc:
            logger.debug(f"[{self.SOURCE_NAME}] JSON fetch failed for {url}: {exc}")
            return None

    def fetch_html(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs: Any,
    ) -> Optional[str]:
        """Safely fetch HTML content string. Returns None on failure."""
        try:
            hdrs = headers or get_browser_headers(accept_json=False)
            resp = self.get(url, params=params, headers=hdrs, **kwargs)
            if resp.status_code == 200:
                return resp.text
            logger.debug(f"[{self.SOURCE_NAME}] HTML fetch {url} returned HTTP {resp.status_code}")
            return None
        except Exception as exc:
            logger.debug(f"[{self.SOURCE_NAME}] HTML fetch failed for {url}: {exc}")
            return None

    def fetch_soup(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        parser: str = "html.parser",
        **kwargs: Any,
    ) -> Optional[Any]:
        """Fetch and parse HTML into a BeautifulSoup DOM tree."""
        if not BS4_AVAILABLE:
            logger.error("BeautifulSoup4 is not installed in the active environment.")
            return None
        html_content = self.fetch_html(url, params=params, headers=headers, **kwargs)
        if not html_content:
            return None
        try:
            return BeautifulSoup(html_content, parser)
        except Exception as exc:
            logger.warning(f"[{self.SOURCE_NAME}] DOM parsing failed for {url}: {exc}")
            return None

    # ------------------------------------------------------------------------
    # Data Normalization Utilities
    # ------------------------------------------------------------------------

    def generate_job_id(self, raw_id: str) -> str:
        """Create a deterministic unique hash for this source + external ID."""
        return generate_job_id(self.SOURCE_NAME, raw_id)

    @staticmethod
    def normalize_work_type(raw_val: Any) -> WorkType:
        """Classify a location or work mode string into a WorkType Enum."""
        if isinstance(raw_val, WorkType):
            return raw_val
        val_str = str(raw_val or "").strip().lower()
        if not val_str or "remote" in val_str or "remoto" in val_str or "anywhere" in val_str or "teletrabalho" in val_str:
            return WorkType.REMOTE
        if "hybrid" in val_str or "híbrido" in val_str:
            return WorkType.HYBRID
        if "onsite" in val_str or "on-site" in val_str or "presencial" in val_str:
            return WorkType.ONSITE
        # Non-empty physical geographic location without remote keywords represents onsite
        return WorkType.ONSITE

    @staticmethod
    def parse_posted_date(val: Any) -> Optional[datetime]:
        """Attempt to parse date strings or epoch timestamps into UTC datetime."""
        if isinstance(val, datetime):
            return val
        if isinstance(val, (int, float)):
            try:
                # Handle millisecond vs second timestamps
                if val > 1e11:
                    val = val / 1000.0
                return datetime.fromtimestamp(val, tz=timezone.utc)
            except Exception:
                return None
        if isinstance(val, str):
            val_clean = val.strip()
            # ISO 8601
            try:
                return datetime.fromisoformat(val_clean.replace("Z", "+00:00"))
            except Exception:
                pass
            # Common date formats (YYYY-MM-DD)
            for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d"):
                try:
                    return datetime.strptime(val_clean, fmt).replace(tzinfo=timezone.utc)
                except Exception:
                    pass
        return None

    # ------------------------------------------------------------------------
    # Polymorphic Contract & Resilient Invocation
    # ------------------------------------------------------------------------

    @abstractmethod
    def fetch_jobs(self, *args: Any, **kwargs: Any) -> List[JobPosting]:
        """
        Query upstream data source and yield standardized JobPosting instances.
        Must be implemented by concrete Tier 1-4 scrapers.
        """
        pass

    def safe_fetch_jobs(self, *args: Any, **kwargs: Any) -> List[JobPosting]:
        """
        Execute fetch_jobs with full exception containment, preventing any single
        scraper outage from propagating and failing the multi-agent pipeline.
        """
        try:
            return self.fetch_jobs(*args, **kwargs)
        except Exception as exc:
            logger.error(f"[{self.SOURCE_NAME}] Scraper execution failed: {exc}", exc_info=True)
            return []
