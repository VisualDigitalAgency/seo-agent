"""
Memory Agent — Extracts and stores learnings from the completed run.
Updates task_history.csv and learnings.json for future retrieval.
"""
import json
import csv
import os
from datetime import datetime
from pathlib import Path
from .base import BaseAgent


class MemoryAgent(BaseAgent):

    def update(self, context):
        self.log("Memory Agent: Extracting and storing run learnings...")

        kw = context.get('keyword_research', {})
        content = context.get('content_writing', {})
        onpage = context.get('onpage_optimization', {})
        links = context.get('internal_linking', {})

        # Ask Claude to extract meaningful learnings
        prompt = f"""
Based on this completed SEO pipeline run, extract actionable learnings for future runs.

TASK: {self.pipeline.task}
KEYWORD DATA SUMMARY: {json.dumps(kw, indent=2)[:1000]}
ONPAGE SCORE: {onpage.get('seo_score', 'N/A')}
ONPAGE IMPROVEMENTS: {json.dumps(onpage.get('improvements', []), indent=2)[:500]}
CONTENT WORD COUNT: {content.get('word_count', 'N/A')}
SKILLS USED: keyword_research, serp_analysis, content_outline, content_writing, onpage_optimization, internal_linking

Extract learnings. Return JSON:
{{
  "insights": [
    "Specific learning 1 — what worked or what to do differently",
    "Specific learning 2",
    "Specific learning 3"
  ],
  "skills_used": ["keyword_research", "serp_analysis", "content_outline", "content_writing", "onpage_optimization", "internal_linking"],
  "content_format_that_worked": "describe format",
  "estimated_ranking_potential": "high|medium|low",
  "notes": "any additional notes for next time"
}}
"""
        learnings_extracted = self.call_claude(
            system_prompt="You are a learning extraction system. Extract concise, actionable insights from SEO run data.",
            user_prompt=prompt
        )

        # Build learning record
        learning = {
            'task': self.pipeline.task,
            'run_id': self.pipeline.run_id,
            'target': self.pipeline.target,
            'audience': self.pipeline.audience,
            'insights': learnings_extracted.get('insights', []),
            'skills_used': learnings_extracted.get('skills_used', []),
            'seo_score': onpage.get('seo_score'),
            'word_count': content.get('word_count'),
            'content_format': learnings_extracted.get('content_format_that_worked'),
            'ranking': None,  # Updated later via analyst
            'traffic': None,
            'date': datetime.utcnow().strftime('%Y-%m-%d'),
            'status': 'completed',
        }

        # Write to learnings.json
        self._append_learning(learning)

        # Write to task_history.csv
        self._append_history({
            'run_id': self.pipeline.run_id,
            'task': self.pipeline.task,
            'status': 'done',
            'date': learning['date'],
            'ranking': '',
            'traffic': '',
        })

        self.log(f"Memory updated. Insights stored: {len(learning['insights'])}")
        return {
            'learning_saved': True,
            'insights_count': len(learning['insights']),
            'insights': learning['insights'],
        }

    def _append_learning(self, learning):
        memory_dir = self.pipeline.memory_dir
        learnings_path = memory_dir / 'learnings.json'

        existing = []
        if learnings_path.exists():
            try:
                existing = json.loads(learnings_path.read_text())
            except Exception:
                existing = []

        # Remove duplicate if run_id exists
        existing = [l for l in existing if l.get('run_id') != learning['run_id']]
        existing.append(learning)

        learnings_path.write_text(json.dumps(existing, indent=2))
        self.log(f"Learnings.json updated ({len(existing)} total records)")

    def _append_history(self, row):
        memory_dir = self.pipeline.memory_dir
        history_path = memory_dir / 'task_history.csv'

        headers = ['run_id', 'task', 'status', 'date', 'ranking', 'traffic']
        write_header = not history_path.exists()

        with open(history_path, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            if write_header:
                writer.writeheader()
            writer.writerow(row)

        self.log("Task history CSV updated")
