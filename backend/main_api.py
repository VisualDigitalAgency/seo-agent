"""
SEO Agent Backend — Unified FastAPI
Runs on Railway / Render (single service, port 8000)

Endpoints:
  Pipeline: /api/run, /runs, /api/run/{id}, /api/run/{id}/resume, /api/stream/{id}, /logs/{id}
  Tools:    /tools, /tools/*
  Schedule: /api/schedules GET/POST/DELETE
  Memory:   /api/memory GET/POST
  Config:   /config GET/POST
  Monitor:  /tool-calls GET (live tool call log)
"""

import os
import json
import asyncio
import logging
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from slowapi.errors import RateLimitExceeded
from dotenv import load_dotenv
from tools._persistent_logger import log_tool_call_persistent

# Load environment variables from .env.local with proper parsing
env_path = Path(os.getcwd()) / ".env.local"
if env_path.exists():
    load_dotenv(dotenv_path=env_path, override=True)

# Validate required environment variables at startup
def validate_env_vars():
    """Check for required environment variables and log warnings for missing ones."""
    required_vars = {
        "OPENROUTER_API_KEY": "OpenRouter API key for LLM calls",
    }

    optional_but_recommended = {
        "SERPER_API_KEY": "Serper.dev API key for search (fallback to SerpAPI)",
        "SERPAPI_KEY": "SerpAPI key as fallback for search",
        "DATAFORSEO_LOGIN": "DataForSEO login for keyword research",
        "DATAFORSEO_PASSWORD": "DataForSEO password for keyword research",
        "GSC_CREDENTIALS_PATH": "Google Service Account credentials for Search Console",
        "GA4_CREDENTIALS_PATH": "Google Service Account credentials for GA4",
        "GA4_PROPERTY_ID": "Google Analytics 4 property ID",
    }

    missing_required = [var for var in required_vars if not os.environ.get(var)]

    for var in missing_required:
        logger.error(f"Missing required environment variable: {var} - {required_vars[var]}")

    if missing_required:
        raise RuntimeError(f"Missing required environment variables: {', '.join(missing_required)}")

    for var, description in optional_but_recommended.items():
        if not os.environ.get(var):
            logger.warning(f"Optional environment variable not set: {var} - {description}")

# Call validation after loading env vars
validate_env_vars()

from fastapi import FastAPI, Request, HTTPException, BackgroundTasks, JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from .rate_limit_middleware import limiter
from fastapi.middleware.cors import CORSMiddleware
from middleware.request_size_limit import RequestSizeLimitMiddleware
from jsonschema import validate, ValidationError
from fastapi.responses import StreamingResponse, JSONResponse, PlainTextResponse
from . import metrics as app_metrics
from middleware.metrics_middleware import MetricsMiddleware

from middleware.guards import PermissionGuard
from middleware.auth import get_auth_middleware
from tools import serper, dataforseo, gsc, ga4, filesystem
from scheduler import SEOScheduler
import fs_utils as fs

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s — %(message)s")
logger = logging.getLogger("seo-backend")

# ── Tool call log (in-memory ring buffer, last 500 calls) ─────────────────────
tool_call_log: list[dict] = []
MAX_TOOL_LOG = 500


def log_tool_call(tool_name: str, args: dict, result: dict, duration_ms: int, error: str = None):
    """Log tool call to both in-memory ring buffer and persistent storage."""
    entry = {
        "id":          len(tool_call_log) + 1,
        "tool":        tool_name,
        "args":        args,
        "result":      result,
        "duration_ms": duration_ms,
        "error":       error,
        "timestamp":   datetime.utcnow().isoformat(),
        "status":      "error" if error else "ok",
    }
    tool_call_log.append(entry)
    if len(tool_call_log) > MAX_TOOL_LOG:
        tool_call_log.pop(0)

    # Record metrics for monitoring
    app_metrics.record_tool_call(tool_name, duration_ms, error is not None)

    # Also persist to disk (fire-and-forget, non-blocking)
    try:
        log_tool_call_persistent(entry)
    except Exception as e:
        logger.warning(f"Failed to persist tool call log: {e}")


