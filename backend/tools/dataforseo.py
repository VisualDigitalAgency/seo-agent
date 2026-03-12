"""
DataForSEO Tool
Handles: keyword volume, difficulty, suggestions, competitor keywords
All operations are READ-only
"""

import os
import httpx
import base64
from typing import List


DFS_BASE = "https://api.dataforseo.com/v3"


def _auth_header() -> dict:
    login    = os.environ.get("DATAFORSEO_LOGIN", "")
    password = os.environ.get("DATAFORSEO_PASSWORD", "")
    if not login or not password:
        return {}
    creds = base64.b64encode(f"{login}:{password}".encode()).decode()
    return {"Authorization": f"Basic {creds}", "Content-Type": "application/json"}


async def _post(path: str, payload: list) -> dict:
    headers = _auth_header()
    if not headers:
        return {"error": "DATAFORSEO_LOGIN / DATAFORSEO_PASSWORD not set", "data": []}

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            f"{DFS_BASE}/{path}",
            headers=headers,
            json=payload,
        )
        response.raise_for_status()
        return response.json()


async def get_keyword_volume(keywords: List[str], location_code: int = 2840) -> dict:
    """
    Monthly search volume for keywords.
    location_code: 2840=US, 2826=UK, 2036=AU, 2124=CA
    """
    payload = [{
        "keywords":      keywords[:100],  # DataForSEO max per request
        "location_code": location_code,
        "language_code": "en",
    }]

    data = await _post("keywords_data/google_ads/search_volume/live", payload)

    results = []
    for task in data.get("tasks", []):
        for item in (task.get("result") or []):
            results.append({
                "keyword":        item.get("keyword"),
                "search_volume":  item.get("search_volume"),
                "competition":    item.get("competition"),
                "cpc":            item.get("cpc"),
                "monthly_searches": item.get("monthly_searches", []),
            })

    return {"keywords": results, "count": len(results), "location_code": location_code}


async def get_keyword_difficulty(keywords: List[str]) -> dict:
    """
    Keyword difficulty score 0-100 for each keyword.
    Higher = harder to rank for.
    """
    payload = [{
        "keywords":      keywords[:1000],
        "location_code": 2840,
        "language_code": "en",
    }]

    data = await _post("dataforseo_labs/google/keyword_difficulty/live", payload)

    results = []
    for task in data.get("tasks", []):
        for item in (task.get("result") or []):
            results.append({
                "keyword":    item.get("keyword"),
                "difficulty": item.get("keyword_difficulty"),
            })

    return {"keywords": results, "count": len(results)}


async def get_keyword_suggestions(keyword: str, limit: int = 20) -> dict:
    """Related keyword suggestions for a seed keyword"""
    payload = [{
        "keyword":       keyword,
        "location_code": 2840,
        "language_code": "en",
        "limit":         limit,
    }]

    data = await _post("dataforseo_labs/google/related_keywords/live", payload)

    suggestions = []
    for task in data.get("tasks", []):
        for item in (task.get("result") or []):
            for kw_item in item.get("items", []):
                kw_data = kw_item.get("keyword_data", {})
                suggestions.append({
                    "keyword":       kw_data.get("keyword"),
                    "search_volume": kw_data.get("keyword_info", {}).get("search_volume"),
                    "difficulty":    kw_data.get("keyword_properties", {}).get("keyword_difficulty"),
                    "cpc":           kw_data.get("keyword_info", {}).get("cpc"),
                })

    return {"seed": keyword, "suggestions": suggestions, "count": len(suggestions)}


async def get_competitor_keywords(domain: str, limit: int = 50) -> dict:
    """Keywords a competitor domain ranks for in top 10"""
    payload = [{
        "target":        domain.replace("https://", "").replace("http://", "").rstrip("/"),
        "location_code": 2840,
        "language_code": "en",
        "limit":         limit,
        "filters":       [["ranked_serp_element.serp_item.rank_group", "<=", 10]],
    }]

    data = await _post("dataforseo_labs/google/ranked_keywords/live", payload)

    keywords = []
    for task in data.get("tasks", []):
        for item in (task.get("result") or []):
            for kw_item in item.get("items", []):
                kw_data = kw_item.get("keyword_data", {})
                keywords.append({
                    "keyword":    kw_data.get("keyword"),
                    "position":   kw_item.get("ranked_serp_element", {}).get("serp_item", {}).get("rank_absolute"),
                    "volume":     kw_data.get("keyword_info", {}).get("search_volume"),
                    "difficulty": kw_data.get("keyword_properties", {}).get("keyword_difficulty"),
                })

    return {"domain": domain, "keywords": keywords, "count": len(keywords)}
