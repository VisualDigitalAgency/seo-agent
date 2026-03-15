"""
Serper + SerpAPI Tool
Primary: Serper.dev (faster, cheaper)
Fallback: SerpAPI (if SERPER_API_KEY not set but SERPAPI_KEY is)

Features:
- Exponential backoff retry (3 attempts with jitter)
- Circuit breaker protection per provider
- Timeout protection (25s total)
- Structured error logging
"""

import os
import asyncio
import logging
import random
from typing import Dict, Any, Optional, List, Callable

import httpx
from ._rate_limit_async import get_async_rate_limiter
from ._circuit_breaker import get_circuit_breaker
from ._cache import get_cache, cached

logger = logging.getLogger("seo-backend")


# Timeouts
DEFAULT_TIMEOUT = 20.0  # HTTP request timeout
TOTAL_TIMEOUT = 25.0     # Total call timeout including retries
MAX_RETRIES = 3


async def _serper_api_call(endpoint: str, payload: dict, api_key: str) -> Dict[str, Any]:
    """
    Low-level Serper API call with timeout.
    May raise httpx exceptions.
    """
    rate_limiter = get_async_rate_limiter("serper")

    async with rate_limiter:
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            response = await client.post(
                f"https://google.serper.dev/{endpoint}",
                headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
                json=payload
            )
            response.raise_for_status()
            return response.json()


async def _serpapi_api_call(params: dict, api_key: str) -> Dict[str, Any]:
    """
    Low-level SerpAPI call with timeout.
    May raise httpx exceptions.
    """
    rate_limiter = get_async_rate_limiter("serper")  # Shared rate limits

    async with rate_limiter:
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            response = await client.get(
                "https://serpapi.com/search",
                params={**params, "api_key": api_key, "output": "json"}
            )
            response.raise_for_status()
            return response.json()


async def _retry_with_backoff(func: Callable[..., Any], *args, **kwargs) -> Any:
    """Execute a function with exponential backoff retry."""
    last_exception = None

    for attempt in range(MAX_RETRIES):
        try:
            if attempt > 0:
                # Exponential backoff with jitter: base * 2^(attempt-1)
                delay = 1.0 * (2 ** (attempt - 1))
                jitter = delay * 0.2 * (2 * random.random() - 1)  # ±20%
                delay_with_jitter = max(0.5, abs(delay + jitter))
                logger.debug(f"Retry attempt {attempt + 1}/{MAX_RETRIES}, delay: {delay_with_jitter}s")
                await asyncio.sleep(min(delay_with_jitter, 10.0))

            return await func(*args, **kwargs)

        except asyncio.TimeoutError as e:
            last_exception = e
            logger.warning(f"API timeout on attempt {attempt + 1}/{MAX_RETRIES}")
            if attempt == MAX_RETRIES - 1:
                raise
        except httpx.HTTPStatusError as e:
            status = e.response.status_code if hasattr(e, 'response') else 0
            last_exception = e

            # Don't retry client errors (4xx except 429 Too Many Requests)
            if 400 <= status < 500 and status != 429:
                logger.error(f"API client error {status}: {str(e)}")
                raise
            elif attempt == MAX_RETRIES - 1:
                logger.error(f"API call failed after {MAX_RETRIES} attempts, final status: {status}")
                raise
            else:
                logger.warning(f"API error {status} on attempt {attempt + 1}/{MAX_RETRIES}")
        except Exception as e:
            last_exception = e
            if attempt == MAX_RETRIES - 1:
                raise
            logger.debug(f"Unexpected error on attempt {attempt + 1}/{MAX_RETRIES}: {str(e)}")

    raise last_exception if last_exception else Exception("All retries exhausted")


async def _serper_with_retry(endpoint: str, payload: dict) -> Optional[Dict[str, Any]]:
    """Serper API call with retry and timeout."""
    api_key = os.environ.get("SERPER_API_KEY", "")
    if not api_key:
        logger.debug("SERPER_API_KEY not set")
        return None

    circuit_breaker = get_circuit_breaker("serper")

    async def _execute() -> Dict[str, Any]:
        return await asyncio.wait_for(
            _retry_with_backoff(_serper_api_call, endpoint, payload, api_key),
            timeout=TOTAL_TIMEOUT
        )

    try:
        if circuit_breaker.can_call():
            return await circuit_breaker.call(_execute)
        else:
            logger.warning("Serper circuit breaker OPEN - skipping call")
            return None
    except Exception as e:
        logger.error(f"Serper API call failed: {str(e)}")
        return None


async def _serpapi_with_retry(params: dict) -> Optional[Dict[str, Any]]:
    """SerpAPI call with retry and timeout."""
    api_key = os.environ.get("SERPAPI_KEY", "")
    if not api_key:
        logger.debug("SERPAPI_KEY not set")
        return None

    circuit_breaker = get_circuit_breaker("serper")  # Same provider, same circuit

    async def _execute() -> Dict[str, Any]:
        return await asyncio.wait_for(
            _retry_with_backoff(_serpapi_api_call, params, api_key),
            timeout=TOTAL_TIMEOUT
        )

    try:
        if circuit_breaker.can_call():
            return await circuit_breaker.call(_execute)
        else:
            logger.warning("SerpAPI circuit breaker OPEN - skipping call")
            return None
    except Exception as e:
        logger.error(f"SerpAPI call failed: {str(e)}")
        return None


