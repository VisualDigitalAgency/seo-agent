"""
DataForSEO Tool
Handles: keyword volume, difficulty, suggestions, competitor keywords
All operations are READ-only

Features:
- Exponential backoff retry (3 attempts with jitter)
- Circuit breaker protection
- Timeout protection (35s total)
- Structured error logging
"""

import os
import asyncio
import logging
import random
import base64
from typing import Dict, Any, Optional, List, Callable

import httpx
from ._rate_limit_async import get_async_rate_limiter
from ._circuit_breaker import get_circuit_breaker

logger = logging.getLogger("seo-backend")

DFS_BASE = "https://api.dataforseo.com/v3"

# Config
DEFAULT_TIMEOUT = 30.0
TOTAL_TIMEOUT = 35.0
MAX_RETRIES = 3


def _auth_header() -> Optional[Dict[str, str]]:
    """Build authentication header from credentials."""
    login = os.environ.get("DATAFORSEO_LOGIN", "")
    password = os.environ.get("DATAFORSEO_PASSWORD", "")

    if not login or not password:
        logger.warning("DATAFORSEO credentials not configured")
        return None

    creds = base64.b64encode(f"{login}:{password}".encode()).decode()
    return {
        "Authorization": f"Basic {creds}",
        "Content-Type": "application/json"
    }


