"""On-Page Optimization Agent"""
from .base import BaseAgent
import json


class OnPageAgent(BaseAgent):

    def optimize(self, context):
        self.log("On-Page Agent: Analyzing and scoring content...")
        skill = self.load_skill('onpage_optimizer')
        content = context.get('content_writing', {})
        kw = context.get('keyword_research', {})
        outline = context.get('content_outline', {})

        article_text = content.get('article_markdown', content.get('article_html', ''))[:3000]  # Truncate for API

        prompt = f"""
{skill}

PRIMARY KEYWORD: {kw.get('primary', self.pipeline.task)}
SECONDARY KEYWORDS: {', '.join(kw.get('secondary', []))}
META TITLE: {content.get('meta_title', '')}
META DESCRIPTION: {content.get('meta_description', '')}
ARTICLE PREVIEW (first 3000 chars):
{article_text}

Perform a full on-page SEO audit. Return JSON:
{{
  "seo_score": 84,
  "grade": "B+",
  "scores": {{
    "title_optimization": {{"score": 90, "notes": "..."}},
    "meta_description": {{"score": 85, "notes": "..."}},
    "keyword_density": {{"score": 80, "notes": "primary kw at X%"}},
    "heading_structure": {{"score": 90, "notes": "..."}},
    "content_depth": {{"score": 85, "notes": "..."}},
    "readability": {{"score": 80, "notes": "..."}},
    "schema_markup": {{"score": 75, "notes": "..."}},
    "entity_coverage": {{"score": 70, "notes": "..."}}
  }},
  "improvements": [
    {{"priority": "high", "action": "specific action", "expected_impact": "what it improves"}},
    {{"priority": "medium", "action": "...", "expected_impact": "..."}}
  ],
  "missing_entities": ["entity1", "entity2"],
  "keyword_density": {{"primary": "1.2%", "secondary": {{"kw": "0.5%"}}}},
  "recommended_internal_links": [
    {{"anchor_text": "...", "target_topic": "page to link to"}}
  ],
  "schema_recommendations": ["FAQPage", "Article"],
  "title_tag": "Optimized title tag under 60 chars",
  "meta_description": "Optimized meta description 150-160 chars"
}}
"""
        result = self.call_claude(
            system_prompt="You are an expert on-page SEO specialist. Analyze content with precision and provide actionable improvements.",
            user_prompt=prompt
        )
        self.log(f"On-page analysis complete. SEO Score: {result.get('seo_score', '?')}/100")
        return result
