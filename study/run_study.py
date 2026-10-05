#!/usr/bin/env python3
"""Prepare and run the 313 PIMPLE sensitivity cases."""

import argparse
import json
import math
import re
import shlex
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "saved_runs/313_pimple_run"
OUTPUT = ROOT / "runs/313_study"
OPENFOAM_BASHRC = Path("/usr/lib/openfoam/openfoam2412/etc/bashrc")
LENGTH = 1.09585
END_TIME = 1.0
RANKS = 6
WARM_START = 0.3
WARM_DELTA_T = 6.79727e-05


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def cases():
    result = [{"name": "maxCo_0p25", "kind": "maxCo", "value": 0.25,
               "restart_time": WARM_START}]
    result.append({"name": "maxCo_1", "kind": "maxCo", "value": 1.0,
                   "restart_time": WARM_START})
    for factor in (0.1, 10.0):
        result.append({"name": f"tolerance_x{factor:g}", "kind": "tolerance", "factor": factor,
                       "restart_time": WARM_START})
    for intensity in (0.01, 0.10):
        result.append({
            "name": f"turbulenceIntensity_{intensity * 100:g}pct",
            "kind": "turbulence_intensity",
            "intensity": intensity,
            "viscosity_ratio": 10,
            "initial_time": 0,
        })
    result.append({"name": "outerCorrectors_4", "kind": "PIMPLE", "value": 4,
                   "restart_time": WARM_START})
    for parameter, baseline in (("upstream_dist", 5), ("downstream_dist", 11), ("roof_height", 6)):
        for direction, offset in (("minus", -1), ("plus", 1)):
            result.append({
                "name": f"{parameter}_{direction}_1L",
                "kind": "domain",
                "parameter": parameter,
                "value": (baseline + offset) * LENGTH,
                "baseline_value": baseline * LENGTH,
            })
    return result


def load_manifest(path):
    if path.exists():
        return json.loads(path.read_text())
    return {
        "source": str(SOURCE),
        "baseline_reference": str(SOURCE),
        "baseline_settings": {"maxCo": 0.5, "endTime": END_TIME},
        "tolerance_definition": (
            "Multiply only tolerance entries for p, U, k, and omega in "
            "system/fvSolution.steady; relTol remains unchanged."
        ),
        "length_m": LENGTH,
        "mpi_ranks": RANKS,
        "warm_start": {"time_s": WARM_START, "deltaT_s": WARM_DELTA_T},
        "cases": {},
    }


def save_manifest(path, manifest):
    path.write_text(json.dumps(manifest, indent=2) + "\n")


def foam(case_dir, *args):
    command = "source " + shlex.quote(str(OPENFOAM_BASHRC)) + " && " + shlex.join(args)
    return subprocess.run(["bash", "-c", command], cwd=case_dir,
                          stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                          text=True, check=False)


def copy_source(case_dir, mesh_case, warm_start=True):
    shutil.copytree(SOURCE / "system", case_dir / "system")
    shutil.copytree(SOURCE / "0.orig", case_dir / "0.orig")
    shutil.copy2(SOURCE / "Allrun.pimple", case_dir / "Allrun.pimple")
    if mesh_case:
        (case_dir / "constant").mkdir()
        for name in ("transportProperties", "turbulenceProperties"):
            shutil.copy2(SOURCE / "constant" / name, case_dir / "constant" / name)
        shutil.copytree(SOURCE / "constant/triSurface", case_dir / "constant/triSurface")
    else:
        shutil.copytree(SOURCE / "constant", case_dir / "constant")
        for rank in range(RANKS):
            proc_name = f"processor{rank}"
            proc_dir = case_dir / proc_name
            proc_dir.mkdir()
            shutil.copytree(SOURCE / proc_name / "constant", proc_dir / "constant")
            shutil.copytree(SOURCE / proc_name / "0", proc_dir / "0")
            if warm_start:
                shutil.copytree(SOURCE / proc_name / "0.3", proc_dir / "0.3")


def set_entry(case_dir, dictionary, entry, value):
    result = foam(case_dir, "foamDictionary", "-entry", entry, "-set", str(value), dictionary)
    if result.returncode:
        detail = result.stderr.strip() if result.stderr else ""
        raise RuntimeError(f"foamDictionary failed for {dictionary}:{entry}: {detail}")


