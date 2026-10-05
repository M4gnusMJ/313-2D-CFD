#!/usr/bin/env python3
"""Refresh separate reports and archives as study cases finish."""

import json
import argparse
import subprocess
import sys
import time
from pathlib import Path

from run_study import OUTPUT


SCRIPT_DIR = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=OUTPUT / "manifest.json",
                        help="manifest whose terminal case states this monitor watches")
    args = parser.parse_args()
    manifest_path = args.manifest
    if not manifest_path.is_absolute():
        manifest_path = Path(__file__).resolve().parents[1] / manifest_path

    previous = None
    while True:
        manifest = json.loads(manifest_path.read_text())
        states = manifest["cases"]
        finished = tuple((name, state["status"]) for name, state in states.items()
                         if state["status"] in ("complete", "failed", "prepare_failed"))
        if finished != previous:
            for script in ("report_results.py", "archive_runs.py"):
                result = subprocess.run([sys.executable, str(SCRIPT_DIR / script)])
                if result.returncode:
                    print(f"{script}: exit {result.returncode}; inspect its reported failures", flush=True)
            previous = finished
        if all(state["status"] in ("complete", "failed", "prepare_failed") for state in states.values()):
            print("All study cases terminal; reports and archives refreshed.", flush=True)
            return
        time.sleep(30)


if __name__ == "__main__":
    main()
