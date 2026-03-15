"""
On-Page Optimization Agent

Mechanical scores (5/8 categories) computed in Python — zero LLM tokens:
  - title_optimization   : keyword presence, char length
  - meta_description     : keyword presence, 150-160 char check
  - keyword_density      : exact count / word count
  - heading_structure    : H1 uniqueness, H2/H3 counts, nesting
  - word_count_score     : target vs actual

LLM call only for the 3 qualitative categories that genuinely need reasoning:
  - content_depth        : comprehensiveness, E-E-A-T signals
  - readability          : paragraph length, sentence structure, flow
  - entity_coverage      : named entities, semantic concepts

Prompt sent to LLM is ~70% smaller than the original.
"""

import re
import json
from .base import BaseAgent


class OnPageAgent(BaseAgent):

    required_tools = []  # This agent doesn't use LLM tool calls

    def optimize(self, context):
        self.log("On-Page Agent: Computing mechanical scores...")

        content = context.get('content_writing', {})
        kw      = context.get('keyword_research', {})

        html      = content.get('article_html', '')
        markdown  = content.get('article_markdown', '')
        article   = markdown or re.sub(r'<[^>]+>', ' ', html)

        primary_kw   = kw.get('primary', self.pipeline.task)
        secondary_kws= kw.get('secondary', [])
        meta_title   = content.get('meta_title', '')
        meta_desc    = content.get('meta_description', '')
        word_target  = context.get('serp_analysis', {}).get('recommended_word_count', 2000)

        # ── Step 1: Deterministic scores ─────────────────────────────────
        mech = self._compute_mechanical(
            html, article, primary_kw, secondary_kws,
            meta_title, meta_desc, word_target
        )
        self.log(
            f"Mechanical: title={mech['title_score']} meta={mech['meta_score']} "
            f"density={mech['density_score']} headings={mech['heading_score']} "
            f"wordcount={mech['wordcount_score']}"
        )

        # ── Step 2: LLM for the 3 qualitative scores only ────────────────
        self.log("Calling LLM for content_depth, readability, entity_coverage only...")
        skill = self.load_skill('onpage_optimizer')

        # Send only first 3000 chars — mechanical analysis already covered structure
        article_preview = article[:3000]

        prompt = f"""
{skill}

PRIMARY KEYWORD: {primary_kw}
SECONDARY KEYWORDS: {', '.join(secondary_kws)}

PRE-COMPUTED MECHANICAL METRICS (do NOT re-score these):
- Title length: {mech['title_len']} chars (optimal: 50-60) | KW present: {mech['kw_in_title']}
- Meta desc length: {mech['meta_len']} chars (optimal: 150-160) | KW present: {mech['kw_in_meta']}
- Keyword density: {mech['density_pct']}% (optimal: 1.0-1.5%) | Count: {mech['kw_count']}
- Word count: {mech['word_count']} words (target: {word_target})
- H1 count: {mech['h1_count']} (should be 1) | H2s: {mech['h2_count']} | H3s: {mech['h3_count']}
- Internal links: {mech['internal_links']} | External links: {mech['external_links']}
- KW in first 100 words: {mech['kw_in_intro']}

ARTICLE PREVIEW (first 3000 chars):
{article_preview}

Score ONLY these 3 categories (the mechanical ones are already computed):
1. content_depth    — comprehensiveness, subtopic coverage, E-E-A-T signals, data/examples
2. readability      — paragraph length, sentence complexity, flow, scanability
3. entity_coverage  — named entities, semantic concepts, related terms present/missing

Also provide:
- improvements list (high/medium/low priority — only what the article needs)
- missing_entities list
- recommended_internal_links list
- optimized title_tag and meta_description if improvements are needed

Return JSON:
{{
  "scores": {{
    "content_depth":   {{"score": 80, "notes": "..."}},
    "readability":     {{"score": 75, "notes": "..."}},
    "entity_coverage": {{"score": 70, "notes": "..."}}
  }},
  "improvements": [
    {{"priority": "high",   "action": "...", "expected_impact": "..."}},
    {{"priority": "medium", "action": "...", "expected_impact": "..."}}
  ],
  "missing_entities": ["entity1", "entity2"],
  "recommended_internal_links": [
    {{"anchor_text": "...", "target_topic": "..."}}
  ],
  "schema_recommendations": ["FAQPage", "Article"],
  "title_tag": "optimized title under 60 chars",
  "meta_description": "optimized meta 150-160 chars"
}}
"""
        qualitative = self.call_claude(
            system_prompt="You are an expert on-page SEO specialist. Provide precise, actionable analysis.",
            user_prompt=prompt
        )

        # ── Step 3: Merge mechanical + qualitative into full result ───────
        result = self._merge_scores(mech, qualitative, primary_kw, secondary_kws)
        self.log(f"On-page complete. SEO Score: {result['seo_score']}/100 ({result['grade']})")
        return result

    # ── Deterministic scorer ──────────────────────────────────────────────────

    def _compute_mechanical(self, html, article, primary_kw, secondary_kws,
                             meta_title, meta_desc, word_target) -> dict:
        text  = article.lower()
        words = [w for w in text.split() if len(w) > 1]
        wc    = len(words)
        kw_l  = primary_kw.lower()

        # Title
        title_len     = len(meta_title)
        kw_in_title   = kw_l in meta_title.lower()
        title_score   = self._score_title(title_len, kw_in_title)

        # Meta description
        meta_len      = len(meta_desc)
        kw_in_meta    = kw_l in meta_desc.lower()
        meta_score    = self._score_meta(meta_len, kw_in_meta)

        # Keyword density
        kw_count      = text.count(kw_l)
        density_pct   = round((kw_count / wc) * 100, 2) if wc else 0
        density_score = self._score_density(density_pct)

        # Heading structure
        h1s = re.findall(r'<h1[^>]*>(.*?)</h1>', html, re.DOTALL | re.IGNORECASE)
        h2s = re.findall(r'<h2[^>]*>(.*?)</h2>', html, re.DOTALL | re.IGNORECASE)
        h3s = re.findall(r'<h3[^>]*>(.*?)</h3>', html, re.DOTALL | re.IGNORECASE)
        h1_count      = len(h1s)
        h2_count      = len(h2s)
        h3_count      = len(h3s)
        kw_in_intro   = kw_l in ' '.join(text.split()[:100])
        heading_score = self._score_headings(h1_count, h2_count, h3_count, h1s, kw_l)

        # Word count vs target
        wordcount_score = self._score_wordcount(wc, word_target)

        # Links
        all_links = re.findall(r'<a\s[^>]*href=["\']([^"\']+)["\']', html, re.IGNORECASE)
        internal_links = sum(1 for l in all_links if not l.startswith('http'))
        external_links = sum(1 for l in all_links if l.startswith('http'))

        # Secondary keyword coverage
        secondary_covered = sum(1 for sk in secondary_kws if sk.lower() in text)

        return {
            'title_score':       title_score,
            'meta_score':        meta_score,
            'density_score':     density_score,
            'heading_score':     heading_score,
            'wordcount_score':   wordcount_score,
            'title_len':         title_len,
            'meta_len':          meta_len,
            'kw_in_title':       kw_in_title,
            'kw_in_meta':        kw_in_meta,
            'kw_count':          kw_count,
            'density_pct':       density_pct,
            'word_count':        wc,
            'h1_count':          h1_count,
            'h2_count':          h2_count,
            'h3_count':          h3_count,
            'h1_unique':         h1_count == 1,
            'kw_in_intro':       kw_in_intro,
            'internal_links':    internal_links,
            'external_links':    external_links,
            'secondary_covered': secondary_covered,
        }

    def _score_title(self, length, kw_present) -> int:
        score = 0
        if 50 <= length <= 60:   score += 60
        elif 45 <= length <= 65: score += 40
        elif length > 0:         score += 20
        if kw_present:           score += 40
        return min(score, 100)

    def _score_meta(self, length, kw_present) -> int:
        score = 0
        if 150 <= length <= 160: score += 60
        elif 130 <= length <= 170: score += 40
        elif length > 0:           score += 20
        if kw_present:             score += 40
        return min(score, 100)

    def _score_density(self, pct) -> int:
        if 1.0 <= pct <= 1.5:   return 100
        if 0.7 <= pct < 1.0:    return 80
        if 1.5 < pct <= 2.0:    return 75
        if 0.4 <= pct < 0.7:    return 60
        if 2.0 < pct <= 3.0:    return 50
        return 30

    def _score_headings(self, h1c, h2c, h3c, h1s, kw_l) -> int:
        score = 0
        if h1c == 1:   score += 40
        elif h1c > 1:  score += 10
        if h2c >= 4:   score += 30
        elif h2c >= 2: score += 20
        if h3c >= 2:   score += 20
        if h1s and kw_l in ' '.join(re.sub(r'<[^>]+>', '', h) for h in h1s).lower():
            score += 10
        return min(score, 100)

    def _score_wordcount(self, actual, target) -> int:
        if target <= 0: return 70
        ratio = actual / target
        if 0.9 <= ratio <= 1.3:  return 100
        if 0.7 <= ratio < 0.9:   return 80
        if 1.3 < ratio <= 1.5:   return 85
        if 0.5 <= ratio < 0.7:   return 60
        return 40

    # ── Merge mechanical + qualitative ───────────────────────────────────────

    def _merge_scores(self, mech: dict, qualitative: dict, primary_kw: str, secondary_kws: list) -> dict:
        q_scores = qualitative.get('scores', {})

        scores = {
            'title_optimization': {
                'score': mech['title_score'],
                'notes': (
                    f"Length: {mech['title_len']} chars | "
                    f"KW {'present' if mech['kw_in_title'] else 'MISSING'}"
                )
            },
            'meta_description': {
                'score': mech['meta_score'],
                'notes': (
                    f"Length: {mech['meta_len']} chars | "
                    f"KW {'present' if mech['kw_in_meta'] else 'MISSING'}"
                )
            },
            'keyword_density': {
                'score': mech['density_score'],
                'notes': (
                    f"Primary KW: {mech['density_pct']}% ({mech['kw_count']} occurrences) | "
                    f"Optimal: 1.0-1.5%"
                )
            },
            'heading_structure': {
                'score': mech['heading_score'],
                'notes': (
                    f"H1: {mech['h1_count']} ({'OK' if mech['h1_unique'] else 'PROBLEM: multiple H1s'}) | "
                    f"H2s: {mech['h2_count']} | H3s: {mech['h3_count']}"
                )
            },
            'word_count': {
                'score': mech['wordcount_score'],
                'notes': f"{mech['word_count']} words"
            },
            'content_depth':   q_scores.get('content_depth',   {'score': 75, 'notes': ''}),
            'readability':     q_scores.get('readability',     {'score': 75, 'notes': ''}),
            'entity_coverage': q_scores.get('entity_coverage', {'score': 70, 'notes': ''}),
        }

        # Weighted average (weights sum to 100)
        weights = {
            'title_optimization': 12,
            'meta_description':    8,
            'keyword_density':    12,
            'heading_structure':  12,
            'word_count':          6,
            'content_depth':      20,
            'readability':        15,
            'entity_coverage':    15,
        }
        seo_score = round(
            sum(scores[k]['score'] * weights[k] for k in weights) / sum(weights.values())
        )

        grade = (
            'A+' if seo_score >= 95 else 'A'  if seo_score >= 90 else
            'B+' if seo_score >= 85 else 'B'  if seo_score >= 80 else
            'C+' if seo_score >= 75 else 'C'  if seo_score >= 70 else
            'D+' if seo_score >= 65 else 'D'
        )

        # Build keyword density detail
        kw_density_detail = {'primary': f"{mech['density_pct']}%"}

        return {
            'seo_score':   seo_score,
            'grade':       grade,
            'scores':      scores,
            'improvements':             qualitative.get('improvements', []),
            'missing_entities':         qualitative.get('missing_entities', []),
            'keyword_density':          kw_density_detail,
            'recommended_internal_links': qualitative.get('recommended_internal_links', []),
            'schema_recommendations':   qualitative.get('schema_recommendations', ['Article', 'FAQPage']),
            'title_tag':               qualitative.get('title_tag', ''),
            'meta_description':        qualitative.get('meta_description', ''),
            'computed_metrics': {
                'word_count':         mech['word_count'],
                'h1_count':           mech['h1_count'],
                'h2_count':           mech['h2_count'],
                'h3_count':           mech['h3_count'],
                'internal_links':     mech['internal_links'],
                'external_links':     mech['external_links'],
                'kw_in_intro':        mech['kw_in_intro'],
                'secondary_covered':  mech['secondary_covered'],
            },
        }