# ── Scheduler ─────────────────────────────────────────────────────────────────
scheduler = SEOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.start()
    logger.info("✅ Scheduler started")
    try:
        yield
    finally:
        logger.info("Lifespan ending. Shutting down...")
        scheduler.shutdown(wait=True)  # Wait for running jobs to complete
        logger.info("Scheduler shutdown complete.")


app = FastAPI(title="SEO Agent Backend", version="1.0.0", lifespan=lifespan)

# Apply request size limit middleware
app.add_middleware(RequestSizeLimitMiddleware)

# Attach rate limiter to app and add middleware
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(MetricsMiddleware)

# Add rate limit exception handler
from slowapi.errors import RateLimitExceeded

@app.exception_handler(RateLimitExceeded)
async def slowapi_rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={
            "error": "rate_limit_exceeded",
            "message": f"Rate limit exceeded. Try again in {exc.retry_after} seconds.",
            "retry_after": exc.retry_after
        }
    )


# Ideally we would attach limiter to app but since slowapi requires additional setup,
# we'll instead implement a simple token bucket rate limiter as middleware.
# For simplicity, we apply rate limiting only to specific high-traffic endpoints.

# Apply rate limiting to public API endpoints with per-endpoint configuration
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    # Only apply rate limiting to public endpoints (not /tools/*)
    if not request.url.path.startswith("/tools/"):
        path = request.url.path

        # Check for per-endpoint rate limits
        matched_limit = None
        for pattern, limits in PER_ENDPOINT_RATE_LIMITS.items():
            # Convert path parameter patterns like "/logs/{run_id}" to match
            pattern_parts = pattern.split('/')
            path_parts = path.split('/')

            if len(pattern_parts) == len(path_parts):
                match = True
                for p_part, path_part in zip(pattern_parts, path_parts):
                    if p_part.startswith('{') and p_part.endswith('}'):
                        # Parameter - any value matches
                        continue
                    elif p_part != path_part:
                        match = False
                        break

                if match:
                    matched_limit = limits
                    break

        # Apply the specific limit if found, else use default
        if matched_limit:
            # Set custom limits for this request by temporarily overriding the limiter's defaults
            original_limits = limiter._default_limits
            limiter._default_limits = matched_limit
            try:
                response = await limiter.middleware(request, call_next)
            finally:
                limiter._default_limits = original_limits
            return response
        else:
            await limiter.middleware(request, call_next)
    else:
        return await call_next(request)

# CORS — allow Vercel frontend + local dev
ALLOWED_ORIGINS = [
    os.environ.get("FRONTEND_URL", "http://localhost:3000"),
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=r"https://.*\.vercel\.app",   # Vercel preview URLs
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
    allow_credentials=False,
)
app.add_middleware(PermissionGuard)


# ── Request ID Middleware ───────────────────────────────────────────────────────
class RequestIdMiddleware(BaseHTTPMiddleware):
    """Middleware to add X-Request-ID to each request and propagate to logs."""

    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # Set request ID in logging context
        logging.LoggerAdapter(logger, {'request_id': request_id})

        response = await call_next(request)

        response.headers['X-Request-ID'] = request_id
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'

        return response


app.add_middleware(RequestIdMiddleware)
app.add_middleware(get_auth_middleware)


# ── Health ────────────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    """Health check endpoint with dependency status"""
    # Check external service availability
    dependencies = {
        "openrouter": bool(os.environ.get("OPENROUTER_API_KEY")),
        "serper": bool(os.environ.get("SERPER_API_KEY")),
        "serpapi": bool(os.environ.get("SERPAPI_KEY")),
        "dataforseo": bool(os.environ.get("DATAFORSEO_LOGIN") and os.environ.get("DATAFORSEO_PASSWORD")),
        "gsc": bool(os.environ.get("GSC_CREDENTIALS_PATH")),
        "ga4": bool(os.environ.get("GA4_CREDENTIALS_PATH") and os.environ.get("GA4_PROPERTY_ID")),
    }

    all_critical_ok = dependencies["openrouter"]

    return {
        "status": "ok" if all_critical_ok else "degraded",
        "scheduler_running": scheduler.is_running(),
        "dependencies": dependencies
    }


