#!/usr/bin/env python3
"""Write per-case and combined reports for the 313 parameter study."""

import argparse
import csv
import importlib.util
import json
import math
import re
import statistics
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "runs/313_study/manifest.json"
QUEUE_MANIFESTS = (MANIFEST.with_name("domain_retry_queue.json"),
                   MANIFEST.with_name("turbulence_queue.json"))
ANALYZER_SPEC = importlib.util.spec_from_file_location("study_analyze", Path(__file__).with_name("analyze.py"))
ANALYZER = importlib.util.module_from_spec(ANALYZER_SPEC)
ANALYZER_SPEC.loader.exec_module(ANALYZER)


def load_study_manifest():
    manifest = json.loads(MANIFEST.read_text())
    for queue_path in QUEUE_MANIFESTS:
        if queue_path.exists():
            queue = json.loads(queue_path.read_text())
            manifest["cases"].update(queue["cases"])
    return manifest


def find_file(directory, names):
    for name in names:
        path = directory / name
        if path.is_file():
            return path
    return None


def solver_log_data(path):
    if path is None or not path.exists():
        return {"solver_log": str(path) if path else None}
    co_pattern = re.compile(r"Courant Number mean:\s*([-+\deE.]+)\s+max:\s*([-+\deE.]+)")
    dt_pattern = re.compile(r"\bdeltaT\s*=\s*([-+\deE.]+)")
    time_pattern = re.compile(r"^Time\s*=\s*([-+\deE.]+)\s*$")
    runtime_pattern = re.compile(r"ExecutionTime\s*=\s*([-+\deE.]+)\s*s\s+ClockTime\s*=\s*([-+\deE.]+)\s*s")
    continuity_pattern = re.compile(
        r"time step continuity errors\s*:\s*sum local\s*=\s*([-+\deE.]+),\s*global\s*=\s*([-+\deE.]+),\s*cumulative\s*=\s*([-+\deE.]+)"
    )
    pending_co = pending_dt = None
    steps = []
    last_time = None
    last_runtime = None
    last_continuity = None
    saw_end = False
    failure_marker = None
    with path.open(errors="replace") as log:
        for line in log:
            co_match = co_pattern.search(line)
            if co_match:
                pending_co = (float(co_match.group(1)), float(co_match.group(2)))
            dt_match = dt_pattern.search(line)
            if dt_match:
                pending_dt = float(dt_match.group(1))
            time_match = time_pattern.match(line.strip())
            if time_match:
                last_time = float(time_match.group(1))
                if pending_co is not None or pending_dt is not None:
                    steps.append({"time_s": last_time, "co_mean": pending_co[0] if pending_co else None,
                                  "co_max": pending_co[1] if pending_co else None,
                                  "delta_t_s": pending_dt})
                pending_co = pending_dt = None
            runtime_match = runtime_pattern.search(line)
            if runtime_match:
                last_runtime = {"execution_s": float(runtime_match.group(1)),
                                "wall_s": float(runtime_match.group(2))}
            continuity_match = continuity_pattern.search(line)
            if continuity_match:
                last_continuity = {"sum_local": float(continuity_match.group(1)),
                                   "global": float(continuity_match.group(2)),
                                   "cumulative": float(continuity_match.group(3))}
            if line.strip() == "End":
                saw_end = True
            if failure_marker is None and any(marker in line for marker in
                                              ("FOAM FATAL", "MPI_ABORT", "Segmentation fault", "Aborted (core dumped)")):
                failure_marker = line.strip()

    completed_times = [step["time_s"] for step in steps]
    return {
        "solver_log": str(path),
        "solver_end_seen": saw_end,
        "failure_marker": failure_marker,
        "simulation_end_time_s": max(completed_times) if completed_times else last_time,
        "runtime": last_runtime,
        "final_continuity_error": last_continuity,
        "steps": steps,
    }


def distribution(values):
    if not values:
        return None
    return {"count": len(values), "min": min(values), "mean": statistics.fmean(values),
            "median": statistics.median(values), "max": max(values)}


