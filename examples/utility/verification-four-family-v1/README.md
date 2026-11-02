# Common four-family development profile

The optional utility environment combines pvlib 0.15.2, Optuna 4.5.0, PyWake 2.6.20,
TOPFARM 2.6.2 and OpenMDAO 3.39.0. Existing interoperability remains pinned to
OpenMDAO 3.41.0. Combining that old feature directly with wind is unsatisfiable:
TOPFARM requires OpenMDAO 3.39.*. The failed solve is retained in install-offline.log.
The separate profile installed and old environment lock entries remained unchanged.
Pixi's offline log warns that PyPI requests can still occur in offline mode.

Versions are recorded in versions.json. The lock has both declared platforms, but
only macOS execution is tested. Resolution is not Linux qualification. The circuit
implementation label now records the actual installed OpenMDAO version. Existing
3.41.0 runs retain their source and are not relabelled.

`rehearse_mixed --include-wind` prepares 28 cells in one parent and one source/lock
closure: seven routes each for exposed Leaf River, solar, circuit and wind tasks.
The original three-family option remains available. The common source/data capture
checks conflicting bytes and rebinds supplied models to the exact common references.
Preparation validates the whole proposal before allocation.

Three preparation checks passed, including a dispatch/network-denied four-family
check. The science subset passed 14 tests with five warnings. The runtime contract
subset passed 70 and failed one documentation test that still expected only the old
extras. After updating that intentional metadata contract and checking both OpenMDAO
pins, documentation passed 19. No numerical criterion changed. Warnings remain in
raw logs.

The real rehearsal is still running at this checkpoint under its original handle.
`active-runs.json` and `runtime-source.json` record its ownership and source bytes.
Do not restart because polling is slow or modify bound code/configuration during
execution. Failed prior three-family and wind-only runs remain separate evidence.

The authored reader performs one full frozen parent replay, one authoritative child
projection, exact full result-envelope checks for every cell, selected-state/source
checks, and public verify/status. It counts all recorded scientific evaluation
statuses. This avoids replaying the full frozen parent for each cell without dropping
result, child, observation or artifact checks. It also archives all bound input/source
bytes before denying the original captured roots. It has not run yet.

This profile uses known exposed data and scripted workers, not an independent or
LLM utility experiment. Private scoring, independent task partitions and confirmation,
platform/host limits, complete costs and human effort remain open. The separate
installed wind qualification uses two additional development processes outside this
suite and is recorded under verification-installed-science-v1.

The producer completed successfully: 28 finished cells, zero added by completed
resume, separate freeze and passing verify/status. Confirmation access is zero.
The guarded reader also completed successfully. It reconstructed all 28 selections,
370 scientific evaluation records (229 Leaf, 91 solar, 31 circuit, 19 wind), all
444 science and 220 host observations with verified stops, 227 archived source/data
files and 28 large selected artifacts. Scientific imports, physical/network dispatch
and original captured-input reads were denied. No process remains active.

`offline-reader.json` and `partial-costs.json` retain the reconstructed results and
unknown costs. Public CLI child durations are in cli-wall-times.json. They include
substantial validation overhead and overlap scientific/host durations. Preparation
and outer producer overhead are unmeasured, so their sum is not total study cost.
The real four-family development path is verified. Independent data/confirmation,
private scoring, full cost/effort, fixed-total-cost comparisons, expert workflow,
platform/host and final utility conclusions remain open.
