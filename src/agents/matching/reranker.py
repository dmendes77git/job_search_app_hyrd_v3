"""
Pass 2 Hybrid Reranker powered by Google Gemini.
Performs deep semantic reranking on the top candidate pool to assess nuanced
cultural, technical, and scope alignment.
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger("Hyrd.Scoring.Reranker")


def rerank_top_jobs_with_gemini(
    top_jobs: List[Dict[str, Any]],
    profile: Dict[str, Any],
    api_key: Optional[str] = None,
    limit: int = 15,
) -> List[Dict[str, Any]]:
    """
    Pass 2 Hybrid Reranker: Uses Google Gemini to perform deep semantic reranking
    on the top candidate pool, evaluating nuanced cultural, technical, and scope alignment.
    Falls back gracefully to existing heuristic rank if Gemini is unavailable or errors.
    """
    if not top_jobs or len(top_jobs) <= 1:
        return top_jobs

    effective_key = api_key or os.environ.get("GEMINI_API_KEY", "")
    if not effective_key:
        return top_jobs

    candidates_to_rerank = top_jobs[:limit]

    jobs_summary = []
    for j in candidates_to_rerank:
        jobs_summary.append({
            "id": j.get("id"),
            "title": j.get("title"),
            "company": j.get("company"),
            "current_score": j.get("fit_score", 85),
            "description_snippet": (j.get("description", "") or "")[:220],
        })

    prompt = f"""You are an elite executive talent recruiter.
Evaluate these {len(jobs_summary)} job opportunities against this candidate profile:
Candidate Target Role: {profile.get("headline") or profile.get("target_role")}
Years Experience: {profile.get("years_of_experience")}
Core Skills: {", ".join((profile.get("core_skills") or [])[:8])}
Summary: {profile.get("summary", "")[:250]}

Jobs to Evaluate:
{json.dumps(jobs_summary, indent=2)}

For each job, provide a calibrated score adjustment (an integer between -4 and +4) and a concise 1-sentence executive recruiter verdict on why this role fits the candidate.
Return JSON formatted as:
[
  {{"id": "job_id", "score_adjustment": 2, "recruiter_verdict": "..."}}
]
"""
    try:
        from src.utils.gemini_client import generate_gemini_json

        result = generate_gemini_json(prompt, api_key=effective_key)
        if isinstance(result, list):
            eval_map = {
                item.get("id"): item
                for item in result
                if isinstance(item, dict) and "id" in item
            }
            for j in candidates_to_rerank:
                jid = j.get("id")
                if jid in eval_map:
                    adj = int(eval_map[jid].get("score_adjustment", 0))
                    adj = max(-4, min(4, adj))
                    new_score = int(min(99, max(72, j.get("fit_score", 85) + adj)))
                    j["fit_score"] = new_score
                    verdict = eval_map[jid].get("recruiter_verdict")
                    if verdict:
                        j["gemini_verdict"] = verdict
                        if "key_reasons" in j and isinstance(j["key_reasons"], list):
                            j["key_reasons"].insert(0, f"🤖 Recruiter Verdict: {verdict}")

            candidates_to_rerank.sort(key=lambda x: x.get("fit_score", 0), reverse=True)
            return candidates_to_rerank + top_jobs[limit:]
    except Exception as e:
        logger.debug(f"Gemini reranking skipped ({e}), using heuristic scores.")

    return top_jobs
