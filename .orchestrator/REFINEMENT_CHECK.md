# 313 refinement-box check

Active user goal: one additional313refinement-boxstudy afterprismstarts; allotherSnappysettingsidentical;resultsreadableinnotebooklikebefore. Prioruserclarification nozexpansionpersists. Expand1Loutwardeachx/yside:L1.09585m,min(-2L,-2L,0),max(5L,3L,.04). Source saved_runs/313_pimple_run preserved. Keepouterdomain,physical/initialandnumericalsettings baseline313,maxCo.5. Start0remeshthroughcopiedAllrun.pimple to1s,6ranks.

Helperstudy_runner owns ONLYstudy/run_313_refinement.py,preparationchecks; no simlaunch. Rootownsnotebookintegration: newsection7printsone six-columnrow fromruns/313_refinement_check/result.json;last2completeCl0cyclesanytime,comparetosavedbaseline_cycle_cd2.1623008003. Mesh/solverfailuresnotaccepted. Pendingrunhandledreadably;noexports.

Evidencechecked: no313refinementcasefolder/studydefinitionyet, noactivehostOpenFOAMprocesses. Prismcombinedalreadycomplete. Needpreparedinputdiffs/evaluatedrefinementbounds,launchauthorizedMPI,pollsamehandle,verifyEnd/time1,actualunchangeddomain/MeshOK,independentCdmeans/rawarchiveSHA/finalall6U,runnotebookcellstoverifyfinalrowbeforemarkinggoalcomplete.

Prepared input diff confirms only snappy refinement box changes; evaluated min (-2.1917,-2.1917,0), max (5.47925,3.28755,.04). Corrected unevaluated vector arithmetic before launch. MPI runner launched: session 20647; settings running. Notebook section 7 integrated with pending-result display; final verification pending.

Mesh verified: 37768 cells, Mesh OK, actual bbox (-5.47925,-1,~0) to(12.0543,6.5751,.04), baseline match. 0.orig/transportProperties/turbulenceProperties byte equal to source. Flow simulation active.

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
