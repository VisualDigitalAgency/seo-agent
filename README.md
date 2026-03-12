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
3. Railway auto-detects `railway.toml` and runs uvicorn
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
```

For GSC + GA4 credentials (JSON files): upload them to the `/data` volume
and set `GSC_CREDENTIALS_PATH=/data/gsc-credentials.json`

6. Copy your Railway backend URL (e.g. `https://seo-backend.up.railway.app`)

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

Use `render.yaml` instead of `railway.toml`. Same env vars.
Render also supports persistent disk mounts at `/data`.

---

## Local development

```bash
# Terminal 1 — backend
cd backend
pip install -r requirements.txt
cp ../.env.example .env
uvicorn main_api:app --port 8000 --reload

# Terminal 2 — frontend
cd frontend
npm install
echo "BACKEND_URL=http://localhost:8000" > .env.local
echo "NEXT_PUBLIC_BACKEND_URL=http://localhost:8000" >> .env.local
npm run dev
```

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
