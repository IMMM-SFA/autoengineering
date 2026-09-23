# Decision 0001: Release A benchmark gate

_Status: Accepted before comparative runs_

_Date: 2026-09-04_

_Baseline revision: `278df4b`_

## Decision

Release A uses the five problems, 30 seeds, five methods, measurements, and numeric criteria below.
These definitions are frozen before the full comparison. A failed criterion will remain visible and
will not be weakened after inspecting results.

All objectives are maximized. Normalized feasible regret is
`min(1, max(0, (reference objective - best feasible objective) / scale))`. Regret is 1 before the
first feasible result. Each problem uses scale 1. The cost-normalized regret area extends the last
observed regret to the problem cost budget and divides the integral by that budget.

## Problems

Every numeric parameter below uses its stated closed interval. Each run permits 10 evaluations.

1. `smooth_continuous` has `x, y in [0, 1]`, unit evaluator cost, and no constraint. Its objective is
   `1 - ((x - 0.25)^2 + (y - 0.75)^2) / 1.125`. The exact optimum is 1 at `(0.25, 0.75)`. The cost
   budget is 10.
2. `constrained_continuous` has `x, y in [0, 1]`, unit evaluator cost, objective
   `1 - ((x - 0.7)^2 + (y - 0.3)^2)`, and constraint
   `0.10 - ((x - 0.5)^2 + (y - 0.5)^2) >= 0`. The exact constrained optimum is 1 at `(0.7, 0.3)`.
   The feasible region is a circle inside the unit square, and the cost budget is 10.
3. `mixed_space` has categorical `algorithm in {fast, robust}`, integer `depth in [1, 5]`, and
   continuous `rate in [0, 1]`. `robust` has objective
   `1 - (rate - 0.65)^2 - 0.04 * (depth - 4)^2`; `fast` has objective
   `0.92 - (rate - 0.35)^2 - 0.04 * (depth - 2)^2`. Evaluations cost one. The exact optimum is 1 at
   `(robust, 4, 0.65)`, and the cost budget is 10.
4. `conditional_space` has categorical `family in {linear, quadratic}`. `slope in [0, 1]` is active
   only for `linear`; `curvature in [0, 1]` and `shift in [0, 1]` are active only for `quadratic`.
   The linear objective is `0.9 - (slope - 0.6)^2`. The quadratic objective is
   `1 - (curvature - 0.7)^2 - (shift - 0.3)^2`. Evaluations cost one. The exact optimum is 1 at
   `(quadratic, 0.7, 0.3)`, and the cost budget is 10.
5. `noisy_chain` has categorical `architecture in {reliable, turbo}`, continuous
   `control in [0, 1]`, integer `stages in [1, 4]`, and `boost in [0, 1]` active only for `turbo`.
   The reliable mean objective is
   `0.94 - (control - 0.6)^2 - 0.03 * (stages - 2)^2`. The turbo mean objective is
   `1.03 - (control - 0.75)^2 - 0.03 * (stages - 3)^2 - 0.2 * (boost - 0.4)^2`.
   The observed objective adds deterministic `Normal(0, 0.02)` noise and records standard error
   0.02. The stability constraint is `>= 0`, where reliable stability is
   `0.30 - abs(control - 0.6) - 0.03 * abs(stages - 2)` and turbo stability is
   `0.22 - abs(control - 0.7) - 0.08 * abs(boost - 0.4) - 0.03 * abs(stages - 3)`.
   Turbo configurations with `control > 0.9` and `boost > 0.75` return `model_failure`.
   Reliable cost is `1 + 0.15 * (stages - 1)`; turbo cost is
   `1.4 + 0.2 * (stages - 1) + 0.3 * boost`. The exact mean optimum is 1.03 at
   `(turbo, 0.75, 3, 0.4)`, which is feasible. The cost budget is 23.

