"""
Content Agent
Handles: content_writing (merged with outline — single LLM call)

The outline stage is eliminated. Instead, the full research context
(competitor H2 patterns, PAA questions, content gaps, SERP angle)
is fed directly into the writing prompt so the LLM plans and writes
in one pass — same quality, one fewer round-trip.
"""

from .base import BaseAgent
import re as _re
import json


class ContentAgent(BaseAgent):

    required_tools = []  # This agent doesn't use LLM tool calls

    def content_writing(self, context):
        self.log("Content Agent: Writing full article (outline + write in one pass)...")
        self.max_tokens = 16000

        skill    = self.load_skill('seo_writer')
        kw       = context.get('keyword_research', {})
        serp     = context.get('serp_analysis', {})

        primary_kw     = kw.get('primary', self.pipeline.task)
        secondary_kws  = ', '.join(kw.get('secondary', [])[:5])
        lsi_kws        = ', '.join(kw.get('lsi_keywords', []))
        word_target    = serp.get('recommended_word_count', 2200)
        rec_format     = serp.get('recommended_format', 'long-form guide')
        intent         = kw.get('intent', 'informational')
        audience       = self.pipeline.audience or 'General'

        # ── Build rich competitor intelligence block ───────────────────────
        h2_patterns    = serp.get('competitor_h2_patterns', [])
        paa_questions  = serp.get('paa_questions', [])
        content_gaps   = serp.get('content_gaps', [])
        angle          = serp.get('content_angle_opportunity', '')
        differentiators= serp.get('differentiators', [])
        weaknesses     = serp.get('competitor_weaknesses', [])
        missing_types  = serp.get('missing_content_types', [])
        answer_box     = serp.get('answer_box_present', False)
        answer_snippet = serp.get('answer_box_snippet', '')
        top_results    = serp.get('top_results_summary', [])

        # Competitor title list — what angles/headings already exist
        competitor_titles = [r.get('title', '') for r in top_results[:5] if r.get('title')]

        # FAQ questions from PAA (exact questions users are asking)
        faq_from_paa = [q['question'] for q in paa_questions if q.get('question')][:6]

        prompt = f"""
{skill}

════════════════════════════════════════════════
TASK
════════════════════════════════════════════════
Write a complete, publication-ready SEO article.
Target keyword: {primary_kw}
Secondary keywords: {secondary_kws}
LSI keywords: {lsi_kws}
Search intent: {intent}
Target audience: {audience}
Target market: {self.pipeline.target or 'Global'}
Word count target: {word_target}
Recommended format: {rec_format}
Notes: {self.pipeline.notes or 'None'}

════════════════════════════════════════════════
COMPETITOR INTELLIGENCE
(Use this to plan your outline — cover what competitors missed)
════════════════════════════════════════════════
WINNING ANGLE: {angle}

COMPETITOR TITLES (what already ranks — your headings must go further):
{chr(10).join(f'  - {t}' for t in competitor_titles)}

HEADING PATTERNS COMPETITORS USE (cover these + add what they miss):
{chr(10).join(f'  - {h}' for h in h2_patterns[:10])}

CONTENT GAPS (topics competitors do NOT cover — you MUST cover these):
{chr(10).join(f'  - {g}' for g in content_gaps)}

COMPETITOR WEAKNESSES (fix these in your article):
{chr(10).join(f'  - {w}' for w in weaknesses)}

DIFFERENTIATORS (what makes your article better):
{chr(10).join(f'  - {d}' for d in differentiators)}

MISSING CONTENT TYPES (add these):
{chr(10).join(f'  - {m}' for m in missing_types)}

{"ANSWER BOX OPPORTUNITY: Write your intro paragraph to directly answer: " + answer_snippet if answer_box and answer_snippet else ""}

════════════════════════════════════════════════
FAQ QUESTIONS (from People Also Ask — use EXACTLY these as FAQ headings)
════════════════════════════════════════════════
{chr(10).join(f'  {i+1}. {q}' for i, q in enumerate(faq_from_paa)) if faq_from_paa else '  Use your best judgment for FAQ questions based on the topic.'}

════════════════════════════════════════════════
WRITING REQUIREMENTS
════════════════════════════════════════════════
1. Write ONE H1 containing the primary keyword
2. Write 5-8 H2 sections — cover competitor patterns + fill all content gaps
3. Use H3s for subsections within H2s
4. Primary keyword in: H1, first paragraph, at least 2 H2s, conclusion
5. Use secondary and LSI keywords naturally throughout
6. Include at least ONE table (comparison, data, pricing, timeline, or feature list)
   Wrap in: <div class="table-wrap"><table>...</table></div>
7. Include real numbers, statistics, and specific examples — not vague claims
8. Write for E-E-A-T: show expertise, cite sources inline, be specific
9. Introduction: hook in first sentence + primary keyword in first 100 words
10. FAQ section: use the exact PAA questions above as <h3> headings
11. Conclusion: summary paragraph + specific CTA
12. COMPLETE THE FULL ARTICLE — no truncation, no "[continues...]" placeholders

Return JSON:
{{
  "title":            "H1 title containing primary keyword",
  "meta_title":       "Meta title under 60 chars with primary keyword",
  "meta_description": "Meta description 150-160 chars with keyword and CTA",
  "url_slug":         "seo-friendly-url-slug",
  "article_html":     "COMPLETE article HTML. Must include: H1, 5-8 H2s, H3 subsections, at least one <div class=\\"table-wrap\\"><table>, FAQ section using PAA questions, conclusion with CTA. Use <p>, <ul>, <li>, <strong>, <a> appropriately. Full article — no placeholders.",
  "word_count":       {word_target},
  "primary_keyword_count": 10,
  "sections_covered": ["list every H2 you wrote"],
  "gaps_filled":      ["list which content gaps you addressed"],
  "faq_schema": {{
    "@context": "https://schema.org",
    "@type": "FAQPage",
    "mainEntity": [
      {{"@type": "Question", "name": "Q?", "acceptedAnswer": {{"@type": "Answer", "text": "A."}}}}
    ]
  }}
}}
"""
        self.log("Calling LLM for article (outline + write in one pass)...")
        result = self.call_claude(
            system_prompt=(
                "You are an expert SEO copywriter. You write complete, publication-ready articles "
                "that rank on Google. You never truncate. You cover every gap and requirement given. "
                "Your articles are specific, data-backed, and genuinely useful."
            ),
            user_prompt=prompt
        )
        self.log(
            f"Article written. "
            f"Word count: {result.get('word_count','?')} | "
            f"Sections: {len(result.get('sections_covered', []))} | "
            f"Gaps filled: {len(result.get('gaps_filled', []))}"
        )
        if result.get('article_html') and not result.get('article_markdown'):
            result['article_markdown'] = self._html_to_markdown(result['article_html'])
        return result

    def _html_to_markdown(self, html: str) -> str:
        """Convert HTML to Markdown including tables (no external deps)."""
        md = html

        def convert_table(m):
            table_html = m.group(0)
            header_cells = _re.findall(r'<th[^>]*>(.*?)</th>', table_html, _re.DOTALL)
            header_cells = [_re.sub(r'<[^>]+>', '', c).strip() for c in header_cells]
            body_rows_raw = _re.findall(r'<tr[^>]*>(.*?)</tr>', table_html, _re.DOTALL)
            data_rows = []
            for row in body_rows_raw:
                cells = _re.findall(r'<td[^>]*>(.*?)</td>', row, _re.DOTALL)
                cells = [_re.sub(r'<[^>]+>', '', c).strip() for c in cells]
                if cells:
                    data_rows.append(cells)
            if not header_cells and data_rows:
                header_cells = data_rows.pop(0)
            if not header_cells:
                return ''
            col_count = max(len(header_cells), max((len(r) for r in data_rows), default=0))
            header_cells += [''] * (col_count - len(header_cells))
            data_rows = [r + [''] * (col_count - len(r)) for r in data_rows]
            lines = ['| ' + ' | '.join(header_cells) + ' |',
                     '| ' + ' | '.join(['---'] * col_count) + ' |']
            for row in data_rows:
                lines.append('| ' + ' | '.join(row) + ' |')
            return '\n' + '\n'.join(lines) + '\n'

        md = _re.sub(
            r'<div[^>]*class=["\']table-wrap["\'][^>]*>\s*(<table[\s\S]*?</table>)\s*</div>',
            lambda m: convert_table(type('M', (), {'group': lambda self, n: m.group(1)})()),
            md, flags=_re.DOTALL
        )
        md = _re.sub(r'<table[\s\S]*?</table>', convert_table, md, flags=_re.DOTALL)
        md = _re.sub(r'<h1[^>]*>(.*?)</h1>', r'# \1',     md, flags=_re.DOTALL)
        md = _re.sub(r'<h2[^>]*>(.*?)</h2>', r'\n## \1',  md, flags=_re.DOTALL)
        md = _re.sub(r'<h3[^>]*>(.*?)</h3>', r'\n### \1', md, flags=_re.DOTALL)
        md = _re.sub(r'<h4[^>]*>(.*?)</h4>', r'\n#### \1',md, flags=_re.DOTALL)
        md = _re.sub(r'<strong[^>]*>(.*?)</strong>', r'**\1**', md, flags=_re.DOTALL)
        md = _re.sub(r'<b[^>]*>(.*?)</b>',           r'**\1**', md, flags=_re.DOTALL)
        md = _re.sub(r'<em[^>]*>(.*?)</em>',          r'_\1_',  md, flags=_re.DOTALL)
        md = _re.sub(r'<i[^>]*>(.*?)</i>',            r'_\1_',  md, flags=_re.DOTALL)
        md = _re.sub(r'<a[^>]*href=["\']([^"\']*)["\'][^>]*>(.*?)</a>', r'[\2](\1)', md, flags=_re.DOTALL)
        md = _re.sub(r'<li[^>]*>(.*?)</li>', r'- \1', md, flags=_re.DOTALL)
        md = _re.sub(r'<[uo]l[^>]*>', '', md)
        md = _re.sub(r'</[uo]l>', '\n', md)
        md = _re.sub(r'<p[^>]*>(.*?)</p>', r'\1\n', md, flags=_re.DOTALL)
        md = _re.sub(r'<blockquote[^>]*>(.*?)</blockquote>', r'> \1', md, flags=_re.DOTALL)
        md = _re.sub(r'<div[^>]*>', '', md)
        md = _re.sub(r'</div>', '',   md)
        md = _re.sub(r'<[^>]+>', '',  md)
        md = _re.sub(r'\n{3,}', '\n\n', md)
        return md.strip()
