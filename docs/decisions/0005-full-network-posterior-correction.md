# Decision 0005: full-network posterior correction

_Status: Accepted after posterior investigation and before the final replacement run_

_Date: 2026-09-04_

_Invalidated run revision: `ed9ac99a1af6bc20032aa56c37bc2c62515c28fe`_

_Corrected implementation revision: `3e83fffd9ea02a6e588331dac211711fc0aed513`_

## Context

The replacement benchmark completed 39 of 40 closed loops. The completed records passed every
frozen regret and fallback comparison. Calibration failed with 0.00625 objective interval coverage
and a 0.3 constraint Brier score.

Investigation found that posterior propagation requested one joint Gaussian process function
sample over all propagation rows. For an upstream component evaluated at one fixed design, those
rows are repeated. The joint draw therefore produced nearly the same value for every requested
posterior sample. This collapsed component uncertainty and did not implement the independent seeded
innovations required by the Item 8 plan and decision 0003.

Two evidence checks also needed correction. The raw audit expected only terminal outcomes, although
the function-network evaluator correctly records every declared intermediate scalar outcome. The
runner compared diagnostic warning lists during action replay. A process-level Torch warning was
emitted only on the first fit, so one otherwise identical action replay was rejected. The two
actions and their configurations were identical.

The invalidated evidence is retained at
`benchmarks/full_network/invalidated/ed9ac99-posterior-sampling/`. It does not evaluate the declared
posterior method and cannot satisfy Item 8.

## Corrections

1. For each component output and propagation path, read the Gaussian process marginal mean and
   variance. Draw an independent standard normal innovation from the declared deterministic seed,
   then calculate `mean + sqrt(variance) * innovation`.
2. Clamp only negative floating point variance to zero before the square root. Reject nonfinite
   propagated results as before.
3. Record `independent_output_and_component_innovations` in fitted diagnostics.
4. Reconstruct all declared source, intermediate, terminal, qualified, and public scalar outcomes
   during the raw audit.
5. Define suggestion replay by the complete action record. Keep diagnostics in raw evidence, but do
   not compare warning lists whose emission can depend on process history. Timing remains excluded.
6. Bind final evidence to this decision, decision 0004, and decision 0003.

The 65,536-sample affine fixture passes the original mean, variance, constraint probability, and
byte replay limits after this correction. A two-problem seed-0 defect check produced 0.8125 pooled
coverage and a 0.0517 constraint Brier score. This check confirmed that uncertainty no longer
collapses. It was not used to change the frozen criteria.

## Unchanged protocol

The two problems, component functions, ten seeds, shared four-point Sobol starts, ten-evaluation
budgets, backend settings, acquisition candidate count, posterior sample counts, held-out points,
measurements, and every acceptance threshold from decision 0003 remain unchanged. The final
replacement run will use the same 40-run matrix. Failed runs and adverse results remain visible.

The corrected aggregate source hash is
`f90d834968a63229a3ce700d618ee457ca4121cda5bf61460036fe126978c8be`.
These source file hashes differ from the decision 0004 revision:

| Source | SHA-256 |
| --- | --- |
| `src/autoengineering/benchmarks/full_network/__main__.py` | `a6b5f55a4998bfbe4faef2cb24fa95ed9166fd317745fa9444c5f7f69a16d148` |
| `src/autoengineering/benchmarks/full_network/problems.py` | `8e7fc03a382b293617fbedf5c68397ca51257c123de0c00ada3b2f68277fa5df` |
| `src/autoengineering/benchmarks/full_network/runner.py` | `49b403a80683b857e2130b40d7249ece0609871ae9009301268cc0eb801a4df8` |
| `src/autoengineering/benchmarks/full_network/summary.py` | `8592c48dd075a1a3c0f585c37f349b4f6704bbb89acdfa3c27fcd7d3f31e6c87` |
| `src/autoengineering/optimization/full_network_backend.py` | `e20e5bd7374f04f439575ab39d078e3168b00aa3b5df121ed0966b8178363ea0` |

The invalidated evidence hashes are:

| Artifact | SHA-256 |
| --- | --- |
| `calibration.json` | `6302b7759dc26b754cde051551a3ce9c9820be721da34a77a53ff69e75a0acd7` |
| `gate.json` | `a825855e04a1a44b87c5e31e4f9866dd7fff708574c2fd7a4b50c368f3e90f1e` |
| `raw-records.jsonl` | `13e45c4c66de590d877904c72d7084d462cf34c3db2f599edd191f81d7a131d2` |
| `report.md` | `37008483619489a01150f968e681c596eb29b63bdc2f53ad4dc556430a7268ac` |
| `run-summary.csv` | `c2ad21f24f9b5f93025c424a883b71202885ee5a45943f96b8ca4d55353fcdbd` |