The benchmark seed is each integer from 0 through 29. The study seed is
`10,000 * problem ordinal + benchmark seed`, where ordinals are 1 through 5 in the order above.
Noise uses `SeedSequence([study seed, evaluation index, 5])`. This gives common random numbers by
problem, seed, and evaluation index without coupling noise to method implementation.

## Methods

The method names are `fixed`, `random`, `sobol`, `smac`, and `botorch`.

- `fixed` uses one unscrambled Sobol candidate order for every seed. Only the noisy observations
  change across seeds.
- `random` uses `RandomBackend` with the declared study seed.
- `sobol` uses scrambled `SobolBackend` with the declared study seed.
- `smac` uses SMAC 2.x ask and tell through a benchmark-only adapter. Scientific constraint
  violations and failures receive a fixed scalar penalty for SMAC's internal minimization, but the
  raw scientific results remain unchanged.
- `botorch` uses `SystemBayesBackend` with `min_initial=5`, `num_restarts=2`, `raw_samples=16`,
  `max_categorical_assignments=16`, and `candidate_retry_limit=2`.

BoTorch and SMAC remain optional and are imported only by selected benchmark adapters. The first
five BoTorch evaluations follow its seeded Sobol cold start. SMAC is told the same first five Sobol
configurations and observations before it selects later configurations. The standalone Sobol method
uses the same prefix. Random and fixed order have no compatible warm-start phase.

Every method receives the same 10-evaluation limit and problem cost budget. An evaluation that
would exceed the cost budget is a benchmark failure, not a truncated success. Every proposed
configuration is validated through `SearchSpace.encode` before evaluation.

## Records and summaries

The command writes:

- `raw-records.jsonl`, one canonical record per evaluation;
- `run-summary.csv`, one row for every problem, method, and seed;
- `report.md`, aggregate method and problem results plus every release criterion; and
- `gate.json`, the machine-readable pass or fail decision and provenance.

Each raw record contains the problem, method, seed, evaluation index, action and result records,
cumulative cost, feasibility and constraint-violation flags, best feasible objective, normalized
regret, optimizer overhead, fallback events, and replay status. The summary records final regret,
cost-normalized regret area, cost to first feasible result, status and violation counts, total cost,
optimizer overhead, fallback counts, invalid proposals, budget overruns, and replay consistency.

The report shows means, medians, and 10th and 90th percentiles. Summary generation reads only the
raw JSONL file. A test must reconstruct the checked CSV and gate decision from those records.

## Release criteria

The gate passes only when all conditions hold:

1. All 750 problem, method, and seed runs complete and produce exactly 7,500 evaluation records.
2. Invalid proposed configurations and evaluator-budget overruns are both zero.
3. Fixed, random, Sobol, and BoTorch action sequences and scientific results replay exactly for all
   600 native runs. Timing fields are excluded from equality.
4. SMAC completes all 150 runs. Any unsupported semantics or adapter failure is retained as a failed
   run and fails this criterion.
5. Unresolved BoTorch fallback events after the five-observation cold start are no more than 10% of
   modeled suggestions in aggregate and no more than three in any run. Cold-start fallback messages
   are expected and excluded. Fit, warning, acquisition, candidate, and categorical-limit fallbacks
   are unresolved.
6. Pooled across all 150 problem-seed pairs, BoTorch mean final regret is at most
   `0.90 * random mean + 0.02`, and its mean regret area is at most
   `0.90 * random mean + 0.02`.
7. Pooled across the same pairs, BoTorch mean final regret and mean regret area are each at most
   `1.10 * the corresponding Sobol mean + 0.01`.
8. BoTorch mean final regret is no more than 0.10 above random and no more than 0.12 above Sobol on
   every problem. It is at or below random on at least three of the five problems.

SMAC and fixed order are reported comparisons but do not set the numeric Release A threshold.

The benchmark command exits nonzero if any criterion fails. Failed runs and unfavorable numeric
results remain in raw data, the summary, and the report.
