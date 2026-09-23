# Decision 0002: Release A evidence corrections

_Status: Accepted after independent review and before the replacement comparative run_

_Date: 2026-09-04_

_Invalidated trial revision: `5c752c7`_

## Context

The first full comparative run passed the numeric criteria in Decision 0001. Independent review
then found defects in the comparison and evidence implementation. These affected the SMAC penalty,
matrix validation, evaluation retention, optimizer timing, fallback classification, failure
taxonomy, provenance coverage, equation tests, and concurrent publication safety.

The first run is not Release A evidence. Its results will not be used to change the problems,
method settings, measurements, or numeric thresholds in Decision 0001.

## Corrections

1. SMAC uses a scalar internal cost of 10.0 for every failure or scientifically infeasible result.
   Successful feasible results retain `reference objective - observed objective` as the internal
   minimization cost. Raw scientific results remain unchanged.
2. The reader rejects unknown fields, problems, methods, noninteger seeds, and noninteger evaluation
   indices. The gate validates the exact five problem by five method by 30 seed Cartesian matrix.
   Every run
   must contain evaluation indices 0 through 9 exactly once. It reconstructs actions and results,
   validates configurations, reruns the deterministic evaluator, and recomputes costs,
   feasibility, constraint flags, incumbent objectives, and regrets before evaluating criteria.
   Independent tests assert hard-coded off-optimum results for every evaluator branch, the exact
   noise seed, constraints, failures, and heterogeneous costs.
3. A completed evaluation is appended to raw evidence even if the method's observation or cleanup
   step fails. A primary failure remains the recorded cause if cleanup also fails. Optimizer
   overhead includes both suggestion and observation work.
4. Fixed, random, and Sobol diagnostics are not fallback events because those methods do not fit a
   surrogate. A cold-start reason is expected only at evaluation indices 0 through 4. Any fallback
   at index 5 or later is unresolved and counts against the Decision 0001 limit.
5. Dedicated exception types identify invalid proposed configurations and evaluator budget
   overruns. Generic type, value, optimizer, evaluator, and cleanup errors do not increment those
   two scientific accounting fields.
6. Provenance hashes the benchmark package, the complete optimization package, `pyproject.toml`,
   `pixi.toml`, `pixi.lock`, and both benchmark decisions. It records the exact clean Git revision
   and versions for NumPy, SciPy, Torch, BoTorch, GPyTorch, SMAC, and ConfigSpace. A new benchmark
   run refuses a dirty checkout.
7. A sibling publication lock prevents concurrent benchmark commands from sharing a destination.
   The destination is checked again before atomic publication. Exceptions leave the destination
   absent, and an existing or concurrently created destination is not changed.

The replacement run uses the original 7,500-evaluation matrix and every unchanged threshold from
Decision 0001. Release A can pass only on the corrected evidence implementation.
