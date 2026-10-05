#!/usr/bin/env python3
"""Run the original 313 mesh with pimpleFoam and Spalart-Allmaras at maxCo=1."""

import argparse
import json
import re
import shutil
import subprocess
import tarfile
from pathlib import Path

from run_study import ROOT, OPENFOAM_BASHRC, solver_complete
from run_prism_symmetry import averages


SOURCE = ROOT / "saved_runs/313_pimple_run"
OUTPUT = ROOT / "runs/313_sa_pimple"
CASE = OUTPUT / "case"


def prepare():
    if CASE.exists():
        return
    CASE.mkdir(parents=True)
    for name in ("system", "0.orig", "constant"):
        shutil.copytree(SOURCE / name, CASE / name)
    path = CASE / "constant/turbulenceProperties"
    path.write_text(path.read_text().replace("kOmegaSST", "SpalartAllmaras"))

    # Retain inlet nut/nu = 10 using the SA relation nut = nuTilda * fv1.
    lower, upper = 10.0, 20.0
    for _ in range(60):
        chi = (lower + upper) / 2
        if chi * chi**3 / (chi**3 + 7.1**3) < 10:
            lower = chi
        else:
            upper = chi
    nu_tilda = (lower + upper) / 2 * 1.5e-5
    text = (CASE / "0.orig/omega").read_text()
    text = text.replace("object      omega;", "object      nuTilda;")
    text = text.replace("[0 0 -1 0 0 0 0]", "[0 2 -1 0 0 0 0]")
    text = text.replace("uniform $turbulentOmega", f"uniform {nu_tilda:.15g}")
    text = text.replace("type            omegaWallFunction;\n        value           $internalField;",
                        "type            fixedValue;\n        value           uniform 0;")
    (CASE / "0.orig/nuTilda").write_text(text)
    for name in ("k", "omega"):
        (CASE / "0.orig" / name).unlink()
    path = CASE / "0.orig/nut"
    path.write_text(path.read_text().replace("nutkWallFunction", "nutUSpaldingWallFunction"))

    path = CASE / "system/fvSolution.steady"
    text = path.read_text()
    text = re.sub(r"\n    omega\n    \{.*?\n    \}\n", "\n", text, flags=re.S)
    text = text.replace("    k\n", "    nuTilda\n")
    text = text.replace("        k               0.7;", "        nuTilda         0.7;")
    text = text.replace("        omega           0.7;\n", "")
    path.write_text(text)
    path = CASE / "system/fvSolution"
    path.write_text(path.read_text().replace("(U|k|omega)Final", "(U|nuTilda)Final"))
    path = CASE / "system/fvSchemes.steady"
    text = path.read_text().replace("div(phi,k)", "div(phi,nuTilda)")
    text = text.replace("    div(phi,omega)  $turbulence;\n", "")
    path.write_text(text)

    path = CASE / "system/controlDict"
    path.write_text(re.sub(r"(?m)^(maxCo[ \t]+)[^;]+;", r"\g<1>1;", path.read_text()))

    # Reuse the exact final mesh; initialize fields and potential flow afresh.
    text = (SOURCE / "Allrun.pimple").read_text()
    start = text.index("runApplication surfaceFeatureExtract")
    end = text.index("runParallel $decompDict renumberMesh")
    text = text[:start] + 'runApplication $decompDict decomposePar -force || exit\n\n' + text[end:]
    (CASE / "Allrun.sa").write_text(text)
    settings = {"source": str(SOURCE), "status": "prepared", "model": "SpalartAllmaras",
                "solver": "pimpleFoam", "maxCo": 1, "mesh_reused": True, "mpi_ranks": 6, "start_time_s": 0, "end_time_s": 1,
                "inlet_viscosity_ratio": 10, "nuTilda_m2_s": nu_tilda,
                "body_nut_condition": "nutUSpaldingWallFunction"}
    (OUTPUT / "settings.json").write_text(json.dumps(settings, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args()
    prepare()
    if args.prepare_only:
        print(f"Prepared {CASE}")
        return
    if (CASE / "execution.log").exists():
        raise RuntimeError("Existing execution preserved; inspect before retrying")
    settings = json.loads((OUTPUT / "settings.json").read_text())
    settings["status"] = "running"
    (OUTPUT / "settings.json").write_text(json.dumps(settings, indent=2) + "\n")
    print(f"Running Spalart-Allmaras 313 case in {CASE}", flush=True)
    with (CASE / "execution.log").open("w") as log:
        run = subprocess.run(["bash", "-c", f"source {OPENFOAM_BASHRC} && bash ./Allrun.sa"],
                             cwd=CASE, stdout=log, stderr=subprocess.STDOUT)
    complete, message = solver_complete(CASE)
    mesh = (CASE / "log.checkMesh").read_text() if (CASE / "log.checkMesh").exists() else ""
    stages_ok = all(re.search(r"^End\s*$", p.read_text(), re.M) and "FOAM FATAL" not in p.read_text()
                    for p in CASE.glob("log.*"))
    accepted = run.returncode == 0 and complete and "Mesh OK." in mesh and stages_ok
    settings["status"] = "complete" if accepted else "failed"
    (OUTPUT / "settings.json").write_text(json.dumps(settings, indent=2) + "\n")
    result = {"accepted": accepted, "returncode": run.returncode,
              "solver_complete": complete, "solver_message": message, "mesh_ok": "Mesh OK." in mesh,
              "stage_logs_ok": stages_ok, "settings": settings}
    if complete:
        result["reference"] = averages(SOURCE)
        result["spalart_allmaras"] = averages(CASE)
        result["change_percent"] = {}
        for metric in ("two_cycle_cd", "fixed_window_cd"):
            old, new = result["reference"].get(metric), result["spalart_allmaras"].get(metric)
            result["change_percent"][metric] = 100 * (new - old) / old if old is not None and new is not None else None
    (OUTPUT / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    lines = ["# Original 313: transient Spalart–Allmaras", "",
             "Original geometry/mesh, pimpleFoam, maxCo=1, fresh initialization, 0–1 s.", "",
             "Cd means use time-weighted integration. Cycle mean uses the last two complete rising Cl=0 cycles anywhere in each file; it may include startup. The fixed 0.5–1 s mean is also reported.", "",
             f"Solver complete: {complete}; Mesh OK: {'Mesh OK.' in mesh}; stage logs OK: {stages_ok}."]
    if complete:
        lines += ["", "| Metric | Saved SST baseline | Spalart–Allmaras | Change (%) |",
                  "|---|---:|---:|---:|"]
        for metric in ("two_cycle_cd", "fixed_window_cd"):
            lines.append(f"| {metric} | {result['reference'].get(metric)} | {result['spalart_allmaras'].get(metric)} | {result['change_percent'].get(metric)} |")
        lines += ["", f"SA cycle bounds (s): {result['spalart_allmaras'].get('two_cycle_bounds_s')}",
                  f"SA per-cycle Cd: {result['spalart_allmaras'].get('per_cycle_cd')}", "",
                  "Comparison changes both turbulence model and maxCo (baseline maxCo=0.5). Solver completion does not establish statistical stationarity."]
    (OUTPUT / "result.md").write_text("\n".join(lines) + "\n")
    target = OUTPUT / ("313_sa_pimple.tar.gz" if accepted else "313_sa_pimple.failed.tar.gz")
    with tarfile.open(target, "w:gz") as archive:
        archive.add(CASE, arcname="313_sa_pimple",
                    filter=lambda info: None if "dynamicCode" in Path(info.name).parts else info)
    print(f"Finished: accepted={accepted}; result={OUTPUT / 'result.md'}", flush=True)


if __name__ == "__main__":
    main()
