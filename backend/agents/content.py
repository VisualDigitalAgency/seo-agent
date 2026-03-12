"""
Content Agent
Handles: content_outline + content_writing stages
"""

from .base import BaseAgent
import json


class ContentAgent(BaseAgent):

    def content_outline(self, context):
        self.log("Content Agent: Building content outline...")
        skill = self.load_skill('content_outline')
        kw = context.get('keyword_research', {})
        serp = context.get('serp_analysis', {})

        prompt = f"""
{skill}

PRIMARY KEYWORD: {self.pipeline.task}
TARGET AUDIENCE: {self.pipeline.audience or 'General'}
TARGET MARKET: {self.pipeline.target or 'Global'}
NOTES: {self.pipeline.notes or 'None'}

KEYWORD DATA:
{json.dumps(kw, indent=2)}

SERP INSIGHTS:
{json.dumps(serp, indent=2)}

Create a comprehensive content outline. Return JSON:
{{
  "title": "SEO-optimized H1 title (include primary keyword)",
  "meta_title": "Meta title under 60 chars",
  "meta_description": "Meta description 150-160 chars with keyword and CTA",
  "url_slug": "seo-friendly-url-slug",
  "word_count_target": 2500,
  "introduction_hook": "Opening hook concept (1-2 sentences)",
  "sections": [
    {{
      "heading": "H2 heading",
      "type": "h2",
      "key_points": ["point1", "point2"],
      "content_note": "what to cover here",
      "includes_keyword": true
    }},
    {{
      "heading": "H3 subheading",
      "type": "h3",
      "parent_h2": "parent H2 heading",
      "key_points": ["point1"],
      "content_note": "detail"
    }}
  ],
  "faq_questions": ["Q1?", "Q2?", "Q3?", "Q4?", "Q5?"],
  "cta": "Call to action concept",
  "schema_types": ["Article", "FAQPage"],
  "content_differentiators": ["what makes this better than SERP competitors"]
}}
"""
        result = self.call_claude(
            system_prompt="You are an expert SEO content strategist. Create outlines that are structured to rank and convert.",
            user_prompt=prompt
        )
        self.log(f"Outline created with {len(result.get('sections', []))} sections.")
        return result

    def content_writing(self, context):
        self.log("Content Agent: Writing full article...")
        skill = self.load_skill('seo_writer')
        outline = context.get('content_outline', {})
        kw = context.get('keyword_research', {})

        primary_kw = kw.get('primary', self.pipeline.task)
        secondary_kws = ', '.join(kw.get('secondary', [])[:5])

        prompt = f"""
{skill}

TASK: Write a complete, SEO-optimized article based on this outline.

PRIMARY KEYWORD: {primary_kw}
SECONDARY KEYWORDS: {secondary_kws}
LSI KEYWORDS: {', '.join(kw.get('lsi_keywords', []))}
TARGET AUDIENCE: {self.pipeline.audience or 'General'}
WORD COUNT TARGET: {outline.get('word_count_target', 2000)}

OUTLINE:
{json.dumps(outline, indent=2)}

WRITING REQUIREMENTS:
- Use H1 for the main title, H2 for major sections, H3 for subsections
- Include primary keyword in: title, first paragraph, at least 2 H2s, conclusion
- Use secondary keywords naturally (don't stuff)
- Include specific data, numbers, examples where relevant
- Write for E-E-A-T (Experience, Expertise, Authority, Trust)
- Include transition sentences between sections
- Write FAQ section with detailed answers
- End with a strong CTA

Return JSON:
{{
  "title": "H1 title",
  "meta_title": "meta title",
  "meta_description": "meta description",
  "url_slug": "slug",
  "article_html": "Full article in HTML with proper H tags (H1, H2, H3, p, ul, li, strong)",
  "article_markdown": "Same article in markdown",
  "word_count": 2400,
  "primary_keyword_count": 12,
  "faq_schema": {{
    "@context": "https://schema.org",
    "@type": "FAQPage",
    "mainEntity": [
      {{"@type": "Question", "name": "Q?", "acceptedAnswer": {{"@type": "Answer", "text": "A."}}}}
    ]
  }}
}}
"""
        self.log("Calling Claude for article writing (this may take a moment)...")
        result = self.call_claude(
            system_prompt="You are an expert SEO copywriter who writes articles that rank on Google and convert readers. Your writing is engaging, authoritative, and optimized.",
            user_prompt=prompt
        )
        self.log(f"Article written. Word count: {result.get('word_count', '?')}")
        return result
