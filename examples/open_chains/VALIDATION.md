# Validation

Executed locally on macOS ARM on 2026-09-05 with the project Pixi lockfile.
Linux x86-64 dependencies are locked but were not executed here.

| Command | Result |
| --- | --- |
| `pixi run test` | 442 passed, 64 skipped |
| `pixi run -e examples test` | 554 passed, 4 skipped (after the 2000-call amendment) |
| `pixi run -e solar python -m pytest tests/test_open_chains.py -q` | 9 passed, 3 skipped |
| `pixi run -e wind python -m pytest tests/test_open_chains.py -q` | 6 passed, 6 skipped |
| `pixi run -e hybrid python -m pytest tests/test_open_chains.py -q` | 5 passed, 7 skipped |
| `pixi run -e examples python -m scripts.check_benchmark_ledger` | 80 passed |
| `pixi run lint` | Passed |
| Waterology constraints on changed Python sources and tests | 8 of 8 passed |

Optional dependency tests skip outside their respective environments. Integration
checks execute real pvlib electrical models, PyWake/TOPFARM layouts and five days
of HOPP/CBC dispatch. Full example runs separately evaluate both solar years, the
16-turbine wind design and finer direction grid, and annual hybrid dispatch.

Solar tests compare independent electrical solvers and check causality, graph
execution and sensor QA. Wind tests compare upstream wake output and screen
layouts. Hybrid tests check hourly physical outputs. Report tests reject changed
artifact bytes, inconsistent summaries and altered frozen selections.

The benchmark cache passed exact-record parity and warm-cache corruption checks.
The production ledger and recovery tests also passed with the adapter, including
changed-budget recovery rejection. A first invocation through stdin could not
launch two multiprocessing tests. Running through the checked-in module resolved
that test-launch error.

Upstream packages emit numerical and deprecation warnings. HOPP's optional
xlwings cleanup also emits an ignored macOS process-enumeration permission error
inside the sandbox after its tests pass. Test commands exit successfully. No
solver failure or warning was converted into a passing assertion.

The full-run objectives and selection decisions are verified by
`scripts/summarize_open_chains.py` from saved arrays, observations, decisions and
hashes. The 2000-call benchmark has a separate ledger audit and historical-prefix
verification in `scripts/summarize_complex_models.py`.

The user subsequently reduced the target cap to 2000. Focused cutoff, model and
report tests passed (31 tests). The cutoff tests cover exclusion of later
improvements, earlier target hits, incomplete sources, failed observations,
ties, held-out scoring from the frozen prefix and timing at the retained call.
All 53 projected studies passed exact-byte source and trajectory verification.
Lint and all eight Waterology constraints passed after the cap change.

The completed reduced matrix contains 75 studies and 24,972
retained calls. 64 studies reached their frozen target and
11 exhausted the 2000-call budget. The independent numeric audit recalculated
all retained successful objectives and all 75 final recommendations, with no
discrepancies or failed model attempts. Final report verification passed all 120
fixed and target studies, all 75 historical target trajectories originally capped
at 200, 46 uncached prefixes through the applicable cap, and all 53 projections.
The final independent review found no blocker.
