# Verification

State: master at 511a1f29e656cc4fbb03684c01ed2e2a75745d35; pre-existing untracked saved_runs/313_pimple_run/313_pimple_run.foam preserved.

- Baseline: solver End marker; coefficient coverage through 1 s; checkMesh reports 20825 cells and Mesh OK. Mean Cd 2.1317665529 independently reproduced with NumPy trapezoidal integration with interpolated boundaries; 2-cycle mean 2.1623008002594957 also independently reproduced. Both assertions passed.
- Exact baseline/selected STL hashes match.
- MPI smoke: sourced v2412; mpirun -np 2 /bin/true. Restricted execution failed local sockets; require_escalated execution exited 0.
- All new simulations: not verified yet.

- T2 passed: independent foamDictionary evaluation checked all 10 variants for maxCo, start/end times, p/U/k/omega absolute tolerances and unchanged relTol, all domain coordinates and unchanged max_h. All copied processor*/0.3 files match saved checkpoint hashes. No new log.pimpleFoam exists.
- Analysis default/cycle CLI and analytical unequal-spacing tests passed. Primary baseline cycle Cd 2.1623008003 (per cycle 2.1074556, 2.2186121).
- Script SHA256: study/analyze.py: 24fd32cec69be0b4fb9bd32999b2f8bf12d58ebfe3362ff64cd1db0985da498e, study/run_study.py: f6bfa00ae260bb9f03ef3f30f2528c7e8f823b3ba273e09494f2d40a15080e3b

- PIMPLE scope addition passed: prepared outerCorrectors_4; independently evaluated nOuterCorrectors=4, nCorrectors=2, nNonOrthogonalCorrectors=2, startTime=.3, endTime=1, maxCo=.5. Shared linear solver settings, discretization/physical/domain inputs, all processor meshes and all .3s checkpoint files match baseline byte-for-byte. Manifest contains 11 prepared cases; no solver logs. Mesh sensitivity excluded by user.
- Updated run_study.py SHA256: 535560db83829e76116c67297f4c3064b81332f0b51265e7db78d6ceb93fa382

- Execution startup passed: escalated runner live session70140, maxCo_1 progressed0.3→0.34218 s; achievedCo~1, deltaT~1e-4. Solver completion and full batch still not verified.

- T3/T4 maxCo_1 passed: solver End/time1; complete2cycle data; independent NumPy fixed/cycle integration matches reports. CycleCd2.1638564814 (+0.0719456%), fixedCd2.1368928485 (+0.240472%). Archive maxCo_1.tar.gz contains identical coefficient data, completed solver log, and latest U fields for all6 ranks. Separate JSON/Markdown files verified.

- Automatic delivery monitor passed startup: session65870 live; initial report refresh returned0, maxCo1 existing archive preserved, all12 per-run JSON records present and firstvariant completion retained. Runner session70140 also verified live. This goal turn is progress plus verifiedwait, not completion. New user files average_cd.ipynb and coefficient-313.dat observed and untouched.

- tolerance_x10 passed: End/time1; complete2cycles; independent NumPy fixed/cycle integration matches reports; archive identical coefficients/completedlog and latestU for all6 ranks. CycleCd 2.1623172318 (+0.000760%); fixedCd 2.1317850003 (+0.000865%).

- T5 passed: staged I1%/10% cases start0/end1/maxCo.5; k/omega inlet/internal evaluated by helper onall6ranks and lead rank0; I1% k=.07407405925926/omega493.8270617284, I10% k7.407405925926/omega49382.70617284. All6rank initial U/p/phi and complete processor meshes byte-identical tobaseline; initialincludes matchedrootnewI; no.3checkpoint; fvSolution unchanged. Mainmanifest11cases preserved andtighterrun live; queue2 separate. Reporter now14records includes two newpendingcases withcorrectmetadata; executiontotal13.

- tolerance_x0.1 passed: End/time1,2completecycles; independent NumPy fixed/cycle means agree; archive has identical coefficientdata, completedlog, latestUall6ranks. CycleCd 2.1623251598 (+0.001127%), fixedCd 2.1317898717.

- Verifiedwait: runner70140 live and outer4 log showsiterations1–4 throughoutprogress through0.50828164s. Reporterstatusrunning/noaverage; nofailures. No completionclaimed.

