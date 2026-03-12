"""
Research Agent
Handles: keyword_research + serp_analysis stages
Uses Serper.dev for live SERP data, Claude for analysis.
"""

import os
import json
import requests
from .base import BaseAgent


class ResearchAgent(BaseAgent):

    def keyword_research(self, context):
        self.log("Research Agent: Starting keyword research...")
        skill = self.load_skill('keyword_research')
        task = self.pipeline.task
        target = self.pipeline.target
        audience = self.pipeline.audience

        # Try to get live SERP data first
        serp_data = self._fetch_serp(task)

        prompt = f"""
{skill}

TARGET KEYWORD: {task}
TARGET MARKET: {target or 'Global'}
TARGET AUDIENCE: {audience or 'General'}
NOTES: {self.pipeline.notes or 'None'}

LIVE SERP CONTEXT:
{json.dumps(serp_data, indent=2) if serp_data else 'No live data available — use your knowledge.'}

Perform comprehensive keyword research. Return JSON with this exact structure:
{{
  "primary": "main target keyword",
  "secondary": ["kw1", "kw2", "kw3", "kw4", "kw5"],
  "long_tail": ["long tail 1", "long tail 2", "long tail 3"],
  "lsi_keywords": ["semantic kw1", "semantic kw2"],
  "intent": "informational|commercial|transactional|navigational",
  "intent_notes": "brief explanation",
  "volume_estimate": "low|medium|high",
  "difficulty_estimate": "easy|medium|hard",
  "target_market": "{target or 'Global'}",
  "audience": "{audience or 'General'}",
  "competitors_observed": ["domain1.com", "domain2.com"],
  "recommended_content_type": "blog|landing page|comparison|guide|listicle"
}}
"""
        self.log("Calling Claude for keyword analysis...")
        result = self.call_claude(
            system_prompt="You are an expert SEO researcher. Analyze keywords with depth and commercial insight.",
            user_prompt=prompt
        )
        self.log(f"Keyword research complete. Primary: {result.get('primary')}")
        return result

    def serp_analysis(self, context):
        self.log("Research Agent: Starting SERP analysis...")
        skill = self.load_skill('serp_analysis')
        task = self.pipeline.task
        kw_data = context.get('keyword_research', {})

        # Fetch SERP for primary keyword
        serp_data = self._fetch_serp(task, num=10)

        prompt = f"""
{skill}

PRIMARY KEYWORD: {task}
KEYWORD DATA: {json.dumps(kw_data, indent=2)}

LIVE SERP RESULTS:
{json.dumps(serp_data, indent=2) if serp_data else 'No live data — infer from knowledge.'}

Analyze the SERP and identify gaps and opportunities. Return JSON:
{{
  "top_results_summary": [
    {{"position": 1, "title": "...", "url": "...", "type": "article|video|featured_snippet"}}
  ],
  "content_gaps": ["gap1", "gap2", "gap3"],
  "missing_content_types": ["e.g. interactive calculator", "comparison table"],
  "serp_features_present": ["featured snippet", "people also ask", "videos"],
  "content_angle_opportunity": "the specific angle that will beat current results",
  "recommended_word_count": 2000,
  "recommended_format": "long-form guide|listicle|comparison|FAQ-heavy",
  "competitor_weaknesses": ["weakness1", "weakness2"],
  "differentiators": ["how our content should differ"]
}}
"""
        self.log("Calling Claude for SERP analysis...")
        result = self.call_claude(
            system_prompt="You are an expert SEO analyst specializing in SERP analysis and competitive intelligence.",
            user_prompt=prompt
        )
        self.log("SERP analysis complete.")
        return result

    def _fetch_serp(self, query, num=10):
        """Fetch SERP data from Serper.dev"""
        api_key = os.environ.get('SERPER_API_KEY', '')
        if not api_key:
            self.log("SERPER_API_KEY not set — skipping live SERP fetch", level='WARNING')
            return None

        try:
            response = requests.post(
                'https://google.serper.dev/search',
                headers={'X-API-KEY': api_key, 'Content-Type': 'application/json'},
                json={'q': query, 'num': num},
                timeout=15
            )
            if response.status_code == 200:
                data = response.json()
                # Extract relevant fields only
                organic = data.get('organic', [])
                simplified = [
                    {
                        'position': r.get('position'),
                        'title': r.get('title'),
                        'link': r.get('link'),
                        'snippet': r.get('snippet'),
                    }
                    for r in organic[:num]
                ]
                self.log(f"SERP fetch successful: {len(simplified)} results")
                return {'organic': simplified, 'searchParameters': data.get('searchParameters', {})}
            else:
                self.log(f"SERP fetch failed: {response.status_code}", level='WARNING')
                return None
        except Exception as e:
            self.log(f"SERP fetch error: {e}", level='WARNING')
            return None