def diagnostics(log_data, case_dir, kind, baseline_cells):
    steps = log_data.get("steps", [])
    all_co = distribution([step["co_max"] for step in steps if step["co_max"] is not None])
    window_steps = [step for step in steps if step["time_s"] >= 0.5]
    window_co = distribution([step["co_max"] for step in window_steps if step["co_max"] is not None])
    all_dt = [step["delta_t_s"] for step in steps if step["delta_t_s"] is not None]
    window_dt = [step["delta_t_s"] for step in window_steps if step["delta_t_s"] is not None]

    if kind in ("domain", "baseline"):
        check_mesh = find_file(case_dir, ("log.checkMesh", "log.checkMesh.snappy"))
        cell_match = None
        if check_mesh:
            cell_match = re.search(r"\bcells:\s*(\d+)", check_mesh.read_text(errors="replace"))
        cells = int(cell_match.group(1)) if cell_match else None
        cell_source = str(check_mesh) if cell_match else "unavailable: no case checkMesh cell count"
    else:
        cells = baseline_cells
        cell_source = "reused baseline checkMesh" if baseline_cells is not None else "unavailable: baseline checkMesh cell count missing"

    yplus_path = find_file(case_dir, ("log.pimpleFoam.yPlus", "log.yPlus"))
    yplus = None
    yplus_source = "unavailable"
    if yplus_path:
        match = re.search(r"patch body y\+\s*:\s*min\s*=\s*([-+\deE.]+),\s*max\s*=\s*([-+\deE.]+),\s*average\s*=\s*([-+\deE.]+)",
                          yplus_path.read_text(errors="replace"))
        if match:
            yplus = {"min": float(match.group(1)), "max": float(match.group(2)),
                     "average": float(match.group(3))}
            yplus_source = str(yplus_path)
    if yplus is None and log_data.get("solver_log"):
        path = Path(log_data["solver_log"])
        if path.exists():
            match = None
            for line in path.read_text(errors="replace").splitlines():
                found = re.search(r"patch body y\+\s*:\s*min\s*=\s*([-+\deE.]+),\s*max\s*=\s*([-+\deE.]+),\s*average\s*=\s*([-+\deE.]+)", line)
                if found:
                    match = found
            if match:
                yplus = {"min": float(match.group(1)), "max": float(match.group(2)),
                         "average": float(match.group(3))}
                yplus_source = str(path)

    return {
        "max_co_all": all_co,
        "max_co_after_0.5_s": window_co,
        "delta_t_all_s": {"min": min(all_dt), "max": max(all_dt)} if all_dt else None,
        "delta_t_after_0.5_s": {"min": min(window_dt), "max": max(window_dt)} if window_dt else None,
        "mesh_cell_count": cells,
        "mesh_cell_count_source": cell_source,
        "body_y_plus": yplus,
        "body_y_plus_source": yplus_source,
    }


def configured_change(case, manifest):
    kind = case.get("kind")
    if kind == "maxCo":
        return {"parameter": "maxCo", "baseline": manifest["baseline_settings"]["maxCo"],
                "configured": case.get("value")}
    if kind == "tolerance":
        return {"parameter": "p, U, k, omega absolute tolerances", "factor": case.get("factor"),
                "definition": manifest.get("tolerance_definition", "relTol unchanged")}
    if kind == "PIMPLE":
        return {"parameter": "PIMPLE nOuterCorrectors", "baseline": 2,
                "configured": case.get("value")}
    if kind == "turbulence_intensity":
        return {"parameter": "inlet turbulence intensity", "baseline": 0.05,
                "configured": case.get("intensity"), "viscosity_ratio": 10}
    if kind == "domain":
        return {"parameter": case.get("parameter"), "baseline": case.get("baseline_value"),
                "configured": case.get("value"), "configured_L": (
                    (case.get("value") - case.get("baseline_value")) / manifest["length_m"]
                    if case.get("value") is not None and case.get("baseline_value") is not None else None)}
    return {"parameter": "none", "configured": None}


def warm_start(case, kind, manifest):
    if kind == "baseline":
        return {"protocol": "original baseline from time 0"}
    if kind in ("domain", "turbulence_intensity"):
        return {"protocol": "initialize from time 0"}
    if case.get("restart_time") is not None:
        return {"protocol": "restart from saved fields", "time_s": case["restart_time"],
                "delta_t_s": case.get("restart_deltaT", manifest.get("warm_start", {}).get("deltaT_s"))}
    return {"protocol": "unavailable"}


