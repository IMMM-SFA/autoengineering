# Item 5 implementation plan: Release A benchmark gate

_Parent plan: [`bayesian-optimization-plan.md`](../bayesian-optimization-plan.md)_

_Decision: [`0001-release-a-benchmark.md`](../decisions/0001-release-a-benchmark.md)_

_Baseline revision: `278df4b`_

## Outcome

Implement the preregistered whole-system benchmark as a reproducible package and Pixi command. The
full run will retain evaluation-level evidence, regenerate its summaries from raw records, audit
native replay, and exit nonzero if any frozen Release A criterion fails.

## Package design

Add `autoengineering.benchmarks.release_a` with these responsibilities:

1. immutable problem definitions and the five deterministic evaluators;
2. a common method adapter returning one validated action at a time;
3. native fixed, random, Sobol, and lazy BoTorch adapters;
4. a lazy SMAC ask-and-tell adapter using the same search-space and result protocol;
5. one sequential run loop with exact evaluation and cost accounting;
6. native replay that compares actions and scientific result fields while excluding timing;
7. canonical JSONL writing and raw-record validation;
8. CSV aggregation, percentile reporting, and frozen gate evaluation; and
9. an atomic output-directory commit so interrupted benchmark runs do not replace prior evidence.

The base `autoengineering.optimization` import will remain free of optional dependencies. Unit tests
will be able to select a reduced problem, method, and seed set without changing the full gate
defaults.

## SMAC boundary

Translate every public parameter kind and condition to ConfigSpace. The adapter will seed SMAC from
the study seed, tell it the five shared Sobol observations, then use ask and tell for the remaining
budget. It will map the maximization objective to SMAC minimization and apply the declared penalty
only inside SMAC. Raw `EvaluationResult` records remain unchanged.

An unavailable or incompatible SMAC installation will produce a concise benchmark dependency error.
The base environment tests will prove that importing the benchmark problem and summary modules does
not load SMAC, Torch, BoTorch, or GPyTorch.

## Evidence workflow

Add `benchmark-release-a` to the Bayesian Pixi environment. A normal full invocation will write to
`benchmarks/release_a/results/` and include the decision document hash, source revision, dependency
versions, platform, and command in `gate.json`.

Run the workflow in this order:

1. unit-test each problem optimum, constraint, cost, failure, and seed mapping;
2. test each method adapter and shared Sobol prefix;
3. test raw-record schema, replay, aggregation, and deliberately failing gates on a reduced run;
4. run the full 750-run benchmark once using the frozen decision;
5. independently regenerate the CSV and gate from `raw-records.jsonl`;
6. inspect every failure and fallback without deleting unfavorable records; and
7. run the full repository completion gates after the final benchmark artifact is written.

Progress output will identify the current problem, method, seed, and completed run count.

## Verification gate

Item 5 is complete only when the checked raw records reproduce `run-summary.csv` and `gate.json`, all
600 native runs replay, all 150 SMAC runs complete, and every frozen release criterion passes at the
same candidate revision. Focused tests, full default and Bayesian tests, lint, whitespace, scoped
Waterology checks, and an independent review must also pass.

If a criterion fails, retain that result and mark item 5 blocked or in progress. Do not alter the
decision thresholds after the full comparison.
