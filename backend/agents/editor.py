"""
Senior Editor Agent
Collects all upstream outputs and produces the final publication-ready article.

Inputs consumed:
  - content_writing    → original draft (article_html, article_markdown)
  - onpage_optimization → score, improvements, missing_entities, optimized title/meta
  - internal_linking   → internal_links_for_this_page
  - analyst_review     → issues_detected, recommendations, opportunities
  - keyword_research   → primary/secondary keywords, intent

Output:
  - final_html         → fully edited, link-injected, optimized article HTML
  - final_markdown     → same article in markdown
  - changes_made       → list of every edit applied (audit trail)
  - seo_score_before / after
  - publication_checklist → boolean checks before going live
"""

from .base import BaseAgent
import json
import re


class EditorAgent(BaseAgent):

    def edit(self, context: dict) -> dict:
        self.log("Senior Editor: Collecting all upstream inputs...")

        # ── Gather all inputs ─────────────────────────────────────────────
        content  = context.get('content_writing', {})
        onpage   = context.get('onpage_optimization', {})
        links    = context.get('internal_linking', {})
        analyst  = context.get('analyst_review', {})
        kw       = context.get('keyword_research', {})

        original_html     = content.get('article_html', '')
        original_markdown = content.get('article_markdown', '')

        if not original_html:
            self.log("WARNING: No article_html found in content_writing stage. "
                     "Content stage may have been truncated.", level='WARNING')

        # ── Build high/medium improvements list ───────────────────────────
        improvements = [
            imp for imp in onpage.get('improvements', [])
            if imp.get('priority') in ('high', 'medium')
        ]

        # ── Build internal links list ─────────────────────────────────────
        internal_links = links.get('internal_links_for_this_page', [])
        # Also include any recommended internal links from the onpage audit
        for rec in onpage.get('recommended_internal_links', []):
            if rec not in internal_links:
                internal_links.append(rec)

        # ── Build analyst action items ────────────────────────────────────
        analyst_actions = [
            r for r in analyst.get('recommendations', [])
            if r.get('priority') == 'high'
        ] + analyst.get('opportunities', [])

        # ── Compile missing entities ──────────────────────────────────────
        missing_entities = (
            onpage.get('missing_entities', []) +
            analyst.get('competitor_threats', [])[:2]
        )

        self.log(f"  Onpage improvements to apply: {len(improvements)}")
        self.log(f"  Internal links to inject: {len(internal_links)}")
        self.log(f"  Analyst actions: {len(analyst_actions)}")
        self.log(f"  Missing entities to add: {len(missing_entities)}")

        # ── Override max_tokens for a full article rewrite ────────────────
        self.max_tokens = 16000

        skill = self.load_skill('senior_editor')

        prompt = f"""
{skill}

════════════════════════════════════════════════
ORIGINAL DRAFT (apply your edits to THIS article)
════════════════════════════════════════════════
{original_html}

════════════════════════════════════════════════
SEO CONTEXT
════════════════════════════════════════════════
PRIMARY KEYWORD: {kw.get('primary', '')}
SECONDARY KEYWORDS: {', '.join(kw.get('secondary', [])[:6])}
TARGET AUDIENCE: {self.pipeline.audience or 'General'}
TARGET MARKET: {self.pipeline.target or 'Global'}
CURRENT SEO SCORE: {onpage.get('seo_score', 'N/A')}/100

════════════════════════════════════════════════
ON-PAGE IMPROVEMENTS TO APPLY (HIGH + MEDIUM PRIORITY)
════════════════════════════════════════════════
{json.dumps(improvements, indent=2)}

════════════════════════════════════════════════
OPTIMIZED META (use these if they score higher)
════════════════════════════════════════════════
Title tag: {onpage.get('title_tag', content.get('meta_title', ''))}
Meta description: {onpage.get('meta_description', content.get('meta_description', ''))}

════════════════════════════════════════════════
INTERNAL LINKS TO INJECT
Place each link where its context field says. Match anchor_text exactly.
════════════════════════════════════════════════
{json.dumps(internal_links, indent=2)}

════════════════════════════════════════════════
MISSING ENTITIES / SEMANTIC GAPS TO FILL
Weave these into the article naturally where relevant.
════════════════════════════════════════════════
{json.dumps(missing_entities, indent=2)}

════════════════════════════════════════════════
ANALYST RECOMMENDATIONS TO INCORPORATE
════════════════════════════════════════════════
{json.dumps(analyst_actions[:5], indent=2)}

════════════════════════════════════════════════
TASK
════════════════════════════════════════════════
Edit the original draft applying ALL of the above. Return the final article as JSON:
{{
  "title":            "final H1 title",
  "meta_title":       "final meta title (under 60 chars)",
  "meta_description": "final meta description (150-160 chars, keyword + CTA)",
  "url_slug":         "seo-friendly-slug",
  "article_html":     "COMPLETE publication-ready article HTML. Must include all injected internal links, external authority links, and applied improvements. Do NOT truncate. Do NOT use [...] placeholders.",
  "word_count":       2400,
  "primary_keyword_count": 12,
  "changes_made": [
    {{"type": "onpage_fix|link_injection|entity_added|analyst_fix|external_link|quality_edit", "description": "what was changed and where"}},
    ...
  ],
  "internal_links_injected": [
    {{"anchor_text": "...", "href": "...", "location": "where in the article"}}
  ],
  "external_links_added": [
    {{"anchor_text": "...", "href": "...", "source_name": "e.g. Harvard Business Review", "reason": "cites the statistic about X"}}
  ],
  "seo_score_before": {onpage.get('seo_score', 0)},
  "seo_score_estimated_after": 90,
  "publication_checklist": {{
    "primary_keyword_in_title": true,
    "primary_keyword_in_intro": true,
    "meta_description_optimized": true,
    "heading_hierarchy_correct": true,
    "internal_links_injected": true,
    "external_authority_links": true,
    "faq_section_present": true,
    "cta_present": true,
    "no_keyword_stuffing": true,
    "word_count_target_met": true
  }},
  "faq_schema": {{
    "@context": "https://schema.org",
    "@type": "FAQPage",
    "mainEntity": [
      {{"@type": "Question", "name": "Q?", "acceptedAnswer": {{"@type": "Answer", "text": "A."}}}}
    ]
  }},
  "editor_notes": "Brief summary of the most impactful changes made"
}}
"""

        self.log("Senior Editor: Rewriting and polishing the final article...")
        result = self.call_claude(
            system_prompt=(
                "You are a senior SEO content editor with 15 years of experience. "
                "You apply every instruction precisely. You write publication-ready content — "
                "no placeholders, no truncation, no 'etc.' You complete the full article every time."
            ),
            user_prompt=prompt
        )

        # ── Post-process: generate markdown from final HTML ───────────────
        final_html = result.get('article_html', '')
        if final_html and not result.get('article_markdown'):
            result['article_markdown'] = self._html_to_markdown(final_html)

        # ── Log the audit trail ───────────────────────────────────────────
        changes = result.get('changes_made', [])
        int_links = result.get('internal_links_injected', [])
        ext_links = result.get('external_links_added', [])

        self.log(f"Senior Editor complete:")
        self.log(f"  Total changes made:      {len(changes)}")
        self.log(f"  Internal links injected: {len(int_links)}")
        self.log(f"  External links added:    {len(ext_links)}")
        self.log(f"  Estimated SEO score:     {result.get('seo_score_estimated_after', '?')}/100")
        self.log(f"  Word count:              ~{result.get('word_count', '?')}")
        if result.get('editor_notes'):
            self.log(f"  Editor notes: {result['editor_notes']}")

        return result

    def _html_to_markdown(self, html: str) -> str:
        """Convert HTML to Markdown including tables (no external deps)."""
        import re as _re

        md = html

        # ── Tables → Markdown pipe tables ────────────────────────────────
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

        # Strip table-wrap div + convert table
        md = _re.sub(
            r'<div[^>]*class=["\']table-wrap["\'][^>]*>\s*(<table[\s\S]*?</table>)\s*</div>',
            lambda m: convert_table(type('M', (), {'group': lambda self, n: m.group(1)})()),
            md, flags=_re.DOTALL
        )
        md = _re.sub(r'<table[\s\S]*?</table>', convert_table, md, flags=_re.DOTALL)

        # ── Standard conversions ──────────────────────────────────────────
        md = _re.sub(r'<h1[^>]*>(.*?)</h1>', r'# \1', md, flags=_re.DOTALL)
        md = _re.sub(r'<h2[^>]*>(.*?)</h2>', r'\n## \1', md, flags=_re.DOTALL)
        md = _re.sub(r'<h3[^>]*>(.*?)</h3>', r'\n### \1', md, flags=_re.DOTALL)
        md = _re.sub(r'<h4[^>]*>(.*?)</h4>', r'\n#### \1', md, flags=_re.DOTALL)
        md = _re.sub(r'<strong[^>]*>(.*?)</strong>', r'**\1**', md, flags=_re.DOTALL)
        md = _re.sub(r'<b[^>]*>(.*?)</b>', r'**\1**', md, flags=_re.DOTALL)
        md = _re.sub(r'<em[^>]*>(.*?)</em>', r'_\1_', md, flags=_re.DOTALL)
        md = _re.sub(r'<i[^>]*>(.*?)</i>', r'_\1_', md, flags=_re.DOTALL)
        md = _re.sub(r'<a[^>]*href=["\']([^"\']*)["\'][^>]*>(.*?)</a>', r'[\2](\1)', md, flags=_re.DOTALL)
        md = _re.sub(r'<li[^>]*>(.*?)</li>', r'- \1', md, flags=_re.DOTALL)
        md = _re.sub(r'<[uo]l[^>]*>', '', md)
        md = _re.sub(r'</[uo]l>', '\n', md)
        md = _re.sub(r'<p[^>]*>(.*?)</p>', r'\1\n', md, flags=_re.DOTALL)
        md = _re.sub(r'<blockquote[^>]*>(.*?)</blockquote>', r'> \1', md, flags=_re.DOTALL)
        md = _re.sub(r'<div[^>]*>', '', md)
        md = _re.sub(r'</div>', '', md)
        md = _re.sub(r'<[^>]+>', '', md)
        md = _re.sub(r'\n{3,}', '\n\n', md)
        return md.strip()