# ── Metrics ─────────────────────────────────────────────────────────────────────
@app.get("/metrics")
def metrics(format: str = "json"):
    """
    Application metrics endpoint.
    Supports Prometheus format (?format=prometheus) or JSON (?format=json).
    """
    if format == "prometheus":
        return PlainTextResponse(content=app_metrics.get_metrics_prometheus(), media_type="text/plain")
    else:
        return JSONResponse(content=app_metrics.get_metrics_json())


# ══════════════════════════════════════════════════════════════════════════════
#  PIPELINE ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/api/run")
@limiter.limit("60/minute")
async def start_run(request: Request, background_tasks: BackgroundTasks):
    try:
        body = await request.json()
        validated = StartRunRequest(**body)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid request: {str(e)}")

    run_id = fs.new_run_id()
    task_data = {
        "task":     validated.task,
        "target":   validated.target or "",
        "audience": validated.audience or "",
        "domain":   validated.domain or "",
        "notes":    validated.notes or "",
        "run_id":   run_id,
        "created_at": datetime.utcnow().isoformat(),
    }

    fs.init_run(run_id, task_data)
    background_tasks.add_task(_run_pipeline, run_id, task_data)
    return {"run_id": run_id, "status": "started"}


@app.get("/runs")
@limiter.limit("60/minute")
def list_runs():
    return {"runs": fs.list_all_runs()}


@app.get("/api/run/{run_id}")
@limiter.limit("60/minute")
def get_run(run_id: str):
    status = fs.read_status(run_id)
    if not status:
        raise HTTPException(404, "Run not found")
    return status


@app.delete("/api/run/{run_id}")
@limiter.limit("60/minute")
def delete_run_endpoint(run_id: str):
    fs.delete_run(run_id)
    return {"deleted": True}


@app.post("/api/run/{run_id}/resume")
@limiter.limit("60/minute")
async def resume_run(run_id: str, background_tasks: BackgroundTasks):
    status = fs.read_status(run_id)
    if not status:
        raise HTTPException(404, "Run not found")
    if status.get("status") == "running":
        raise HTTPException(400, "Already running")

    updated_stages = {s: v if v == "done" else "pending"
                      for s, v in status.get("stages", {}).items()}
    resume_from = next((s for s, v in updated_stages.items() if v != "done"), None)

    fs.write_status(run_id, {**status, "status": "pending",
                              "stages": updated_stages,
                              "resume_from": resume_from, "error": None})

    task_data = fs.read_stage_output(run_id, 0) or {"task": status.get("task", "")}
    background_tasks.add_task(_run_pipeline, run_id, task_data, resume=True)
    return {"resumed": True, "resume_from": resume_from}


@app.get("/api/run/{run_id}/stage/{n}")
@limiter.limit("60/minute")
def get_stage_output(run_id: str, n: int):
    data = fs.read_stage_output(run_id, n)
    if not data:
        raise HTTPException(404, "Stage output not found")
    return data


@app.get("/logs/{run_id}")
@limiter.limit("60/minute")
def get_logs(run_id: str, tail: int = 200):
    return {"lines": fs.read_log_tail(run_id, tail)}