async def _dfs_api_call(path: str, payload: list, headers: Dict[str, str]) -> Dict[str, Any]:
    """
    Low-level DataForSEO API call. May raise httpx exceptions.
    """
    rate_limiter = get_async_rate_limiter("dataforseo")

    async with rate_limiter:
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            response = await client.post(
                f"{DFS_BASE}/{path}",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            return response.json()


async def _retry_with_backoff(func: Callable[..., Any], *args, **kwargs) -> Any:
    """Execute a function with exponential backoff retry."""
    last_exception = None

    for attempt in range(MAX_RETRIES):
        try:
            if attempt > 0:
                delay = 2.0 * (2 ** (attempt - 1))
                jitter = delay * 0.2 * (2 * random.random() - 1)  # ±20%
                delay_with_jitter = max(0.5, abs(delay + jitter))
                logger.debug(f"Retry attempt {attempt + 1}/{MAX_RETRIES}, delay: {delay_with_jitter:.2f}s")
                await asyncio.sleep(min(delay_with_jitter, 15.0))

            return await func(*args, **kwargs)

        except asyncio.TimeoutError as e:
            last_exception = e
            logger.warning(f"DataForSEO timeout on attempt {attempt + 1}/{MAX_RETRIES}")
            if attempt == MAX_RETRIES - 1:
                raise
        except httpx.HTTPStatusError as e:
            status = e.response.status_code if hasattr(e, 'response') else 0
            last_exception = e

            if 400 <= status < 500:
                logger.error(f"DataForSEO client error {status}: {str(e)}")
                raise
            elif attempt == MAX_RETRIES - 1:
                logger.error(f"DataForSEO failed after {MAX_RETRIES} attempts, final status: {status}")
                raise
            else:
                logger.warning(f"DataForSEO error {status} on attempt {attempt + 1}/{MAX_RETRIES}")
        except Exception as e:
            last_exception = e
            if attempt == MAX_RETRIES - 1:
                raise
            logger.debug(f"Unexpected error on DataForSEO attempt {attempt + 1}/{MAX_RETRIES}: {str(e)}")

    raise last_exception if last_exception else Exception("All retries exhausted")


async def _post_with_retry(path: str, payload: list) -> Dict[str, Any]:
    """
    DataForSEO POST request with retry, timeout, and circuit breaker.
    """
    headers = _auth_header()
    if not headers:
        return {"error": "DATAFORSEO_LOGIN / DATAFORSEO_PASSWORD not set", "data": []}

    circuit_breaker = get_circuit_breaker("dataforseo")

    async def _execute() -> Dict[str, Any]:
        return await asyncio.wait_for(
            _retry_with_backoff(_dfs_api_call, path, payload, headers),
            timeout=TOTAL_TIMEOUT
        )

    try:
        if circuit_breaker.can_call():
            return await circuit_breaker.call(_execute)
        else:
            logger.warning("DataForSEO circuit breaker OPEN - skipping call")
            return {"error": "Service temporarily unavailable (circuit breaker open)", "data": []}
    except Exception as e:
        logger.error(f"DataForSEO call failed: {str(e)}")
        return {"error": str(e), "data": []}


async def get_keyword_volume(keywords: List[str], location_code: int = 2840) -> dict:
    """Monthly search volume for keywords."""
    payload = [{
        "keywords": keywords[:100],
        "location_code": location_code,
        "language_code": "en",
    }]

    data = await _post_with_retry("keywords_data/google_ads/search_volume/live", payload)

    if "error" in data:
        return {"keywords": [], "count": 0, "location_code": location_code, "error": data["error"]}

    results = []
    for task in data.get("tasks", []):
        for item in (task.get("result") or []):
            results.append({
                "keyword": item.get("keyword"),
                "search_volume": item.get("search_volume"),
                "competition": item.get("competition"),
                "cpc": item.get("cpc"),
                "monthly_searches": item.get("monthly_searches", []),
            })

    return {"keywords": results, "count": len(results), "location_code": location_code}


async def get_keyword_difficulty(keywords: List[str]) -> dict:
    """Keyword difficulty score 0-100."""
    payload = [{
        "keywords": keywords[:1000],
        "location_code": 2840,
        "language_code": "en",
    }]

    data = await _post_with_retry("dataforseo_labs/google/keyword_difficulty/live", payload)

    if "error" in data:
        return {"keywords": [], "count": 0, "error": data["error"]}

    results = []
    for task in data.get("tasks", []):
        for item in (task.get("result") or []):
            results.append({
                "keyword": item.get("keyword"),
                "difficulty": item.get("keyword_difficulty"),
            })

    return {"keywords": results, "count": len(results)}


async def get_keyword_suggestions(keyword: str, limit: int = 20) -> dict:
    """Get related keyword suggestions."""
    payload = [{
        "keyword": keyword,
        "location_code": 2840,
        "language_code": "en",
        "limit": limit,
    }]

    data = await _post_with_retry("dataforseo_labs/google/related_keywords/live", payload)

    if "error" in data:
        return {"seed": keyword, "suggestions": [], "count": 0, "error": data["error"]}

    suggestions = []
    for task in data.get("tasks", []):
        for item in (task.get("result") or []):
            for kw_item in item.get("items", []):
                kw_data = kw_item.get("keyword_data", {})
                suggestions.append({
                    "keyword": kw_data.get("keyword"),
                    "search_volume": kw_data.get("keyword_info", {}).get("search_volume"),
                    "difficulty": kw_data.get("keyword_properties", {}).get("keyword_difficulty"),
                    "cpc": kw_data.get("keyword_info", {}).get("cpc"),
                })

    return {"seed": keyword, "suggestions": suggestions[:limit], "count": len(suggestions[:limit])}


async def get_competitor_keywords(domain: str, limit: int = 50) -> dict:
    """Get keywords a competitor ranks for in top 10."""
    payload = [{
        "target": domain.replace("https://", "").replace("http://", "").rstrip("/"),
        "location_code": 2840,
        "language_code": "en",
        "limit": limit,
        "filters": [["ranked_serp_element.serp_item.rank_group", "<=", 10]],
    }]

    data = await _post_with_retry("dataforseo_labs/google/ranked_keywords/live", payload)

    if "error" in data:
        return {"domain": domain, "keywords": [], "count": 0, "error": data["error"]}

    keywords = []
    for task in data.get("tasks", []):
        for item in (task.get("result") or []):
            for kw_item in item.get("items", []):
                kw_data = kw_item.get("keyword_data", {})
                keywords.append({
                    "keyword": kw_data.get("keyword"),
                    "position": kw_item.get("ranked_serp_element", {}).get("serp_item", {}).get("rank_absolute"),
                    "volume": kw_data.get("keyword_info", {}).get("search_volume"),
                    "difficulty": kw_data.get("keyword_properties", {}).get("keyword_difficulty"),
                })

    return {"domain": domain, "keywords": keywords[:limit], "count": len(keywords[:limit])}
