# Decision 0002: Release A evidence corrections

_Status: Accepted after independent review and before the replacement comparative run_

_Date: 2026-09-04_

_Invalidated trial revision: `5c752c7`_

## Context

The first full comparative run passed the numeric criteria in Decision 0001. Independent review
then found four defects in the evidence implementation. The SMAC penalty was not a single fixed
value, raw records could satisfy count checks without representing the exact declared matrix,
an optimizer observation failure could omit an evaluation that had already occurred, and the
source hash covered only the benchmark package.

The first run is not Release A evidence. Its results will not be used to change the problems,
method settings, measurements, or numeric thresholds in Decision 0001.

## Corrections

1. SMAC uses a scalar internal cost of 10.0 for every failure or scientifically infeasible result.
   Successful feasible results retain `reference objective - observed objective` as the internal
   minimization cost. Raw scientific results remain unchanged.
2. The gate validates the exact five problem by five method by 30 seed Cartesian matrix. Every run
   must contain evaluation indices 0 through 9 exactly once. It reconstructs actions and results,
   validates configurations, reruns the deterministic evaluator, and recomputes costs,
   feasibility, constraint flags, incumbent objectives, and regrets before evaluating criteria.
3. A completed evaluation is appended to raw evidence even if the method's observation step fails.
   Optimizer overhead includes both suggestion and observation work.
4. Provenance hashes the benchmark package, the complete optimization package, `pyproject.toml`,
   `pixi.toml`, `pixi.lock`, and both benchmark decisions. It records the exact clean Git revision
   and versions for NumPy, SciPy, Torch, BoTorch, GPyTorch, SMAC, and ConfigSpace. A new benchmark
   run refuses a dirty checkout.

The replacement run uses the original 7,500-evaluation matrix and every unchanged threshold from
Decision 0001. Release A can pass only on the corrected evidence implementation.
