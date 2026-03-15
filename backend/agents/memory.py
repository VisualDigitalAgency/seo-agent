"""
Memory Agent — Pure Python, zero LLM calls.

All insights are derived directly from upstream stage outputs.
No LLM needed — every data point already exists in context.
"""
import json
import csv
from datetime import datetime
from .base import BaseAgent


class MemoryAgent(BaseAgent):

    required_tools = []  # This agent doesn't use LLM tool calls

    def update(self, context):
        self.log("Memory Agent: Aggregating run data (no LLM)...")

        kw      = context.get('keyword_research', {})
        serp    = context.get('serp_analysis', {})
        content = context.get('content_writing', {})
        onpage  = context.get('onpage_optimization', {})
        links   = context.get('internal_linking', {})
        editor  = context.get('senior_editor', {})
        analyst = context.get('analyst_review', {})

        # Use final article stats (editor > content_writing fallback)
        final        = editor if editor.get('article_html') else content
        word_count   = final.get('word_count', content.get('word_count'))
        seo_score    = onpage.get('seo_score')
        seo_after    = editor.get('seo_score_estimated_after')
        sections     = content.get('sections_covered', [])
        gaps_filled  = content.get('gaps_filled', [])
        int_links    = editor.get('internal_links_injected', [])
        ext_links    = editor.get('external_links_added', [])
        checklist    = editor.get('publication_checklist', {})
        changes      = editor.get('changes_made', [])

        # ── Build deterministic insights from stage data ──────────────────
        insights = self._derive_insights(
            kw, serp, onpage, content, editor, analyst, links
        )

        # ── Determine content format from what was actually produced ──────
        html = final.get('article_html', '')
        content_format = self._detect_format(html, content.get('recommended_format', ''))

        # ── Ranking potential from onpage score + gap coverage ────────────
        gap_coverage = len(gaps_filled) / max(len(serp.get('content_gaps', [])), 1)
        ranking_potential = (
            'high'   if (seo_score or 0) >= 80 and gap_coverage >= 0.6 else
            'medium' if (seo_score or 0) >= 65 else
            'low'
        )

        # ── Build learning record ─────────────────────────────────────────
        learning = {
            'task':            self.pipeline.task,
            'run_id':          self.pipeline.run_id,
            'target':          self.pipeline.target,
            'audience':        self.pipeline.audience,
            'date':            datetime.utcnow().strftime('%Y-%m-%d'),
            'status':          'completed',

            # Content stats
            'word_count':      word_count,
            'content_format':  content_format,
            'sections_count':  len(sections),
            'gaps_filled':     gaps_filled,

            # SEO scores
            'seo_score':       seo_score,
            'seo_score_final': seo_after or seo_score,

            # Editor stats
            'changes_applied': len(changes),
            'internal_links':  len(int_links),
            'external_links':  len(ext_links),
            'pub_checklist_passed': sum(1 for v in checklist.values() if v),
            'pub_checklist_total':  len(checklist),

            # Keywords
            'primary_keyword':   kw.get('primary'),
            'secondary_keywords': kw.get('secondary', []),
            'intent':            kw.get('intent'),

            # Competitive context
            'competitor_gaps_identified': len(serp.get('content_gaps', [])),
            'paa_questions_used':         len(serp.get('paa_questions', [])),
            'serp_features_targeted':     serp.get('serp_features_present', []),

            # Insights
            'insights':              insights,
            'ranking_potential':     ranking_potential,
            'skills_used': [
                'keyword_research', 'serp_analysis', 'content_writing',
                'onpage_optimization', 'internal_linking', 'analyst_review', 'senior_editor'
            ],
        }

        self._append_learning(learning)
        self._append_history({
            'run_id':  self.pipeline.run_id,
            'task':    self.pipeline.task,
            'status':  'done',
            'date':    learning['date'],
            'ranking': '',
            'traffic': '',
        })

        self.log(f"Memory updated. Insights: {len(insights)} | Ranking potential: {ranking_potential}")
        return {
            'learning_saved':    True,
            'insights_count':    len(insights),
            'insights':          insights,
            'ranking_potential': ranking_potential,
            'seo_score_final':   seo_after or seo_score,
        }

    # ── Deterministic insight derivation ─────────────────────────────────────

    def _derive_insights(self, kw, serp, onpage, content, editor, analyst, links) -> list:
        insights = []
        seo_score   = onpage.get('seo_score', 0)
        seo_after   = editor.get('seo_score_estimated_after', 0)
        gaps_filled = content.get('gaps_filled', [])
        gaps_total  = len(serp.get('content_gaps', []))
        paa_count   = len(serp.get('paa_questions', []))
        wc          = content.get('word_count', 0)
        wc_target   = serp.get('recommended_word_count', 2000)
        density     = onpage.get('computed_metrics', {}).get('keyword_density_pct', 0)
        changes     = editor.get('changes_made', [])
        ext_links   = editor.get('external_links_added', [])
        int_links_count = len(editor.get('internal_links_injected', []))
        checklist   = editor.get('publication_checklist', {})

        # Score improvement
        if seo_score and seo_after and seo_after > seo_score:
            insights.append(
                f"SEO score improved from {seo_score} to {seo_after}/100 after senior editor pass "
                f"({seo_after - seo_score} point gain)"
            )

        # Content gap coverage
        if gaps_filled and gaps_total:
            pct = round(len(gaps_filled) / gaps_total * 100)
            insights.append(
                f"Covered {len(gaps_filled)}/{gaps_total} identified competitor gaps ({pct}% coverage)"
            )

        # PAA integration
        if paa_count > 0:
            insights.append(
                f"{paa_count} People Also Ask questions integrated as FAQ — "
                f"targets featured snippet and PAA boxes"
            )

        # Word count vs target
        if wc and wc_target:
            ratio = wc / wc_target
            if ratio >= 0.95:
                insights.append(f"Hit word count target: {wc} words (target: {wc_target})")
            else:
                insights.append(
                    f"Word count below target: {wc} vs {wc_target} — "
                    f"consider expanding thin sections next time"
                )

        # Internal linking
        if int_links_count > 0:
            insights.append(f"{int_links_count} internal links injected by Senior Editor")

        # External authority links
        if ext_links:
            sources = [l.get('source_name', '') for l in ext_links if l.get('source_name')]
            if sources:
                insights.append(f"External authority links added: {', '.join(sources[:3])}")

        # Top improvement types applied
        change_types = [c.get('type', '') for c in changes]
        from collections import Counter
        top_types = Counter(change_types).most_common(2)
        if top_types:
            type_str = ' and '.join(f"{t} ({n}x)" for t, n in top_types)
            insights.append(f"Most common editor changes: {type_str}")

        # Checklist completeness
        if checklist:
            passed = sum(1 for v in checklist.values() if v)
            total  = len(checklist)
            if passed == total:
                insights.append("All publication checklist items passed — article is fully optimized")
            elif passed < total:
                failed = [k for k, v in checklist.items() if not v]
                insights.append(
                    f"Checklist: {passed}/{total} passed. "
                    f"Failed: {', '.join(failed[:2])}"
                )

        # Content intent
        intent = kw.get('intent', '')
        if intent:
            insights.append(
                f"Search intent: {intent} — "
                f"format '{serp.get('recommended_format', '')}' chosen to match"
            )

        return insights[:8]  # Cap at 8 meaningful insights

    def _detect_format(self, html: str, recommended: str) -> str:
        import re
        h2s = re.findall(r'<h2[^>]*>(.*?)</h2>', html, re.DOTALL | re.IGNORECASE)
        h2_text = ' '.join(h2s).lower()
        if '<table' in html and ('best' in h2_text or 'compare' in h2_text):
            return 'comparison listicle with table'
        if '<table' in html:
            return 'long-form guide with comparison table'
        if len(h2s) >= 6:
            return 'comprehensive long-form guide'
        return recommended or 'long-form article'

    def _append_learning(self, learning: dict):
        learnings_path = self.pipeline.memory_dir / 'learnings.json'
        existing = []
        if learnings_path.exists():
            try:
                existing = json.loads(learnings_path.read_text())
            except Exception:
                existing = []
        existing = [l for l in existing if l.get('run_id') != learning['run_id']]
        existing.append(learning)
        learnings_path.write_text(json.dumps(existing, indent=2))
        self.log(f"Learnings.json updated ({len(existing)} total records)")

    def _append_history(self, row: dict):
        history_path = self.pipeline.memory_dir / 'task_history.csv'
        headers      = ['run_id', 'task', 'status', 'date', 'ranking', 'traffic']
        write_header = not history_path.exists()
        with open(history_path, 'a', newline='') as f:
            import csv
            writer = csv.DictWriter(f, fieldnames=headers)
            if write_header:
                writer.writeheader()
            writer.writerow(row)
        self.log("Task history CSV updated")