# ── SSE streaming ─────────────────────────────────────────────────────────────
@app.get("/api/stream/{run_id}")
@limiter.limit("30/minute")
async def stream_run(run_id: str):
    async def event_generator():
        import aiofiles
        log_path = fs.get_log_path(run_id)
        log_pos  = 0

        # Seek to end of existing log
        if log_path.exists():
            log_pos = log_path.stat().st_size

        yield f"data: {json.dumps({'type': 'connected', 'run_id': run_id})}\n\n"

        for _ in range(30 * 60 * 2):   # 30 min max
            await asyncio.sleep(0.5)

            # Read new log lines
            if log_path.exists():
                size = log_path.stat().st_size
                if size > log_pos:
                    with open(log_path, "rb") as f:
                        f.seek(log_pos)
                        new_bytes = f.read(size - log_pos)
                    log_pos = size
                    for line in new_bytes.decode("utf-8", errors="ignore").split("\n"):
                        if line.strip():
                            yield f"data: {json.dumps({'type': 'log', 'line': line})}\n\n"
                            if "[STAGE:" in line:
                                import re
                                m = re.search(r"\[STAGE:(\w+)\]\s+(DONE|RUNNING|FAILED)", line)
                                if m:
                                    status_word = 'failed' if 'FAILED' in line else m.group(2).lower()
                                    yield f"data: {json.dumps({'type': 'stage_update', 'stage': m.group(1), 'status': status_word})}\n\n"

            status = fs.read_status(run_id)
            if status and status.get("status") in ("done", "failed"):
                yield f"data: {json.dumps({'type': status['status'], 'status': status})}\n\n"
                return

    return StreamingResponse(event_generator(),
                              media_type="text/event-stream",
                              headers={"Cache-Control": "no-cache",
                                       "X-Accel-Buffering": "no"})


# ══════════════════════════════════════════════════════════════════════════════
#  SCHEDULE ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/api/schedules")
@limiter.limit("60/minute")
def list_schedules():
    return {"schedules": scheduler.list_schedules()}


@app.post("/api/schedules")
async def create_schedule(request: Request, background_tasks: BackgroundTasks):
    try:
        body = await request.json()
        validated = ScheduleConfig(**body)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid request: {str(e)}")

    # Convert pydantic model back to dict for scheduler
    schedule_data = validated.model_dump()
    result = scheduler.add_schedule(schedule_data)
    return result


@app.delete("/api/schedules/{schedule_id}")
@limiter.limit("60/minute")
def delete_schedule(schedule_id: str):
    scheduler.remove_schedule(schedule_id)
    return {"deleted": True}


@app.post("/api/schedules/{schedule_id}/run-now")
@limiter.limit("60/minute")
async def run_schedule_now(schedule_id: str, background_tasks: BackgroundTasks):
    sched = scheduler.get_schedule(schedule_id)
    if not sched:
        raise HTTPException(404, "Schedule not found")
    run_id = fs.new_run_id()
    fs.init_run(run_id, sched["task_config"])
    background_tasks.add_task(_run_pipeline, run_id, sched["task_config"])
    return {"run_id": run_id, "triggered": True}


# ══════════════════════════════════════════════════════════════════════════════
#  MEMORY ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/api/memory")
@limiter.limit("60/minute")
def get_memory(q: str = ""):
    learnings = fs.read_learnings()
    history   = fs.read_task_history()
    if q:
        q_lower = q.lower()
        learnings = [l for l in learnings if q_lower in (l.get("task") or "").lower()
                     or any(q_lower in i.lower() for i in l.get("insights", []))]
        history   = [h for h in history if q_lower in (h.get("task") or "").lower()]
    return {"learnings": learnings, "history": history, "total": len(learnings)}


@app.post("/api/memory")
@limiter.limit("60/minute")
async def post_memory(request: Request):
    try:
        body = await request.json()
        validated = MemoryEntryRequest(**body)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid request: {str(e)}")

    t, data = validated.type, validated.data
    if t == "learning":
        learnings = fs.read_learnings()
        learnings.append({**data, "date": datetime.utcnow().strftime("%Y-%m-%d")})
        fs.write_learnings(learnings)
    elif t == "history":
        fs.append_task_history(data)
    return {"saved": True}


# ══════════════════════════════════════════════════════════════════════════════
#  CONFIG ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/config")
@limiter.limit("60/minute")
def get_config():
    cfg = fs.read_config()
    env = fs.read_env_keys()
    return {**cfg, "env": env}


