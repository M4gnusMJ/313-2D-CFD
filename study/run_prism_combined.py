#!/usr/bin/env python3
"""Run the requested combined prism domain/refinement/Courant check."""

import argparse
import json
import re
import shutil
import subprocess
import tarfile
from pathlib import Path

from analyze import coefficient_file, read_coefficients, rising_crossings, weighted_stats
from run_study import OPENFOAM_BASHRC, ROOT, set_block_mesh_dimension, solver_complete


SOURCE = ROOT / "saved_runs/prism_pimple_run"
OUTPUT = ROOT / "runs/prism_combined_check"
CASE = OUTPUT / "case"
LENGTH = 1.09585
DIMENSIONS = {"upstream_dist": 7 * LENGTH, "downstream_dist": 14 * LENGTH,
              "roof_height": 9 * LENGTH}


def replace_definition(path, entry, value):
    text, count = re.subn(
        rf"(?m)^([ \t]*{entry}[ \t]+)[^;\r\n]*(;[^\r\n]*)$",
        lambda match: match.group(1) + value + match.group(2), path.read_text(),
    )
    if count != 1:
        raise ValueError(f"Expected one {entry} definition in {path}")
    path.write_text(text)


def prepare():
    if CASE.exists():
        return
    OUTPUT.mkdir(parents=True, exist_ok=True)
    CASE.mkdir()
    for name in ("system", "0.orig"):
        shutil.copytree(SOURCE / name, CASE / name)
    (CASE / "constant").mkdir()
    for name in ("transportProperties", "turbulenceProperties"):
        shutil.copy2(SOURCE / "constant" / name, CASE / "constant" / name)
    shutil.copytree(SOURCE / "constant/triSurface", CASE / "constant/triSurface")
    shutil.copy2(SOURCE / "Allrun.pimple", CASE / "Allrun.pimple")
    for entry, value in DIMENSIONS.items():
        set_block_mesh_dimension(CASE, entry, value)
    snappy = CASE / "system/snappyHexMeshDict"
    replace_definition(snappy, "box_top", f"{3 * LENGTH:.15g}")
    replace_definition(snappy, "box_back", f"{5 * LENGTH:.15g}")
    replace_definition(snappy, "min", f"({-2 * LENGTH:.15g} {-2 * LENGTH:.15g} 0.0)")
    replace_definition(CASE / "system/controlDict", "maxCo", "1")
    settings = {
        "source": str(SOURCE), "status": "prepared", "length_m": LENGTH,
        "domain_m": DIMENSIONS, "maxCo": 1, "start_time_s": 0, "end_time_s": 1,
        "refinement_box_min_m": [-2 * LENGTH, -2 * LENGTH, 0],
        "refinement_box_max_m": [5 * LENGTH, 3 * LENGTH, 0.04],
        "changes": "Inlet +2L, outlet +3L, roof +3L, each x/y refinement-box side outward +1L; z unchanged; maxCo=1.",
    }
    (OUTPUT / "settings.json").write_text(json.dumps(settings, indent=2) + "\n")


def averages(case):
    samples = read_coefficients(coefficient_file(case), ("Cd", "Cl"))
    cd = [(time, drag) for time, drag, lift in samples]
    crossings = rising_crossings(samples, 0)
    result = {"fixed_window_cd": weighted_stats(cd, 0.5, 1)[0]}
    if len(crossings) < 3:
        result.update(two_cycle_cd=None, note="Fewer than two complete lift cycles in file")
    else:
        bounds = crossings[-3:]
        result.update(two_cycle_bounds_s=bounds,
                      two_cycle_cd=weighted_stats(cd, bounds[0], bounds[-1])[0],
                      per_cycle_cd=[weighted_stats(cd, start, end)[0]
                                    for start, end in zip(bounds[:-1], bounds[1:])])
    return result