def domain_mesh_check(case_dir, kind):
    if kind != "domain":
        return {"required": False, "status": "not_required", "passed": True, "file": None, "error": None}
    path = find_file(case_dir, ("log.checkMesh", "log.checkMesh.snappy"))
    if path is None:
        return {"required": True, "status": "pending", "passed": False, "file": None,
                "error": "domain variant has no case-specific checkMesh log"}
    content = path.read_text(errors="replace")
    fatal = next((line.strip() for line in content.splitlines()
                  if any(marker in line for marker in ("FOAM FATAL", "MPI_ABORT", "Segmentation fault", "Aborted (core dumped)"))), None)
    if fatal:
        return {"required": True, "status": "failed", "passed": False, "file": str(path), "error": fatal}
    failed_checks = re.search(r"Failed\s+(\d+)\s+mesh checks", content)
    if failed_checks:
        return {"required": True, "status": "failed", "passed": False, "file": str(path),
                "error": f"checkMesh failed {failed_checks.group(1)} mesh checks"}
    if "Mesh OK." not in content:
        return {"required": True, "status": "incomplete", "passed": False, "file": str(path),
                "error": "case-specific checkMesh log does not contain Mesh OK."}
    return {"required": True, "status": "passed", "passed": True, "file": str(path), "error": None}


def source_coefficients(case_dir):
    try:
        return ANALYZER.coefficient_file(case_dir)
    except ValueError:
        return None


def analyze_complete(case_dir, data_path, name):
    if data_path is None:
        return None, "error", "completed solver has no coefficient.dat"
    try:
        summary = ANALYZER.summarize(data_path, 2, 0.5)
        return summary, "two_cycle", ""
    except ValueError as error:
        if "rising Cl=0 crossings" not in str(error):
            return None, "error", str(error)
        try:
            summary = ANALYZER.summarize(data_path)
            return summary, "fixed_window_fallback", str(error)
        except ValueError as fixed_error:
            return None, "error", str(fixed_error)


def make_record(name, case, manifest, baseline_dir, expected_end):
    is_baseline = case is None
    kind = "baseline" if is_baseline else case.get("kind", "unknown")
    case_dir = baseline_dir if is_baseline else ROOT / "runs/313_study" / name
    manifest_status = "complete" if is_baseline else case.get("status", "prepared")
    data_path = source_coefficients(case_dir)
    log_path = find_file(case_dir, ("log.pimpleFoam",))
    log_data = solver_log_data(log_path)
    mesh_check = domain_mesh_check(case_dir, kind)
    baseline_check = find_file(baseline_dir, ("log.checkMesh",))
    baseline_match = re.search(r"\bcells:\s*(\d+)", baseline_check.read_text(errors="replace")) if baseline_check else None
    baseline_cells = int(baseline_match.group(1)) if baseline_match else None
    diag = diagnostics(log_data, case_dir, kind, baseline_cells)

    coverage = None
    coverage_error = None
    if data_path:
        try:
            samples = ANALYZER.read_cd(data_path)
            coverage = {"start_s": samples[0][0], "end_s": samples[-1][0], "sample_count": len(samples)}
        except (OSError, ValueError) as error:
            coverage_error = str(error)

    solver_end = log_data.get("solver_end_seen", False)
    process_failed = log_data.get("failure_marker") is not None
    log_end_time = log_data.get("simulation_end_time_s")
    solver_complete = solver_end and log_end_time is not None and log_end_time >= expected_end - 1e-9
    data_complete = (coverage is not None and coverage["start_s"] <= 0.5 and
                     coverage["end_s"] >= expected_end - 1e-9)
    solver_data_complete = solver_complete and data_complete
    complete_evidence = solver_data_complete and mesh_check["passed"]
    error = None
    if process_failed:
        status = "failed"
        error = log_data["failure_marker"]
    elif solver_data_complete and not mesh_check["passed"]:
        status = "error"
        error = mesh_check["error"]
    elif complete_evidence:
        status = "complete"
    elif manifest_status == "failed":
        status = "failed"
        error = case.get("error", case.get("failure", case.get("message", "manifest records solver failure")))
    elif manifest_status == "complete":
        status = "error"
        error = "manifest says complete, but solver End/end time and full source data coverage are not both proven"
    elif is_baseline:
        status = "error"
        error = "baseline solver End/end time and full source data coverage are not both proven"
    elif manifest_status == "running":
        status = "running"
    else:
        status = "pending"

    summary = None
    analysis_method = None
    analysis_note = None
    analysis_status = "pending"
    if status == "complete":
        summary, analysis_method, analysis_note = analyze_complete(case_dir, data_path, name)
        analysis_status = "complete" if summary else "error"
        if not summary:
            status = "error"
            error = analysis_note

    return {
        "name": name,
        "status": status,
        "manifest_status": manifest_status,
        "case_directory": str(case_dir),
        "kind": kind,
        "configured_change": {"parameter": "baseline", "configured": manifest["baseline_settings"]}
            if is_baseline else configured_change(case, manifest),
        "warm_start": warm_start(case or {}, kind, manifest),
        "domain_mesh_check": mesh_check,
        "solver": {key: value for key, value in log_data.items() if key != "steps"},
        "diagnostics": diag,
        "source_data": {"file": str(data_path) if data_path else None,
                        "coverage": coverage, "error": coverage_error,
                        "complete_for_study": data_complete},
        "analysis": summary,
        "analysis_method": analysis_method,
        "analysis_status": analysis_status,
        "analysis_note": analysis_note,
        "error": error,
        "solver_completion_proven": solver_complete,
    }


