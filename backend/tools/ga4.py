"""
Google Analytics 4 Tool
Handles: page traffic, top pages, traffic drop detection
All operations are READ-only (uses GA4 Data API with service account)
"""

import os
from datetime import datetime, timedelta
from typing import Optional


def _get_client():
    """Build GA4 client from service account credentials"""
    try:
        from google.analytics.data_v1beta import BetaAnalyticsDataClient
        from google.oauth2 import service_account

        creds_path = os.environ.get("GA4_CREDENTIALS_PATH", "")
        if not creds_path or not os.path.exists(creds_path):
            return None, None, "GA4_CREDENTIALS_PATH not set or file not found"

        property_id = os.environ.get("GA4_PROPERTY_ID", "")
        if not property_id:
            return None, None, "GA4_PROPERTY_ID not set (format: properties/123456789)"

        creds  = service_account.Credentials.from_service_account_file(
            creds_path,
            scopes=["https://www.googleapis.com/auth/analytics.readonly"]
            # .readonly scope enforced at OAuth level
        )
        client = BetaAnalyticsDataClient(credentials=creds)
        return client, property_id, None

    except ImportError:
        return None, None, "google-analytics-data not installed. Run: pip install google-analytics-data"
    except Exception as e:
        return None, None, str(e)


def _run_report(client, property_id: str, dimensions: list, metrics: list,
                date_ranges: list, dimension_filter=None, limit: int = 20) -> list:
    """Run a GA4 report and return rows as list of dicts"""
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

    response = client.run_report(request)

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


async def get_page_traffic(page_path: str, days: int = 30) -> dict:
    """Sessions, users, bounce rate for a specific page"""
    client, property_id, err = _get_client()
    if err:
        return {"error": err}

    try:
        from google.analytics.data_v1beta.types import (
            FilterExpression, Filter, DimensionFilter
        )

        end_date   = datetime.utcnow().date()
        start_date = end_date - timedelta(days=days)

        dim_filter = FilterExpression(
            filter=Filter(
                field_name="pagePath",
                string_filter=Filter.StringFilter(value=page_path, match_type=Filter.StringFilter.MatchType.EXACT)
            )
        )

        rows = _run_report(
            client, property_id,
            dimensions=["pagePath", "pageTitle"],
            metrics=["sessions", "totalUsers", "bounceRate", "averageSessionDuration", "screenPageViews"],
            date_ranges=[{"start_date": str(start_date), "end_date": str(end_date)}],
            dimension_filter=dim_filter,
            limit=1,
        )

        if not rows:
            return {"page_path": page_path, "days": days, "data": None, "message": "No data found"}

        row = rows[0]
        return {
            "page_path":          page_path,
            "days":               days,
            "sessions":           int(row.get("sessions", 0)),
            "users":              int(row.get("totalUsers", 0)),
            "page_views":         int(row.get("screenPageViews", 0)),
            "bounce_rate":        round(float(row.get("bounceRate", 0)) * 100, 2),
            "avg_session_duration": round(float(row.get("averageSessionDuration", 0)), 1),
        }
    except Exception as e:
        return {"error": str(e)}


async def get_top_pages(days: int = 30, limit: int = 20) -> dict:
    """Top pages by sessions"""
    client, property_id, err = _get_client()
    if err:
        return {"error": err, "pages": []}

    try:
        end_date   = datetime.utcnow().date()
        start_date = end_date - timedelta(days=days)

        rows = _run_report(
            client, property_id,
            dimensions=["pagePath", "pageTitle"],
            metrics=["sessions", "totalUsers", "bounceRate", "screenPageViews"],
            date_ranges=[{"start_date": str(start_date), "end_date": str(end_date)}],
            limit=limit,
        )

        pages = [
            {
                "page_path":   r.get("pagePath"),
                "page_title":  r.get("pageTitle"),
                "sessions":    int(r.get("sessions", 0)),
                "users":       int(r.get("totalUsers", 0)),
                "page_views":  int(r.get("screenPageViews", 0)),
                "bounce_rate": round(float(r.get("bounceRate", 0)) * 100, 2),
            }
            for r in rows
        ]

        return {"days": days, "pages": pages, "count": len(pages)}
    except Exception as e:
        return {"error": str(e), "pages": []}


async def detect_traffic_drops(days: int = 30, drop_pct_threshold: float = 20.0) -> dict:
    """
    Compare sessions current period vs previous period.
    Flags pages where sessions dropped by more than drop_pct_threshold %.
    """
    client, property_id, err = _get_client()
    if err:
        return {"error": err, "drops": []}

    try:
        end_date    = datetime.utcnow().date()
        cur_start   = end_date - timedelta(days=days)
        prev_start  = cur_start - timedelta(days=days)
        prev_end    = cur_start - timedelta(days=1)

        rows = _run_report(
            client, property_id,
            dimensions=["pagePath"],
            metrics=["sessions"],
            date_ranges=[
                {"start_date": str(cur_start),  "end_date": str(end_date)},
                {"start_date": str(prev_start), "end_date": str(prev_end)},
            ],
            limit=200,
        )

        # GA4 returns dateRange0 and dateRange1 columns for comparison
        drops = []
        for row in rows:
            cur_sessions  = int(row.get("sessions",          0))
            prev_sessions = int(row.get("sessions.1",        0))  # second date range
            if prev_sessions > 0 and cur_sessions < prev_sessions:
                pct_drop = round(((prev_sessions - cur_sessions) / prev_sessions) * 100, 1)
                if pct_drop >= drop_pct_threshold:
                    drops.append({
                        "page_path":       row.get("pagePath"),
                        "current_sessions": cur_sessions,
                        "prev_sessions":    prev_sessions,
                        "drop_pct":         pct_drop,
                    })

        drops.sort(key=lambda x: x["drop_pct"], reverse=True)

        return {
            "current_period": {"start": str(cur_start),  "end": str(end_date)},
            "prev_period":    {"start": str(prev_start), "end": str(prev_end)},
            "threshold_pct":  drop_pct_threshold,
            "drops":          drops,
            "count":          len(drops),
        }
    except Exception as e:
        return {"error": str(e), "drops": []}
