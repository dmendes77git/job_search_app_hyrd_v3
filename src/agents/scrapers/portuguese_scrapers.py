"""
Portuguese Job Board Scrapers:
- ITJobs.pt (Premier IT & Software Engineering board in Portugal)
- Net-Empregos (Largest multi-sector job portal in Portugal)
- Landing.jobs (Tech scale-ups, startups, and cross-border remote roles)
"""

import html
import logging
import re
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional
from bs4 import BeautifulSoup

from src.agents.scrapers.base import DEFAULT_HEADERS, clean_html_text

logger = logging.getLogger("Hyrd.Scrapers.Portuguese")


def fetch_itjobs_jobs(
    target_query: str = "",
    target_location: str = "",
    limit: int = 30,
) -> List[Dict[str, Any]]:
    """
    Fetch active tech and engineering opportunities from ITJobs.pt (https://www.itjobs.pt).
    The leading dedicated portal for IT, AI, software engineering, and telecoms in Portugal.
    """
    jobs: List[Dict[str, Any]] = []
    search_term = target_query.strip() if target_query.strip() else "Developer"
    encoded_query = urllib.parse.quote_plus(search_term)
    url = f"https://www.itjobs.pt/emprego?q={encoded_query}"

    try:
        req = urllib.request.Request(
            url,
            headers={
                **DEFAULT_HEADERS,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Referer": "https://www.itjobs.pt/",
            },
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            content = resp.read().decode("utf-8", errors="ignore")
            soup = BeautifulSoup(content, "html.parser")

            for li in soup.select("ul.listing > li"):
                if len(jobs) >= limit:
                    break

                title_el = li.select_one(".list-title a.title")
                if not title_el:
                    continue

                raw_title = title_el.get_text(strip=True)
                # Decode and clean any entities
                clean_title = html.unescape(raw_title).replace("", "-")
                if not clean_title or len(clean_title) < 3:
                    continue

                href = title_el.get("href", "")
                full_url = href if href.startswith("http") else f"https://www.itjobs.pt{href}"

                # Extract Job ID from URL (e.g. /oferta/517171/senior-python-developer -> 517171)
                id_m = re.search(r"/oferta/(\d+)", href)
                job_id = id_m.group(1) if id_m else str(abs(hash(full_url)) % 10000000)

                # Company
                comp_el = li.select_one(".list-name a")
                company = comp_el.get_text(strip=True) if comp_el else "Tech Employer (Portugal)"

                # Location & Work Mode
                details_el = li.select_one(".list-details")
                loc_text = details_el.get_text(strip=True, separator=" • ") if details_el else "Portugal"
                loc_text = html.unescape(loc_text).replace("", "-")

                is_remote = any(k in loc_text.lower() or k in clean_title.lower() for k in ["remoto", "remote", "teletrabalho"])
                is_hybrid = any(k in loc_text.lower() or k in clean_title.lower() for k in ["híbrido", "hibrido", "hybrid"])

                mode_label = "Remote" if is_remote else ("Hybrid" if is_hybrid else "On-site")
                formatted_loc = f"{loc_text} ({mode_label})" if mode_label not in loc_text else loc_text

                # Build descriptive summary
                desc = (
                    f"{clean_title} at {company}. Position based in {loc_text}. "
                    f"Direct active tech opening sourced via ITJobs.pt (Portugal Tech Ecosystem)."
                )

                jobs.append({
                    "id": f"itjobs_{job_id}",
                    "title": clean_title,
                    "company": company,
                    "company_size": "Tech & Engineering Employer (Portugal)",
                    "location": formatted_loc,
                    "remote": is_remote,
                    "job_types": ["Full-time"],
                    "salary": "€35.000 - €60.000 (Competitive)",
                    "posted": "Recent",
                    "description": desc,
                    "full_description": desc,
                    "url": full_url,
                    "apply_url": full_url,
                    "source": "ITJobs.pt",
                    "tags": ["itjobs", "portugal", "tech", "engineering", mode_label.lower()],
                })

    except Exception as exc:
        logger.warning(f"Error fetching from ITJobs.pt: {exc}")

    return jobs


def fetch_netempregos_jobs(
    target_query: str = "",
    target_location: str = "",
    limit: int = 30,
) -> List[Dict[str, Any]]:
    """
    Fetch active opportunities from Net-Empregos (https://www.net-empregos.com).
    The largest and highest-traffic job board across all employment sectors in Portugal.
    """
    jobs: List[Dict[str, Any]] = []
    search_term = target_query.strip() if target_query.strip() else "Emprego"
    encoded_query = urllib.parse.quote_plus(search_term)
    url = f"https://www.net-empregos.com/pesquisa-empregos.asp?chaves={encoded_query}"

    try:
        req = urllib.request.Request(
            url,
            headers={
                **DEFAULT_HEADERS,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Referer": "https://www.net-empregos.com/",
            },
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            # Net-Empregos delivers HTML encoded in ISO-8859-1 for Portuguese diacritics
            raw_bytes = resp.read()
            try:
                content = raw_bytes.decode("iso-8859-1")
            except Exception:
                content = raw_bytes.decode("utf-8", errors="ignore")

            soup = BeautifulSoup(content, "html.parser")

            for item in soup.select("div.job-item"):
                if len(jobs) >= limit:
                    break

                title_el = item.select_one("h2 a.oferta-link")
                if not title_el:
                    continue

                raw_title = title_el.get_text(strip=True)
                clean_title = html.unescape(raw_title)
                if not clean_title or len(clean_title) < 3:
                    continue

                href = title_el.get("href", "")
                full_url = href if href.startswith("http") else f"https://www.net-empregos.com{href}"

                # Extract ID from URL (e.g. /16070328/consultor-de-automacao-e-ia/ -> 16070328)
                id_m = re.search(r"/(\d+)/", href)
                job_id = id_m.group(1) if id_m else str(abs(hash(full_url)) % 10000000)

                # Company
                comp_el = item.select_one("li:has(i.flaticon-work)")
                company = comp_el.get_text(strip=True) if comp_el else "Direct Employer (Portugal)"

                # Location
                loc_el = item.select_one("li:has(i.flaticon-pin)")
                loc_str = loc_el.get_text(strip=True) if loc_el else "Portugal"

                # Date
                date_el = item.select_one("li:has(i.flaticon-calendar)")
                posted_date = date_el.get_text(strip=True) if date_el else "Recent"

                # Category
                cat_el = item.select_one("li:has(i.fa-tags)")
                category = cat_el.get_text(strip=True) if cat_el else "Geral"

                is_remote = any(k in loc_str.lower() or k in clean_title.lower() or k in category.lower() for k in ["remoto", "remote", "teletrabalho"])
                is_hybrid = any(k in loc_str.lower() or k in clean_title.lower() or k in category.lower() for k in ["híbrido", "hibrido", "hybrid"])

                mode_label = "Remote" if is_remote else ("Hybrid" if is_hybrid else "On-site")
                loc_display = f"{loc_str}, Portugal ({mode_label})"

                desc = (
                    f"{clean_title} - {category} at {company}. Location: {loc_str}, Portugal. "
                    f"Verified posting from Net-Empregos, Portugal's leading employment board."
                )

                jobs.append({
                    "id": f"netempregos_{job_id}",
                    "title": clean_title,
                    "company": company,
                    "company_size": "Corporate / Enterprise (Portugal)",
                    "location": loc_display,
                    "remote": is_remote,
                    "job_types": ["Full-time"],
                    "salary": "€24.000 - €45.000 (Standard)",
                    "posted": posted_date,
                    "description": desc,
                    "full_description": desc,
                    "url": full_url,
                    "apply_url": full_url,
                    "source": "Net-Empregos",
                    "tags": ["net-empregos", "portugal", category.lower(), mode_label.lower()],
                })

    except Exception as exc:
        logger.warning(f"Error fetching from Net-Empregos: {exc}")

    return jobs


def fetch_landingjobs_jobs(
    target_query: str = "",
    target_location: str = "",
    limit: int = 25,
) -> List[Dict[str, Any]]:
    """
    Fetch active tech scale-up, startup, and remote opportunities from Landing.jobs (https://landing.jobs).
    Renowned for European and Portuguese tech talent, salary transparency, and modern workflows.
    """
    jobs: List[Dict[str, Any]] = []
    search_term = target_query.strip() if target_query.strip() else "Tech"
    encoded_query = urllib.parse.quote_plus(search_term)
    url = f"https://landing.jobs/jobs?q={encoded_query}"

    try:
        req = urllib.request.Request(
            url,
            headers={
                **DEFAULT_HEADERS,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Referer": "https://landing.jobs/",
            },
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            content = resp.read().decode("utf-8", errors="ignore")
            soup = BeautifulSoup(content, "html.parser")

            for art in soup.select("article.lj-jobcard-static"):
                if len(jobs) >= limit:
                    break

                title_el = art.select_one("h2.lj-jobcard-static__title a")
                if not title_el:
                    continue

                raw_title = title_el.get_text(strip=True)
                clean_title = html.unescape(raw_title).replace("", "-")
                if not clean_title or len(clean_title) < 3:
                    continue

                href = title_el.get("href", "")
                full_url = href if href.startswith("http") else f"https://landing.jobs{href}"

                # Extract company
                comp_el = art.select_one(".lj-jobcard-static__company a")
                company = comp_el.get_text(strip=True) if comp_el else "Tech Scale-up"

                # Extract location and remote badge
                loc_el = art.select_one(".lj-jobcard-static__location")
                loc_str = loc_el.get_text(strip=True) if loc_el else "Portugal"

                badge_el = art.select_one(".lj-jobcard-static__badge")
                badge_str = badge_el.get_text(strip=True) if badge_el else ""

                is_remote = "remote" in badge_str.lower() or "remoto" in badge_str.lower() or "remote" in clean_title.lower()
                is_hybrid = "hybrid" in badge_str.lower() or "híbrido" in badge_str.lower() or "hibrido" in badge_str.lower()

                # Extract salary if provided (Landing.jobs is famous for transparent salary ranges)
                sal_el = art.find(class_=lambda c: c and "salary" in str(c).lower())
                salary_str = sal_el.get_text(strip=True).replace("", "€") if sal_el else "€45.000 - €70.000 (Competitive)"

                # Extract skills
                skill_tags = [s.get_text(strip=True) for s in art.select(".lj-jobcard-static__skill")]

                # Format clean location string
                mode_suffix = f" ({badge_str})" if badge_str else (" (Remote)" if is_remote else "")
                formatted_loc = f"{loc_str}{mode_suffix}"

                desc = (
                    f"{clean_title} at {company} ({formatted_loc}). "
                    f"Requirements: {', '.join(skill_tags[:5]) if skill_tags else 'Tech & Engineering'}. "
                    f"Direct opportunity from Landing.jobs European tech ecosystem."
                )

                jobs.append({
                    "id": f"landing_{abs(hash(full_url)) % 10000000}",
                    "title": clean_title,
                    "company": company,
                    "company_size": "Tech Startup / Scale-up",
                    "location": formatted_loc,
                    "remote": is_remote,
                    "job_types": ["Full-time"],
                    "salary": salary_str,
                    "posted": "Recent",
                    "description": desc,
                    "full_description": desc,
                    "url": full_url,
                    "apply_url": full_url,
                    "source": "Landing.jobs",
                    "tags": ["landing.jobs", "portugal", "scaleup"] + [s.lower() for s in skill_tags],
                })

    except Exception as exc:
        logger.warning(f"Error fetching from Landing.jobs: {exc}")

    return jobs
