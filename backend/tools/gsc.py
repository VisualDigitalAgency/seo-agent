"""
Google Search Console Tool
Handles: rankings, queries, click data, ranking drop detection
All operations are READ-only (uses GSC API with service account)

Features:
- Exponential backoff retry for API calls
- Circuit breaker protection
- Timeout protection (35s per API call)
- Structured error logging
"""

import os
import asyncio
import logging
import random
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Callable

from ._rate_limit_async import get_async_rate_limiter
from ._circuit_breaker import get_circuit_breaker

logger = logging.getLogger("seo-backend")

# Config
DEFAULT_TIMEOUT = 30.0
TOTAL_TIMEOUT = 35.0
MAX_RETRIES = 3


def _get_service():
    """Build GSC service from service account credentials."""
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        creds_path = os.environ.get("GSC_CREDENTIALS_PATH", "")
        if not creds_path or not os.path.exists(creds_path):
            logger.warning("GSC_CREDENTIALS_PATH not set or file not found")
            return None, "GSC_CREDENTIALS_PATH not set or file not found"

        creds = service_account.Credentials.from_service_account_file(
            creds_path,
            scopes=["https://www.googleapis.com/auth/webmasters.readonly"]
        )
        service = build("searchconsole", "v1", credentials=creds, cache_discovery=False)
        return service, None
    except ImportError:
        logger.error("google-api-python-client not installed")
        return None, "google-api-python-client not installed. Run: pip install google-api-python-client google-auth"
    except Exception as e:
        logger.error(f"Failed to initialize GSC service: {str(e)}", exc_info=True)
        return None, str(e)


def _date_range(days: int):
    """Calculate date range for GSC queries."""
    end = datetime.utcnow().date() - timedelta(days=3)  # GSC has ~3 day delay
    start = end - timedelta(days=days)
    return str(start), str(end)