def attach_comparisons(records):
    baseline = records[0]
    baseline_analysis = baseline.get("analysis") or {}
    for record in records:
        result = record.get("analysis") or {}
        fixed_base = baseline_analysis.get("mean_cd_0.5_1.0")
        cycle_base = baseline_analysis.get("cycle_mean_cd")
        record["comparison"] = {
            "fixed_cd_change_percent": (
                (result["mean_cd_0.5_1.0"] - fixed_base) / fixed_base * 100
                if result.get("mean_cd_0.5_1.0") is not None and fixed_base else None),
            "cycle_cd_change_percent": (
                (result["cycle_mean_cd"] - cycle_base) / cycle_base * 100
                if result.get("cycle_mean_cd") is not None and cycle_base else None),
            "half_window_drift_percent": (
                (result["mean_cd_0.75_1.0"] - result["mean_cd_0.5_0.75"])
                / result["mean_cd_0.5_0.75"] * 100
                if result.get("mean_cd_0.5_0.75") else None),
        }


def cycle_means(summary):
    if not summary or "cycle_mean_cd" not in summary:
        return None
    means = []
    periods = []
    index = 1
    while f"cycle_{index}_mean_cd" in summary:
        means.append(summary[f"cycle_{index}_mean_cd"])
        periods.append(summary[f"cycle_{index}_period_s"])
        index += 1
    return {"start_s": summary["cycle_1_start_s"],
            "end_s": summary[f"cycle_{index - 1}_end_s"],
            "per_cycle_mean_cd": means, "periods_s": periods,
            "combined_mean_cd": summary["cycle_mean_cd"]}