@app.post("/config")
@limiter.limit("60/minute")
async def post_config(request: Request):
    try:
        body = await request.json()
        validated = ConfigUpdateRequest(**body)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid request: {str(e)}")

    existing = fs.read_config()
    if validated.model:
        existing["model"] = validated.model
    if validated.pipeline:
        existing["pipeline"] = validated.pipeline
    fs.write_config(existing)
    if validated.env:
        fs.write_env_keys({k: v for k, v in validated.env.items() if v})
    return {"saved": True}


# ══════════════════════════════════════════════════════════════════════════════
#  TOOL SERVER ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/tools")
@limiter.limit("60/minute")
def get_tools():
    from server_tools import TOOL_DEFINITIONS
    return {"tools": TOOL_DEFINITIONS}


@app.get("/tool-calls")
@limiter.limit("60/minute")
def get_tool_calls(limit: int = 100, persistent: bool = False, days: int = 1):
    """
    Get recent tool calls.

    Args:
        limit: Maximum number of entries to return
        persistent: If True, read from persistent logs (historical data)
        days: Number of days to look back when persistent=True
    """
    if persistent:
        # Read from persistent logs
        try:
            from tools._persistent_logger import get_persistent_tool_calls
            calls = get_persistent_tool_calls(days=days, limit=limit)
            return {"calls": calls, "total": len(calls), "source": "persistent"}
        except Exception as e:
            logger.error(f"Failed to read persistent tool logs: {e}")
            # Fall back to in-memory
            return {"calls": tool_call_log[-limit:], "total": len(tool_call_log), "source": "memory_fallback"}

    return {"calls": tool_call_log[-limit:], "total": len(tool_call_log), "source": "memory"}


async def _timed_tool_call(name: str, coro_fn, args: dict):
    import time
    start = time.monotonic()
    error = None
    result = {}
    try:
        result = await coro_fn(**args)
    except Exception as e:
        error  = str(e)
        result = {"error": error}
    duration = int((time.monotonic() - start) * 1000)
    log_tool_call(name, args, result, duration, error)
    return result


@app.post("/tools/search_serp")
async def t_search_serp(request: Request):
    body = await request.json()
    return await _timed_tool_call("search_serp", serper.search_serp,
                                   {"query": body.get("query",""), "num": int(body.get("num_results",10)), "country": body.get("country","us")})

@app.post("/tools/search_web")
async def t_search_web(request: Request):
    body = await request.json()
    return await _timed_tool_call("search_web", serper.search_web, {"query": body.get("query","")})

@app.post("/tools/search_news")
async def t_search_news(request: Request):
    body = await request.json()
    return await _timed_tool_call("search_news", serper.search_news, {"query": body.get("query","")})

@app.post("/tools/get_related_questions")
async def t_related_questions(request: Request):
    body = await request.json()
    return await _timed_tool_call("get_related_questions", serper.get_related_questions, {"query": body.get("query","")})

@app.post("/tools/get_keyword_volume")
async def t_kw_volume(request: Request):
    body = await request.json()
    return await _timed_tool_call("get_keyword_volume", dataforseo.get_keyword_volume,
                                   {"keywords": body.get("keywords",[]), "location_code": body.get("location_code",2840)})

@app.post("/tools/get_keyword_difficulty")
async def t_kw_difficulty(request: Request):
    body = await request.json()
    return await _timed_tool_call("get_keyword_difficulty", dataforseo.get_keyword_difficulty, {"keywords": body.get("keywords",[])})

@app.post("/tools/get_keyword_suggestions")
async def t_kw_suggestions(request: Request):
    body = await request.json()
    return await _timed_tool_call("get_keyword_suggestions", dataforseo.get_keyword_suggestions,
                                   {"keyword": body.get("keyword",""), "limit": int(body.get("limit",20))})

