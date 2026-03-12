"""
Google Search Console Tool
Handles: rankings, queries, click data, ranking drop detection
All operations are READ-only (uses GSC API with service account)
"""

import os
import json
from datetime import datetime, timedelta
from typing import Optional


def _get_service():
    """Build GSC service from service account credentials file"""
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        creds_path = os.environ.get("GSC_CREDENTIALS_PATH", "")
        if not creds_path or not os.path.exists(creds_path):
            return None, "GSC_CREDENTIALS_PATH not set or file not found"

        creds = service_account.Credentials.from_service_account_file(
            creds_path,
            scopes=["https://www.googleapis.com/auth/webmasters.readonly"]
            # Note: .readonly scope — LLM gets read-only access at the OAuth level too
        )
        service = build("searchconsole", "v1", credentials=creds, cache_discovery=False)
        return service, None
    except ImportError:
        return None, "google-api-python-client not installed. Run: pip install google-api-python-client google-auth"
    except Exception as e:
        return None, str(e)


def _date_range(days: int):
    end   = datetime.utcnow().date() - timedelta(days=3)  # GSC has ~3 day delay
    start = end - timedelta(days=days)
    return str(start), str(end)


async def get_rankings(site_url: str, page_url: str = "", days: int = 30) -> dict:
    """Page rankings, impressions, CTR from GSC"""
    service, err = _get_service()
    if err:
        return {"error": err, "rows": []}

    start_date, end_date = _date_range(days)

    request_body = {
        "startDate":  start_date,
        "endDate":    end_date,
        "dimensions": ["page"],
        "rowLimit":   25,
        "startRow":   0,
    }

    if page_url:
        request_body["dimensionFilterGroups"] = [{
            "filters": [{"dimension": "page", "operator": "equals", "expression": page_url}]
        }]

    try:
        response = service.searchanalytics().query(siteUrl=site_url, body=request_body).execute()
        rows = [
            {
                "page":        r["keys"][0],
                "clicks":      r.get("clicks", 0),
                "impressions": r.get("impressions", 0),
                "ctr":         round(r.get("ctr", 0) * 100, 2),
                "position":    round(r.get("position", 0), 1),
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
    """Top search queries driving traffic"""
    service, err = _get_service()
    if err:
        return {"error": err, "queries": []}

    start_date, end_date = _date_range(days)

    request_body = {
        "startDate":  start_date,
        "endDate":    end_date,
        "dimensions": ["query"],
        "rowLimit":   limit,
    }

    if page_url:
        request_body["dimensionFilterGroups"] = [{
            "filters": [{"dimension": "page", "operator": "equals", "expression": page_url}]
        }]

    try:
        response = service.searchanalytics().query(siteUrl=site_url, body=request_body).execute()
        queries = [
            {
                "query":       r["keys"][0],
                "clicks":      r.get("clicks", 0),
                "impressions": r.get("impressions", 0),
                "ctr":         round(r.get("ctr", 0) * 100, 2),
                "position":    round(r.get("position", 0), 1),
            }
            for r in response.get("rows", [])
        ]
        return {
            "site_url":   site_url,
            "page_url":   page_url,
            "date_range": {"start": start_date, "end": end_date},
            "queries":    queries,
            "count":      len(queries),
        }
    except Exception as e:
        return {"error": str(e), "queries": []}


async def detect_ranking_drops(site_url: str, drop_threshold: float = 3.0, days: int = 28) -> dict:
    """
    Compare average position current period vs previous period.
    Flags pages where position dropped by more than drop_threshold.
    """
    service, err = _get_service()
    if err:
        return {"error": err, "drops": []}

    # Current period
    cur_end   = datetime.utcnow().date() - timedelta(days=3)
    cur_start = cur_end - timedelta(days=days)

    # Previous period (same length, before current)
    prev_end   = cur_start - timedelta(days=1)
    prev_start = prev_end - timedelta(days=days)

    def fetch_period(start, end):
        try:
            body = {
                "startDate":  str(start),
                "endDate":    str(end),
                "dimensions": ["page"],
                "rowLimit":   500,
            }
            resp = service.searchanalytics().query(siteUrl=site_url, body=body).execute()
            return {r["keys"][0]: r.get("position", 0) for r in resp.get("rows", [])}
        except Exception:
            return {}

    current  = fetch_period(cur_start, cur_end)
    previous = fetch_period(prev_start, prev_end)

    drops = []
    for page, cur_pos in current.items():
        prev_pos = previous.get(page)
        if prev_pos and (cur_pos - prev_pos) >= drop_threshold:
            drops.append({
                "page":              page,
                "current_position":  round(cur_pos, 1),
                "previous_position": round(prev_pos, 1),
                "drop":              round(cur_pos - prev_pos, 1),
            })

    drops.sort(key=lambda x: x["drop"], reverse=True)

    return {
        "site_url":       site_url,
        "current_period": {"start": str(cur_start), "end": str(cur_end)},
        "prev_period":    {"start": str(prev_start), "end": str(prev_end)},
        "drop_threshold": drop_threshold,
        "drops":          drops,
        "count":          len(drops),
    }
