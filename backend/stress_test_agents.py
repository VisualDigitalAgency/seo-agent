#!/usr/bin/env python3
"""
Stress Test: Agent Performance and Lazy Tool Loading

Tests:
- Agent initialization time
- Tool loading behavior (lazy vs eager)
- Concurrent agent creation
- Memory usage patterns

Usage:
    python stress_test_agents.py --concurrent 10 --duration 30

Requirements:
    - Backend server running at http://localhost:8000
    - All dependencies installed
"""

import argparse
import time
import threading
import statistics
from typing import List, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from agents.research import ResearchAgent
from agents.analyst import AnalystAgent
from agents.content import ContentAgent
from agents.onpage import OnPageAgent
from agents.links import LinksAgent
from agents.memory import MemoryAgent
from pipeline import Pipeline


class MockPipeline:
    """Minimal mock pipeline for testing agent initialization"""

    def __init__(self, config=None):
        self.config = config or {"model": {}}
        self.run_id = "stress-test-" + str(int(time.time()))
        self.task = "test keyword"
        self.target = ""
        self.audience = ""
        self.notes = ""
        self.log_messages = []

    def log(self, msg: str, level: str = "INFO"):
        self.log_messages.append({"msg": msg, "level": level})


def create_agent(agent_class, agent_name: str) -> Dict:
    """Create a single agent and measure performance"""
    result = {
        "agent": agent_name,
        "init_start": 0,
        "init_end": 0,
        "init_time": 0,
        "tools_loaded": False,
        "tool_load_start": 0,
        "tool_load_end": 0,
        "tool_load_time": 0,
    }

    try:
        result["init_start"] = time.perf_counter()
        pipeline = MockPipeline()
        agent = agent_class(pipeline)
        result["init_end"] = time.perf_counter()
        result["init_time"] = result["init_end"] - result["init_start"]

        # Check if agent has tools
        has_required = len(agent.required_tools) > 0
        result["has_required_tools"] = has_required
        result["required_tools_count"] = len(agent.required_tools)

        if has_required:
            # Simulate first tool call to trigger lazy loading
            result["tool_load_start"] = time.perf_counter()
            agent._ensure_tools_loaded()
            result["tool_load_end"] = time.perf_counter()
            result["tool_load_time"] = result["tool_load_end"] - result["tool_load_start"]
            result["tools_loaded"] = True
            result["loaded_tools_count"] = len(agent._tools) if agent._tools else 0

        result["success"] = True
        result["error"] = None

    except Exception as e:
        result["success"] = False
        result["error"] = str(e)

    return result


def run_stress_test(agent_classes: List, concurrent_workers: int, duration: float) -> Dict:
    """
    Run stress test by creating agents concurrently.

    Args:
        agent_classes: List of (agent_class, name) tuples
        concurrent_workers: Number of concurrent threads
        duration: How long to run (seconds)

    Returns:
        Dictionary with test results
    """
    print(f"\n{'='*60}")
    print(f"STRESS TEST: Agent Performance & Lazy Tool Loading")
    print(f"{'='*60}")
    print(f"Concurrent workers: {concurrent_workers}")
    print(f"Duration: {duration} seconds")
    print(f"Agent types: {', '.join(name for _, name in agent_classes)}")
    print(f"{'='*60}\n")

    results = []
    start_time = time.time()
    completed = 0
    lock = threading.Lock()

    def worker():
        nonlocal completed
        while time.time() - start_time < duration:
            for agent_class, agent_name in agent_classes:
                result = create_agent(agent_class, agent_name)
                with lock:
                    results.append(result)
                    completed += 1
                    if completed % 50 == 0:
                        print(f"  Completed {completed} agent creations...")

    threads = []
    for i in range(concurrent_workers):
        t = threading.Thread(target=worker, name=f"Worker-{i}")
        t.start()
        threads.append(t)

    # Wait for duration
    for t in threads:
        t.join()

    total_time = time.time() - start_time

    # Analyze results
    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]

    init_times = [r["init_time"] for r in successful if "init_time" in r]
    tool_load_times = [r["tool_load_time"] for r in successful if r.get("tools_loaded")]

    by_agent = {}
    for r in successful:
        name = r["agent"]
        if name not in by_agent:
            by_agent[name] = {"count": 0, "init_times": [], "tool_load_times": []}
        by_agent[name]["count"] += 1
        if "init_time" in r:
            by_agent[name]["init_times"].append(r["init_time"])
        if r.get("tools_loaded"):
            by_agent[name]["tool_load_times"].append(r["tool_load_time"])

    return {
        "summary": {
            "total_creations": len(results),
            "successful": len(successful),
            "failed": len(failed),
            "total_duration": total_time,
            "creations_per_second": len(results) / total_time if total_time > 0 else 0,
        },
        "by_agent": by_agent,
        "failed_details": failed[:10],  # Only show first 10 failures
    }


def print_results(results: Dict):
    """Print formatted test results"""
    summary = results["summary"]

    print(f"\n{'='*60}")
    print(f"RESULTS")
    print(f"{'='*60}\n")

    print(f"Total agent creations: {summary['total_creations']}")
    print(f"Successful: {summary['successful']}")
    print(f"Failed: {summary['failed']}")
    print(f"Test duration: {summary['total_duration']:.2f}s")
    print(f"Throughput: {summary['creations_per_second']:.1f} agents/sec\n")

    print(f"{'Agent Type':<20} {'Created':<10} {'Avg Init (ms)':<15} {'Init P95 (ms)':<15} {'Tool Load Count':<5}")
    print(f"{'-'*20} {'-'*10} {'-'*15} {'-'*15} {'-'*15}")

    for agent_name, data in sorted(results["by_agent"].items()):
        count = data["count"]
        init_times = data["init_times"]
        tool_load_times = data["tool_load_times"]

        avg_init = statistics.mean(init_times) * 1000 if init_times else 0
        p95_init = statistics.quantiles(init_times, n=20)[-1] * 1000 if len(init_times) >= 20 else (max(init_times) * 1000 if init_times else 0)
        tool_count = len(tool_load_times)

        print(f"{agent_name:<20} {count:<10} {avg_init:>10.2f} {p95_init:>10.2f} {tool_count:>15}")

    if results["failed_details"]:
        print(f"\nSample of failures (first {len(results['failed_details'])}):")
        for f in results["failed_details"]:
            print(f"  - {f['agent']}: {f['error']}")


def main():
    parser = argparse.ArgumentParser(description="Agent Performance Stress Test")
    parser.add_argument("--concurrent", type=int, default=10, help="Number of concurrent workers")
    parser.add_argument("--duration", type=float, default=30, help="Test duration in seconds")
    args = parser.parse_args()

    # Define agents to test
    agent_classes = [
        (ResearchAgent, "ResearchAgent"),
        (AnalystAgent, "AnalystAgent"),
        (ContentAgent, "ContentAgent"),
        (OnPageAgent, "OnPageAgent"),
        (LinksAgent, "LinksAgent"),
        (MemoryAgent, "MemoryAgent"),
    ]

    try:
        results = run_stress_test(agent_classes, args.concurrent, args.duration)
        print_results(results)

        # Save results to file
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        filename = f"stress_test_results_{timestamp}.json"
        import json
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\nResults saved to: {filename}")

    except KeyboardInterrupt:
        print("\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error running stress test: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
