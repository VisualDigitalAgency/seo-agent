#!/usr/bin/env python3
"""
SEO Agent — Main Entry Point
Usage: python3 main.py --run-id <id> --task "keyword" [--resume]
"""

import argparse
import sys
import os
sys.stdout.reconfigure(line_buffering=True)

# Add python dir to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pipeline import Pipeline


def main():
    parser = argparse.ArgumentParser(description='SEO Agent Pipeline')
    parser.add_argument('--run-id', required=True, help='Unique run identifier')
    parser.add_argument('--task', required=True, help='Target keyword / topic')
    parser.add_argument('--target', default='', help='Target market (e.g. US, UK)')
    parser.add_argument('--audience', default='', help='Target audience description')
    parser.add_argument('--domain', default='', help='Client domain for internal linking')
    parser.add_argument('--notes', default='', help='Additional notes / requirements')
    parser.add_argument('--resume', action='store_true', help='Resume from last completed stage')
    args = parser.parse_args()

    pipeline = Pipeline(
        run_id=args.run_id,
        task=args.task,
        target=args.target,
        audience=args.audience,
        domain=args.domain,
        notes=args.notes,
    )

    try:
        if args.resume:
            pipeline.resume()
        else:
            pipeline.run()
    except KeyboardInterrupt:
        pipeline.log("Pipeline interrupted by user")
        pipeline.update_status('failed', error='Interrupted')
        sys.exit(1)
    except Exception as e:
        pipeline.log(f"FATAL ERROR: {e}", level='ERROR')
        pipeline.update_status('failed', error=str(e))
        sys.exit(1)


if __name__ == '__main__':
    main()
