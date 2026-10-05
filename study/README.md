# 313 PIMPLE sensitivity study

`run_study.py` prepares one-factor-at-a-time cases from the saved completed
baseline in `saved_runs/313_pimple_run`. It does not change `base_setup` or the
saved baseline. All generated cases, logs, manifests, and analysis tables go in
the ignored `runs/313_study/` directory.

The sweep contains two `maxCo` variants (0.25 and 1.0), two absolute linear
solver tolerance variants (all `p`, `U`, `k`, and `omega` tolerance entries in
`system/fvSolution.steady` multiplied by 0.1 or 10), one PIMPLE convergence
variant (four outer correctors versus the baseline's two), six domain variants,
and two inlet turbulence intensity variants at 1% and 10%. The turbulence
variants keep the viscosity ratio at 10 and derive `k` and `omega` from the
unchanged formulas in `initialConditions`.
For each domain variant, one of `upstream_dist`, `downstream_dist`, or
`roof_height` changes by `-L` or `+L`, with `L = 1.09585 m` as configured for
this study. These dimensions are based on the saved `system/blockMeshDict`
settings; `max_h` and all other model, physical, and numerical settings stay
at their baseline values. Tolerance `relTol` values remain unchanged.
The PIMPLE variant changes only `nOuterCorrectors`; pressure correctors,
non-orthogonal correctors, and solver tolerances remain at their baseline values.
Mesh sensitivity is outside the scope of this study.
The refinement box dimensions and refinement levels remain unchanged.
Domain dimensions are edited before evaluating the vertex and cell-count
expressions, and final `checkMesh` bounds must match the requested dimensions.

The saved baseline uses inlet speed 22.2222222222 m/s, kinematic viscosity
1.5e-5 m²/s, kOmegaSST, turbulence intensity 5%, and viscosity ratio 10.
Force coefficients use rhoInf = 1 kg/m³, Aref = 0.043834 m², and lRef = 1.42 m.
Its adaptive maxCo is 0.5, initial deltaT is 0.0001 s, maxDeltaT is 0.005 s,
and the time scheme is backward. PIMPLE outer/pressure/non-orthogonal
correctors are 2/2/2. Absolute tolerances are p = 1e-7 and U/k/omega = 1e-8;
relTol is 0.01 for p and 0.1 for U/k/omega, with 0 for final solves.

Run the preparation step after installing OpenFOAM v2412 at the configured
setup path:

```sh
python3 study/run_study.py --prepare-only
```

Run the simulations sequentially with six MPI ranks per case:

```sh
python3 study/run_study.py
```

Use `--cases maxCo_0p25 tolerance_x10` to prepare/run selected case names. The
runner records each case's status in `runs/313_study/manifest.json`, skips
completed cases, and leaves pre-existing unmanaged case directories untouched.
Failed cases remain recorded and can be selected again for a retry. The five
existing same-mesh numerical variants reuse the saved initialized processor
fields at 0.3 s, including their old-time fields and `uniform/time`, then run
through 1 s. The turbulence variants start at 0 with the saved baseline
velocity fields so the inlet change can convect to the body. Their prepared
status is kept in `runs/313_study/turbulence_queue.json` until that isolated
queue is merged after the active runner finishes.
Domain variants start at 0 and run the copied `Allrun.pimple` to rebuild the
mesh before solving. Solver completion requires a `log.pimpleFoam` `End` marker
and a final time of 1 s; domain variants additionally require `Mesh OK.` in
`log.checkMesh`. For mesh rebuild runs, each generated `log.*` must also end
cleanly.

After each completed variant, the runner updates `summary_fixed.csv` and
`summary_fixed.md` with the existing fixed-window results, and `summary.csv`
and `summary.md` with the saved baseline and cases that contain two complete
lift-coefficient cycles after 0.5 s. Both reports include the saved baseline
as their reference. The fixed-window report retains the 0.5–1.0 s mean and its
two half-window means; the saved baseline shows about 7.2% difference between
the half-window means. Cases without two complete cycles are listed in the
cycle report and their manifest entries identify the incomplete coverage.

The saved baseline PIMPLE solve took about 1,388 s (23 min) with six ranks.
The domain cases also rebuild the mesh, so their total runtime will be longer;
runtime depends on available compute resources.

Write separate JSON/Markdown result files and the combined comparison with:

```sh
python3 study/report_results.py
```

Save each completed case (inputs, processor fields, logs and coefficient data)
as its own compressed file under `runs/313_study/archives/` with:

```sh
python3 study/archive_runs.py
```

Compiler caches are omitted from archives. Both commands can run between
completed cases; live simulations are not archived.
Terminal failed cases with solver output are also preserved separately as
`<case>.failed.tar.gz`; this does not count them as accepted results.

While the batch runs, a separate monitor can refresh individual reports and
archives whenever a case finishes:

```sh
python3 -u study/monitor_study.py
```

It does not start or restart simulations, and exits when all case statuses
are terminal. Simulation liveness must still be checked against the runner
process/session rather than inferred from the manifest.
