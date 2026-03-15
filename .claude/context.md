# SEO Agent - Production Context Memory

**Last Updated:** 2026-03-15
**Status:** Production Ready (100% Complete - 33/33 Tasks)
**Build ID:** Continuous integration active

---

## 🎯 Quick Start Context

You are working on the **SEO Agent** - an autonomous SEO pipeline with Next.js frontend (Vercel) and FastAPI backend (Railway/Render). The codebase is production-ready with enterprise-grade security, reliability, and observability.

### Current State
- ✅ All critical security vulnerabilities fixed
- ✅ Circuit breakers, retries, timeouts on all external APIs
- ✅ Rate limiting, authentication, audit logging active
- ✅ Comprehensive monitoring with Prometheus metrics
- ✅ CI/CD pipelines for testing and security scanning
- ✅ Frontend has error boundaries, skeletons, SSE reconnection
- ✅ **Production readiness: 100% complete (33/33 tasks)**

### Environment Setup (5 minutes)
```bash
# Backend
cd backend
pip install -r requirements.txt
# Create .env.local with at least:
# OPENROUTER_API_KEY=sk-or-...
uvicorn main_api:app --port 8000 --reload

# Frontend
cd frontend
npm install
# Create .env.local with:
# BACKEND_URL=http://localhost:8000
npm run dev  # on :3000
```

---

## 🏗️ Architecture at a Glance

### Backend (FastAPI)
- **Port:** 8000
- **Main API:** `backend/main_api.py` (480 lines)
- **Pipeline:** `backend/pipeline.py` - 8 sequential stages with checkpoint/resume
- **Agents:** `backend/agents/` - ResearchAgent, ContentAgent, OnPageAgent, LinksAgent, AnalystAgent, EditorAgent, MemoryAgent
- **Tools:** `backend/tools/` - serper, dataforseo, gsc, ga4, filesystem
- **Middleware Stack:**
  1. RequestIdMiddleware (X-Request-ID)
  2. SlowAPIMiddleware (rate limiting)
  3. MetricsMiddleware (monitoring)
  4. RequestSizeLimitMiddleware (10MB max)
  5. AuthenticationMiddleware (API key)
  6. PermissionGuard (tool protection)
  7. CORS (Vercel + localhost)

### Frontend (Next.js 14 App Router)
- **Port:** 3000
- **Pages:** /, /task, /runs, /runs/[id], /scheduler, /tools, /memory, /settings
- **API Proxy:** `frontend/app/api/` routes to backend
- **Streaming:** SSE at `/api/stream/[runId]` with reconnection
- **Styling:** Custom CSS (no Tailwind) with CSS variables

### Data Storage
- **Persistent Volume:** `/data` on Railway/Render (falls back to cwd in dev)
- **Structure:**
  - `runs/{run_id}/` - stage outputs (01_*.json through 08_*.json), logs, status
  - `memory/` - learnings.json, task_history.csv (with CSV injection protection)
  - `config.json` - validated against JSON schema
  - `schedules.json` - scheduled pipeline runs
  - `tool_logs/` - persistent tool call logs with rotation

---

## 🔒 Security Model (Production Grade)

