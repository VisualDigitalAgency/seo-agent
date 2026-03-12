"""
Serper + SerpAPI Tool
Primary: Serper.dev (faster, cheaper)
Fallback: SerpAPI (if SERPER_API_KEY not set but SERPAPI_KEY is)
"""

import os
import httpx


async def _serper_post(endpoint: str, payload: dict) -> dict | None:
    key = os.environ.get("SERPER_API_KEY", "")
    if not key:
        return None
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.post(f"https://google.serper.dev/{endpoint}",
                          headers={"X-API-KEY": key, "Content-Type": "application/json"},
                          json=payload)
        r.raise_for_status()
        return r.json()


async def _serpapi_get(params: dict) -> dict | None:
    key = os.environ.get("SERPAPI_KEY", "")
    if not key:
        return None
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.get("https://serpapi.com/search",
                         params={**params, "api_key": key, "output": "json"})
        r.raise_for_status()
        return r.json()


def _no_key_error():
    return {"error": "Neither SERPER_API_KEY nor SERPAPI_KEY is set", "organic": [], "results": []}


async def search_serp(query: str, num: int = 10, country: str = "us") -> dict:
    """Google organic SERP — Serper primary, SerpAPI fallback"""

    # ── Serper.dev ──────────────────────────────────────────────────────────
    data = await _serper_post("search", {"q": query, "num": min(num, 20), "gl": country})
    if data:
        organic = [
            {"position": r.get("position"), "title": r.get("title"),
             "link": r.get("link"), "snippet": r.get("snippet"),
             "displayed_link": r.get("displayedLink")}
            for r in data.get("organic", [])
        ]
        return {
            "query": query, "source": "serper",
            "organic": organic,
            "featured_snippet": data.get("answerBox"),
            "people_also_ask": [q.get("question") for q in data.get("peopleAlsoAsk", [])],
            "related_searches": [r.get("query") for r in data.get("relatedSearches", [])],
        }

    # ── SerpAPI fallback ────────────────────────────────────────────────────
    data = await _serpapi_get({"q": query, "num": num, "gl": country, "engine": "google"})
    if data:
        organic = [
            {"position": r.get("position"), "title": r.get("title"),
             "link": r.get("link"), "snippet": r.get("snippet")}
            for r in data.get("organic_results", [])
        ]
        return {
            "query": query, "source": "serpapi",
            "organic": organic,
            "featured_snippet": data.get("answer_box"),
            "people_also_ask": [q.get("question") for q in data.get("related_questions", [])],
            "related_searches": [r.get("query") for r in data.get("related_searches", [])],
        }

    return _no_key_error()


async def search_web(query: str) -> dict:
    return await search_serp(query=query, num=10)


async def search_news(query: str) -> dict:
    # Serper
    data = await _serper_post("news", {"q": query, "num": 10})
    if data:
        return {"query": query, "source": "serper",
                "news": [{"title": r.get("title"), "link": r.get("link"),
                          "snippet": r.get("snippet"), "date": r.get("date"),
                          "source": r.get("source")} for r in data.get("news", [])]}
    # SerpAPI fallback
    data = await _serpapi_get({"q": query, "engine": "google_news", "num": 10})
    if data:
        return {"query": query, "source": "serpapi",
                "news": [{"title": r.get("title"), "link": r.get("link"),
                          "snippet": r.get("snippet")} for r in data.get("news_results", [])]}
    return _no_key_error()


async def get_related_questions(query: str) -> dict:
    data = await _serper_post("search", {"q": query, "num": 10})
    if data:
        paa = [{"question": i.get("question"), "snippet": i.get("snippet"),
                "link": i.get("link")} for i in data.get("peopleAlsoAsk", [])]
        return {"query": query, "questions": paa, "count": len(paa)}

    data = await _serpapi_get({"q": query, "engine": "google"})
    if data:
        paa = [{"question": q.get("question"), "snippet": q.get("snippet"),
                "link": q.get("link")} for q in data.get("related_questions", [])]
        return {"query": query, "questions": paa, "count": len(paa)}

    return _no_key_error()
