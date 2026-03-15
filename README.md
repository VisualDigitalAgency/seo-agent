# SEO Agent — Final Production Build

Full autonomous SEO pipeline. Vercel (frontend) + Railway or Render (backend).

```
frontend/   →  Deploy to Vercel
backend/    →  Deploy to Railway or Render
```

---

## Deploy in 3 steps

### Step 1 — Deploy backend to Railway

1. Create a new Railway project
2. Connect your GitHub repo (point root to `/backend`)
3. Railway auto-detects `railway.toml` and uses gunicorn for production
4. Add a **Volume** mounted at `/data` (persistent storage)
5. Add environment variables in Railway dashboard:

```
OPENROUTER_API_KEY=sk-or-...
SERPER_API_KEY=...
SERPAPI_KEY=...           ← fallback if Serper fails
DATAFORSEO_LOGIN=...
DATAFORSEO_PASSWORD=...
GA4_PROPERTY_ID=properties/123456789
FRONTEND_URL=https://your-app.vercel.app
GSC_CREDENTIALS_PATH=/data/gsc-credentials.json
GA4_CREDENTIALS_PATH=/data/ga4-credentials.json
```

For GSC + GA4 credentials (JSON files): upload them to the `/data` volume
and set the credentials paths accordingly.

6. Deploy — Railway will auto-detect and use gunicorn with 8 workers
7. Copy your Railway backend URL (e.g. `https://seo-backend.up.railway.app`)
8. Set up Health Check at `/health` (Railway default)

---

### Step 2 — Deploy frontend to Vercel

1. Import your repo into Vercel (point root to `/frontend`)
2. Add environment variables in Vercel dashboard:

```
BACKEND_URL=https://seo-backend.up.railway.app
NEXT_PUBLIC_BACKEND_URL=https://seo-backend.up.railway.app
```

3. Deploy — Vercel auto-detects Next.js

---

### Step 3 — Configure via UI

Open your Vercel URL → Settings → add API keys.

---

## Render alternative (backend)

1. Create a new **Web Service** on Render
2. Connect your GitHub repo (point root to `/backend`)
3. Render auto-detects `render.yaml` and uses gunicorn for production
4. Add a **Persistent Disk** mounted at `/data` (1 GB minimum)
5. Add environment variables in Render dashboard:

```
OPENROUTER_API_KEY=sk-or-...
SERPER_API_KEY=...
SERPAPI_KEY=...
DATAFORSEO_LOGIN=...
DATAFORSEO_PASSWORD=...
GA4_PROPERTY_ID=properties/123456789
FRONTEND_URL=https://your-app.vercel.app
GSC_CREDENTIALS_PATH=/data/gsc-credentials.json
GA4_CREDENTIALS_PATH=/data/ga4-credentials.json
```

For GSC + GA4 credentials (JSON files): upload them to the `/data` disk
(you can use Render's shell to copy files or use `render disk` CLI).

6. Deploy — Render uses gunicorn with 8 workers, 120s timeout
7. Copy your Render backend URL (e.g. `https://seo-backend.onrender.com`)
8. Health Check automatically set at `/health`

---

## Local development

```bash
# Terminal 1 — backend
cd backend
pip install -r requirements.txt
cp ../.env.example .env
uvicorn main_api:app --port 8000 --reload   # development (hot reload)
# OR for production-like testing:
# gunicorn -c gunicorn.conf.py main_api:app

# Terminal 2 — frontend
cd frontend
npm install
echo "BACKEND_URL=http://localhost:8000" > .env.local
echo "NEXT_PUBLIC_BACKEND_URL=http://localhost:8000" >> .env.local
npm run dev
```

---

## Production considerations

- **Workers**: Gunicorn runs 8 workers by default (2 x CPU cores + 1). Adjust if needed.
- **Timeout**: 120 seconds for long-running pipeline stages.
- **Memory**: Each worker holds the full app state. Monitor RAM usage; increase plan if OOM.
- **Disk**: `/data` volume is critical — stores all run outputs, memory, and config.
- **Logs**: Access via Railway/Render dashboard. Logs stream to stdout/stderr.
- **Health**: `/health` endpoint returns `{"status":"ok","timestamp":"..."}`.
- **Rate limits**: SlowAPI middleware protects against abuse; configure in `rate_limit_middleware.py`.
- **Secrets**: ALWAYS use platform secret stores; never commit `.env` files.

---

## Architecture

```
Browser
  └── Vercel (Next.js)
        └── API routes (proxy)
              └── Railway/Render (FastAPI)
                    ├── Pipeline runner (background tasks)
                    ├── Scheduler (APScheduler)
                    ├── Tool server (Serper, DataForSEO, GSC, GA4)
                    └── /data volume (runs/, memory/, config.json)
```

## Permission model (LLM access)

| Layer | Rule |
|-------|------|
| HTTP methods | DELETE/PUT/PATCH blocked by PermissionGuard middleware |
| Request body | Destructive keywords (delete, drop, truncate) rejected |
| OAuth scopes | GSC + GA4 use `.readonly` scopes |
| filesystem.py | No delete functions exist — cannot be called |

## Pages

| Page | Path |
|------|------|
| Dashboard | / |
| New Task | /task |
| All Runs | /runs |
| Run Detail (live) | /runs/[id] |
| Scheduler | /scheduler |
| Tool Monitor | /tools |
| Memory | /memory |
| Settings | /settings |
