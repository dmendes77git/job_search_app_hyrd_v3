"""
Salary Benchmark Data & Geographic Compensation Factors.
Provides baseline compensation bands by role family and seniority tier (USD),
along with regional cost-of-living adjustments, local currency symbols, and FX rates.
"""

from typing import Any, Dict, Tuple

# Market rate annual benchmarks in USD by role family and seniority tier
MARKET_BENCHMARKS: Dict[str, Dict[str, Tuple[float, float]]] = {
    "ai_ml": {
        "entry": (95000.0, 135000.0),
        "mid": (135000.0, 175000.0),
        "senior": (170000.0, 215000.0),
        "lead_staff": (200000.0, 260000.0),
        "executive": (245000.0, 340000.0),
    },
    "software_eng": {
        "entry": (85000.0, 120000.0),
        "mid": (120000.0, 160000.0),
        "senior": (155000.0, 195000.0),
        "lead_staff": (185000.0, 240000.0),
        "executive": (220000.0, 310000.0),
    },
    "data": {
        "entry": (80000.0, 115000.0),
        "mid": (115000.0, 155000.0),
        "senior": (150000.0, 190000.0),
        "lead_staff": (180000.0, 230000.0),
        "executive": (210000.0, 295000.0),
    },
    "product": {
        "entry": (80000.0, 110000.0),
        "mid": (115000.0, 150000.0),
        "senior": (150000.0, 195000.0),
        "lead_staff": (180000.0, 235000.0),
        "executive": (215000.0, 300000.0),
    },
    "marketing_sales": {
        "entry": (60000.0, 85000.0),
        "mid": (85000.0, 125000.0),
        "senior": (125000.0, 170000.0),
        "lead_staff": (155000.0, 210000.0),
        "executive": (190000.0, 275000.0),
    },
    "finance_ops": {
        "entry": (65000.0, 90000.0),
        "mid": (90000.0, 130000.0),
        "senior": (130000.0, 175000.0),
        "lead_staff": (160000.0, 215000.0),
        "executive": (195000.0, 285000.0),
    },
    "general": {
        "entry": (65000.0, 95000.0),
        "mid": (95000.0, 135000.0),
        "senior": (135000.0, 180000.0),
        "lead_staff": (165000.0, 220000.0),
        "executive": (200000.0, 280000.0),
    },
}

TIER_LABELS: Dict[str, str] = {
    "entry": "Junior / Entry (0-2 yrs)",
    "mid": "Mid-Level (3-5 yrs)",
    "senior": "Senior (5-8 yrs)",
    "lead_staff": "Lead / Staff / Principal (8+ yrs)",
    "executive": "Executive / Director (10+ yrs)",
}

# Geographic salary benchmark factors relative to US/Global baseline (1.00)
# Calibrated according to regional market compensation standards
GEOGRAPHIC_SALARY_FACTORS: Dict[str, Dict[str, Any]] = {
    "switzerland": {
        "factor": 1.18,
        "name": "Switzerland",
        "symbol": "CHF",
        "fx_to_usd": 1.12,
    },
    "united states": {
        "factor": 1.00,
        "name": "United States",
        "symbol": "$",
        "fx_to_usd": 1.00,
    },
    "singapore": {
        "factor": 0.85,
        "name": "Singapore",
        "symbol": "S$",
        "fx_to_usd": 0.76,
    },
    "canada": {
        "factor": 0.84,
        "name": "Canada",
        "symbol": "CAD$",
        "fx_to_usd": 0.74,
    },
    "australia": {
        "factor": 0.84,
        "name": "Australia",
        "symbol": "A$",
        "fx_to_usd": 0.66,
    },
    "united kingdom": {
        "factor": 0.82,
        "name": "United Kingdom",
        "symbol": "£",
        "fx_to_usd": 1.28,
    },
    "germany": {
        "factor": 0.78,
        "name": "Germany",
        "symbol": "€",
        "fx_to_usd": 1.08,
    },
    "netherlands": {
        "factor": 0.78,
        "name": "Netherlands",
        "symbol": "€",
        "fx_to_usd": 1.08,
    },
    "ireland": {
        "factor": 0.78,
        "name": "Ireland",
        "symbol": "€",
        "fx_to_usd": 1.08,
    },
    "norway": {
        "factor": 0.78,
        "name": "Norway",
        "symbol": "NOK",
        "fx_to_usd": 0.095,
    },
    "denmark": {
        "factor": 0.78,
        "name": "Denmark",
        "symbol": "DKK",
        "fx_to_usd": 0.145,
    },
    "austria": {
        "factor": 0.75,
        "name": "Austria",
        "symbol": "€",
        "fx_to_usd": 1.08,
    },
    "sweden": {
        "factor": 0.74,
        "name": "Sweden",
        "symbol": "SEK",
        "fx_to_usd": 0.096,
    },
    "france": {
        "factor": 0.72,
        "name": "France",
        "symbol": "€",
        "fx_to_usd": 1.08,
    },
    "finland": {
        "factor": 0.72,
        "name": "Finland",
        "symbol": "€",
        "fx_to_usd": 1.08,
    },
    "israel": {
        "factor": 0.86,
        "name": "Israel",
        "symbol": "₪",
        "fx_to_usd": 0.27,
    },
    "japan": {
        "factor": 0.70,
        "name": "Japan",
        "symbol": "¥",
        "fx_to_usd": 0.0066,
    },
    "spain": {
        "factor": 0.60,
        "name": "Spain",
        "symbol": "€",
        "fx_to_usd": 1.08,
    },
    "italy": {
        "factor": 0.60,
        "name": "Italy",
        "symbol": "€",
        "fx_to_usd": 1.08,
    },
    "portugal": {
        "factor": 0.58,
        "name": "Portugal",
        "symbol": "€",
        "fx_to_usd": 1.08,
    },
    "poland": {
        "factor": 0.55,
        "name": "Poland",
        "symbol": "PLN",
        "fx_to_usd": 0.25,
    },
    "brazil": {
        "factor": 0.45,
        "name": "Brazil",
        "symbol": "R$",
        "fx_to_usd": 0.18,
    },
    "mexico": {
        "factor": 0.45,
        "name": "Mexico",
        "symbol": "MX$",
        "fx_to_usd": 0.051,
    },
    "india": {
        "factor": 0.40,
        "name": "India",
        "symbol": "₹",
        "fx_to_usd": 0.012,
    },
    "europe": {
        "factor": 0.76,
        "name": "Europe",
        "symbol": "€",
        "fx_to_usd": 1.08,
    },
}
