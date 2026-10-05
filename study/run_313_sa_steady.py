#!/usr/bin/env python3
"""Run the original 313 mesh with simpleFoam and Spalart-Allmaras."""

import argparse
import json
import re
import shutil
import subprocess
import tarfile

from analyze import coefficient_file, read_coefficients
from run_study import ROOT, OPENFOAM_BASHRC


SOURCE = ROOT / "saved_runs/313_pimple_run"
OUTPUT = ROOT / "runs/313_sa_steady"
CASE = OUTPUT / "case"
NU_TILDA = 0.000180705958724582  # nuTilda*fv1/nu = 10, nu=1.5e-5, Cv1=7.1


def prepare():
    if CASE.exists():
        return
    CASE.mkdir(parents=True)
    for name in ("system", "0.orig", "constant"):
        shutil.copytree(SOURCE / name, CASE / name)
    path = CASE / "constant/turbulenceProperties"
    path.write_text(path.read_text().replace("kOmegaSST", "SpalartAllmaras"))
    for name in ("controlDict", "fvSchemes", "fvSolution"):
        shutil.copy2(CASE / "system" / (name + ".steady"), CASE / "system" / name)
    path = CASE / "system/controlDict"
    path.write_text(path.read_text().replace('    #include "foamReport"\n', ""))

    text = (CASE / "0.orig/omega").read_text()
    text = text.replace("object      omega;", "object      nuTilda;")
    text = text.replace("[0 0 -1 0 0 0 0]", "[0 2 -1 0 0 0 0]")
    text = text.replace("uniform $turbulentOmega", f"uniform {NU_TILDA:.15g}")
    text = text.replace("type            omegaWallFunction;\n        value           $internalField;",
                        "type            fixedValue;\n        value           uniform 0;")
    (CASE / "0.orig/nuTilda").write_text(text)
    for name in ("k", "omega"):
        (CASE / "0.orig" / name).unlink()
    path = CASE / "0.orig/nut"
    path.write_text(path.read_text().replace("nutkWallFunction", "nutUSpaldingWallFunction"))
    path = CASE / "system/fvSolution"
    text = re.sub(r"\n    omega\n    \{.*?\n    \}\n", "\n", path.read_text(), flags=re.S)
    text = text.replace("    k\n", "    nuTilda\n")
    text = text.replace("        k               0.7;", "        nuTilda         0.7;")
    text = text.replace("        omega           0.7;\n", "")
    path.write_text(text)
    path = CASE / "system/fvSchemes"
    text = path.read_text().replace("div(phi,k)", "div(phi,nuTilda)")
    path.write_text(text.replace("    div(phi,omega)  $turbulence;\n", ""))

    text = (SOURCE / "Allrun.pimple").read_text()
    start = text.index("runApplication surfaceFeatureExtract")
    end = text.index("runParallel $decompDict renumberMesh")
    text = text[:start] + 'runApplication $decompDict decomposePar -force || exit\n\n' + text[end:]
    text = text.replace("pimpleFoam", "simpleFoam")
    (CASE / "Allrun.sa").write_text(text)
    settings = {"source": str(SOURCE), "status": "prepared", "model": "SpalartAllmaras",
                "solver": "simpleFoam", "mesh_reused": True, "mpi_ranks": 6,
                "start_iteration": 0, "end_iteration": 500,
                "inlet_viscosity_ratio": 10, "nuTilda_m2_s": NU_TILDA}
    (OUTPUT / "settings.json").write_text(json.dumps(settings, indent=2) + "\n")


def finish(returncode):
    settings = json.loads((OUTPUT / "settings.json").read_text())
    log = (CASE / "log.simpleFoam").read_text() if (CASE / "log.simpleFoam").exists() else ""
    iterations = re.findall(r"^Time = (\S+)", log, re.M)
    complete = bool(iterations) and float(iterations[-1]) == 500 and bool(re.search(r"^End\s*$", log, re.M))
    mesh = (CASE / "log.checkMesh").read_text() if (CASE / "log.checkMesh").exists() else ""
    stages_ok = all(re.search(r"^End\s*$", p.read_text(), re.M) and "FOAM FATAL" not in p.read_text()
                    for p in CASE.glob("log.*"))
    accepted = returncode == 0 and complete and "Mesh OK." in mesh and stages_ok
    settings["status"] = "complete" if accepted else "failed"
    (OUTPUT / "settings.json").write_text(json.dumps(settings, indent=2) + "\n")
    result = {"accepted": accepted, "returncode": returncode, "solver_complete": complete,
              "mesh_ok": "Mesh OK." in mesh, "stage_logs_ok": stages_ok, "settings": settings,
              "note": "500 steady SIMPLE iterations; reaching the iteration limit does not establish convergence."}
    if complete:
        samples = read_coefficients(coefficient_file(CASE), ("Cd",))
        tail = [cd for iteration, cd in samples if iteration > 400]
        result.update(final_cd=samples[-1][1], last_100_iterations_mean_cd=sum(tail) / len(tail),
                      last_100_iterations_cd_range=[min(tail), max(tail)])
        result["final_initial_residuals"] = {
            field: float(re.findall(rf"Solving for {field}, Initial residual = (\S+),", log)[-1])
            for field in ("Ux", "Uy", "p", "nuTilda")}
    (OUTPUT / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    lines = ["# Original 313: steady Spalart–Allmaras", "", result["note"], "",
             f"Solver completed: {complete}; Mesh OK: {result['mesh_ok']}; stage logs OK: {stages_ok}."]
    if complete:
        lines += ["", f"Final Cd: {result['final_cd']}",
                  f"Mean Cd, iterations 401–500: {result['last_100_iterations_mean_cd']}",
                  f"Cd range, iterations 401–500: {result['last_100_iterations_cd_range']}",
                  f"Final initial residuals: {result['final_initial_residuals']}"]
    (OUTPUT / "result.md").write_text("\n".join(lines) + "\n")
    target = OUTPUT / ("313_sa_steady.tar.gz" if accepted else "313_sa_steady.failed.tar.gz")
    with tarfile.open(target, "w:gz") as archive:
        archive.add(CASE, arcname="313_sa_steady",
                    filter=lambda info: None if "dynamicCode" in info.name.split("/") else info)
    print(f"Finished: accepted={accepted}; result={OUTPUT / 'result.md'}", flush=True)


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
    print(f"Running steady Spalart-Allmaras 313 in {CASE}", flush=True)
    with (CASE / "execution.log").open("w") as log:
        run = subprocess.run(["bash", "-c", f"source {OPENFOAM_BASHRC} && bash ./Allrun.sa"],
                             cwd=CASE, stdout=log, stderr=subprocess.STDOUT)
    finish(run.returncode)


if __name__ == "__main__":
    main()
