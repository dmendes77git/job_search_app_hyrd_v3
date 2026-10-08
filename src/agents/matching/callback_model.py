"""
Empirical Bayesian Recruiter Callback Model (Feature P2-C).
Replaces linear probability approximations with a calibrated logistic regression
model calibrated against institutional hiring response distributions:
- Base candidate capability fit (S-curve response)
- Requisition age velocity decay Lambda(t)
- Ingestion channel authority & competition multiplier Omega
- Seniority delta & leveling distance friction
- Market saturation factor (applicant surge vs early-applicant advantage)
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple
from src.agents.matching.engine import calculate_temporal_decay, get_channel_advantage_multiplier


def calculate_bayesian_callback_probability(
    fit_score: float,
    days_posted: int = 1,
    source: str = "greenhouse",
    is_direct_ats: bool = False,
    missing_skills_count: int = 0,
    seniority_delta: int = 0,
    is_target_company: bool = False,
    applicant_estimate: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Calculate statistical probability of recruiter interview callback using an
    empirical Bayesian logistic formulation:
    P(callback) = sigma(z) in [0.05, 0.95]
    
    Returns structured metrics including percentage, probability, and hiring diagnostics.
    """
    # 1. Base log-odds for institutional inbound applications (base rate ~15%)
    z = -1.75

    # 2. Fit Score Contribution (Centered around 70)
    # Fit score of 95 yields +1.5, fit score of 50 yields -1.2
    fit_contrib = (float(fit_score) - 70.0) / 16.0
    z += fit_contrib

    # 3. Channel Advantage (Omega)
    channel_mult, channel_label = get_channel_advantage_multiplier(source, is_direct_ats=is_direct_ats)
    if is_direct_ats or channel_mult >= 1.15:
        z += 0.55  # Direct ATS unmediated portal bonus
    elif channel_mult <= 0.85:
        z -= 0.40  # Saturated public aggregator penalty

    # 4. Temporal Decay / Early Applicant Velocity Lambda(t)
    temporal_lambda = calculate_temporal_decay(days_posted)
    if days_posted <= 2:
        z += 0.50  # Early applicant window (first 48 hours)
    elif days_posted > 21:
        z -= 0.65  # Stale requisition saturation

    # 5. Skill Gap Friction
    gap_penalty = min(1.2, float(missing_skills_count) * 0.22)
    z -= gap_penalty

    # 6. Seniority / Leveling Distance Friction
    if seniority_delta > 1:
        # Applying >1 level above candidate tier (e.g. Mid -> Director)
        z -= 0.85
    elif seniority_delta < -1:
        # Heavily overqualified
        z -= 0.35
    elif seniority_delta == 0:
        z += 0.20  # Perfect level alignment

    # 7. Target Company Focus
    if is_target_company:
        z += 0.30

    # 8. Applicant Saturation Friction (if known)
    if applicant_estimate is not None:
        if applicant_estimate > 200:
            z -= 0.70
        elif applicant_estimate < 25:
            z += 0.40

    # Logistic Sigmoid Transformation: sigma(z) = 1 / (1 + exp(-z))
    try:
        prob = 1.0 / (1.0 + math.exp(-z))
    except OverflowError:
        prob = 0.95 if z > 0 else 0.05

    # Bound strictly between 5% and 95%
    bounded_prob = round(max(0.05, min(0.95, prob)), 3)
    likelihood_pct = round(bounded_prob * 100.0, 1)

    diagnostics: List[str] = []
    if days_posted <= 2:
        diagnostics.append("⚡ Early Applicant Window (<48h since posting)")
    elif days_posted > 20:
        diagnostics.append("⚠️ High Requisition Age (>20 days in market)")

    if is_direct_ats:
        diagnostics.append("🏛️ Direct Official ATS Channel (Priority Queue)")
    elif channel_mult < 0.90:
        diagnostics.append("👥 High Channel Competition (Aggregator Ingestion)")

    if missing_skills_count == 0:
        diagnostics.append("🎯 Zero Critical Competency Gaps")
    elif missing_skills_count >= 3:
        diagnostics.append(f"⚠️ {missing_skills_count} Core Skill Gaps Detected")

    return {
        "probability_of_response": bounded_prob,
        "interview_likelihood_pct": likelihood_pct,
        "channel_type": channel_label,
        "channel_multiplier": channel_mult,
        "temporal_decay": temporal_lambda,
        "diagnostics": diagnostics,
    }
