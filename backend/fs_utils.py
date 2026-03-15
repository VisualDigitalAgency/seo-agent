"""
File system utilities for cloud deployment.
On Railway/Render, uses /data (persistent volume) if available,
otherwise falls back to /tmp (ephemeral — fine for dev/testing).
"""

import os
import json
import csv
import re
from datetime import datetime
from pathlib import Path


def _base() -> Path:
    """Persistent volume on Railway (/data), ephemeral fallback (/tmp)"""
    if Path("/data").exists():
        return Path("/data")
    return Path(os.getcwd())


RUNS_DIR   = lambda: _base() / "runs"
MEMORY_DIR = lambda: _base() / "memory"
CONFIG_PATH = lambda: _base() / "config.json"
ENV_PATH    = lambda: _base() / ".env.local"
SCHEDULES_PATH = lambda: _base() / "schedules.json"

# Validate run_id to prevent path traversal attacks
RUN_ID_PATTERN = re.compile(r'^run_\d{8}_\d{6}$')


def new_run_id() -> str:
    now = datetime.utcnow()
    return f"run_{now.strftime('%Y%m%d_%H%M%S')}"


def get_run_dir(run_id: str) -> Path:
    """
    Get the run directory for a given run_id.
    Validates run_id to prevent path traversal attacks.
    run_id must match pattern: run_YYYYMMDD_HHMMSS
    """
    if not RUN_ID_PATTERN.match(run_id):
        raise ValueError(f"Invalid run_id format: {run_id}. Must match pattern: run_YYYYMMDD_HHMMSS")

    p = RUNS_DIR() / run_id
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_log_path(run_id: str) -> Path:
    return get_run_dir(run_id) / "run.log"


def get_status_path(run_id: str) -> Path:
    return get_run_dir(run_id) / "status.json"


def init_run(run_id: str, task_data: dict):
    RUNS_DIR().mkdir(parents=True, exist_ok=True)
    run_dir = get_run_dir(run_id)
    (run_dir / "00_task.json").write_text(json.dumps(task_data, indent=2))
    write_status(run_id, {
        "run_id":  run_id,
        "task":    task_data.get("task", ""),
        "target":  task_data.get("target", ""),
        "audience":task_data.get("audience", ""),
        "domain":  task_data.get("domain", ""),
        "status":  "pending",
        "stages": {
            "keyword_research":    "pending",
            "serp_analysis":       "pending",
            "content_writing":     "pending",
            "onpage_optimization": "pending",
            "internal_linking":    "pending",
            "analyst_review":      "pending",
            "senior_editor":       "pending",
            "memory_update":       "pending",
        },
        "resume_from": None,
        "error":       None,
        "started_at":  datetime.utcnow().isoformat(),
    })


def read_status(run_id: str) -> dict | None:
    p = get_status_path(run_id)
    if not p.exists():
        return None
    return json.loads(p.read_text())


def write_status(run_id: str, data: dict):
    data["last_updated"] = datetime.utcnow().isoformat()
    get_status_path(run_id).write_text(json.dumps(data, indent=2))


def read_stage_output(run_id: str, stage_num: int) -> dict | None:
    run_dir = RUNS_DIR() / run_id
    if not run_dir.exists():
        return None
    prefix = str(stage_num).zfill(2) + "_"
    files  = [f for f in run_dir.iterdir() if f.name.startswith(prefix)]
    if not files:
        return None
    return json.loads(files[0].read_text())


def list_all_runs() -> list:
    d = RUNS_DIR()
    if not d.exists():
        return []
    runs = []
    for entry in sorted(d.iterdir(), reverse=True):
        if entry.is_dir():
            s = read_status(entry.name)
            runs.append(s or {"run_id": entry.name, "task": "Unknown", "status": "unknown", "stages": {}})
    return runs


def delete_run(run_id: str):
    import shutil
    d = RUNS_DIR() / run_id
    if d.exists():
        shutil.rmtree(d)


def read_log_tail(run_id: str, lines: int = 200) -> list[str]:
    p = get_log_path(run_id)
    if not p.exists():
        return []
    content = p.read_text(errors="ignore")
    return [l for l in content.split("\n") if l][-lines:]


# ── Memory ────────────────────────────────────────────────────────────────────

def read_learnings() -> list:
    p = MEMORY_DIR() / "learnings.json"
    if not p.exists():
        return []
    try:
        return json.loads(p.read_text())
    except Exception:
        return []


def write_learnings(data: list):
    MEMORY_DIR().mkdir(parents=True, exist_ok=True)
    (MEMORY_DIR() / "learnings.json").write_text(json.dumps(data, indent=2))


def read_task_history() -> list:
    p = MEMORY_DIR() / "task_history.csv"
    if not p.exists():
        return []
    rows = []
    with open(p, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(dict(row))
    return rows


def _escape_csv_field(value: str) -> str:
    """Escape CSV fields to prevent formula injection.
    Prefix fields starting with =, +, -, @, tab, or CR with single quote.
    """
    if value and value[0] in ('=', '+', '-', '@', '\t', '\r', '\n'):
        return f"'{value}"
    return value


def append_task_history(row: dict):
    MEMORY_DIR().mkdir(parents=True, exist_ok=True)
    p = MEMORY_DIR() / "task_history.csv"
    headers = ["run_id", "task", "status", "date", "ranking", "traffic"]
    write_header = not p.exists()

    # Escape all string values in the row
    escaped_row = {k: _escape_csv_field(str(v)) if isinstance(v, str) else str(v) for k, v in row.items()}

    with open(p, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers, extrasaction="ignore")
        if write_header:
            writer.writeheader()
        writer.writerow(escaped_row)


# ── Config ────────────────────────────────────────────────────────────────────

def read_config(validate: bool = True) -> dict:
    """
    Read configuration from config.json.

    Args:
        validate: If True, validate against schema and return safe defaults on failure.
                 If False, return raw config (may be used by migration scripts).
    """
    from config_validator import get_validated_config
    return get_validated_config()


def write_config(data: dict):
    CONFIG_PATH().write_text(json.dumps(data, indent=2))


def read_env_keys() -> dict:
    keys = ["OPENROUTER_API_KEY", "SERPER_API_KEY", "SERPAPI_KEY",
            "DATAFORSEO_LOGIN", "DATAFORSEO_PASSWORD",
            "GSC_CREDENTIALS_PATH", "GA4_CREDENTIALS_PATH", "GA4_PROPERTY_ID"]
    result = {}
    p = ENV_PATH()
    content = p.read_text() if p.exists() else ""
    for key in keys:
        import re
        m = re.search(rf"^{key}=(.*)$", content, re.MULTILINE)
        result[key] = m.group(1).strip() if m else os.environ.get(key, "")
    return result


def write_env_keys(env: dict):
    p = ENV_PATH()
    content = p.read_text() if p.exists() else ""
    for key, val in env.items():
        import re
        if re.search(rf"^{key}=", content, re.MULTILINE):
            content = re.sub(rf"^{key}=.*$", f"{key}={val}", content, flags=re.MULTILINE)
        else:
            content += f"\n{key}={val}"
    p.write_text(content.strip() + "\n")


# ── Schedules ─────────────────────────────────────────────────────────────────

def read_schedules() -> list:
    p = SCHEDULES_PATH()
    if not p.exists():
        return []
    try:
        return json.loads(p.read_text())
    except Exception:
        return []


def write_schedules(schedules: list):
    SCHEDULES_PATH().write_text(json.dumps(schedules, indent=2))
