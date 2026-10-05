# Final verification audit

All 13 requested variants reached 1 s with solver End and full 0.5–1 s force-data coverage. All 13 have individual JSON/Markdown reports and separate archives. Raw coefficient SHA256, archived solver End and all six final U fields were checked for every archive.

Independent NumPy integration and rising lift zero crossings agree with all accepted reported fixed/cycle means to 1e-10. Actual requested geometry and Mesh OK were verified for each accepted domain case. Transport/turbulence properties, force normalization, schemes and refinement dictionary match the saved baseline byte for byte in every variant.

Two cases lack two complete cycles: downstream_dist_plus_1L, roof_height_minus_1L. Fixed-window fallback is explicit. The shorter-inlet case is rejected for one highly skewed face; its failed-run archive and separate rejected diagnostic preserve the data.

| Case | Terminal state | Analysis | Archive bytes |
|---|---|---|---:|
| maxCo_0p25 | complete | two_cycle | 36145522 |
| maxCo_1 | complete | two_cycle | 27801042 |
| tolerance_x0.1 | complete | two_cycle | 30630596 |
| tolerance_x10 | complete | two_cycle | 30630294 |
| turbulenceIntensity_1pct | complete | two_cycle | 38515133 |
| turbulenceIntensity_10pct | complete | two_cycle | 38512650 |
| outerCorrectors_4 | complete | two_cycle | 33301597 |
| upstream_dist_minus_1L | failed | rejected | 37928420 |
| upstream_dist_plus_1L | complete | two_cycle | 39247450 |
| downstream_dist_minus_1L | complete | two_cycle | 38244437 |
| downstream_dist_plus_1L | complete | fixed_window_fallback | 38688676 |
| roof_height_minus_1L | complete | fixed_window_fallback | 38634026 |
| roof_height_plus_1L | complete | two_cycle | 38603057 |