def finish(returncode):
    settings = json.loads((OUTPUT / "settings.json").read_text())
    complete, message = solver_complete(CASE)
    mesh_path = CASE / "log.checkMesh"
    mesh = mesh_path.read_text() if mesh_path.exists() else ""
    bounds = re.search(r"Overall domain bounding box\s*\(([^)]+)\)\s*\(([^)]+)\)", mesh)
    geometry_ok = False
    if bounds:
        lower = list(map(float, bounds[1].split()))
        upper = list(map(float, bounds[2].split()))
        expected = [-DIMENSIONS["upstream_dist"], -1, 0,
                    DIMENSIONS["downstream_dist"], DIMENSIONS["roof_height"], 0.04]
        geometry_ok = all(abs(actual - target) < 1e-4 for actual, target in zip(lower + upper, expected))
    accepted = returncode == 0 and complete and "Mesh OK." in mesh and geometry_ok
    result = {"accepted": accepted, "returncode": returncode,
              "solver_complete": complete, "solver_message": message,
              "mesh_ok": "Mesh OK." in mesh, "requested_geometry_verified": geometry_ok,
              "settings": settings, "baseline": averages(SOURCE)}
    if complete:
        result["combined"] = averages(CASE)
        for metric in ("two_cycle_cd", "fixed_window_cd"):
            old, new = result["baseline"].get(metric), result["combined"].get(metric)
            result[metric + "_change_percent"] = 100 * (new - old) / old if old is not None and new is not None else None
    settings["status"] = "complete" if accepted else "failed"
    (OUTPUT / "settings.json").write_text(json.dumps(settings, indent=2) + "\n")
    (OUTPUT / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    lines = ["# Combined prism check", "", settings["changes"], "",
             "Mean Cd uses the last two complete lift cycles anywhere in each file, bounded by rising Cl=0 crossings, with time-weighted integration. The 0.5–1 s mean is retained as a reference.", "",
             f"Accepted: {accepted}; solver complete: {complete}; Mesh OK: {'Mesh OK.' in mesh}; requested geometry verified: {geometry_ok}.", "",
             "| Metric | Saved prism baseline | Combined run | Change (%) |",
             "|---|---:|---:|---:|"]
    if complete:
        for metric in ("two_cycle_cd", "fixed_window_cd"):
            lines.append(f"| {metric} | {result['baseline'].get(metric)} | {result['combined'].get(metric)} | {result.get(metric + '_change_percent')} |")
        lines += ["", f"Baseline cycle bounds: {result['baseline'].get('two_cycle_bounds_s')}",
                  f"Combined cycle bounds: {result['combined'].get('two_cycle_bounds_s')}",
                  f"Baseline per-cycle Cd: {result['baseline'].get('per_cycle_cd')}",
                  f"Combined per-cycle Cd: {result['combined'].get('per_cycle_cd')}", "",
                  "This combined check does not isolate the effects of domain size, refinement-box size, or Courant number. Passing solver and mesh checks does not establish statistical stationarity; inspect the individual cycle means."]
    (OUTPUT / "result.md").write_text("\n".join(lines) + "\n")
    target = OUTPUT / ("prism_combined.tar.gz" if accepted else "prism_combined.failed.tar.gz")
    temporary = target.with_name(target.name + ".tmp")
    with tarfile.open(temporary, "w:gz") as archive:
        archive.add(CASE, arcname="prism_combined",
                    filter=lambda info: None if "dynamicCode" in Path(info.name).parts else info)
    temporary.replace(target)
    print(f"Finished: accepted={accepted}; result={OUTPUT / 'result.md'}; archive={target}", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args()
    prepare()
    if args.prepare_only:
        print(f"Prepared {CASE}")
        return
    if (CASE / "execution.log").exists():
        raise RuntimeError("Existing execution preserved; inspect its process/results before retrying")
    settings = json.loads((OUTPUT / "settings.json").read_text())
    settings["status"] = "running"
    (OUTPUT / "settings.json").write_text(json.dumps(settings, indent=2) + "\n")
    print(f"Running combined prism case in {CASE}", flush=True)
    with (CASE / "execution.log").open("w") as log:
        result = subprocess.run(["bash", "-c", f"source {OPENFOAM_BASHRC} && bash ./Allrun.pimple"],
                                cwd=CASE, stdout=log, stderr=subprocess.STDOUT)
    finish(result.returncode)


if __name__ == "__main__":
    main()
