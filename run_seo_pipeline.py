#!/usr/bin/env python3
"""
Run SEO Agent Pipeline with user inputs:
Task: 'Ai agent development cost'
Target: 'Global'
Audience: 'Startups'
Domain: 'www.troniextechnologies.com'
"""

import os
import sys
import json
import subprocess
import time
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / 'backend'))

# Define user inputs
task = 'Ai agent development cost'
target = 'Global'
audience = 'Startups'
domain = 'www.troniextechnologies.com'
notes = ''

print("=" * 60)
print("STARTING SEO AGENT PIPELINE")
print("=" * 60)
print(f"Task: {task}")
print(f"Target: {target}")
print(f"Audience: {audience}")
print(f"Domain: {domain}")
print(f"Notes: {notes}")
print("=" * 60)
print()

# Create unique run ID
run_id = f"seo-{int(time.time())}"

# Build command
cmd = [
    sys.executable,
    "backend/main.py",
    "--run-id", run_id,
    "--task", task,
    "--target", target,
    "--audience", audience,
    "--domain", domain,
    "--notes", notes
]

print(f"Executing: {' '.join(cmd)}")
print()

# Run the pipeline
process = subprocess.Popen(
    cmd,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    universal_newlines=True,
    bufsize=1,
    cwd=str(Path(__file__).parent)
)

# Stream output line by line
for line in process.stdout:
    print(line, end='')

# Wait for completion
exit_code = process.wait()

print("=" * 60)
print(f"PIPELINE EXECUTION {'COMPLETE' if exit_code == 0 else 'FAILED'}")
print(f"Exit code: {exit_code}")
print(f"Run ID: {run_id}")
print(f"Results directory: runs/{run_id}")
print("=" * 60)

# Check if runs directory exists
if exit_code == 0:
    run_dir = Path('runs') / run_id
    if run_dir.exists():
        print(f"\nPipeline output files:")
        for file in sorted(run_dir.iterdir()):
            print(f"  {file.name}")

        # Check for log file
        log_file = run_dir / 'run.log'
        if log_file.exists():
            print(f"\nLast 10 lines of log:")
            with open(log_file) as f:
                lines = f.readlines()
                for line in lines[-10:]:
                    print(f"  {line.strip()}")
    else:
        print(f"\nWarning: Runs directory not found at: {run_dir}")