def set_block_mesh_dimension(case_dir, entry, value):
    path = case_dir / "system/blockMeshDict"
    text = path.read_text()
    pattern = rf"(?m)^([ \t]*{re.escape(entry)}[ \t]+)[^;\r\n]*(;[^\r\n]*)$"
    updated, count = re.subn(
        pattern,
        lambda match: match.group(1) + format(value, ".15g") + match.group(2),
        text,
    )
    if count != 1:
        raise RuntimeError(f"expected one {entry} definition in {path}, found {count}")
    path.write_text(updated)


def configure_warm_start(case_dir):
    for rank in range(RANKS):
        proc_dir = case_dir / f"processor{rank}"
        checkpoint = proc_dir / "0.3"
        if not checkpoint.exists():
            shutil.copytree(SOURCE / f"processor{rank}/0.3", checkpoint)
    set_entry(case_dir, "system/controlDict", "startFrom", "startTime")
    set_entry(case_dir, "system/controlDict", "startTime", WARM_START)
    set_entry(case_dir, "system/controlDict", "deltaT", WARM_DELTA_T)


def set_initial_intensity(case_dir, intensity):
    paths = [case_dir / "0.orig/include/initialConditions"]
    paths.extend(case_dir / f"processor{rank}/0/include/initialConditions" for rank in range(RANKS))
    for path in paths:
        text = path.read_text()
        updated, count = re.subn(
            r"(?m)^([ \t]*I[ \t]+)[^;\r\n]+(;[^\r\n]*)$",
            lambda match: match.group(1) + f"{intensity:g}" + match.group(2),
            text,
        )
        if count != 1:
            raise RuntimeError(f"expected one inlet intensity entry in {path}, found {count}")
        path.write_text(updated)


def prepare_case(spec, manifest):
    case_dir = OUTPUT / spec["name"]
    state = manifest["cases"].get(spec["name"])
    if case_dir.exists():
        if state is None:
            manifest["cases"][spec["name"]] = {
                **spec, "status": "existing_unmanaged", "updated": now(),
                "message": "Existing directory preserved; runner will not modify it.",
            }
        elif spec["kind"] in ("maxCo", "tolerance", "PIMPLE") and state.get("status") == "prepared" and "restart_time" not in state:
            if (case_dir / "log.pimpleFoam").exists():
                raise RuntimeError(f"{spec['name']}: solver log exists; warm-start migration left untouched")
            configure_warm_start(case_dir)
            state.update(restart_time=WARM_START, restart_deltaT=WARM_DELTA_T, updated=now())
        return case_dir

    mesh_case = spec["kind"] == "domain"
    case_dir.mkdir(parents=True)
    warm_start = spec["kind"] != "turbulence_intensity"
    copy_source(case_dir, mesh_case, warm_start=warm_start)
    if spec["kind"] == "maxCo":
        set_entry(case_dir, "system/controlDict", "maxCo", spec["value"])
    elif spec["kind"] == "tolerance":
        for field, baseline in (("p", 1e-7), ("U", 1e-8), ("k", 1e-8), ("omega", 1e-8)):
            set_entry(case_dir, "system/fvSolution.steady", f"solvers.{field}.tolerance",
                      baseline * spec["factor"])
    elif spec["kind"] == "PIMPLE":
        set_entry(case_dir, "system/fvSolution", "PIMPLE.nOuterCorrectors", spec["value"])
    elif spec["kind"] == "turbulence_intensity":
        set_initial_intensity(case_dir, spec["intensity"])
    else:
        set_block_mesh_dimension(case_dir, spec["parameter"], spec["value"])
    if not mesh_case and warm_start:
        configure_warm_start(case_dir)
    manifest["cases"][spec["name"]] = {**spec, "status": "prepared", "updated": now()}
    return case_dir


def solver_complete(case_dir):
    log = case_dir / "log.pimpleFoam"
    if not log.is_file():
        return False, "missing log.pimpleFoam"
    contents = log.read_text(errors="replace")
    if not re.search(r"^End\s*$", contents, re.MULTILINE):
        return False, "log.pimpleFoam has no End marker"
    times = [float(value) for value in re.findall(r"^Time\s*=\s*([0-9.eE+-]+)", contents, re.MULTILINE)]
    if not times or not math.isclose(max(times), END_TIME, rel_tol=0, abs_tol=1e-8):
        return False, f"log.pimpleFoam did not reach {END_TIME:g} s"
    return True, "solver log ended at 1 s"