async def _gsc_api_call(service, site_url: str, request_body: dict) -> Dict[str, Any]:
    """
    Low-level GSC API call. May raise exceptions.
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: service.searchanalytics().query(siteUrl=site_url, body=request_body).execute()
    )


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
                await asyncio.sleep(min(delay_with_jitter, 10.0))

            return await func(*args, **kwargs)

        except asyncio.TimeoutError as e:
            last_exception = e
            logger.warning(f"GSC timeout on attempt {attempt + 1}/{MAX_RETRIES}")
            if attempt == MAX_RETRIES - 1:
                raise
        except Exception as e:
            last_exception = e
            logger.warning(f"GSC error on attempt {attempt + 1}/{MAX_RETRIES}: {type(e).__name__}: {str(e)}")
            if attempt == MAX_RETRIES - 1:
                raise

    raise last_exception if last_exception else Exception("All retries exhausted")


async def _execute_gsc_query_with_retry(
    circuit_breaker,
    service,
    site_url: str,
    request_body: dict,
    timeout: float = DEFAULT_TIMEOUT
) -> Dict[str, Any]:
    """
    Execute GSC query with retry, timeout, and circuit breaker.
    """
    async def _execute() -> Dict[str, Any]:
        return await asyncio.wait_for(
            _retry_with_backoff(_gsc_api_call, service, site_url, request_body),
            timeout=timeout
        )

    try:
        if circuit_breaker.can_call():
            return await circuit_breaker.call(_execute)
        else:
            logger.warning("GSC circuit breaker OPEN - skipping query")
            raise Exception("Service temporarily unavailable (circuit breaker open)")
    except Exception as e:
        logger.error(f"GSC query failed: {str(e)}")
        raise


async def get_rankings(site_url: str, page_url: str = "", days: int = 30) -> dict:
    """Get page rankings, impressions, CTR from GSC."""
    rate_limiter = get_async_rate_limiter("gsc")
    circuit_breaker = get_circuit_breaker("gsc")

    async with rate_limiter:
        service, err = _get_service()
        if err:
            return {"error": err, "rows": []}

        try:
            start_date, end_date = _date_range(days)

            request_body = {
                "startDate": start_date,
                "endDate": end_date,
                "dimensions": ["page"],
                "rowLimit": 25,
                "startRow": 0,
            }

            if page_url:
                request_body["dimensionFilterGroups"] = [{
                    "filters": [{"dimension": "page", "operator": "equals", "expression": page_url}]
                }]

            response = await _execute_gsc_query_with_retry(circuit_breaker, service, site_url, request_body)

            rows = [
                {
                    "page": r["keys"][0],
                    "clicks": r.get("clicks", 0),
                    "impressions": r.get("impressions", 0),
                    "ctr": round(r.get("ctr", 0) * 100, 2),
                    "position": round(r.get("position", 0), 1),
                }
                for r in response.get("rows", [])
            ]

            return {
                "site_url": site_url,
                "date_range": {"start": start_date, "end": end_date},
                "rows": rows,
                "count": len(rows),
            }

        except Exception as e:
            return {"error": str(e), "rows": []}


async def get_top_queries(site_url: str, page_url: str = "", days: int = 30, limit: int = 25) -> dict:
    """Get top search queries driving traffic."""
    rate_limiter = get_async_rate_limiter("gsc")
    circuit_breaker = get_circuit_breaker("gsc")

    async with rate_limiter:
        service, err = _get_service()
        if err:
            return {"error": err, "queries": []}

        try:
            start_date, end_date = _date_range(days)

            request_body = {
                "startDate": start_date,
                "endDate": end_date,
                "dimensions": ["query"],
                "rowLimit": limit,
            }

            if page_url:
                request_body["dimensionFilterGroups"] = [{
                    "filters": [{"dimension": "page", "operator": "equals", "expression": page_url}]
                }]

            response = await _execute_gsc_query_with_retry(circuit_breaker, service, site_url, request_body)

            queries = [
                {
                    "query": r["keys"][0],
                    "clicks": r.get("clicks", 0),
                    "impressions": r.get("impressions", 0),
                    "ctr": round(r.get("ctr", 0) * 100, 2),
                    "position": round(r.get("position", 0), 1),
                }
                for r in response.get("rows", [])
            ]

            return {
                "site_url": site_url,
                "page_url": page_url,
                "date_range": {"start": start_date, "end": end_date},
                "queries": queries,
                "count": len(queries),
            }

        except Exception as e:
            return {"error": str(e), "queries": []}


async def detect_ranking_drops(site_url: str, drop_threshold: float = 3.0, days: int = 28) -> dict:
    """Detect pages with significant ranking drops."""
    rate_limiter = get_async_rate_limiter("gsc")
    circuit_breaker = get_circuit_breaker("gsc")

    async with rate_limiter:
        service, err = _get_service()
        if err:
            return {"error": err, "drops": []}

        try:
            cur_end = datetime.utcnow().date() - timedelta(days=3)
            cur_start = cur_end - timedelta(days=days)
            prev_end = cur_start - timedelta(days=1)
            prev_start = prev_end - timedelta(days=days)

            async def fetch_period(start, end):
                body = {
                    "startDate": str(start),
                    "endDate": str(end),
                    "dimensions": ["page"],
                    "rowLimit": 500,
                }
                try:
                    response = await _execute_gsc_query_with_retry(
                        circuit_breaker, service, site_url, body, timeout=DEFAULT_TIMEOUT + 5.0
                    )
                    return {r["keys"][0]: r.get("position", 0) for r in response.get("rows", [])}
                except Exception as e:
                    logger.error(f"GSC period fetch failed for {start}-{end}: {str(e)}")
                    return {}

            # Fetch periods sequentially (could be parallelized but respects rate limits)
            current = await fetch_period(cur_start, cur_end)
            previous = await fetch_period(prev_start, prev_end)

            drops = []
            for page, cur_pos in current.items():
                prev_pos = previous.get(page)
                if prev_pos and (cur_pos - prev_pos) >= drop_threshold:
                    drops.append({
                        "page": page,
                        "current_position": round(cur_pos, 1),
                        "previous_position": round(prev_pos, 1),
                        "drop": round(cur_pos - prev_pos, 1),
                    })

            drops.sort(key=lambda x: x["drop"], reverse=True)

            return {
                "site_url": site_url,
                "current_period": {"start": str(cur_start), "end": str(cur_end)},
                "prev_period": {"start": str(prev_start), "end": str(prev_end)},
                "drop_threshold": drop_threshold,
                "drops": drops,
                "count": len(drops),
            }

        except Exception as e:
            logger.error(f"GSC detect_ranking_drops failed: {str(e)}")
            return {"error": str(e), "drops": []}