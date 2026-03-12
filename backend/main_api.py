"""
SEO Agent Backend — Unified FastAPI
Runs on Railway / Render (single service, port 8000)

Endpoints:
  Pipeline: /run, /runs, /run/{id}, /run/{id}/resume, /stream/{id}, /logs/{id}
  Tools:    /tools, /tools/*
  Schedule: /schedules GET/POST/DELETE
  Memory:   /memory GET/POST
  Config:   /config GET/POST
  Monitor:  /tool-calls GET (live tool call log)
"""

import os
import json
import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse

from middleware.guards import PermissionGuard
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


# ── Scheduler ─────────────────────────────────────────────────────────────────
scheduler = SEOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.start()
    logger.info("✅ Scheduler started")
    yield
    scheduler.shutdown()
    logger.info("Scheduler stopped")


app = FastAPI(title="SEO Agent Backend", version="1.0.0", lifespan=lifespan)

# CORS — allow Vercel frontend + local dev
ALLOWED_ORIGINS = [
    os.environ.get("FRONTEND_URL", "http://localhost:3000"),
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
app.add_middleware(CORSMiddleware, allow_origins=ALLOWED_ORIGINS,
                   allow_methods=["GET", "POST", "DELETE"], allow_headers=["*"])
app.add_middleware(PermissionGuard)


# ── Health ────────────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok", "scheduler_running": scheduler.is_running()}


# ══════════════════════════════════════════════════════════════════════════════
#  PIPELINE ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/run")
async def start_run(request: Request, background_tasks: BackgroundTasks):
    body     = await request.json()
    task     = body.get("task", "").strip()
    if not task:
        raise HTTPException(400, "task is required")

    run_id   = fs.new_run_id()
    task_data = {
        "task":     task,
        "target":   body.get("target", ""),
        "audience": body.get("audience", ""),
        "domain":   body.get("domain", ""),
        "notes":    body.get("notes", ""),
        "run_id":   run_id,
        "created_at": datetime.utcnow().isoformat(),
    }

    fs.init_run(run_id, task_data)
    background_tasks.add_task(_run_pipeline, run_id, task_data)
    return {"run_id": run_id, "status": "started"}


@app.get("/runs")
def list_runs():
    return {"runs": fs.list_all_runs()}


@app.get("/run/{run_id}")
def get_run(run_id: str):
    status = fs.read_status(run_id)
    if not status:
        raise HTTPException(404, "Run not found")
    return status


@app.delete("/run/{run_id}")
def delete_run_endpoint(run_id: str):
    fs.delete_run(run_id)
    return {"deleted": True}


@app.post("/run/{run_id}/resume")
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


@app.get("/run/{run_id}/stage/{n}")
def get_stage_output(run_id: str, n: int):
    data = fs.read_stage_output(run_id, n)
    if not data:
        raise HTTPException(404, "Stage output not found")
    return data


@app.get("/logs/{run_id}")
def get_logs(run_id: str, tail: int = 200):
    return {"lines": fs.read_log_tail(run_id, tail)}


# ── SSE streaming ─────────────────────────────────────────────────────────────
@app.get("/stream/{run_id}")
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
                                m = re.search(r"\[STAGE:(\w+)\]\s+(DONE|FAILED|RUNNING)", line)
                                if m:
                                    yield f"data: {json.dumps({'type': 'stage_update', 'stage': m.group(1), 'status': m.group(2).lower()})}\n\n"

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

@app.get("/schedules")
def list_schedules():
    return {"schedules": scheduler.list_schedules()}


@app.post("/schedules")
async def create_schedule(request: Request, background_tasks: BackgroundTasks):
    body = await request.json()
    result = scheduler.add_schedule(body)
    return result


@app.delete("/schedules/{schedule_id}")
def delete_schedule(schedule_id: str):
    scheduler.remove_schedule(schedule_id)
    return {"deleted": True}


@app.post("/schedules/{schedule_id}/run-now")
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

@app.get("/memory")
def get_memory(q: str = ""):
    learnings = fs.read_learnings()
    history   = fs.read_task_history()
    if q:
        q_lower = q.lower()
        learnings = [l for l in learnings if q_lower in (l.get("task") or "").lower()
                     or any(q_lower in i.lower() for i in l.get("insights", []))]
        history   = [h for h in history if q_lower in (h.get("task") or "").lower()]
    return {"learnings": learnings, "history": history, "total": len(learnings)}


@app.post("/memory")
async def post_memory(request: Request):
    body = await request.json()
    t, data = body.get("type"), body.get("data", {})
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
def get_config():
    cfg = fs.read_config()
    env = fs.read_env_keys()
    return {**cfg, "env": env}


@app.post("/config")
async def post_config(request: Request):
    body = await request.json()
    existing = fs.read_config()
    if "model"    in body: existing["model"]    = body["model"]
    if "pipeline" in body: existing["pipeline"] = body["pipeline"]
    fs.write_config(existing)
    if "env" in body:
        fs.write_env_keys({k: v for k, v in body["env"].items() if v})
    return {"saved": True}


# ══════════════════════════════════════════════════════════════════════════════
#  TOOL SERVER ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/tools")
def get_tools():
    from server_tools import TOOL_DEFINITIONS
    return {"tools": TOOL_DEFINITIONS}


@app.get("/tool-calls")
def get_tool_calls(limit: int = 100):
    return {"calls": tool_call_log[-limit:], "total": len(tool_call_log)}


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
    import sys, importlib
    sys.path.insert(0, str(Path(__file__).parent))

    from pipeline import Pipeline
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


from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def root():
    return {"status": "SEO Agent API running"}

@app.get("/health")
def health():
    return {"status": "ok"}
