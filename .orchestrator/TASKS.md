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
