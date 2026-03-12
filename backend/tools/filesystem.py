"""
Filesystem Tool — Write / Create ONLY
No delete, remove, or unlink methods exist in this module.
The LLM can create and write files — never delete them.
"""

import os
import json
from datetime import datetime
from pathlib import Path


RUNS_DIR   = Path(os.getcwd()) / "runs"
MEMORY_DIR = Path(os.getcwd()) / "memory"

STAGE_FILE_MAP = {
    "keyword_research":    "01_keywords.json",
    "serp_analysis":       "02_serp.json",
    "content_outline":     "03_outline.json",
    "content_writing":     "04_content.json",
    "onpage_optimization": "05_onpage.json",
    "internal_linking":    "06_links.json",
    "memory_update":       "memory_update.json",
}


def write_stage_output(run_id: str, stage: str, data: dict) -> dict:
    """
    Write pipeline stage output to runs/{run_id}/{stage_file}.json
    Creates directory if needed. Overwrites if already exists (idempotent).
    """
    run_dir = RUNS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    filename = STAGE_FILE_MAP.get(stage, f"{stage}.json")
    output_path = run_dir / filename

    data["_meta"] = {
        "stage":        stage,
        "run_id":       run_id,
        "written_at":   datetime.utcnow().isoformat(),
        "written_by":   "tool_server",
    }

    output_path.write_text(json.dumps(data, indent=2))

    return {
        "written":  True,
        "path":     str(output_path),
        "stage":    stage,
        "filename": filename,
    }


def write_memory(entry: dict) -> dict:
    """
    Append a learning entry to memory/learnings.json.
    Creates file if it doesn't exist.
    """
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    learnings_path = MEMORY_DIR / "learnings.json"

    existing = []
    if learnings_path.exists():
        try:
            existing = json.loads(learnings_path.read_text())
        except Exception:
            existing = []

    entry["saved_at"] = datetime.utcnow().isoformat()

    # Deduplicate by run_id if present
    if "run_id" in entry:
        existing = [e for e in existing if e.get("run_id") != entry["run_id"]]

    existing.append(entry)
    learnings_path.write_text(json.dumps(existing, indent=2))

    return {
        "written": True,
        "total_learnings": len(existing),
        "path": str(learnings_path),
    }


def append_log(run_id: str, line: str) -> dict:
    """
    Append a line to runs/{run_id}/run.log.
    Creates log file if needed.
    """
    run_dir = RUNS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    log_path = run_dir / "run.log"

    timestamp = datetime.utcnow().strftime("%H:%M:%S")
    log_line  = f"[{timestamp}] {line}\n"

    with open(log_path, "a") as f:
        f.write(log_line)

    return {"written": True, "path": str(log_path)}