@app.post("/tools/get_competitor_keywords")
async def t_competitor_kw(request: Request):
    body = await request.json()
    return await _timed_tool_call("get_competitor_keywords", dataforseo.get_competitor_keywords,
                                   {"domain": body.get("domain",""), "limit": int(body.get("limit",50))})

@app.post("/tools/gsc_get_rankings")
async def t_gsc_rankings(request: Request):
    body = await request.json()
    return await _timed_tool_call("gsc_get_rankings", gsc.get_rankings,
                                   {"site_url": body.get("site_url",""), "page_url": body.get("page_url",""), "days": int(body.get("days",30))})

@app.post("/tools/gsc_get_top_queries")
async def t_gsc_queries(request: Request):
    body = await request.json()
    return await _timed_tool_call("gsc_get_top_queries", gsc.get_top_queries,
                                   {"site_url": body.get("site_url",""), "page_url": body.get("page_url",""),
                                    "days": int(body.get("days",30)), "limit": int(body.get("limit",25))})

@app.post("/tools/gsc_detect_ranking_drops")
async def t_gsc_drops(request: Request):
    body = await request.json()
    return await _timed_tool_call("gsc_detect_ranking_drops", gsc.detect_ranking_drops,
                                   {"site_url": body.get("site_url",""), "drop_threshold": float(body.get("drop_threshold",3.0)),
                                    "days": int(body.get("days",28))})

@app.post("/tools/ga4_get_page_traffic")
async def t_ga4_traffic(request: Request):
    body = await request.json()
    return await _timed_tool_call("ga4_get_page_traffic", ga4.get_page_traffic,
                                   {"page_path": body.get("page_path",""), "days": int(body.get("days",30))})

@app.post("/tools/ga4_get_top_pages")
async def t_ga4_top(request: Request):
    body = await request.json()
    return await _timed_tool_call("ga4_get_top_pages", ga4.get_top_pages,
                                   {"days": int(body.get("days",30)), "limit": int(body.get("limit",20))})

@app.post("/tools/ga4_detect_traffic_drops")
async def t_ga4_drops(request: Request):
    body = await request.json()
    return await _timed_tool_call("ga4_detect_traffic_drops", ga4.detect_traffic_drops,
                                   {"days": int(body.get("days",30)), "drop_pct_threshold": float(body.get("drop_pct",20.0))})

@app.post("/tools/write_stage_output")
async def t_write_stage(request: Request):
    body = await request.json()
    return filesystem.write_stage_output(run_id=body.get("run_id",""), stage=body.get("stage",""), data=body.get("data",{}))

@app.post("/tools/write_memory")
async def t_write_memory(request: Request):
    body = await request.json()
    return filesystem.write_memory(entry=body.get("entry",{}))

@app.post("/tools/append_log")
async def t_append_log(request: Request):
    body = await request.json()
    return filesystem.append_log(run_id=body.get("run_id",""), line=body.get("line",""))


# ══════════════════════════════════════════════════════════════════════════════
#  PIPELINE RUNNER (background task)
# ══════════════════════════════════════════════════════════════════════════════

async def _run_pipeline(run_id: str, task_data: dict, resume: bool = False):
    """
    Run the pipeline in a thread pool executor so the synchronous pipeline code
    (and all the blocking requests/LLM calls inside it) doesn't block the
    FastAPI event loop — keeping SSE streams, status polls, and other requests
    responsive while the pipeline runs.
    """
    import sys, asyncio
    sys.path.insert(0, str(Path(__file__).parent))
    from pipeline import Pipeline

    def _run_sync():
        pipeline = Pipeline(
            run_id   = run_id,
            task     = task_data.get("task", ""),
            target   = task_data.get("target", ""),
            audience = task_data.get("audience", ""),
            domain   = task_data.get("domain", ""),
            notes    = task_data.get("notes", ""),
        )
        try:
            if resume:
                pipeline.resume()
            else:
                pipeline.run()
        except Exception as e:
            logger.error(f"Pipeline {run_id} error: {e}")
            pipeline.update_status("failed", error=str(e))

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _run_sync)
