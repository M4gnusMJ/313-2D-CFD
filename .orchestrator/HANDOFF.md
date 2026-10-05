# Final handoff

The 313 study execution and reporting are complete. All thirteen variants reached 1 s, with solver End and full fixed-window data coverage. All thirteen have separate archives; twelve passed mesh quality, one is preserved as a failed archive. Ten provide two-cycle means; longer outlet and lower roof lack two cycles and are explicitly fixed-window fallbacks. No runs or monitors remain active.

Authoritative delivery: runs/313_study/results/README.md, comparison.md, comparison.csv, individual JSON/Markdown reports, and runs/313_study/archives/*.tar.gz. Main manifest consolidated after all runners finished. Complete independent evidence is in .orchestrator/FINAL_AUDIT.md and VERIFICATION.md.

Shorter inlet failed one checkMesh skewness check (one face, max8.4413), excluded from accepted comparisons. Raw means are retained only in upstream_dist_minus_1L.rejected_diagnostic.json with accepted=false. Initial incorrect domain setups were quarantined under invalid_domain_setup and excluded. Corrected domain preparation preserves #calc/substitutions; accepted domain bounds independently checked.

Refinement box/levels stayed unchanged; mesh sensitivity remains out of scope. Five numerical variants warm-started at0.3; domain and turbulence cases started0. End1 and agreed averaging protocol preserved. Baseline cycle variation5.274% and half-window drift7.213% limit stationarity claims. Some runs concurrent, so wall times are not controlled benchmarks.

Runner60766 terminalexit1 reflects the single mesh failure; all six domain solvers reached1. Domainmonitor93065 exited0. Originalrunner70140 terminalexit1 from historical launch failures; all numerical variants verified. I runner49378/monitor80999 exited0. Other historical sessions finished. Do not restart completed cases.

User notebook average_cd.ipynb and coefficient-313.dat preserved; saved baseline and shared base_setup unchanged. Generated output ignored by Git. No commit requested or made.