def _build_no_key_error() -> Dict[str, Any]:
    """Return structured error when no API keys configured."""
    return {
        "error": "Neither SERPER_API_KEY nor SERPAPI_KEY is set",
        "organic": [],
        "featured_snippet": None,
        "people_also_ask": [],
        "related_searches": [],
    }


@cached("search_serp", ttl=300)  # 5 minute cache
async def search_serp(query: str, num: int = 10, country: str = "us") -> Dict[str, Any]:
    """
    Google organic SERP search - Serper primary, SerpAPI fallback.

    Args:
        query: Search query
        num: Number of results (max 20 for Serper)
        country: Country code (gl parameter)

    Returns:
        Structured SERP results
    """
    # Try Serper first
    data = await _serper_with_retry("search", {"q": query, "num": min(num, 20), "gl": country})
    if data:
        try:
            organic = [
                {
                    "position": r.get("position"),
                    "title": r.get("title"),
                    "link": r.get("link"),
                    "snippet": r.get("snippet"),
                    "displayed_link": r.get("displayedLink")
                }
                for r in data.get("organic", [])
            ]
            return {
                "query": query,
                "source": "serper",
                "organic": organic,
                "featured_snippet": data.get("answerBox"),
                "people_also_ask": [q.get("question") for q in data.get("peopleAlsoAsk", [])],
                "related_searches": [r.get("query") for r in data.get("relatedSearches", [])],
            }
        except Exception as e:
            logger.error(f"Failed to parse Serper response: {str(e)}")
            # Continue to fallback

    # SerpAPI fallback
    data = await _serpapi_with_retry({"q": query, "num": num, "gl": country, "engine": "google"})
    if data:
        try:
            organic = [
                {
                    "position": r.get("position"),
                    "title": r.get("title"),
                    "link": r.get("link"),
                    "snippet": r.get("snippet")
                }
                for r in data.get("organic_results", [])
            ]
            return {
                "query": query,
                "source": "serpapi",
                "organic": organic,
                "featured_snippet": data.get("answer_box"),
                "people_also_ask": [q.get("question") for q in data.get("related_questions", [])],
                "related_searches": [r.get("query") for r in data.get("related_searches", [])],
            }
        except Exception as e:
            logger.error(f"Failed to parse SerpAPI response: {str(e)}")

    # Both failed or no API keys
    return _build_no_key_error()


async def search_web(query: str) -> Dict[str, Any]:
    """Simple web search wrapper."""
    return await search_serp(query=query, num=10)


async def search_news(query: str) -> Dict[str, Any]:
    """News search - Serper primary, SerpAPI fallback."""
    data = await _serper_with_retry("news", {"q": query, "num": 10})
    if data:
        try:
            return {
                "query": query,
                "source": "serper",
                "news": [
                    {
                        "title": r.get("title"),
                        "link": r.get("link"),
                        "snippet": r.get("snippet"),
                        "date": r.get("date"),
                        "source": r.get("source")
                    }
                    for r in data.get("news", [])
                ]
            }
        except Exception as e:
            logger.error(f"Failed to parse Serper news response: {str(e)}")

    data = await _serpapi_with_retry({"q": query, "engine": "google_news", "num": 10})
    if data:
        try:
            return {
                "query": query,
                "source": "serpapi",
                "news": [
                    {
                        "title": r.get("title"),
                        "link": r.get("link"),
                        "snippet": r.get("snippet")
                    }
                    for r in data.get("news_results", [])
                ]
            }
        except Exception as e:
            logger.error(f"Failed to parse SerpAPI news response: {str(e)}")

    return _build_no_key_error()


async def get_related_questions(query: str) -> Dict[str, Any]:
    """Get related questions (People Also Ask)."""
    data = await _serper_with_retry("search", {"q": query, "num": 10})
    if data:
        try:
            paa = [
                {
                    "question": item.get("question"),
                    "snippet": item.get("snippet"),
                    "link": item.get("link")
                }
                for item in data.get("peopleAlsoAsk", [])
            ]
            return {"query": query, "questions": paa, "count": len(paa)}
        except Exception as e:
            logger.error(f"Failed to parse Serper PAA response: {str(e)}")

    data = await _serpapi_with_retry({"q": query, "engine": "google"})
    if data:
        try:
            paa = [
                {
                    "question": q.get("question"),
                    "snippet": q.get("snippet"),
                    "link": q.get("link")
                }
                for q in data.get("related_questions", [])
            ]
            return {"query": query, "questions": paa, "count": len(paa)}
        except Exception as e:
            logger.error(f"Failed to parse SerpAPI PAA response: {str(e)}")

    return _build_no_key_error()
