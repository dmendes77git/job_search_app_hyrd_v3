"""
Unified Gemini API Gateway & Model Cascade Resilience Engine.
Provides thread-safe client instantiation, dynamic model discovery,
automatic 503/429 backoff retry, and robust JSON/text generation.
"""

import json
import logging
import os
import random
import re
import time
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("Hyrd.GeminiClient")

# Candidate default fallback models in descending order of preference
DEFAULT_MODEL_CASCADE = [
    "gemini-3.8-flash",
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-flash",
]

_CLIENT_CACHE: Dict[str, Any] = {}
_DISCOVERED_MODELS_CACHE: Dict[str, List[str]] = {}


def sort_models_by_priority(model_names: List[str], preferred_model: Optional[str] = None) -> List[str]:
    """
    Sort available models to prioritize fast, high-capacity flash models:
    1. Preferred model if explicitly requested by user
    2. Flash models (gemini-*-flash) sorted by version
    3. Pro models (gemini-*-pro)
    Filter out embedding, audio-only, vision-only or translation models.
    """
    def model_score(name: str) -> int:
        n = name.lower()
        score = 0
        if preferred_model and preferred_model.lower() in n:
            score += 10000
        if "flash" in n:
            score += 1000
        if "lite" in n:
            score += 200
        if "3.8" in n:
            score += 90
        elif "3.5" in n:
            score += 80
        elif "3.1" in n:
            score += 70
        elif "2.5" in n:
            score += 60
        elif "2.0" in n:
            score += 50
        elif "1.5" in n:
            score += 40
        # Exclude non-text/generation endpoints
        if any(x in n for x in ["embed", "tts", "image", "live", "transcribe", "vision"]):
            score -= 50000
        return score

    filtered = [
        m for m in model_names
        if not any(x in m.lower() for x in ["embed", "tts", "image", "live", "transcribe", "banana"])
    ]
    return sorted(filtered, key=model_score, reverse=True)


def get_genai_client(api_key: Optional[str] = None) -> Optional[Any]:
    """
    Get or create a cached Google GenAI Client instance.
    Returns None if no API key is provided or found in the environment.
    """
    effective_key = (api_key or os.environ.get("GEMINI_API_KEY", "")).strip()
    if not effective_key:
        return None

    if effective_key in _CLIENT_CACHE:
        return _CLIENT_CACHE[effective_key]

    try:
        from google import genai
        logging.getLogger("google_genai.models").setLevel(logging.ERROR)
        client = genai.Client(api_key=effective_key)
        _CLIENT_CACHE[effective_key] = client
        return client
    except Exception as exc:
        logger.warning(f"Failed to initialize Google GenAI Client: {exc}")
        return None


def get_available_models(client: Any, preferred_model: Optional[str] = None) -> Tuple[List[str], Optional[str]]:
    """
    Dynamically discover all models available for generateContent on this client/API key.
    Results are cached per client instance.
    """
    if client is None:
        return DEFAULT_MODEL_CASCADE, "Client is not initialized"

    cache_key = id(client)
    if cache_key in _DISCOVERED_MODELS_CACHE:
        cached = _DISCOVERED_MODELS_CACHE[cache_key]
        if preferred_model:
            return sort_models_by_priority(cached, preferred_model), None
        return cached, None

    try:
        raw_models = []
        for m in client.models.list():
            actions = getattr(m, "supported_actions", []) or []
            if "generateContent" in actions:
                clean_name = m.name.replace("models/", "")
                raw_models.append(clean_name)
        if raw_models:
            sorted_models = sort_models_by_priority(raw_models, preferred_model)
            _DISCOVERED_MODELS_CACHE[cache_key] = sorted_models
            return sorted_models, None
    except Exception as exc:
        logger.debug(f"Dynamic model listing failed ({exc}), falling back to default cascade.")

    return DEFAULT_MODEL_CASCADE, None


def clean_markdown_fences(raw_text: str) -> str:
    """Strip markdown code fence blocks (```json, ```) and leading/trailing whitespace."""
    if not raw_text:
        return ""
    clean = raw_text.strip()
    clean = re.sub(r"^```(?:json)?\s*", "", clean)
    clean = re.sub(r"\s*```$", "", clean)
    return clean.strip()


def generate_gemini_content(
    prompt: str,
    api_key: Optional[str] = None,
    preferred_model: Optional[str] = None,
    max_retries_per_model: int = 2,
    backoff_delay: float = 2.0,
    config: Optional[Any] = None,
) -> Optional[str]:
    """
    Robust text generation via Gemini API.
    Handles client resolution, automatic model priority cascade,
    and resilience against 503/429 capacity spikes.
    """
    client = get_genai_client(api_key)
    if not client:
        return None

    discovered, _ = get_available_models(client, preferred_model)
    cascade = discovered if discovered else DEFAULT_MODEL_CASCADE

    from google.genai import types

    gen_config = config
    if gen_config is None:
        gen_config = types.GenerateContentConfig(
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )

    for model_name in cascade[:6]:
        for attempt in range(max_retries_per_model):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=gen_config,
                )
                if response and response.text:
                    return response.text.strip()
            except Exception as e:
                err_str = str(e).lower()
                # Stop immediately on fatal authentication errors
                if any(k in err_str for k in ["401", "403", "api_key_invalid", "permission_denied"]):
                    logger.error(f"Gemini authentication failed: {e}")
                    return None
                # If model is not found, skip directly to the next model in cascade
                if "404" in err_str or "not found" in err_str:
                    break
                # Immediate failover on 503 capacity / high demand spikes: skip retry, failover to next model
                if any(k in err_str for k in ["503", "unavailable", "high demand", "capacity", "spikes in demand", "overloaded"]):
                    logger.warning(f"Model {model_name} overloaded (503/capacity). Fast failover to next cascade tier.")
                    break
                # Jittered backoff retry on 429 rate limit / quota
                if any(k in err_str for k in ["429", "quota", "resource_exhausted"]) and attempt < max_retries_per_model - 1:
                    jittered_delay = min(0.5 * (2 ** attempt) + random.uniform(0, 0.2), 1.5)
                    logger.info(f"Model {model_name} rate limited (429). Retrying in {jittered_delay:.2f}s...")
                    time.sleep(jittered_delay)
                    continue
                break

    return None


def generate_gemini_json(
    prompt: str,
    api_key: Optional[str] = None,
    preferred_model: Optional[str] = None,
    schema: Optional[Any] = None,
) -> Optional[Dict[str, Any]]:
    """
    Generate and safely parse JSON structured content via Gemini API.
    Strips markdown code fences and handles JSON parsing gracefully.
    """
    from google.genai import types

    config = None
    if schema is not None:
        try:
            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=schema,
                automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
            )
        except Exception:
            config = None

    raw_text = generate_gemini_content(
        prompt=prompt,
        api_key=api_key,
        preferred_model=preferred_model,
        config=config,
    )

    if not raw_text:
        return None

    cleaned = clean_markdown_fences(raw_text)
    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return parsed
        elif isinstance(parsed, list):
            return {"items": parsed}
    except Exception as exc:
        logger.warning(f"Failed to parse Gemini JSON output: {exc}. Raw snippet: {cleaned[:150]}")

    return None
