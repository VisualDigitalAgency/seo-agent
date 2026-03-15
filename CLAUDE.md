# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 🧠 Context Memory & Startup Protocol

**IMPORTANT:** A comprehensive context memory file exists at `.claude/context.md`. You **MUST** read this file at the start of every session to understand:
- Current production readiness status (84.8% complete)
- Security model and recent fixes
- Architecture patterns and conventions
- Deployment configurations
- Monitoring and debugging procedures

**At Startup:** Always read `.claude/context.md` before proceeding with any task.

**When User Types `/clear`:**
1. Read and summarize `.claude/context.md` in your response
2. Document what was summarized
3. Then clear/forget the context as requested
4. Reinforce that the context file is available for future reference

This ensures continuity across sessions and preserves critical institutional knowledge.

---

## Project Overview

SEO Agent is an autonomous SEO pipeline with a Next.js frontend (Vercel) and FastAPI backend (Railway/Render). It runs a multi-stage pipeline for keyword research, content writing, on-page optimization, and review using LLM agents with tool-calling capabilities.

## Development Commands

### Backend (FastAPI)
```bash
cd backend
pip install -r requirements.txt
uvicorn main_api:app --port 8000 --reload
```

### Frontend (Next.js)
```bash
cd frontend
npm install
npm run dev          # Dev server on :3000
npm run build        # Production build
npm run lint         # ESLint
```

### Environment Setup
```bash
# Backend (.env in backend/ or /data/.env.local)
OPENROUTER_API_KEY=sk-or-...
SERPER_API_KEY=...
SERPAPI_KEY=...
DATAFORSEO_LOGIN=...
DATAFORSEO_PASSWORD=...
GA4_PROPERTY_ID=properties/...

# Frontend (.env.local in frontend/)
BACKEND_URL=http://localhost:8000
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
```

## Architecture

### Pipeline Stages (pipeline.py)
The pipeline runs 8 sequential stages with checkpoint/resume support:
1. `keyword_research` → 01_keywords.json (ResearchAgent)
2. `serp_analysis` → 02_serp.json (ResearchAgent, API-only parsing)
3. `content_writing` → 04_content.json (ContentAgent)
4. `onpage_optimization` → 05_onpage.json (OnPageAgent)
5. `internal_linking` → 06_links.json (LinksAgent)
6. `analyst_review` → 07_analyst.json (AnalystAgent)
7. `senior_editor` → 08_final.json (EditorAgent)
8. `memory_update` → memory_update.json (MemoryAgent)

Each stage writes JSON output before proceeding. On resume, completed stages are skipped.

### Agent Architecture (agents/base.py)
- All agents inherit from `BaseAgent`
- Agents use OpenRouter API with tool-calling support
- Tool definitions fetched from `/tools` endpoint
- Multi-turn loop: LLM calls tool → result fed back → repeat until final response
- Per-agent model override supported via config: `{agent_name}_model` key

### Tool Server (main_api.py, server_tools.py)
- Tools are HTTP endpoints at `/tools/{tool_name}`
- Tools: search_serp, search_web, search_news, get_related_questions, get_keyword_volume, get_keyword_difficulty, get_keyword_suggestions, get_competitor_keywords, gsc_get_rankings, gsc_get_top_queries, gsc_detect_ranking_drops, ga4_get_page_traffic, ga4_get_top_pages, ga4_detect_traffic_drops
- Tool calls logged to in-memory ring buffer (last 500)

### Permission Model (middleware/guards.py)
- `PermissionGuard` middleware blocks destructive operations on `/tools/*`
- Blocked HTTP methods on tools: DELETE, PUT, PATCH
- Blocked keywords in POST body: delete, drop, truncate, destroy, etc.
- User-facing endpoints (/api/run/{id}, /api/schedules/{id}) allow DELETE

### File System (fs_utils.py)
- Uses `/data` persistent volume on Railway/Render, falls back to cwd
- Structure: `runs/{run_id}/`, `memory/`, `config.json`, `.env.local`, `schedules.json`
- Run files: `00_task.json`, `01_keywords.json`, ..., `status.json`, `run.log`

### Scheduler (scheduler.py)
- APScheduler with async IO
- Supports: daily, weekly, monthly, hourly, custom cron
- Schedules persisted to `schedules.json`
- Auto-registers jobs on startup

### Frontend Structure
- Next.js 14 with App Router
- API routes in `frontend/app/api/` proxy to backend
- SSE streaming at `/api/stream/[runId]` for live logs
- Key pages: / (dashboard), /task, /runs, /runs/[id], /scheduler, /tools, /memory, /settings

## Key Patterns

### Adding a New Agent
1. Create `backend/agents/{name}.py` inheriting from `BaseAgent`
2. Add to `backend/agents/__init__.py`
3. Register in `pipeline.py` stage_to_agent mapping
4. Add stage file mapping in `STAGE_FILE_MAP`
5. Update `STAGES` list if needed

### Adding a New Tool
1. Add function in `backend/tools/{module}.py`
2. Add OpenAI-compatible definition in `backend/server_tools.py` TOOL_DEFINITIONS
3. Add endpoint in `backend/main_api.py` at `/tools/{tool_name}`

### Skill Files
- Markdown files in `backend/skills/`
- Loaded by agents via `load_skill(skill_name)`
- Provide system prompts for each stage

## API Endpoints

### Pipeline
- `POST /api/run` - Start new run
- `GET /runs` - List all runs
- `GET /api/run/{id}` - Get run status
- `POST /api/run/{id}/resume` - Resume failed run
- `GET /api/run/{id}/stage/{n}` - Get stage output
- `GET /api/stream/{id}` - SSE log stream
- `GET /logs/{id}` - Get log tail

### Schedule
- `GET /api/schedules` - List schedules
- `POST /api/schedules` - Create schedule
- `DELETE /api/schedules/{id}` - Delete schedule
- `POST /api/schedules/{id}/run-now` - Trigger immediately

### Memory & Config
- `GET/POST /api/memory` - Learnings and task history
- `GET/POST /config` - Model and pipeline config
- `GET /tool-calls` - Recent tool call log

## Deployment

### Railway (Backend)
- `railway.toml` configures uvicorn startup
- Mount volume at `/data` for persistence
- Health check at `/health`

### Vercel (Frontend)
- `next.config.js` sets SSE headers for streaming
- API routes proxy to backend via `BACKEND_URL`

### Render Alternative
- `render.yaml` provided as alternative to Railway