def domain_bounds_match(spec, check_mesh_log):
    bounding_box = re.findall(
        r"Overall domain bounding box\s*\(\s*([-+0-9.eE]+)\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\s*\)"
        r"\s*\(\s*([-+0-9.eE]+)\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\s*\)",
        check_mesh_log,
    )
    if not bounding_box:
        return False, "domain checkMesh has no overall bounding box"
    values = tuple(float(value) for value in bounding_box[-1])
    dimensions = {"upstream_dist": 5, "downstream_dist": 11, "roof_height": 6}
    expected = {
        "upstream_dist": dimensions["upstream_dist"] * LENGTH,
        "downstream_dist": dimensions["downstream_dist"] * LENGTH,
        "roof_height": dimensions["roof_height"] * LENGTH,
    }
    expected[spec["parameter"]] = spec["value"]
    actual = {"upstream_dist": -values[0], "downstream_dist": values[3], "roof_height": values[4]}
    for parameter, value in expected.items():
        if not math.isclose(actual[parameter], value, rel_tol=0, abs_tol=1e-4):
            return False, (
                f"domain checkMesh {parameter} extent {actual[parameter]:g} m "
                f"does not match requested {value:g} m"
            )
    return True, "domain checkMesh bounds match requested extents"


def case_complete(spec, case_dir):
    complete, message = solver_complete(case_dir)
    if not complete:
        return complete, message
    if spec["kind"] == "domain":
        log = case_dir / "log.checkMesh"
        if not log.is_file():
            return False, "missing domain log.checkMesh"
        contents = log.read_text(errors="replace")
        if "Mesh OK." not in contents:
            return False, "domain checkMesh did not report Mesh OK."
        complete, message = domain_bounds_match(spec, contents)
        if not complete:
            return complete, message
    return True, message


def run_case(spec, case_dir):
    mesh_case = spec["kind"] == "domain"
    if mesh_case:
        log = case_dir / "execution.log"
        with log.open("w") as output:
            command = "source " + shlex.quote(str(OPENFOAM_BASHRC)) + " && bash ./Allrun.pimple"
            result = subprocess.run(["bash", "-c", command], cwd=case_dir,
                                    stdout=output, stderr=subprocess.STDOUT, check=False)
        if result.returncode:
            return False, f"Allrun.pimple exited {result.returncode}"
        for path in sorted(case_dir.glob("log.*")):
            if path.is_file() and not re.search(r"^End\s*$", path.read_text(errors="replace"), re.MULTILINE):
                return False, f"{path.name} has no End marker"
    else:
        log = case_dir / "log.pimpleFoam"
        if log.exists():
            previous = case_dir / f"log.pimpleFoam.previous-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            shutil.copy2(log, previous)
        command = (
            "source " + shlex.quote(str(OPENFOAM_BASHRC)) +
            f" && mpirun -np {RANKS} pimpleFoam -parallel"
        )
        with log.open("w") as output:
            result = subprocess.run(["bash", "-c", command], cwd=case_dir,
                                    stdout=output, stderr=subprocess.STDOUT, check=False)
        if result.returncode:
            return False, f"pimpleFoam exited {result.returncode}"
    return case_complete(spec, case_dir)


