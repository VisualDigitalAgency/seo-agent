"""
Analyst Agent
Handles: analyst_review stage
Uses GSC + GA4 + SERP to detect ranking drops, CTR issues, content decay.
Generates specific actionable recommendations and optionally flags for refresh.
"""

import os
import json
import requests
from .base import BaseAgent

TOOL_SERVER = os.environ.get("TOOL_SERVER_URL", "http://localhost:8000")


class AnalystAgent(BaseAgent):

    def analyze(self, context: dict) -> dict:
        self.log("Analyst Agent: Starting performance analysis...")

        content   = context.get("content_writing", {})
        onpage    = context.get("onpage_optimization", {})
        kw        = context.get("keyword_research", {})
        domain    = self.pipeline.domain
        site_url  = f"https://{domain}" if domain and not domain.startswith("http") else domain

        analysis_data = {}

        # ── Pull live data via tool server ─────────────────────────────────
        if site_url:
            self.log("Fetching GSC rankings...")
            gsc_rankings = self._tool("gsc_get_rankings", {"site_url": site_url, "days": 30})
            analysis_data["gsc_rankings"] = gsc_rankings

            self.log("Fetching GSC top queries...")
            gsc_queries = self._tool("gsc_top_queries", {"site_url": site_url, "days": 30, "limit": 20})
            analysis_data["gsc_top_queries"] = gsc_queries

            self.log("Detecting GSC ranking drops...")
            gsc_drops = self._tool("gsc_detect_ranking_drops", {"site_url": site_url, "drop_threshold": 2.0, "days": 28})
            analysis_data["gsc_drops"] = gsc_drops

            self.log("Fetching GA4 top pages...")
            ga4_top = self._tool("ga4_get_top_pages", {"days": 30, "limit": 20})
            analysis_data["ga4_top_pages"] = ga4_top

            self.log("Detecting GA4 traffic drops...")
            ga4_drops = self._tool("ga4_detect_traffic_drops", {"days": 30, "drop_pct": 15.0})
            analysis_data["ga4_drops"] = ga4_drops
        else:
            self.log("No domain set — skipping GSC/GA4 analysis", level="WARNING")

        # ── SERP check for current content ────────────────────────────────
        primary_kw = kw.get("primary", self.pipeline.task)
        self.log(f"Checking current SERP for '{primary_kw}'...")
        serp_data = self._tool("search_serp", {"query": primary_kw, "num_results": 10})
        analysis_data["serp_snapshot"] = serp_data

        # ── Ask Claude to analyze everything ──────────────────────────────
        skill = self.load_skill("analyst")

        prompt = f"""
{skill}

TASK / PRIMARY KEYWORD: {self.pipeline.task}
DOMAIN: {domain or 'Not set'}
CURRENT SEO SCORE: {onpage.get("seo_score", "N/A")}/100
CONTENT WORD COUNT: {context.get("content_writing", {}).get("word_count", "N/A")}

LIVE DATA COLLECTED:
{json.dumps(analysis_data, indent=2)[:4000]}

Analyze the performance data and generate a comprehensive analyst report.
Return JSON:
{{
  "overall_health": "good|warning|critical",
  "health_score": 75,
  "summary": "2-3 sentence executive summary",

  "ranking_analysis": {{
    "current_position": null,
    "position_trend": "improving|stable|declining|unknown",
    "impressions_trend": "up|stable|down|unknown",
    "ctr": null,
    "notes": ""
  }},

  "traffic_analysis": {{
    "sessions_trend": "up|stable|down|unknown",
    "top_traffic_pages": [],
    "traffic_drop_alerts": []
  }},

  "issues_detected": [
    {{
      "type": "ranking_drop|ctr_issue|traffic_drop|content_decay|keyword_gap",
      "severity": "high|medium|low",
      "description": "specific description",
      "affected_page": "",
      "data_point": ""
    }}
  ],

  "recommendations": [
    {{
      "priority": "high|medium|low",
      "action": "specific action to take",
      "expected_impact": "what it will improve",
      "effort": "low|medium|high"
    }}
  ],

  "content_refresh_needed": true,
  "refresh_reason": "why refresh is needed",
  "competitor_threats": ["competitor or trend threatening rankings"],
  "opportunities": ["new opportunity detected in SERP"]
}}
"""
        self.log("Claude analyzing performance data...")
        result = self.call_claude(
            system_prompt="You are an expert SEO analyst. Analyze performance data and generate specific, data-backed recommendations.",
            user_prompt=prompt,
        )

        result["raw_data"] = {
            "gsc_drops_count":  len(analysis_data.get("gsc_drops", {}).get("drops", [])),
            "ga4_drops_count":  len(analysis_data.get("ga4_drops", {}).get("drops", [])),
            "serp_snapshot_at": serp_data.get("query", ""),
        }

        self.log(f"Analysis complete. Health: {result.get('overall_health')} | Issues: {len(result.get('issues_detected', []))}")
        return result

    def _tool(self, tool_name: str, args: dict) -> dict:
        """Call a tool via the tool server HTTP endpoint"""
        try:
            resp = requests.post(
                f"{TOOL_SERVER}/tools/{tool_name}",
                json=args,
                timeout=20,
            )
            if resp.status_code == 200:
                return resp.json()
            return {"error": f"Tool {tool_name} returned {resp.status_code}"}
        except Exception as e:
            self.log(f"Tool call {tool_name} failed: {e}", level="WARNING")
            return {"error": str(e)}
