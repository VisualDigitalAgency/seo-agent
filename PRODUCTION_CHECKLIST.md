# SEO Agent - Production Deployment Checklist

## 🚀 Pre-Deployment Verification

### Environment Setup
- [ ] **API Keys Configured:**
  - `OPENROUTER_API_KEY` - LLM provider (required)
  - `SERPER_API_KEY` - Primary search API
  - `SERPAPI_KEY` - Fallback search API
  - `DATAFORSEO_LOGIN` / `DATAFORSEO_PASSWORD` - Keyword research
  - `GSC_CREDENTIALS_PATH` - Google Search Console
  - `GA4_CREDENTIALS_PATH` / `GA4_PROPERTY_ID` - Google Analytics 4
  - `API_KEYS` - Comma-separated admin API keys
  - `FRONTEND_URL` - CORS origin

### Backend Configuration
- [ ] **Config Validation:** Run `python -c "from backend.config_validator import validate_config; validate_config()"`
- [ ] **Security Settings:**
  - API key authentication enabled
  - CORS origins properly configured
  - Rate limiting limits appropriate for expected traffic
- [ ] **Logging Configuration:**
  - Structured logging enabled
  - Log level set to INFO (DEBUG for troubleshooting)
  - Log file rotation configured

### Frontend Configuration
- [ ] **Environment Variables:**
  - `BACKEND_URL` pointing to backend
  - `NEXT_PUBLIC_BACKEND_URL` for frontend API calls
- [ ] **Build Verification:** `npm run build` completes without errors
- [ ] **Security Headers:** CSP, HSTS, X-Frame-Options configured

## 🚀 Deployment Steps

### Railway Deployment
1. **Push to Railway:**
   ```bash
   git push railway main
   ```

2. **Verify Environment Variables:**
   - Check Railway dashboard for all required env vars
   - Set `FRONTEND_URL` to Vercel deployment URL

3. **Health Check:**
   - Verify `GET /health` returns 200
   - Check dependencies (API keys, filesystem)

4. **Initial Testing:**
   - Test `GET /metrics` endpoint
   - Verify tool endpoints respond correctly

### Vercel Deployment
1. **Push to Vercel:**
   ```bash
   git push vercel main
   ```

2. **Environment Variables:**
   - Set `BACKEND_URL` to Railway backend URL
   - Configure build settings

3. **Security Headers:**
   - Verify CSP headers in `vercel.json`
   - Test CORS with backend

## 📊 Post-Deployment Verification

### Core Functionality
- [ ] **Pipeline Test:**
  - Start test pipeline: `POST /api/run` with sample task
  - Monitor progress via SSE streaming
  - Verify all 8 stages complete successfully

- [ ] **Tool Integration:**
  - Test search tools (Serper, SERPAPI)
  - Verify keyword research tools
  - Check GA4 and GSC integrations

- [ ] **Authentication:**
  - Test API key authentication
  - Verify rate limiting works
  - Confirm permission guards block destructive operations

### Performance & Monitoring
- [ ] **Health Endpoints:**
  - `GET /health` - All dependencies green
  - `GET /metrics` - Metrics collection working
  - `GET /tool-calls` - Tool logs accessible

- [ ] **Monitoring Setup:**
  - Verify metrics collection to Prometheus
  - Test alert routing configuration
  - Check log aggregation

### Security Verification
- [ ] **Security Headers:**
  - CSP headers present
  - HSTS enabled
  - X-Content-Type-Options nosniff
  - Referrer-Policy configured

- [ ] **Authentication Tests:**
  - Invalid API keys rejected
  - Rate limiting enforced
  - Permission guards working

## 🔧 Scaling Configuration

### Backend (Gunicorn)
- **Workers:** Set to `2 * CPU + 1` (e.g., 5 workers for 2 CPU)
- **Timeout:** 300 seconds for pipeline operations
- **Graceful Timeout:** 120 seconds for restarts
- **Worker Class:** sync for CPU-bound tasks

### Frontend (Vercel)
- **Build Optimization:** Code splitting enabled
- **Asset Caching:** CDN configured for static assets
- **Security Headers:** CSP with nonce for inline scripts

## 🔄 Performance Tuning

### Caching Strategy
- **Redis Integration:** For shared cache across workers
- **Tool Result Caching:** 5-minute TTL for search APIs
- **Database Connection Pooling:** If using PostgreSQL

### Monitoring Thresholds
- **Error Rate:** Alert if >5% for 5 minutes
- **Latency:** Alert if >2s for 95th percentile
- **Uptime:** Alert if <99.9% over 1 hour
- **Circuit Breakers:** Alert when any provider trips

## 🚨 Troubleshooting Guide

### Common Issues
1. **Pipeline Stuck:**
   - Check `/health` for dependency status
   - Verify API keys in logs
   - Check circuit breaker status

2. **High Error Rates:**
   - Monitor `/metrics` for error trends
   - Check tool call logs for specific failures
   - Verify rate limiting not being exceeded

3. **Frontend Issues:**
   - Check browser console for CORS errors
   - Verify SSE reconnection logic
   - Test API proxy functionality

### Recovery Procedures
- **Restart Backend:** `railway restart`
- **Clear Cache:** If Redis enabled, flush cache
- **Reset Circuit Breakers:** Automatic after timeout
- **Rollback:** Use Railway rollbacks if needed

## 📝 Maintenance Tasks

### Weekly
- [ ] Review monitoring dashboards
- [ ] Check log aggregation for errors
- [ ] Verify backup configurations
- [ ] Test alerting functionality

### Monthly
- [ ] Review security logs
- [ ] Update dependencies
- [ ] Check performance metrics
- [ ] Validate backup restoration

### Quarterly
- [ ] Security audit
- [ ] Performance optimization review
- [ ] Cost analysis
- [ ] Documentation updates

## 📊 Success Criteria

### Technical
- [ ] All endpoints respond within SLA
- [ ] Pipeline completes in <15 minutes
- [ ] Error rate <1% over 24 hours
- [ ] Monitoring system fully operational

### Business
- [ ] Content generation quality meets standards
- [ ] Tool integrations working reliably
- [ ] User authentication functional
- [ ] Security model preventing unauthorized access

## 📚 References

- **Architecture:** `CLAUDE.md` - Core project instructions
- **Security Model:** `backend/middleware/guards.py` - Permission system
- **Monitoring:** `backend/metrics.py` - Metrics collection
- **Deployment:** `backend/railway.toml` - Railway config
- **Frontend:** `frontend/vercel.json` - Vercel config

---

**Last Updated:** 2026-03-15
**Status:** Ready for Production
**Verification:** Complete all checkboxes before marking as production-ready