def flat_row(record):
    analysis = record.get("analysis") or {}
    solver = record.get("solver", {})
    diagnostics = record.get("diagnostics", {})
    coverage = record.get("source_data", {}).get("coverage") or {}
    change = record.get("configured_change", {})
    warm = record.get("warm_start", {})
    co = diagnostics.get("max_co_all") or {}
    co_window = diagnostics.get("max_co_after_0.5_s") or {}
    dt = diagnostics.get("delta_t_all_s") or {}
    dt_window = diagnostics.get("delta_t_after_0.5_s") or {}
    yplus = diagnostics.get("body_y_plus") or {}
    cycle = cycle_means(analysis)
    return {
        "case": record["name"], "status": record["status"], "manifest_status": record["manifest_status"],
        "kind": record["kind"], "changed_parameter": change.get("parameter"),
        "baseline_value": change.get("baseline"), "configured_value": change.get("configured", change.get("factor")),
        "configured_L_delta": change.get("configured_L"),
        "warm_start_protocol": warm.get("protocol"), "warm_start_time_s": warm.get("time_s"),
        "warm_start_deltaT_s": warm.get("delta_t_s"),
        "coverage_start_s": coverage.get("start_s"), "coverage_end_s": coverage.get("end_s"),
        "solver_end_time_s": solver.get("simulation_end_time_s"),
        "solver_completion_proven": record.get("solver_completion_proven"),
        "wall_runtime_s": (solver.get("runtime") or {}).get("wall_s"),
        "maxCo_all_count": co.get("count"), "maxCo_all_min": co.get("min"),
        "maxCo_all_mean": co.get("mean"), "maxCo_all_median": co.get("median"),
        "maxCo_all_max": co.get("max"), "maxCo_after_0.5_mean": co_window.get("mean"),
        "maxCo_after_0.5_max": co_window.get("max"),
        "deltaT_all_min_s": dt.get("min"), "deltaT_all_max_s": dt.get("max"),
        "deltaT_after_0.5_min_s": dt_window.get("min"), "deltaT_after_0.5_max_s": dt_window.get("max"),
        "final_continuity_global": (solver.get("final_continuity_error") or {}).get("global"),
        "mesh_cell_count": diagnostics.get("mesh_cell_count"),
        "mesh_cell_count_source": diagnostics.get("mesh_cell_count_source"),
        "domain_mesh_check_passed": record.get("domain_mesh_check", {}).get("passed"),
        "domain_mesh_check_status": record.get("domain_mesh_check", {}).get("status"),
        "domain_mesh_check_error": record.get("domain_mesh_check", {}).get("error"),
        "body_y_plus_min": yplus.get("min"), "body_y_plus_max": yplus.get("max"),
        "body_y_plus_average": yplus.get("average"),
        "fixed_window_cd": analysis.get("mean_cd_0.5_1.0"),
        "fixed_window_change_percent": record["comparison"].get("fixed_cd_change_percent"),
        "first_half_cd": analysis.get("mean_cd_0.5_0.75"),
        "second_half_cd": analysis.get("mean_cd_0.75_1.0"),
        "half_window_drift_percent": record["comparison"].get("half_window_drift_percent"),
        "cycle_start_s": cycle.get("start_s") if cycle else None,
        "cycle_end_s": cycle.get("end_s") if cycle else None,
        "cycle_periods_s": json.dumps(cycle.get("periods_s")) if cycle else None,
        "cycle_means_cd": json.dumps(cycle.get("per_cycle_mean_cd")) if cycle else None,
        "cycle_mean_cd": cycle.get("combined_mean_cd") if cycle else None,
        "cycle_change_percent": record["comparison"].get("cycle_cd_change_percent"),
        "analysis_method": record.get("analysis_method"), "error": record.get("error") or record.get("analysis_note"),
    }


def render_run_markdown(record):
    flat = flat_row(record)
    lines = [f"# {record['name']}", "", f"Status: **{record['status']}** (manifest: {record['manifest_status']}).", ""]
    change = record["configured_change"]
    lines += [f"Configured change: `{json.dumps(change, sort_keys=True)}`.",
              f"Warm-start protocol: `{json.dumps(record['warm_start'], sort_keys=True)}`.", ""]
    if record.get("error"):
        lines += [f"Error: {record['error']}", ""]
    if record.get("analysis_note"):
        lines += [f"Analysis note: {record['analysis_note']}", ""]
    lines += ["| Measure | Result |", "|---|---:|",
              f"| Source coverage | {flat['coverage_start_s']}–{flat['coverage_end_s']} s |",
              f"| Solver end time / completion proven | {flat['solver_end_time_s']} s / {flat['solver_completion_proven']} |",
              f"| Wall runtime | {flat['wall_runtime_s']} s |",
              f"| maxCo all run (min / mean / median / max) | {flat['maxCo_all_min']} / {flat['maxCo_all_mean']} / {flat['maxCo_all_median']} / {flat['maxCo_all_max']} |",
              f"| maxCo after 0.5 s (mean / max) | {flat['maxCo_after_0.5_mean']} / {flat['maxCo_after_0.5_max']} |",
              f"| deltaT all run (min / max) | {flat['deltaT_all_min_s']} / {flat['deltaT_all_max_s']} s |",
              f"| deltaT after 0.5 s (min / max) | {flat['deltaT_after_0.5_min_s']} / {flat['deltaT_after_0.5_max_s']} s |",
              f"| Final continuity global error | {flat['final_continuity_global']} |",
              f"| Cell count | {flat['mesh_cell_count']} ({flat['mesh_cell_count_source']}) |",
              f"| Required domain checkMesh | {flat['domain_mesh_check_status']} ({flat['domain_mesh_check_error'] or 'passed / not required'}) |",
              f"| Body y+ min / max / average | {flat['body_y_plus_min']} / {flat['body_y_plus_max']} / {flat['body_y_plus_average']} |",
              f"| Fixed-window Cd / change vs baseline | {flat['fixed_window_cd']} / {flat['fixed_window_change_percent']}% |",
              f"| Half-window Cd (0.5–0.75 / 0.75–1.0 s) | {flat['first_half_cd']} / {flat['second_half_cd']} |",
              f"| Two-cycle Cd / change vs baseline | {flat['cycle_mean_cd']} / {flat['cycle_change_percent']}% |",
              f"| Cycle bounds / periods / individual means | {flat['cycle_start_s']}–{flat['cycle_end_s']} s / {flat['cycle_periods_s']} s / {flat['cycle_means_cd']} |",
              f"| Analysis method | {record.get('analysis_method')} |", ""]
    return "\n".join(lines)