### Implemented Protections
1. **Path Traversal Prevention** - run_id validated with regex: `^run_\d{8}_\d{6}$`
2. **CSV Injection Prevention** - All CSV fields escaped if starting with =, +, -, @, tab, CR
3. **Input Validation** - Pydantic models on all API endpoints (validation.py)
4. **Authentication** - API key-based (X-API-Key or Authorization: Bearer)
5. **Rate Limiting** - 60/min, 1000/hour per IP on public endpoints
6. **Request Size Limits** - 10MB max body size
7. **Security Headers** - CSP, X-Frame-Options: DENY, X-Content-Type-Options: nosniff, Referrer-Policy
8. **Permission Guard** - Blocks DELETE/PUT/PATCH on /tools/* endpoints
9. **Audit Logging** - All admin actions logged with IP, user agent, timestamp

### Required Environment Variables
**Critical:**
- `OPENROUTER_API_KEY` - LLM provider (required)

**Recommended:**
- `SERPER_API_KEY` - Primary search API
- `SERPAPI_KEY` - Fallback search API
- `DATAFORSEO_LOGIN` / `DATAFORSEO_PASSWORD` - Keyword research
- `GSC_CREDENTIALS_PATH` - Google Search Console service account
- `GA4_CREDENTIALS_PATH` / `GA4_PROPERTY_ID` - Google Analytics 4
- `API_KEYS` - Comma-separated admin API keys for authentication
- `FRONTEND_URL` - CORS origin

---

## 🔧 Key Configuration Files

### Backend
- `backend/main_api.py` - All routes, middleware, tool endpoints
- `backend/pipeline.py` - Pipeline orchestration (8 stages)
- `backend/fs_utils.py` - File system abstraction with validation
- `backend/config_validator.py` - Config loading with env-specific overrides
- `backend/validation.py` - Pydantic request schemas
- `backend/middleware/auth.py` - API key authentication
- `backend/middleware/request_size_limit.py` - Request size enforcement
- `backend/tools/_error_handling.py` - Retry, backoff, circuit breakers
- `backend/tools/_circuit_breaker.py` - Provider-specific circuit breakers
- `backend/tools/_cache.py` - In-memory tool result caching (5min TTL)
- `backend/tools/_persistent_logger.py` - Disk-based tool log rotation
- `backend/metrics.py` - Prometheus metrics collection
- `backend/config_schema.json` - JSON schema for config validation

### Config Files
- `backend/config.json` - Main configuration (validated)
- `backend/config.development.json` - Dev overrides
- `backend/railway.toml` - Railway deployment (gunicorn)
- `backend/render.yaml` - Render deployment
- `backend/gunicorn.conf.py` - Gunicorn worker config
- `frontend/vercel.json` - Vercel headers (CSP, security)

### CI/CD
- `.github/workflows/test.yml` - Tests, lint, type check (Python + JS)
- `.github/workflows/dependency-review.yml` - Security scanning (pip-audit, npm audit, Snyk)

---

## 📊 Monitoring & Observability

### Endpoints
- `GET /health` - Health check with dependency status
- `GET /metrics?format=json|prometheus` - Application metrics
- `GET /tool-calls?persistent=true&days=1` - Tool call logs (in-memory + disk)
- `GET /logs/{runId}?tail=200` - Pipeline logs
- `GET /api/stream/{runId}` - SSE live stream

### Key Metrics
- `seo_uptime_seconds` - Application uptime
- `seo_active_runs` - Currently running pipelines
- `seo_pipeline_runs_total/completed/failed/running` - Pipeline statistics
- `seo_api_calls_total{endpoint}` - API call counts
- `seo_api_errors_total{endpoint}` - API error counts
- `seo_tool_calls_total{tool}` - Tool invocation counts
- `seo_tool_errors_total{tool}` - Tool error counts
- `seo_tool_call_duration_ms_avg{tool}` - Tool latency

### Alert Thresholds (Configurable)
- **Error Rate:** >5% for 5 minutes
- **High Latency:** >2s for 95th percentile
- **Circuit Breaker:** 3+ trips in 5 minutes
- **Rate Limit:** 100+ hits in 1 hour
- **Auth Failures:** 50+ in 1 hour
- **Security Blocks:** 20+ in 1 hour

---

## 🚀 Common Workflows

### Start a New Pipeline
```bash
POST /api/run
{
  "task": "Create content about sustainable gardening",
  "target": "gardening.com",
  "audience": "homeowners"
}
```
Returns `{ "run_id": "run_20260315_123456", "status": "started" }`

### Monitor Live
```bash
# SSE stream
GET /api/stream/run_20260315_123456
# Or open in browser: /runs/run_20260315_123456
```

### Resume Failed Run
```bash
POST /api/run/{runId}/resume
```

### Get Stage Output
```bash
GET /api/run/{runId}/stage/{n}  # n=01..08
```

### View Recent Tool Calls
```bash
GET /tool-calls?limit=100&persistent=true&days=1
```

### Schedule Recurring
```bash
POST /api/schedules
{
  "name": "Daily keyword research",
  "frequency": "daily",
  "hour": 9,
  "minute": 0,
  "task_config": { "task": "...", ... }
}
```

---

## 🐛 Debugging Guide

### Pipeline Stuck?
1. Check `/health` - dependencies ok?
2. Check `/metrics` - any circuit breakers open?
3. Check recent logs: `/logs/{runId}`
4. Check tool calls: `/tool-calls?persistent=true&days=1`
5. Look for ERROR level JSON logs in log files

### High Error Rates?
1. Check circuit breaker status in tool logs
2. Verify API keys in backend logs (startup validation)
3. Check rate limiting - are you hitting limits?
4. Inspect `/tool-calls` for specific failing tools

### Frontend Issues?
1. Check browser console for errors
2. Check network tab for failed API calls (CORS issues?)
3. SSE reconnection? Look for "Reconnecting..." badge
4. Check backend logs for 4xx/5xx errors

### Need More Debug Info?
- Enable DEBUG level logging: set `SEO_LOG_LEVEL=DEBUG` env var
- Check structured logs include `run_id` and `stage`
- Use `X-Request-ID` from response headers to trace request

---

## 🧪 Testing

```bash
# Backend unit tests
cd backend
pytest tests/ -v

# Type checking
mypy --ignore-missing-imports agents/ tools/ main_api.py pipeline.py fs_utils.py

# Frontend lint
cd frontend
npm run lint

# Full build test
npm run build
```

---

## 📝 Important Notes

### Production Checklist (see PRODUCTION_FINAL_SUMMARY.md)
- ✅ Set OPENROUTER_API_KEY
- ✅ Configure API_KEYS for admin auth
- ✅ Deploy with gunicorn (workers = 2*CPU + 1)
- ✅ Mount /data volume
- ✅ Set FRONTEND_URL
- ✅ Configure logging aggregation
- ✅ Setup monitoring alerts
- ✅ Test /health and /metrics

### Known Limitations (By Design)
- No database (file-based storage) - can add PostgreSQL if needed
- In-memory cache not shared across workers (use Redis for multi-worker)
- Tool logs use rotating files (can switch to DB/ELK for long-term)
- Authentication is API key only (no user management yet)

### Performance Characteristics
- Typical pipeline: 5-15 minutes depending on content depth
- Concurrent runs: Limited by parallel_stages config (default 1)
- API latency: Simple endpoints < 50ms, pipeline start < 200ms
- Memory: ~200MB per worker + cache

---

## 🔄 Patterns & Conventions

### Code Style
- Python: type hints, docstrings, structured logging
- JavaScript: functional components, hooks, inline styles (existing pattern)
- Error handling: raise exceptions, caught by pipeline with logging

### Adding New Tools
1. Create `backend/tools/{module}.py`
2. Implement async function with proper error handling
3. Use `_rate_limit_async` for rate limiting
4. Use `get_circuit_breaker("{provider}")` for resilience
5. Add endpoint in `main_api.py` at `/tools/{tool_name}`

### Adding New Agents
1. Inherit from `BaseAgent` in `backend/agents/{name}.py`
2. Implement `run()` method with LLM + tool calls
3. Register in `pipeline.py` stage_to_agent mapping
4. Add stage file in `STAGE_FILE_MAP`

---

## 📚 Related Files

- `PRODUCTION_FINAL_SUMMARY.md` - Detailed completion report
- `CLAUDE.md` - Core project instructions (this file supplements that)
- `docs/` - Additional documentation

---

**Remember:** This context is loaded automatically at startup. Always check here first for architecture decisions, security model, and deployment patterns before making changes.

**Status:** Production Ready (100% Complete - 33/33 Tasks)
**Completion Date:** 2026-03-15
**Build ID:** Continuous integration active

---

**Note:** This context has been updated to reflect the completed production readiness plan. All 33 tasks are now complete and the system is ready for production deployment.