- Verifiedwait: live70140+65870; outer4 progressed.52775→0.74017925s with4iterations. No newcompletion; all13study requirements remaininforce.

- outerCorrectors_4 passed: End/time1/2cycles; independent NumPy means agree; archive identical coefficients/completedlog/latestUall6ranks. CycleCd2.1610760446 (-0.056641%), fixedCd2.1307050756.
- Sixdomain launches failedbeforemeshing due bashAllrun.pimple path causing cdfile. Corrected to bash./Allrun.pimple; preserved initialfailurelogs and staged6 retries inindependent domain_retry_queue.json toprotect70140liveCo.25. Retryrunner54510 launched; no numericalinputchanges.

- Domainretry startup passed: 54510 live, correctedcasepath launchedallmeshstages; checkMesh20824cells/Mesh OK; pimple advancedthrough.13s. Aggregate13case state verified: 4complete,2running,7pending; old6launchfailures supersededbyactualretryqueue. Monitor93065 live andarchiveflockpreventsconcurrentwriters. CPUaffinityreadonlycheck: domain6ranks unbound16CPU, originalCo6ranks corebound; noCPUsettingchanges.

- Verifiedwait: 70140+54510 live; Co.25 .504→.603s andfirstdomain .202→.459s; bothreportsrunning/noCdaverages, aggregate13statesnoold-launchfailures. Domaindeliverymonitor93065 polledlive. Fullscope remains13; no completionclaimed.

upstream_dist_minus_1L complete: independent NumPy fixed/cycle means agree <1e-10; cycle Cd 2.1501192316178686 (-0.5633614269%). Mesh OK; archive raw coefficient SHA matches, End present, processor0..5/1/U present.

maxCo_0p25 complete: independent NumPy fixed/cycle agree <1e-10, cycleCd 2.1492961817075686, change -0.6014250445805854%. Archive coefficient SHA, End, processor0..5/1/U verified.

INVALIDATION: domain foamDictionary -set expanded vertices/Nx/Ny at baseline before updating parameter. Earlier upstream-minus Cd and archive verify arithmetic but NOT requested geometry; withdrawn from accepted results. All six domain folders/previous archive preserved under runs/313_study/invalid_domain_setup; runner54510 terminated143 before correction. Main numerical and I cases unaffected.

Corrected domain dictionaries independently evaluated with foamDictionary: inlet +/- actual4.3834/6.5751 Nx33/38; outlet +/-10.9585/13.1502 Nx33/38; roof +/-5.47925/7.67095 Ny13/18. Original variable references and #calc preserved. All6 evaluated bounds matched requested values within1e-4. Runner now checks final checkMesh bounding box against requested extents. Unchanged Phi belongs potentialFoam initialization, not warm pimple solves; retains baseline setting appropriately.

Corrected upstream-minus actual bounds match requested xMin-4.3834,xMax12.0543,yMax6.5751. HOWEVER checkMesh FAILED1 check: max skewness8.4413, one highlyskewface;20213cells. Do NOT claim MeshOK or acceptedCd. Solver currentlyprogressing, runner will flagfailed at completion under existinggate. Preserveoutputs, keep meshsettingsunchanged as requested.

Archive delivery now preserves terminal failed runs with solver logs as <case>.failed.tar.gz, separately from accepted results; live cases skipped. py_compile passed. Needed for user requirement each run saved, including mesh-quality failures.

I1% complete/accepted: independentNumPy means agree<1e-10; cycleCd2.1655140682397853 (+.1486041156%), fixed2.1348024718288325. Archive rawcoeff SHA matches, solverEnd and sixprocessor1/U present.

Corrected upstream-minus terminal: solverEnd/time1 but meshFailed1. Reportstatuserror/manifestfailed/noanalysis verified; .failed.tar.gz rawcoefficientSHA matches, sixfinalU fields/End/checkMeshfailure preserved. NoacceptedCd claimed.

Longer-inlet actual checkMesh verified: bounds(-6.5751,-1,z~0)to(12.0543,6.5751,.04), MeshOK,20752cells,maxskew1.77821. Requestedgeometryconfirmed. Solver60766live.

