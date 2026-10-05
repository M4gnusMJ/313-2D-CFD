# Combined prism check

User requests one further prism run: refinement box expanded by1L on each x/y face; no z expansion; inlet+2L,outlet+3L,roof+3L,maxCo1. L1.09585m. Source saved_runs/prism_pimple_run preserved. Prepared fresh from0.orig, remesh from0 to1s,6MPI ranks. Case runs/prism_combined_check/case; driver study/run_prism_combined.py automatically writes resultJSON/MD and fullarchive at completion. No rerun if execution.log exists.

Evaluated geometry verified: domainx[-7.67095,15.3419],y[-1,9.86265],z[0,.04];Nx47,Ny22. Refinementboxmin[-2.1917,-2.1917,0],max[5.47925,3.28755,.04]. Only3domaindefinitions,3refinementdefinitions,maxCo changed. Geometry/0.orig/other systemdicts bytepreserved. Expected actualcheckMeshbounds within1e-4 and MeshOK gate. No numericaltolerance/PIMPLE/turbulencechanges.

Cdprotocol: last2complete risingCl0 cycles anywhere in eachfile (no.5restriction), exacttimeweightedtrapezoidal boundaryinterpolation; fixed.5–1reference. Prismbaselinefixed2.0311298485, last2cycle2.2344190968,bounds.3350345608/.6957437712/.9472604956,percycle2.4806754894/1.8812539180. Thisbaselineisnot313.

Run launched with host MPI authorization; record sessionhandle from launchtool. Poll thatsamehandle toverifyliveness; do notduplicate. Final independentlyverify rawmeans,actualdomainbounds,MeshOK,fullarchiverawcoeffSHA/End/all6processor1/U. Driver archivesfailedruns separately. Do not mark acceptance until actualevidencechecked.

LIVE session45898. Currentactualmesh36019cells,MeshOK,boundsmatchallrequestedvalues. Solverthrough.0938s. Independenthelperauditfoundnomaterialsetupflaw. Sourcebaseline20537cells,MeshOK. All13prior313variantsremaincompleteanduntouched. Do not restartliveprism.

COMPLETE: runner45898exit0; actualmesh36019cellsMeshOK/requestedboundsverified, solvertime1End. Last2cycleCd2.3002190755 vsprismbaseline2.2344190968 (+2.9448360351%). Fixed.5–1Cd2.3992798877 vs2.0311298485 (+18.1253817641%). IndependentNumPyintegration/boundsagree<1e-10 bothruns. Allgeneratedstage logsEnd/noFOAMFATAL. Archive56646938bytes coefficientSHA/End/MeshOK/all6processor1/Uverified. Runtime1315s. ResultJSON/MD/standalonetar in runs/prism_combined_check. Per-cycle means baseline2.4806754894/1.8812539180 andnew2.1583262245/2.4953802461; materiallyvarying,donotclaimstationarity. Noactiveprocessesremain. Originalprism and313study preserved.
