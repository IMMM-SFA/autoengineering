# Integration burden and resource evidence

This record compares inspected workflows and retained development artifacts. It
measures neither author hours nor general optimizer superiority.

| Path | Before integration | Delivered shared responsibility | Remaining custom work |
| --- | --- | --- | --- |
| BMI | `examples/local_models/bmi_chain.py` implements initialize, variable exchange, stepping and finalization directly. | `adapters/bmi.py` applies the campaign lifecycle, metadata/time validation, copied exchange and primary-error-preserving cleanup. The installed reservoir example matches all outputs and conservation. | Trusted factory, units, daily origin and scientific inspection remain model-specific. Spatial/seconds models remain unsupported. |
| Optuna | `optimizer_comparison/optuna_replay.py` and its worker own trial/configuration translation, failed-result projection and journal reconciliation. | The public policy and controller own deterministic proposal recovery, budgets, ledger-based recommendations and CLI/campaign dispatch. | An executable evaluator and scientific constraints remain required. External trial/result receipts now link existing physical attempts; final regression status is in the completion audit. |
| OpenMDAO | `circuit/model.py` constructs the coupled Problem, records solver work and runs native derivatives/driver. | The adapter runs a whole supplied Problem through fresh lifecycle, binding checks, convergence inspection and cleanup. Direct and wrapped circuit outputs agree. | Problem construction, residual science and derivative reference remain explicit. Native optimization has separate, unmatched work limits. |
| Solar | The preserved open-chain script owns cache verification, timestamp filtering and pvlib execution. | The campaign bundles declared source/data identities, fitting-only search, comparison selection, physical vetoes and resumable physical-attempt accounting. | Data access/redistribution, supplied alternatives and future independent confirmation remain explicit. |

The reusable interfaces remove repeated lifecycle and transaction ownership from
callers. The examples intentionally retain model-specific equations, numerical
checks and data assumptions. This is the documented integration benefit. No
measured reduction in engineering time is claimed.

`optimizer-resource-summary.json` aggregates repeated measurements already saved
in the matched v2 study. Optuna completed all nine cells with median recorded
suggest/tell phases of 0.0052/0.0055 seconds and median peak RSS of 133.8 MB.
Sobol's phases were 0.0044/0.0047 seconds and 126.1 MB. These phases include
transcript reconstruction and durable writes. Ax has only two summarized cells
out of nine. Its surviving measurements cannot represent the failed cells.
All 35 Ax physical starts, including cells without a summary, remain counted.

The recorded `import_seconds` measures only the worker's explicit import phase.
Imports may already be cached by earlier module initialization, so it is not a
cold-start framework comparison. Supervision elapsed time and sampled memory
remain the process-level evidence. Prototype dependency resolution is retained
in its separate `pixi.lock`; the admitted environment excludes Ax, BoTorch and
Torch. Base-package import tests exclude all optional frameworks.

Final dependency and source-size records are `dependency-footprint-v6.json` and
`integration-code-footprint-v6.json`. The inspected prototype environment's
required dependency closure contains 11 distributions and 53.2 MB of regular
installed files for Optuna, versus 53 distributions and 777.1 MB for Ax. Shared
files are deduplicated within each closure. These figures exclude Python's
standard library and external system libraries. They are not memory measurements
or estimates of engineering time. The exact versions and file-size scope remain
in the machine-readable record.
