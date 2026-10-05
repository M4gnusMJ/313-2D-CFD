# Tasks

- T1 baseline/time-weighted analysis — cd_analysis — verified: analytical worker checks and independent NumPy integration passed. Deliverable study/analyze.py.
- T2 prepare 11 independent variants and runner — study_runner — verified preparation: lead independently checked all 11 evaluated dictionary sets and byte-for-byte restart checkpoints. Deliverables study/run_study.py, study/README.md; source saved_runs/313_pimple_run.
- T3 execute simulations — lead — running; full execution now authorized by active goal. Record progress in runs/313_study/.
- T4 verify and publish results — lead + cd_analysis reporting helper — running alongside T3; compare actual dictionary settings, completed time, coefficient coverage and solver logs.

T3 progress: maxCo_1 verified complete/archived; tolerance_x10 running; remaining9 queued. T4 reporting scripts integrated and baseline/firstvariant independently verified; finalbatch report pending.

T3/T4 progress: tolerance_x10 now independently verified complete and separately archived. Two of11 variants complete; tolerance_x0.1 running; remaining8 queued.

- T5 add two inlet-turbulence sensitivity cases — study_runner — verified preparation: I1%/10%, ratio10, baseline mesh, from0. Independent turbulence_queue.json; do not alter live mainmanifest. Dependencies: execute after original T3runner exits; include in T4 final reports/archives.

T3/T4: tolerance_x0.1 independently verified/archived;3of13done; outerCorrectors_4running. Both Icases remain queued outside originalmanifest.

T3/T4: outer4verified/archived,4of13done. Co.25(original70140)running. Sixdomains initiallylaunchfailed; pathcorrected, independentretryrunner54510 nowrunninginletminus meshing. Retryqueue authoritative. T5Iexecutionawaits originalCo.25terminal; no mainmanifestmergewhileoldlive.

Domain acceptance reopened: previous setup froze vertices at baseline; invalid outputs preserved and withdrawn. Corrected six-case batch60766 started after independent evaluated-geometry checks. Five numerical variants complete; two I runs remain in livequeue49378.

FINAL DELIVERY: all13 runs terminal/time1/End/fullfixeddata, all13archives independently checked (12accepted +1.failed),14individualreports includingbaseline. Tenprimarycyclevariants,twoexplicitfixedfallbacks,oneskewnessrejectionwithrawdiagnostic. FinalroofpluscycleCd1.955198839224089(-9.57785156%),fixed1.935368155764412(-9.21294111%). Final audit .orchestrator/FINAL_AUDIT.md passed. Mainmanifest consolidated, reportupdated withbaselinevalues/refinementfixed/fallbacklabels/limitations. Runner60766 terminalexit1 due knownshorterinletmeshfailure;monitor93065terminal0; I runner49378/monitor80999terminal0. No remainingruns. ResultsREADME/comparison/CSV andseparatearchivesready.

- P1 prepare lower-symmetry driver — symmetry_runner — running; study/run_prism_symmetry.py; verify input diff and evaluated dimensions.
- P2 execute fresh case — lead — pending; runs/prism_symmetry_check/case, six MPI ranks, same 0..1s.
- P3 verify/report/archive — lead — pending; independent bounds, mesh/field symmetry, solver completion and Cd checks.

P1 verified: prepared input diffs only blockMesh geometry/Ny/lower patch and five fields lower symmetry. foamDictionary Ny38, lower_height8.7668; source/rest preserved. P2 running: exec session85253, python3 -u study/run_prism_symmetry.py with host MPI authorization. P3 pending actual run completion.

P2/P3 verified complete: runner85253 exit0,1sEnd,allstageEnd,MeshOK,bounds/symmetryverified. NumPy independent means agree<1e-10; archive content/SHA verified. ResultJSON/MD and prism_symmetry.tar.gz in runs/prism_symmetry_check. Evidence VERIFICATION.md prism section. No remaining work.

- SA1 prepare study/run_prism_sa.py and case — lead — running; preserve exact latest mesh/settings, SA-required changes only.
- SA2 launch and verify advancing SA solver — lead — pending; result/status auto-written in runs/prism_sa_check; user requests start, not wait for completion.

SA1/SA2 verified start: runner50139 live, actual SpalartAllmaras selection, nuTilda solves advancing to0.018918124s, MeshOK47593cells/samebounds. Exact source mesh/input invariants checked before launch; nuTilda ratio10 numerically checked; local v2412 source/tutorial review passed. Completion not yet verified. Plot task complete: study/plot_prism_symmetry.py produces runs/prism_symmetry_check/cd_comparison.png/.pdf, onlyCd,legend,ylim1..3,time0..1; rendered image inspected.

SA completed subsequently:50139exit0,1sEnd,allstageEnd/all6finalnuTilda checked. Requested comparison plot includes fullSA Cd0..1s and preserves user reference line/labels andylim1..5; PNG/PDF regenerated.

- S313-1 preparation — lead — verified: exact saved mesh/STL/input invariants; SAsetup/local source review, compile. Driver study/run_313_sa_steady.py; case runs/313_sa_steady/case.
- S313-2 execute/verify/report/archive — lead — pending; sixranks simpleFoam500iterations.

S313-2 running: execsession54733, authorized six-rank launch. Do not duplicate.

S313-2 verified execution/report/archive:54733exit0,500End,MeshOK/allstagesEnd/originalgeometry andSAverified; independentmeans/archiverawSHA/finalfields passed. Cd not converged (range1.502–2.005 overlast100,residualsremainhigh); documented withoutchanging originalnumericalsettings.

- T313SA-1 prepare — lead — verified inputinvariants/SAfieldcomparison; study/run_313_sa_pimple.py, runs/313_sa_pimple/case.
- T313SA-2 execute/report/verify — lead — pending; pimpleFoam6ranks,0..1s,maxCo1.

T313SA-2 running: session50732 hostMPI,0..1s. Model/backward/maxCo1/PIMPLE2/2/2 evaluated beforelaunch.

T313SA-2 verified complete:50732exit0,1sEnd,MeshOK/allstageEnd/SA/originalgeometry verified. IndependentCd NumPy auditpassed,archivecontent/SHApassed. Results runs/313_sa_pimple/result.json,result.md,313_sa_pimple.tar.gz. No remainingrun.
