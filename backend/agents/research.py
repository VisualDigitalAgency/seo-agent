"""
Research Agent
Stage 01 — keyword_research:  LLM call (intent, difficulty, LSI — needs reasoning)
Stage 02 — serp_analysis:     Pure Serper.dev API parsing — zero LLM
                               Extracts competitor titles, PAA, SERP features,
                               content gaps, H2 patterns deterministically.
"""

import os
import re
import json
import requests
from collections import Counter
from .base import BaseAgent


class ResearchAgent(BaseAgent):

    # Uses search_serp tool with Serper primary + SerpAPI fallback
    required_tools = ["search_serp"]

    # ── Stage 01: Keyword Research (LLM) ─────────────────────────────────────

    def keyword_research(self, context):
        self.log("Research Agent: Starting keyword research...")
        skill    = self.load_skill('keyword_research')
        task     = self.pipeline.task
        target   = self.pipeline.target
        audience = self.pipeline.audience

        serp_data = self._fetch_serp(task)

        prompt = f"""
{skill}

TARGET KEYWORD: {task}
TARGET MARKET:  {target or 'Global'}
TARGET AUDIENCE:{audience or 'General'}
NOTES:          {self.pipeline.notes or 'None'}

LIVE SERP CONTEXT:
{json.dumps(serp_data, indent=2) if serp_data else 'No live data — use your knowledge.'}

Perform comprehensive keyword research. Return JSON:
{{
  "primary":                  "main target keyword",
  "secondary":                ["kw1","kw2","kw3","kw4","kw5"],
  "long_tail":                ["long tail 1","long tail 2","long tail 3"],
  "lsi_keywords":             ["semantic kw1","semantic kw2","semantic kw3"],
  "intent":                   "informational|commercial|transactional|navigational",
  "intent_notes":             "brief explanation",
  "volume_estimate":          "low|medium|high",
  "difficulty_estimate":      "easy|medium|hard",
  "target_market":            "{target or 'Global'}",
  "audience":                 "{audience or 'General'}",
  "competitors_observed":     ["domain1.com","domain2.com"],
  "recommended_content_type": "blog|landing page|comparison|guide|listicle"
}}
"""
        self.log("Calling LLM for keyword analysis...")
        result = self.call_claude(
            system_prompt="You are an expert SEO researcher. Analyze keywords with depth and commercial insight.",
            user_prompt=prompt
        )
        self.log(f"Keyword research complete. Primary: {result.get('primary')}")
        return result

    # ── Stage 02: SERP Analysis (pure API — zero LLM) ────────────────────────

    def serp_analysis(self, context):
        self.log("Research Agent: SERP analysis (API-only, no LLM)...")

        task    = self.pipeline.task
        kw_data = context.get('keyword_research', {})
        primary = kw_data.get('primary', task)

        raw = self._fetch_serp_full(primary, num=10)

        if not raw:
            self.log("No SERP data — building fallback analysis from keyword data", level='WARNING')
            return self._fallback_analysis(kw_data)

        result = self._parse_serp(raw, primary, kw_data)
        self.log(
            f"SERP analysis complete (API-only). "
            f"Top results: {len(result['top_results_summary'])} | "
            f"PAA: {len(result['paa_questions'])} | "
            f"Gaps: {len(result['content_gaps'])}"
        )
        return result

    # ── Pure-Python SERP parser ───────────────────────────────────────────────

    def _parse_serp(self, raw: dict, primary_kw: str, kw_data: dict) -> dict:
        organic         = raw.get('organic', [])
        paa             = raw.get('peopleAlsoAsk', [])
        related         = raw.get('relatedSearches', [])
        answer_box      = raw.get('answerBox', {})
        knowledge_graph = raw.get('knowledgeGraph', {})
        top_stories     = raw.get('topStories', [])
        videos          = raw.get('videos', [])

        # ── Top results summary ───────────────────────────────────────────
        top_results        = []
        competitor_domains = []
        all_titles         = []
        all_snippets       = []

        for r in organic[:10]:
            title   = r.get('title', '')
            url     = r.get('link', '')
            snippet = r.get('snippet', '')
            domain  = self._extract_domain(url)

            top_results.append({
                'position':     r.get('position'),
                'title':        title,
                'url':          url,
                'domain':       domain,
                'snippet':      snippet,
                'content_type': self._classify_content_type(title, snippet),
            })
            if domain:   competitor_domains.append(domain)
            if title:    all_titles.append(title)
            if snippet:  all_snippets.append(snippet)

        type_counts = Counter(r['content_type'] for r in top_results)

        # ── Competitor H2 patterns ────────────────────────────────────────
        competitor_h2_patterns = self._extract_h2_patterns(all_titles, all_snippets, primary_kw)

        # ── SERP features detected ────────────────────────────────────────
        serp_features = []
        if answer_box:       serp_features.append('answer_box')
        if knowledge_graph:  serp_features.append('knowledge_graph')
        if paa:              serp_features.append('people_also_ask')
        if top_stories:      serp_features.append('top_stories')
        if videos:           serp_features.append('videos')
        if any(r.get('sitelinks') for r in organic[:3]):
            serp_features.append('sitelinks')

        # ── PAA questions (ready-made FAQ questions) ──────────────────────
        paa_questions = [
            {'question': p.get('question', ''), 'snippet': p.get('snippet', '')}
            for p in paa if p.get('question')
        ]

        # ── Related searches ──────────────────────────────────────────────
        related_searches = [r.get('query', '') for r in related if r.get('query')]

        # ── Content gaps ──────────────────────────────────────────────────
        content_gaps = self._detect_content_gaps(
            all_titles, all_snippets, primary_kw,
            kw_data.get('secondary', []), paa_questions
        )

        # ── Missing content types ─────────────────────────────────────────
        missing_types = []
        kw_l = primary_kw.lower()
        if type_counts.get('comparison', 0) == 0 and any(w in kw_l for w in ['vs','best','top','compare']):
            missing_types.append('comparison table')
        if any(w in kw_l for w in ['cost','price','salary','roi','budget']):
            missing_types.append('cost breakdown table / estimator')
        if paa_questions and 'faq' not in ' '.join(all_titles).lower():
            missing_types.append('dedicated FAQ section targeting PAA questions')

        # ── Recommended word count ────────────────────────────────────────
        avg_snip = sum(len(s.split()) for s in all_snippets) / max(len(all_snippets), 1)
        recommended_wc = max(1500, min(4000, int(avg_snip * 18)))

        weaknesses   = self._detect_weaknesses(all_snippets, paa_questions)
        angle        = self._detect_angle_opportunity(all_titles, all_snippets, primary_kw, type_counts)
        rec_format   = self._recommend_format(primary_kw, type_counts, paa_questions)
        differentiators = self._build_differentiators(content_gaps, weaknesses, missing_types)

        return {
            'top_results_summary':       top_results,
            'competitor_domains':         list(dict.fromkeys(competitor_domains)),
            'competitor_h2_patterns':     competitor_h2_patterns,
            'paa_questions':              paa_questions,
            'related_searches':           related_searches[:10],
            'serp_features_present':      serp_features,
            'content_gaps':               content_gaps,
            'missing_content_types':      missing_types,
            'content_angle_opportunity':  angle,
            'recommended_word_count':     recommended_wc,
            'recommended_format':         rec_format,
            'competitor_weaknesses':      weaknesses,
            'differentiators':            differentiators,
            'answer_box_present':         bool(answer_box),
            'answer_box_snippet':         answer_box.get('snippet', '') if answer_box else '',
            'data_source':                'serper_api_parsed',
        }

    # ── Parsing helpers ───────────────────────────────────────────────────────

    def _extract_domain(self, url: str) -> str:
        m = re.search(r'https?://(?:www\.)?([^/]+)', url)
        return m.group(1) if m else ''

    def _classify_content_type(self, title: str, snippet: str) -> str:
        t = (title + ' ' + snippet).lower()
        if any(w in t for w in [' vs ', ' vs.', 'versus', 'compare', 'comparison']): return 'comparison'
        if any(w in t for w in ['best ', 'top ', 'list of', ' ways to']):             return 'listicle'
        if any(w in t for w in ['how to', 'tutorial', 'step-by-step', 'steps to']):  return 'guide'
        if any(w in t for w in ['review', 'tested', 'we tried']):                     return 'review'
        if any(w in t for w in ['what is', 'definition', 'meaning', 'overview']):     return 'explainer'
        if any(w in t for w in ['case study', 'success story']):                      return 'case_study'
        return 'article'

    def _extract_h2_patterns(self, titles: list, snippets: list, primary_kw: str) -> list:
        """Extract heading angles competitors use — tells content agent what to cover."""
        kw_words = set(primary_kw.lower().split())
        angles   = []

        for title in titles:
            # Split on common separators to isolate angle parts
            for part in re.split(r'\s*[\|\-\u2013\u2014:]\s*', title):
                part = part.strip()
                words = part.lower().split()
                if len(words) >= 3 and not all(w in kw_words for w in words):
                    angles.append(part)

        for snippet in snippets[:6]:
            for sent in re.split(r'[.!?]', snippet):
                sent = sent.strip()
                word_c = len(sent.split())
                if 5 <= word_c <= 14:
                    angles.append(sent)

        seen, unique = set(), []
        for a in angles:
            k = a.lower()[:40]
            if k not in seen:
                seen.add(k)
                unique.append(a)
        return unique[:12]

    def _detect_content_gaps(self, titles, snippets, primary_kw, secondary_kws, paa) -> list:
        all_top = ' '.join(titles + snippets).lower()
        gaps    = []

        # PAA questions not answered in top results
        for item in paa:
            q = item.get('question', '')
            key = re.sub(r'^(what|how|why|when|where|can|is|are|do|does)\s+', '', q.lower()).strip()
            if key and key[:30] not in all_top:
                gaps.append(f"Answer: {q}")

        # Secondary keywords with no organic coverage
        for kw in secondary_kws[:5]:
            if kw.lower() not in all_top:
                gaps.append(f"Section covering: {kw}")

        # Topic-pattern based gaps
        expected = {
            'cost':   ['hidden costs', 'cost breakdown', 'pricing factors', 'roi calculation'],
            'how to': ['common mistakes', 'prerequisites', 'tools needed', 'troubleshooting'],
            'best':   ['selection criteria', 'comparison table', 'pros and cons'],
            'guide':  ['beginner tips', 'advanced tips', 'real examples', 'checklist'],
            'vs':     ['side-by-side comparison', 'when to choose each', 'verdict'],
        }
        for trigger, sections in expected.items():
            if trigger in primary_kw.lower():
                for section in sections:
                    if section not in all_top:
                        gaps.append(f"Missing section: {section}")

        return list(dict.fromkeys(gaps))[:8]

    def _detect_weaknesses(self, snippets, paa) -> list:
        all_snip = ' '.join(snippets).lower()
        w = []
        if 'example' not in all_snip and 'case study' not in all_snip:
            w.append("Competitors lack real-world examples and case studies")
        if '%' not in all_snip and 'statistic' not in all_snip and ' data ' not in all_snip:
            w.append("No data-backed claims or statistics in top results")
        if len(paa) > 3:
            w.append(f"Top results don't directly answer {len(paa)} PAA questions")
        if 'table' not in all_snip and 'comparison' not in all_snip:
            w.append("No comparison tables in competitor content")
        return w[:4]

    def _detect_angle_opportunity(self, titles, snippets, primary_kw, type_counts) -> str:
        all_text = ' '.join(titles).lower()
        if 'guide' not in all_text and 'how to' not in all_text:
            return "Comprehensive step-by-step guide — competitors lack structured how-to content"
        if type_counts.get('comparison', 0) == 0:
            return "Comparison angle — no competitor provides a side-by-side comparison table"
        if 'example' not in ' '.join(snippets).lower():
            return "Real-world examples angle — competitors are theoretical; add case studies and data"
        return "Depth + structure angle — go deeper with better headings, data, and original insights"

    def _recommend_format(self, primary_kw, type_counts, paa) -> str:
        kw = primary_kw.lower()
        if 'how to' in kw or 'guide' in kw:   return 'long-form step-by-step guide'
        if 'best' in kw or 'top' in kw:        return 'listicle with comparison table'
        if 'vs' in kw or 'compare' in kw:      return 'comparison article with side-by-side table'
        if 'what is' in kw or 'definition' in kw: return 'explainer with FAQ section'
        if len(paa) >= 5:                       return 'FAQ-heavy long-form guide'
        return 'comprehensive long-form guide'

    def _build_differentiators(self, gaps, weaknesses, missing_types) -> list:
        diffs = []
        for g in gaps[:3]:    diffs.append(f"Fill gap: {g}")
        for w in weaknesses[:2]: diffs.append(f"Fix weakness: {w}")
        for m in missing_types[:2]: diffs.append(f"Add: {m}")
        return diffs or ["More depth, better structure, and real data than competitors"]

    def _fallback_analysis(self, kw_data: dict) -> dict:
        return {
            'top_results_summary':       [],
            'competitor_domains':         kw_data.get('competitors_observed', []),
            'competitor_h2_patterns':     [],
            'paa_questions':              [],
            'related_searches':           kw_data.get('long_tail', []),
            'serp_features_present':      [],
            'content_gaps':               [],
            'missing_content_types':      [],
            'content_angle_opportunity':  'Comprehensive in-depth guide — no live SERP data available',
            'recommended_word_count':     2000,
            'recommended_format':         kw_data.get('recommended_content_type', 'long-form guide'),
            'competitor_weaknesses':      [],
            'differentiators':            ['Comprehensive coverage with data and examples'],
            'answer_box_present':         False,
            'answer_box_snippet':         '',
            'data_source':                'fallback_no_api',
        }

    # ── API fetchers ──────────────────────────────────────────────────────────

    def _fetch_serp(self, query: str, num: int = 10) -> dict | None:
        """Slim fetch for keyword_research LLM context (organic only)."""
        raw = self._fetch_serp_full(query, num)
        if not raw:
            return None
        return {
            'organic': [
                {'position': r.get('position'), 'title': r.get('title'),
                 'link': r.get('link'),         'snippet': r.get('snippet')}
                for r in raw.get('organic', [])[:num]
            ],
        }

    def _fetch_serp_full(self, query: str, num: int = 10) -> dict | None:
        """Full Serper.dev fetch — organic + PAA + related + all features."""
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
                self.log(
                    f"SERP fetch OK: {len(data.get('organic',[]))} organic | "
                    f"{len(data.get('peopleAlsoAsk',[]))} PAA | "
                    f"{len(data.get('relatedSearches',[]))} related"
                )
                return data
            self.log(f"SERP fetch failed: {response.status_code}", level='WARNING')
        except Exception as e:
            self.log(f"SERP fetch error: {e}", level='WARNING')
        return None