def update_report(manifest):
    completed = [name for name, state in manifest["cases"].items() if state.get("status") == "complete"]
    baseline_coeff = SOURCE / "postProcessing/forceCoeffs1/0/coefficient.dat"
    case_paths = [str(baseline_coeff)] + [str(OUTPUT / name) for name in sorted(completed)]
    script = str(ROOT / "study/analyze.py")
    fixed = subprocess.run([sys.executable, script, *case_paths,
                            "--csv", str(OUTPUT / "summary_fixed.csv"),
                            "--markdown", str(OUTPUT / "summary_fixed.md")],
                           cwd=ROOT, capture_output=True, text=True, check=False)
    manifest["fixed_window_analysis_status"] = "complete" if fixed.returncode == 0 else "failed"
    manifest["fixed_window_analysis_error"] = fixed.stderr.strip() if fixed.returncode else ""

    cycle_cases = []
    missing_cycles = []
    for name, path in zip(["saved_baseline"] + sorted(completed), case_paths):
        cycle = subprocess.run([sys.executable, script, path, "--cycles", "2"],
                               cwd=ROOT, capture_output=True, text=True, check=False)
        if cycle.returncode == 0:
            cycle_cases.append(path)
            if name != "saved_baseline":
                manifest["cases"][name].update(cycle_analysis_status="complete", cycle_analysis_error="")
        else:
            reason = cycle.stderr.strip()
            if name != "saved_baseline":
                manifest["cases"][name].update(cycle_analysis_status="incomplete", cycle_analysis_error=reason)
            missing_cycles.append((name, reason))

    cycle_result = (subprocess.run([sys.executable, script, *cycle_cases, "--cycles", "2",
                                    "--csv", str(OUTPUT / "summary.csv"),
                                    "--markdown", str(OUTPUT / "summary.md")],
                                   cwd=ROOT, capture_output=True, text=True, check=False)
                    if cycle_cases else None)
    if cycle_result is not None and cycle_result.returncode == 0:
        with (OUTPUT / "summary.md").open("a") as markdown:
            if missing_cycles:
                markdown.write("\nCycle average omitted for cases without two complete Cl cycles after 0.5 s:\n\n")
                markdown.writelines(f"- {name}: {reason}\n" for name, reason in missing_cycles)
    manifest["cycle_analysis_status"] = (
        "complete" if cycle_result is not None and cycle_result.returncode == 0 else "failed"
    )
    manifest["cycle_analysis_error"] = (
        cycle_result.stderr.strip() if cycle_result is not None and cycle_result.returncode else ""
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare-only", action="store_true", help="prepare cases without running simulations")
    parser.add_argument("--cases", nargs="+", help="run only these case names")
    parser.add_argument("--manifest", type=Path, default=OUTPUT / "manifest.json",
                        help="manifest for this batch (default: runs/313_study/manifest.json)")
    args = parser.parse_args()
    specs = cases()
    by_name = {spec["name"]: spec for spec in specs}
    if args.cases:
        unknown = sorted(set(args.cases) - set(by_name))
        if unknown:
            parser.error("unknown case name(s): " + ", ".join(unknown))
        specs = [by_name[name] for name in args.cases]

    if not SOURCE.is_dir():
        parser.error(f"saved baseline not found: {SOURCE}")
    if not OPENFOAM_BASHRC.is_file():
        parser.error(f"OpenFOAM setup script not found: {OPENFOAM_BASHRC}")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    manifest_path = args.manifest.resolve()
    manifest = load_manifest(manifest_path)
    manifest.setdefault("warm_start", {"time_s": WARM_START, "deltaT_s": WARM_DELTA_T})

    for spec in specs:
        try:
            case_dir = prepare_case(spec, manifest)
        except (OSError, RuntimeError) as error:
            manifest["cases"][spec["name"]] = {**spec, "status": "prepare_failed",
                                                "updated": now(), "message": str(error)}
            save_manifest(manifest_path, manifest)
            print(f"{spec['name']}: preparation failed: {error}", file=sys.stderr)
            continue
        state = manifest["cases"][spec["name"]]
        if state.get("status") == "existing_unmanaged":
            print(f"{spec['name']}: existing directory left untouched")
            continue
        if args.prepare_only:
            if state.get("status") not in ("failed", "prepare_failed", "complete"):
                state.update(status="prepared", updated=now())
            print(f"{spec['name']}: {state['status']} (preparation only)")
        elif state.get("status") == "complete":
            complete, message = case_complete(spec, case_dir)
            if complete:
                print(f"{spec['name']}: already complete, skipped")
                continue
            state.update(status="failed", updated=now(), message=message)
        else:
            state.update(status="running", updated=now())
            save_manifest(manifest_path, manifest)
            print(f"{spec['name']}: running", flush=True)
            try:
                ok, message = run_case(spec, case_dir)
            except OSError as error:
                ok, message = False, str(error)
            state.update(status="complete" if ok else "failed", updated=now(), message=message)
            print(f"{spec['name']}: {state['status']} ({message})")
            if ok:
                update_report(manifest)
        save_manifest(manifest_path, manifest)

    if args.prepare_only:
        update_report(manifest)
        save_manifest(manifest_path, manifest)
    return 0 if all(manifest["cases"].get(spec["name"], {}).get("status") in ("prepared", "complete", "existing_unmanaged")
                    for spec in specs) else 1


if __name__ == "__main__":
    sys.exit(main())