def render_comparison(records, manifest):
    baseline = records[0].get("analysis") or {}
    baseline_cycles = cycle_means(baseline)
    cycle_variation = None
    if baseline_cycles and baseline_cycles["per_cycle_mean_cd"][0]:
        values = baseline_cycles["per_cycle_mean_cd"]
        cycle_variation = (values[-1] - values[0]) / values[0] * 100
    base_halves = records[0].get("comparison", {}).get("half_window_drift_percent")
    lines = [
        "# 313 sensitivity study results", "",
        "Saved baseline setup: inlet speed 22.2222222222 m/s; kinematic viscosity 1.5e-5 m²/s; kOmegaSST; inlet turbulence intensity 5% and viscosity ratio 10. Force-coefficient normalization uses rhoInf = 1 kg/m³, Aref = 0.043834 m², and lRef = 1.42 m.",
        "Baseline numerical settings: adaptive maxCo = 0.5, initial deltaT = 0.0001 s, maxDeltaT = 0.005 s, backward time scheme; PIMPLE outer/pressure/non-orthogonal correctors = 2/2/2. Absolute linear tolerances are p = 1e-7 and U/k/omega = 1e-8; relTol is 0.01 for p and 0.1 for U/k/omega (final solves use relTol = 0).",
        "Each reported Cd mean uses time-weighted trapezoidal integration of the saved adaptive-time samples, with linear interpolation at integration boundaries.",
        "The primary Cd metric averages the first two complete cycles bounded by interpolated rising Cl=0 crossings after 0.5 s; the fixed 0.5–1.0 s mean is retained as a reference.",
        "maxCo and deltaT are summarized both over the full available run and after 0.5 s; whole-run maxima can include startup or warm-start steps before the averaging window.",
        f"Baseline cycle-to-cycle variation is {cycle_variation:.3f}% (second cycle relative to first). Baseline half-window drift is {base_halves:+.3f}% (0.75–1.0 s relative to 0.5–0.75 s)." if cycle_variation is not None and base_halves is not None else "Baseline drift metrics are unavailable until the baseline analysis completes.",
        f"Configured length L = {manifest['length_m']} m. Domain variants change one configured boundary distance by ±1 L; the refinement box, refinement levels, and max_h = 0.5 m remain unchanged. Remeshing may change cell placement and count. Mesh sensitivity is excluded.", "",
        "## Cd results", "",
        "| Case | Status | Configured change | Warm start | Cycle window (s) | Cycle Cd / change | Fixed Cd / change |",
        "|---|---|---|---|---:|---:|---:|",
    ]
    for record in records:
        flat = flat_row(record)
        delta = record["configured_change"]
        param = delta.get("parameter", "")
        value = delta.get("configured", delta.get("factor", ""))
        if delta.get("baseline") is not None:
            configured = f"{param}: {delta['baseline']} → {value}"
        elif value != "":
            configured = f"{param}: {value}"
        else:
            configured = param
        warm = record["warm_start"].get("time_s", record["warm_start"].get("protocol"))
        cycle = "unavailable" if flat["cycle_mean_cd"] is None else f"{flat['cycle_mean_cd']:.7g} / {flat['cycle_change_percent']:+.3f}%"
        fixed = "unavailable" if flat["fixed_window_cd"] is None else f"{flat['fixed_window_cd']:.7g} / {flat['fixed_window_change_percent']:+.3f}%"
        if record.get("analysis_method") == "fixed_window_fallback":
            cycle = "unavailable: insufficient complete cycles"
            fixed += " (fixed-window fallback)"
        bounds = "unavailable" if flat["cycle_start_s"] is None else f"{flat['cycle_start_s']:.6g}–{flat['cycle_end_s']:.6g}"
        lines.append(f"| {record['name']} | {record['status']} | {configured} | {warm} | {bounds} | {cycle} | {fixed} |")
    lines += ["", "## Solver and mesh diagnostics", "",
              "| Case | Status | maxCo distribution (min / mean / median / max; all run) | maxCo mean / max after 0.5 s | deltaT all run (min–max s) | End time / wall time (s) | Final global continuity | Mesh check | Cells | Body y+ min / max / avg |",
              "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for record in records:
        flat = flat_row(record)
        co = "unavailable" if flat["maxCo_all_count"] is None else (
            f"{flat['maxCo_all_min']:.4g} / {flat['maxCo_all_mean']:.4g} / "
            f"{flat['maxCo_all_median']:.4g} / {flat['maxCo_all_max']:.4g}")
        window_co = "unavailable" if flat["maxCo_after_0.5_mean"] is None else (
            f"{flat['maxCo_after_0.5_mean']:.4g} / {flat['maxCo_after_0.5_max']:.4g}")
        dt = "unavailable" if flat["deltaT_all_min_s"] is None else f"{flat['deltaT_all_min_s']:.4g}–{flat['deltaT_all_max_s']:.4g}"
        runtime = "unavailable" if flat["solver_end_time_s"] is None else (
            f"{flat['solver_end_time_s']:.6g} / {flat['wall_runtime_s']}")
        continuity = "unavailable" if flat["final_continuity_global"] is None else f"{flat['final_continuity_global']:.4g}"
        cells = "unavailable" if flat["mesh_cell_count"] is None else f"{flat['mesh_cell_count']} ({flat['mesh_cell_count_source']})"
        mesh_check = flat["domain_mesh_check_status"]
        yplus = "unavailable" if flat["body_y_plus_min"] is None else (
            f"{flat['body_y_plus_min']:.4g} / {flat['body_y_plus_max']:.4g} / {flat['body_y_plus_average']:.4g}")
        lines.append(f"| {record['name']} | {record['status']} | {co} | {window_co} | {dt} | {runtime} | {continuity} | {mesh_check} | {cells} | {yplus} |")
    lines += ["", "Pending and running cases have no complete Cd record. A complete record requires solver `End`, final time at or beyond 1 s, and force-coefficient coverage of the full averaging interval. Missing diagnostics are marked unavailable.", ""]
    lines += ["Mesh-quality failures are excluded from accepted Cd comparisons and saved as separate `.failed.tar.gz` archives. The shorter-inlet case failed one skewness check (one highly skewed face, maximum skewness 8.4413).",
              "Two-cycle means do not establish statistical stationarity: the baseline cycle-to-cycle variation and half-window drift remain appreciable. Small parameter differences should be interpreted in that context. Domain remeshing also changes cell placement; this study does not isolate mesh sensitivity.",
              "Some cases ran concurrently, and numerical variants warm-started at 0.3 s while domain and turbulence variants started at 0 s. Wall times are descriptive and are not a controlled performance comparison.", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "runs/313_study/results",
                        help="report directory (default: runs/313_study/results)")
    args = parser.parse_args()
    errors = []
    try:
        manifest = load_study_manifest()
        baseline_dir = Path(manifest["baseline_reference"])
        expected_end = float(manifest["baseline_settings"]["endTime"])
        records = [make_record("baseline_313", None, manifest, baseline_dir, expected_end)]
        records.extend(make_record(name, case, manifest, baseline_dir, expected_end)
                       for name, case in manifest["cases"].items())
        attach_comparisons(records)
        args.output.mkdir(parents=True, exist_ok=True)
        for record in records:
            (args.output / f"{record['name']}.json").write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
            (args.output / f"{record['name']}.md").write_text(render_run_markdown(record))
            if record["status"] in ("error", "failed"):
                errors.append(f"{record['name']}: {record.get('error') or 'solver failed'}")
        rows = [flat_row(record) for record in records]
        with (args.output / "comparison.csv").open("w", newline="") as output:
            writer = csv.DictWriter(output, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
        (args.output / "comparison.md").write_text(render_comparison(records, manifest))
        print(f"Wrote {len(records)} per-run reports and comparison files to {args.output}")
        print("Statuses: " + ", ".join(f"{name}={sum(record['status'] == name for record in records)}"
                                      for name in ("complete", "running", "pending", "failed", "error")))
        for error in errors:
            print(error, file=sys.stderr)
        return 1 if errors else 0
    except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError) as error:
        print(f"report error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