upstream_dist_plus_1L: independent NumPy fixed/cycle agree<1e-10; cycleCd2.109056633152357,change-2.462384840293675%. Archive rawcoeffSHA/End/sixfinalU verified.

turbulenceIntensity_10pct: independent NumPy fixed/cycle agree<1e-10; cycleCd2.1620593745212497,change-0.01116522447834052%. Archive rawcoeffSHA/End/sixfinalU verified.

downstream_dist_minus_1L verified: independentmeans<1e-10, requestedactualgeometry/MeshOK, archiveSHA/End/sixU. cycleCd2.1056066313229103,change-2.6219371943894947%,fixed2.0711321136462337.

Longeroutletcompleted/verified: insufficientcycles(two risingcrossings only,needthree), primarycycle unavailable. FixedCd1.9511281945368804 (-8.4736463329%), independentNumPyagree<1e-10. Actualbounds/MeshOK,archiveSHA/End/sixU verified.

roof_height_minus_1L: independentmeans<1e-10,actualgeometry/MeshOK,archiveSHA/End/sixU verified; cycleCdNone,fixed1.9741827921627522,comparison{'cycle_cd_change_percent': None, 'fixed_cd_change_percent': -7.3921678006983, 'half_window_drift_percent': -6.174728366025974}.

FINAL DELIVERY: all13 runs terminal/time1/End/fullfixeddata, all13archives independently checked (12accepted +1.failed),14individualreports includingbaseline. Tenprimarycyclevariants,twoexplicitfixedfallbacks,oneskewnessrejectionwithrawdiagnostic. FinalroofpluscycleCd1.955198839224089(-9.57785156%),fixed1.935368155764412(-9.21294111%). Final audit .orchestrator/FINAL_AUDIT.md passed. Mainmanifest consolidated, reportupdated withbaselinevalues/refinementfixed/fallbacklabels/limitations. Runner60766 terminalexit1 due knownshorterinletmeshfailure;monitor93065terminal0; I runner49378/monitor80999terminal0. No remainingruns. ResultsREADME/comparison/CSV andseparatearchivesready.

## Completed 313 refinement-box check

Only refinementBox expanded 1L outward on each x/y side. Z unchanged 0–0.04 m. Input diff against saved313 baseline: only snappy box_top, box_back, min entries; all remaining system dictionaries, initial conditions, physics and Allrun equal. maxCo=.5. Evaluated box min(-2.1917,-2.1917,0), max(5.47925,3.28755,.04). Fresh mesh/run0–1 completed session20647 exit0. Mesh OK:37768cells, unchanged actual outer bbox verified.

| Requirement | Evidence | Verdict |
|---|---|---|
| Single 313 run, only requested box bounds changed; no z expansion | recursive system diff, initial/physics/Allrun byte comparison, evaluated foamDictionary box, settings.json | passed |
| Complete simulation and valid mesh, unchanged outer domain | log.pimpleFoam Time=1/End, log.checkMesh Mesh OK/bbox, result.json accepted true | passed |
| Last two complete cycles and same saved baseline | independent integration agrees<1e-10; Cd2.1623008002594957 to2.1144296671530443, delta−2.2138979507710697%; case bounds.5879726024,.7781746654,.9646981042 | passed |
| Notebook readable in existing table style | all code cells executed; final printed sixcolumnrow saved to finalcell output, delta−2.214%; samebaseline variable, noexports | passed |
| Full saved result/archive | JSON/MD/tar exist; archived rawSHA matches case; final6 U fields, solverEnd/MeshOK archived | passed |

Per-cycle Cd2.068697740926697/2.161063520584611; fixedmean2.0856964109083815 (−2.1611251%). Passing checks does not establish statistical stationarity. Notebook sources/outputs earlier than appended section preserved. py_compile and git diff --check passed. Root dictionary-validation generated dynamicCode moved under ignored runs/313_refinement_check.

Tested files (SHA256):
study/run_313_refinement.py: 9bbd5af5ac2cf9d5c8d473773eb8bd88acd4af3678679085c2fa68642534655b
parameter_study_results.ipynb: cc35396ee9b3b48e19fdac0b67224e0f20eafaa6ffa967abc5340d9aec5c797d
runs/313_refinement_check/result.json: 556f1c53d5648487179d7deefbdcb468bb97328fa9cd14b7d231d76996abf00a
