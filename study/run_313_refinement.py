#!/usr/bin/env python3
"""Run one 313 case with the snappyHexMesh refinement box expanded by 1L."""

import argparse
import json
import re
import shutil
import subprocess
import tarfile
from pathlib import Path

from run_prism_combined import averages
from run_study import OPENFOAM_BASHRC, SOURCE, copy_source, solver_complete


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "runs/313_refinement_check"
CASE = OUTPUT / "case"
LENGTH = 1.09585


def replace_definition(path, entry, value):
    text, count = re.subn(
        rf"(?m)^([ \t]*{re.escape(entry)}[ \t]+)[^;\r\n]*(;[^\r\n]*)$",
        lambda match: match.group(1) + value + match.group(2), path.read_text(),
    )
    if count != 1:
        raise ValueError(f"Expected one {entry} definition in {path}, found {count}")
    path.write_text(text)


def prepare():
    if CASE.exists():
        return
    OUTPUT.mkdir(parents=True, exist_ok=True)
    CASE.mkdir()
    copy_source(CASE, mesh_case=True)
    snappy = CASE / "system/snappyHexMeshDict"
    replace_definition(snappy, "box_top", "#calc \"3*$L\"")
    replace_definition(snappy, "box_back", "#calc \"(2 + 3)*$L\"")
    replace_definition(snappy, "min", f"({-2 * LENGTH:.15g} {-2 * LENGTH:.15g} 0.0)")
    settings = {
        "source": str(SOURCE),
        "status": "prepared",
        "length_m": LENGTH,
        "refinement_box_min_m": [-2 * LENGTH, -2 * LENGTH, 0.0],
        "refinement_box_max_m": [5 * LENGTH, 3 * LENGTH, 0.04],
        "start_time_s": 0.0,
        "end_time_s": 1.0,
        "maxCo": 0.5,
        "changes": "Only snappyHexMesh refinementBox expanded 1L outward on each x/y side; z unchanged.",
    }
    (OUTPUT / "settings.json").write_text(json.dumps(settings, indent=2) + "\n")


def mesh_bounds(case_dir):
    path = case_dir / "log.checkMesh"
    if not path.is_file():
        return None
    match = re.search(
        r"Overall domain bounding box\s*\(([^)]+)\)\s*\(([^)]+)\)",
        path.read_text(errors="replace"),
    )
    if not match:
        return None
    return list(map(float, match[1].split() + match[2].split()))


def same_baseline_domain(case_dir):
    baseline = mesh_bounds(SOURCE)
    actual = mesh_bounds(case_dir)
    if baseline is None or actual is None:
        return False, baseline, actual
    matches = all(abs(a - b) < 1e-4 for a, b in zip(actual, baseline))
    return matches, baseline, actual


def finish(returncode):
    settings = json.loads((OUTPUT / "settings.json").read_text())
    complete, solver_message = solver_complete(CASE)
    check_mesh = CASE / "log.checkMesh"
    mesh_text = check_mesh.read_text(errors="replace") if check_mesh.is_file() else ""
    bounds_ok, baseline_bounds, case_bounds = same_baseline_domain(CASE)
    mesh_ok = "Mesh OK." in mesh_text
    accepted = returncode == 0 and complete and mesh_ok and bounds_ok
    result = {
        "accepted": accepted,
        "returncode": returncode,
        "solver_complete": complete,
        "solver_message": solver_message,
        "mesh_ok": mesh_ok,
        "baseline_domain_verified": bounds_ok,
        "baseline_domain_bounds_m": baseline_bounds,
        "case_domain_bounds_m": case_bounds,
        "settings": settings,
        "baseline": averages(SOURCE),
    }
    if complete:
        result["combined"] = averages(CASE)
        baseline_cycle = result["baseline"].get("two_cycle_cd")
        combined_cycle = result["combined"].get("two_cycle_cd")
        result["two_cycle_cd_change_percent"] = (
            100 * (combined_cycle - baseline_cycle) / baseline_cycle
            if baseline_cycle is not None and combined_cycle is not None else None
        )
    settings["status"] = "complete" if accepted else "failed"
    (OUTPUT / "settings.json").write_text(json.dumps(settings, indent=2) + "\n")
    (OUTPUT / "result.json").write_text(json.dumps(result, indent=2) + "\n")

    baseline = result["baseline"]
    combined = result.get("combined", {})
    lines = [
        "# 313 refinement-box check", "", settings["changes"], "",
        "The Cd comparison uses the last two complete rising Cl=0 cycles in each file, with time-weighted integration. The fixed 0.5–1.0 s mean is included as a reference.", "",
        f"Accepted: {accepted}; solver complete at 1 s: {complete}; Mesh OK: {mesh_ok}; baseline domain bounds verified: {bounds_ok}.", "",
        "| Metric | Saved 313 baseline | Refinement case | Change (%) |",
        "|---|---:|---:|---:|",
    ]
    for metric, change_metric in (("two_cycle_cd", "two_cycle_cd_change_percent"),
                                  ("fixed_window_cd", "fixed_window_cd_change_percent")):
        old, new = baseline.get(metric), combined.get(metric)
        change = (100 * (new - old) / old
                  if old is not None and new is not None and old != 0 else None)
        if metric == "fixed_window_cd":
            result[change_metric] = change
        lines.append(f"| {metric} | {old} | {new} | {change} |")
    lines += [
        "",
        f"Baseline two-cycle bounds (s): {baseline.get('two_cycle_bounds_s')}",
        f"Case two-cycle bounds (s): {combined.get('two_cycle_bounds_s')}",
        f"Baseline per-cycle Cd: {baseline.get('per_cycle_cd')}",
        f"Case per-cycle Cd: {combined.get('per_cycle_cd')}",
        "",
        "Only the refinement-box bounds were changed. Mesh and solver acceptance do not establish statistical stationarity; consider the individual cycle means.",
    ]
    (OUTPUT / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    (OUTPUT / "result.md").write_text("\n".join(lines) + "\n")
    archive_path = OUTPUT / ("313_refinement.tar.gz" if accepted else "313_refinement.failed.tar.gz")
    temporary = archive_path.with_name(archive_path.name + ".tmp")
    with tarfile.open(temporary, "w:gz") as archive:
        archive.add(CASE, arcname="313_refinement",
                    filter=lambda info: None if "dynamicCode" in Path(info.name).parts else info)
    temporary.replace(archive_path)
    print(f"Finished: accepted={accepted}; result={OUTPUT / 'result.md'}; archive={archive_path}", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare-only", action="store_true", help="prepare the case without running OpenFOAM")
    args = parser.parse_args()
    if not SOURCE.is_dir():
        parser.error(f"saved baseline not found: {SOURCE}")
    prepare()
    if args.prepare_only:
        print(f"Prepared {CASE}")
        return 0
    if (CASE / "execution.log").exists():
        raise RuntimeError("Existing execution preserved; inspect its process/results before retrying")
    settings_path = OUTPUT / "settings.json"
    settings = json.loads(settings_path.read_text())
    settings["status"] = "running"
    settings_path.write_text(json.dumps(settings, indent=2) + "\n")
    print(f"Running 313 refinement case in {CASE}", flush=True)
    with (CASE / "execution.log").open("w") as log:
        command = f"source {OPENFOAM_BASHRC} && bash ./Allrun.pimple"
        run = subprocess.run(["bash", "-c", command], cwd=CASE,
                             stdout=log, stderr=subprocess.STDOUT, check=False)
    finish(run.returncode)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
