"""
Pipeline Orchestrator — Checkpoint + Resume Logic
Each stage writes output JSON before moving to the next.
On resume, completed stages are skipped entirely (no API calls wasted).
"""

import os
import sys
import json
import time
import logging
from datetime import datetime
from pathlib import Path
from pythonjsonlogger import jsonlogger


class Pipeline:
    STAGES = [
        'keyword_research',
        'serp_analysis',
        'content_writing',
        'onpage_optimization',
        'internal_linking',
        'analyst_review',
        'senior_editor',
        'memory_update',
    ]

    STAGE_FILE_MAP = {
        'keyword_research':   '01_keywords.json',
        'serp_analysis':      '02_serp.json',
        'content_writing':    '04_content.json',
        'onpage_optimization':'05_onpage.json',
        'internal_linking':   '06_links.json',
        'analyst_review':     '07_analyst.json',
        'senior_editor':      '08_final.json',
        'memory_update':      'memory_update.json',
    }

    def __init__(self, run_id, task, target='', audience='', domain='', notes=''):
        self.run_id = run_id
        self.task = task
        self.target = target
        self.audience = audience
        self.domain = domain
        self.notes = notes

        # Paths
        self.runs_dir = Path(os.getcwd()) / 'runs'
        self.run_dir = self.runs_dir / run_id
        self.memory_dir = Path(os.getcwd()) / 'memory'
        self.skills_dir = Path(os.path.dirname(os.path.abspath(__file__))) / 'skills'
        self.log_path = self.run_dir / 'run.log'
        self.status_path = self.run_dir / 'status.json'

        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.memory_dir.mkdir(parents=True, exist_ok=True)

        # Setup logging
        self._setup_logging()

        # Load config
        self.config = self._load_config()

    def _setup_logging(self):
        self.logger = logging.getLogger(self.run_id)
        self.logger.setLevel(logging.DEBUG)
        self.logger.handlers = []

        # Structured JSON logging
        class CustomJsonFormatter(jsonlogger.JsonFormatter):
            def add_fields(self, log_record, record, message_dict):
                super(CustomJsonFormatter, self).add_fields(log_record, record, message_dict)
                if not log_record.get('timestamp'):
                    log_record['timestamp'] = datetime.utcnow().isoformat()
                if not log_record.get('run_id'):
                    log_record['run_id'] = self.run_id
                if not log_record.get('stage'):
                    log_record['stage'] = None

        # File handler with JSON format
        fh = logging.FileHandler(self.log_path)
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(CustomJsonFormatter())

        # Console handler with JSON format
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logging.DEBUG)
        ch.setFormatter(CustomJsonFormatter())

        self.logger.addHandler(fh)
        self.logger.addHandler(ch)

    def _load_config(self):
        config_path = Path(os.getcwd()) / 'config.json'
        defaults = {
            'model': {'model': 'openrouter/free', 'max_tokens': 65536, 'temperature': 0.3},
            'pipeline': {'max_retries': 3, 'retry_delay': 5, 'timeout_per_stage': 120}
        }
        if config_path.exists():
            try:
                with open(config_path) as f:
                    loaded = json.load(f)
                defaults.update(loaded)
            except Exception:
                pass
        return defaults

    def log(self, msg, level='INFO', stage=None, extra=None):
        """
        Log a message with structured context.

        Args:
            msg: The log message
            level: Log level (INFO, ERROR, WARNING, DEBUG)
            stage: Optional stage name to include in log
            extra: Optional dict of additional fields to include
        """
        logger = getattr(self.logger, level.lower(), self.logger.info)

        # Build extra fields
        log_extra = {'stage': stage} if stage else {'stage': None}
        if extra:
            log_extra.update(extra)

        logger(msg, extra=log_extra) if extra else logger(msg)

    # ── Status management ─────────────────────────────────────────
    def read_status(self):
        if not self.status_path.exists():
            return {}
        with open(self.status_path) as f:
            return json.load(f)

    def update_status(self, status=None, stage=None, stage_status=None, error=None, resume_from=None):
        current = self.read_status()
        if status:
            current['status'] = status
        if stage and stage_status:
            current.setdefault('stages', {})[stage] = stage_status
        if error is not None:
            current['error'] = error
        if resume_from is not None:
            current['resume_from'] = resume_from
        current['last_updated'] = datetime.utcnow().isoformat()
        with open(self.status_path, 'w') as f:
            json.dump(current, f, indent=2)

    # ── Stage file helpers ────────────────────────────────────────
    def stage_output_path(self, stage):
        return self.run_dir / self.STAGE_FILE_MAP[stage]

    def stage_output_exists(self, stage):
        return self.stage_output_path(stage).exists()

    def write_stage_output(self, stage, data):
        path = self.stage_output_path(stage)
        data['_meta'] = {
            'stage': stage,
            'run_id': self.run_id,
            'generated_at': datetime.utcnow().isoformat(),
            'cached': False,
        }
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
        self.log(f"✓ Stage output written: {self.STAGE_FILE_MAP[stage]}")
        return data

    def read_stage_output(self, stage):
        path = self.stage_output_path(stage)
        if not path.exists():
            return None
        with open(path) as f:
            return json.load(f)

    def load_skill(self, skill_name):
        skill_path = self.skills_dir / f'{skill_name}.md'
        if skill_path.exists():
            return skill_path.read_text()
        return f'# {skill_name}\nAnalyze and produce high-quality SEO output for this skill.'

    # ── Main entry points ─────────────────────────────────────────
    def run(self):
        self.log(f"{'='*60}")
        self.log(f"SEO AGENT PIPELINE STARTING")
        self.log(f"Run ID: {self.run_id}")
        self.log(f"Task: {self.task}")
        if self.target: self.log(f"Target: {self.target}")
        if self.audience: self.log(f"Audience: {self.audience}")
        self.log(f"{'='*60}")

        self.update_status(status='running', error=None)
        self._execute_stages(self.STAGES)

    def resume(self):
        status = self.read_status()
        stages = status.get('stages', {})

        # Determine which stages to run
        to_run = [s for s in self.STAGES if stages.get(s) != 'done']
        resume_from = to_run[0] if to_run else None

        self.log(f"{'='*60}")
        self.log(f"RESUMING PIPELINE — Run ID: {self.run_id}")
        self.log(f"Resume from: {resume_from}")
        self.log(f"Skipping done stages: {[s for s in self.STAGES if stages.get(s) == 'done']}")
        self.log(f"{'='*60}")

        self.update_status(status='running', error=None, resume_from=resume_from)
        self._execute_stages(to_run)

    def _execute_stages(self, stages_to_run):
        context = {}  # Accumulated data passed between stages

        # Pre-load existing outputs into context
        for stage in self.STAGES:
            if self.stage_output_exists(stage):
                context[stage] = self.read_stage_output(stage)

        for stage in stages_to_run:
            self.log(f"\n[STAGE:{stage}] RUNNING")
            self.update_status(stage=stage, stage_status='running')

            # Check cache
            if self.stage_output_exists(stage):
                self.log(f"[STAGE:{stage}] Cache hit — loading from {self.STAGE_FILE_MAP[stage]}")
                context[stage] = self.read_stage_output(stage)
                self.update_status(stage=stage, stage_status='done')
                self.log(f"[STAGE:{stage}] DONE (cached)")
                continue

            # Execute with retries
            max_retries = self.config.get('pipeline', {}).get('max_retries', 3)
            retry_delay = self.config.get('pipeline', {}).get('retry_delay', 5)
            last_error = None

            for attempt in range(max_retries):
                try:
                    result = self._run_stage(stage, context)
                    context[stage] = result
                    self.update_status(stage=stage, stage_status='done')
                    self.log(f"[STAGE:{stage}] DONE")
                    last_error = None
                    break
                except Exception as e:
                    last_error = str(e)
                    self.log(f"[STAGE:{stage}] Attempt {attempt+1}/{max_retries} failed: {e}", level='ERROR')
                    if attempt < max_retries - 1:
                        self.log(f"Retrying in {retry_delay}s...")
                        time.sleep(retry_delay * (attempt + 1))  # Exponential backoff

            if last_error:
                self.log(f"[STAGE:{stage}] FAILED after {max_retries} attempts: {last_error}", level='ERROR')
                self.update_status(stage=stage, stage_status='failed', status='failed', error=f'{stage}: {last_error}')
                return  # Stop pipeline on failure

        self.log(f"\n{'='*60}")
        self.log("PIPELINE COMPLETE ✓")
        self.log(f"{'='*60}")
        self.update_status(status='done', error=None)

    def _run_stage(self, stage, context):
        """Dispatch to the correct agent method"""
        import importlib

        # Lazy import agents to avoid loading all at startup
        stage_to_agent = {
            'keyword_research':    ('agents.research',  'ResearchAgent',  'keyword_research'),
            'serp_analysis':       ('agents.research',  'ResearchAgent',  'serp_analysis'),
            'content_writing':     ('agents.content',   'ContentAgent',   'content_writing'),
            'onpage_optimization': ('agents.onpage',    'OnPageAgent',    'optimize'),
            'internal_linking':    ('agents.links',     'LinksAgent',     'build_cluster'),
            'analyst_review':      ('agents.analyst',   'AnalystAgent',   'analyze'),
            'senior_editor':       ('agents.editor',    'EditorAgent',    'edit'),
            'memory_update':       ('agents.memory',    'MemoryAgent',    'update'),
        }

        if stage not in stage_to_agent:
            raise ValueError(f"Unknown stage: {stage}")

        module_path, class_name, method_name = stage_to_agent[stage]
        module = importlib.import_module(module_path)
        AgentClass = getattr(module, class_name)

        agent = AgentClass(pipeline=self)
        method = getattr(agent, method_name)
        result = method(context)
        return self.write_stage_output(stage, result)
