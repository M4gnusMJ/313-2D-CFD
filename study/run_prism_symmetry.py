#!/usr/bin/env python3
"""Run the prism symmetry-boundary check."""

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
REFERENCE = ROOT / "runs/prism_combined_check/case"
OUTPUT = ROOT / "runs/prism_symmetry_check"
CASE = OUTPUT / "case"
LENGTH = 1.09585
LOWER_HEIGHT = 8 * LENGTH
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


def set_lower_symmetry(path):
    text = path.read_text()
    pattern = r"(?ms)(^[ \t]*lowerWall\s*\{)(.*?)(^[ \t]*\})"

    def update(match):
        block = re.sub(r"(?m)^([ \t]*type[ \t]+)[^;]+;", r"\1symmetryPlane;", match.group(2))
        block = re.sub(r"(?m)^[ \t]*value[ \t]+[^;]+;[^\r\n]*\n", "", block)
        return match.group(1) + block + match.group(3)

    updated, count = re.subn(pattern, update, text)
    if count != 1:
        raise ValueError(f"Expected one lowerWall patch in {path}")
    path.write_text(updated)


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
    block_mesh = CASE / "system/blockMeshDict"
    text = block_mesh.read_text()
    text, count = re.subn(r"(?m)^([ \t]*roof_height[ \t]+[^;\r\n]*;[^\r\n]*)$",
                          lambda match: match.group(1) + '\nlower_height        #calc "8*1.09585";', text)
    if count != 1:
        raise ValueError(f"Expected one roof_height definition in {block_mesh}")
    start, end = text.index("vertices"), text.index("// As per the guide")
    vertices = text[start:end]
    if vertices.count("-1") != 4:
        raise ValueError(f"Expected four lower vertices in {block_mesh}")
    text = text[:start] + vertices.replace("-1", "-$lower_height") + text[end:]
    block_mesh.write_text(text)
    replace_definition(block_mesh, "Ny", '#calc "static_cast<int>(std::ceil(($roof_height + $lower_height)/$max_h))"')
    text = block_mesh.read_text().replace("lowerWall\n    {\n        type patch;", "lowerWall\n    {\n        type symmetryPlane;")
    block_mesh.write_text(text)
    for field in (CASE / "0.orig").iterdir():
        if field.is_file():
            set_lower_symmetry(field)
    snappy = CASE / "system/snappyHexMeshDict"
    replace_definition(snappy, "box_top", f"{3 * LENGTH:.15g}")
    replace_definition(snappy, "box_back", f"{5 * LENGTH:.15g}")
    replace_definition(snappy, "min", f"({-2 * LENGTH:.15g} {-2 * LENGTH:.15g} 0.0)")
    replace_definition(CASE / "system/controlDict", "maxCo", "1")
    settings = {
        "source": str(SOURCE), "reference": str(REFERENCE), "status": "prepared", "length_m": LENGTH,
        "nominal_prism_height_m": LENGTH, "lower_boundary_y_m": -LOWER_HEIGHT,
        "domain_m": DIMENSIONS, "maxCo": 1, "mpi_ranks": 6, "start_time_s": 0, "end_time_s": 1,
        "refinement_box_min_m": [-2 * LENGTH, -2 * LENGTH, 0],
        "refinement_box_max_m": [5 * LENGTH, 3 * LENGTH, 0.04],
        "changes": "Lower boundary moved to -8L and changed to symmetryPlane; lowerWall field conditions changed to symmetryPlane. Other study inputs follow the combined prism check.",
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


def patch_type(path, name):
    text = path.read_text() if path.exists() else ""
    match = re.search(rf"(?ms)^[ \t]*{name}\s*\{{(.*?)^[ \t]*\}}", text)
    if not match:
        return None
    value = re.search(r"(?m)^[ \t]*type[ \t]+([^;]+);", match.group(1))
    return value.group(1).strip() if value else None


def finish(returncode):
    settings = json.loads((OUTPUT / "settings.json").read_text())
    complete, message = solver_complete(CASE)
    mesh_path = CASE / "log.checkMesh"
    mesh = mesh_path.read_text(errors="replace") if mesh_path.exists() else ""
    bounds = re.search(r"Overall domain bounding box\s*\(([^)]+)\)\s*\(([^)]+)\)", mesh)
    geometry_ok = False
    if bounds:
        lower, upper = list(map(float, bounds[1].split())), list(map(float, bounds[2].split()))
        expected = [-DIMENSIONS["upstream_dist"], -LOWER_HEIGHT, 0,
                    DIMENSIONS["downstream_dist"], DIMENSIONS["roof_height"], 0.04]
        geometry_ok = all(abs(actual - target) < 1e-4 for actual, target in zip(lower + upper, expected))
    boundary = CASE / "constant/polyMesh/boundary"
    symmetry = patch_type(boundary, "lowerWall") == "symmetryPlane" and patch_type(boundary, "upperWall") == "symmetryPlane"
    logs = [path.read_text(errors="replace") for path in CASE.glob("log.*")]
    execution = CASE / "execution.log"
    if execution.exists():
        logs.append(execution.read_text(errors="replace"))
    no_fatal = all("FOAM FATAL" not in log for log in logs)
    stages_end = all(re.search(r"^End\s*$", path.read_text(errors="replace"), re.MULTILINE)
                     for path in CASE.glob("log.*") if path.stat().st_size)
    accepted = returncode == 0 and complete and "Mesh OK." in mesh and geometry_ok and symmetry and no_fatal and stages_end
    result = {"accepted": accepted, "returncode": returncode,
              "solver_complete": complete, "solver_message": message,
              "mesh_ok": "Mesh OK." in mesh, "requested_geometry_verified": geometry_ok,
              "lower_and_upper_symmetry_verified": symmetry, "no_foam_fatal": no_fatal,
              "stage_logs_end": stages_end, "settings": settings,
              "combined_reference": averages(REFERENCE), "saved_prism_baseline": averages(SOURCE)}
    if complete:
        result["symmetry_run"] = averages(CASE)
        for reference in ("combined_reference", "saved_prism_baseline"):
            result[reference + "_change_percent"] = {}
            for metric in ("two_cycle_cd", "fixed_window_cd"):
                old, new = result[reference].get(metric), result["symmetry_run"].get(metric)
                result[reference + "_change_percent"][metric] = 100 * (new - old) / old if old is not None and new is not None else None
    settings["status"] = "complete" if accepted else "failed"
    (OUTPUT / "settings.json").write_text(json.dumps(settings, indent=2) + "\n")
    (OUTPUT / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    lines = ["# Prism symmetry check", "", settings["changes"], "",
             "Mean Cd uses the last two complete lift cycles anywhere in each file, bounded by rising Cl=0 crossings, with time-weighted integration. The 0.5–1 s mean is retained as a reference.", "",
             f"Accepted: {accepted}; solver complete: {complete}; Mesh OK: {'Mesh OK.' in mesh}; geometry verified: {geometry_ok}; symmetry verified: {symmetry}; no FOAM FATAL: {no_fatal}; stage logs end: {stages_end}.", ""]
    if complete:
        lines += ["| Reference | Metric | Reference Cd | Symmetry run Cd | Change (%) |", "|---|---|---:|---:|---:|"]
        for reference, label in (("combined_reference", "Latest combined prism"), ("saved_prism_baseline", "Saved prism baseline")):
            for metric in ("two_cycle_cd", "fixed_window_cd"):
                lines.append(f"| {label} | {metric} | {result[reference].get(metric)} | {result['symmetry_run'].get(metric)} | {result[reference + '_change_percent'].get(metric)} |")
        lines += ["", f"Symmetry run cycle bounds (s): {result['symmetry_run'].get('two_cycle_bounds_s')}",
                  f"Symmetry run per-cycle Cd: {result['symmetry_run'].get('per_cycle_cd')}", "",
                  "The cycle window may include startup. Mesh and solver checks do not establish statistical stationarity; compare the individual cycle means and fixed-window result."]
    (OUTPUT / "result.md").write_text("\n".join(lines) + "\n")
    target = OUTPUT / ("prism_symmetry.tar.gz" if accepted else "prism_symmetry.failed.tar.gz")
    temporary = target.with_name(target.name + ".tmp")
    with tarfile.open(temporary, "w:gz") as archive:
        archive.add(CASE, arcname="prism_symmetry", filter=lambda info: None if "dynamicCode" in Path(info.name).parts else info)
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
    print(f"Running prism symmetry case in {CASE}", flush=True)
    with (CASE / "execution.log").open("w") as log:
        result = subprocess.run(["bash", "-c", f"source {OPENFOAM_BASHRC} && bash ./Allrun.pimple"],
                                cwd=CASE, stdout=log, stderr=subprocess.STDOUT)
    finish(result.returncode)


if __name__ == "__main__":
    main()
