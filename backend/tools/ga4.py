"""
Google Analytics 4 Tool
Handles: page traffic, top pages, traffic drop detection
All operations are READ-only (uses GA4 Data API with service account)

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


def _get_client():
    """Build GA4 client from service account credentials."""
    try:
        from google.analytics.data_v1beta import BetaAnalyticsDataClient
        from google.oauth2 import service_account

        creds_path = os.environ.get("GA4_CREDENTIALS_PATH", "")
        if not creds_path or not os.path.exists(creds_path):
            logger.warning("GA4_CREDENTIALS_PATH not set or file not found")
            return None, None, "GA4_CREDENTIALS_PATH not set or file not found"

        property_id = os.environ.get("GA4_PROPERTY_ID", "")
        if not property_id:
            logger.warning("GA4_PROPERTY_ID not set")
            return None, None, "GA4_PROPERTY_ID not set (format: properties/123456789)"

        creds = service_account.Credentials.from_service_account_file(
            creds_path,
            scopes=["https://www.googleapis.com/auth/analytics.readonly"]
        )
        client = BetaAnalyticsDataClient(credentials=creds)
        return client, property_id, None
    except ImportError:
        logger.error("google-analytics-data not installed")
        return None, None, "google-analytics-data not installed. Run: pip install google-analytics-data"
    except Exception as e:
        logger.error(f"Failed to initialize GA4 client: {str(e)}", exc_info=True)
        return None, None, str(e)


def _run_report(client, property_id: str, dimensions: list, metrics: list,
                date_ranges: list, dimension_filter=None, limit: int = 20) -> list:
    """Run a GA4 report."""
    from google.analytics.data_v1beta.types import (
        RunReportRequest, Dimension, Metric, DateRange, FilterExpression,
        Filter, DimensionFilter
    )

    request = RunReportRequest(
        property=property_id,
        dimensions=[Dimension(name=d) for d in dimensions],
        metrics=[Metric(name=m) for m in metrics],
        date_ranges=[DateRange(**dr) for dr in date_ranges],
        limit=limit,
    )

    if dimension_filter:
        request.dimension_filter = dimension_filter

    try:
        response = client.run_report(request)
        return _parse_ga4_response(response)
    except Exception as e:
        logger.error(f"GA4 report execution failed: {str(e)}", exc_info=True)
        raise


def _parse_ga4_response(response) -> list:
    """Parse GA4 response into list of dicts."""
    dim_headers = [h.name for h in response.dimension_headers]
    met_headers = [h.name for h in response.metric_headers]

    rows = []
    for row in response.rows:
        r = {}
        for i, dim in enumerate(row.dimension_values):
            r[dim_headers[i]] = dim.value
        for i, met in enumerate(row.metric_values):
            r[met_headers[i]] = met.value
        rows.append(r)
    return rows


async def _ga4_api_call(
    client,
    property_id: str,
    dimensions: list,
    metrics: list,
    date_ranges: list,
    dimension_filter=None,
    limit: int = 20
) -> list:
    """
    Low-level GA4 API call. May raise exceptions.
    """
    return _run_report(client, property_id, dimensions, metrics, date_ranges, dimension_filter, limit)


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
            logger.warning(f"GA4 timeout on attempt {attempt + 1}/{MAX_RETRIES}")
            if attempt == MAX_RETRIES - 1:
                raise
        except Exception as e:
            last_exception = e
            logger.warning(f"GA4 error on attempt {attempt + 1}/{MAX_RETRIES}: {type(e).__name__}: {str(e)}")
            if attempt == MAX_RETRIES - 1:
                raise

    raise last_exception if last_exception else Exception("All retries exhausted")


async def _execute_ga4_query_with_retry(
    circuit_breaker,
    client,
    property_id: str,
    dimensions: list,
    metrics: list,
    date_ranges: list,
    dimension_filter=None,
    limit: int = 20,
    timeout: float = DEFAULT_TIMEOUT
) -> list:
    """
    Execute GA4 query with retry, timeout, and circuit breaker.
    """
    async def _execute() -> list:
        return await asyncio.wait_for(
            _retry_with_backoff(_ga4_api_call, client, property_id, dimensions, metrics, date_ranges, dimension_filter, limit),
            timeout=timeout
        )

    try:
        if circuit_breaker.can_call():
            return await circuit_breaker.call(_execute)
        else:
            logger.warning("GA4 circuit breaker OPEN - skipping query")
            raise Exception("Service temporarily unavailable (circuit breaker open)")
    except Exception as e:
        logger.error(f"GA4 query failed: {str(e)}")
        raise


async def get_page_traffic(page_path: str, days: int = 30) -> dict:
    """Get sessions, users, bounce rate for a specific page."""
    rate_limiter = get_async_rate_limiter("ga4")
    circuit_breaker = get_circuit_breaker("ga4")

    async with rate_limiter:
        client, property_id, err = _get_client()
        if err:
            return {"error": err}

        try:
            from google.analytics.data_v1beta.types import (
                FilterExpression, Filter, DimensionFilter
            )

            end_date = datetime.utcnow().date()
            start_date = end_date - timedelta(days=days)

            dim_filter = FilterExpression(
                filter=Filter(
                    field_name="pagePath",
                    string_filter=Filter.StringFilter(
                        value=page_path,
                        match_type=Filter.StringFilter.MatchType.EXACT
                    )
                )
            )

            rows = await _execute_ga4_query_with_retry(
                circuit_breaker, client, property_id,
                dimensions=["pagePath", "pageTitle"],
                metrics=["sessions", "totalUsers", "bounceRate", "averageSessionDuration", "screenPageViews"],
                date_ranges=[{"start_date": str(start_date), "end_date": str(end_date)}],
                dimension_filter=dim_filter,
                limit=1,
                timeout=DEFAULT_TIMEOUT + 5.0
            )

            if not rows:
                return {
                    "page_path": page_path,
                    "days": days,
                    "data": None,
                    "message": "No data found"
                }

            row = rows[0]
            return {
                "page_path": page_path,
                "days": days,
                "sessions": int(row.get("sessions", 0)),
                "users": int(row.get("totalUsers", 0)),
                "page_views": int(row.get("screenPageViews", 0)),
                "bounce_rate": round(float(row.get("bounceRate", 0)) * 100, 2),
                "avg_session_duration": round(float(row.get("averageSessionDuration", 0)), 1),
            }

        except Exception as e:
            logger.error(f"GA4 get_page_traffic failed: {str(e)}")
            return {"error": str(e)}


async def get_top_pages(days: int = 30, limit: int = 20) -> dict:
    """Get top pages by sessions."""
    rate_limiter = get_async_rate_limiter("ga4")
    circuit_breaker = get_circuit_breaker("ga4")

    async with rate_limiter:
        client, property_id, err = _get_client()
        if err:
            return {"error": err, "pages": []}

        try:
            end_date = datetime.utcnow().date()
            start_date = end_date - timedelta(days=days)

            rows = await _execute_ga4_query_with_retry(
                circuit_breaker, client, property_id,
                dimensions=["pagePath", "pageTitle"],
                metrics=["sessions", "totalUsers", "bounceRate", "screenPageViews"],
                date_ranges=[{"start_date": str(start_date), "end_date": str(end_date)}],
                limit=limit,
                timeout=DEFAULT_TIMEOUT + 5.0
            )

            pages = [
                {
                    "page_path": r.get("pagePath"),
                    "page_title": r.get("pageTitle"),
                    "sessions": int(r.get("sessions", 0)),
                    "users": int(r.get("totalUsers", 0)),
                    "page_views": int(r.get("screenPageViews", 0)),
                    "bounce_rate": round(float(r.get("bounceRate", 0)) * 100, 2),
                }
                for r in rows
            ]

            return {"days": days, "pages": pages, "count": len(pages)}

        except Exception as e:
            logger.error(f"GA4 get_top_pages failed: {str(e)}")
            return {"error": str(e), "pages": []}


async def detect_traffic_drops(days: int = 30, drop_pct_threshold: float = 20.0) -> dict:
    """Detect pages with significant traffic drops."""
    rate_limiter = get_async_rate_limiter("ga4")
    circuit_breaker = get_circuit_breaker("ga4")

    async with rate_limiter:
        client, property_id, err = _get_client()
        if err:
            return {"error": err, "drops": []}

        try:
            end_date = datetime.utcnow().date()
            cur_start = end_date - timedelta(days=days)
            prev_start = cur_start - timedelta(days=days)
            prev_end = cur_start - timedelta(days=1)

            rows = await _execute_ga4_query_with_retry(
                circuit_breaker, client, property_id,
                dimensions=["pagePath"],
                metrics=["sessions"],
                date_ranges=[
                    {"start_date": str(cur_start), "end_date": str(end_date)},
                    {"start_date": str(prev_start), "end_date": str(prev_end)},
                ],
                limit=200,
                timeout=DEFAULT_TIMEOUT + 10.0
            )

            drops = []
            for row in rows:
                cur_sessions = int(row.get("sessions", 0))
                prev_sessions = int(row.get("sessions.1", 0))  # second date range
                if prev_sessions > 0 and cur_sessions < prev_sessions:
                    pct_drop = round(((prev_sessions - cur_sessions) / prev_sessions) * 100, 1)
                    if pct_drop >= drop_pct_threshold:
                        drops.append({
                            "page_path": row.get("pagePath"),
                            "current_sessions": cur_sessions,
                            "prev_sessions": prev_sessions,
                            "drop_pct": pct_drop,
                        })

            drops.sort(key=lambda x: x["drop_pct"], reverse=True)

            return {
                "current_period": {"start": str(cur_start), "end": str(end_date)},
                "prev_period": {"start": str(prev_start), "end": str(prev_end)},
                "threshold_pct": drop_pct_threshold,
                "drops": drops,
                "count": len(drops),
            }

        except Exception as e:
            logger.error(f"GA4 detect_traffic_drops failed: {str(e)}")
            return {"error": str(e), "drops": []}