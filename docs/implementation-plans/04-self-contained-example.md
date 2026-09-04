# Item 4 implementation plan: self-contained optimization example

_Parent plan: [`bayesian-optimization-plan.md`](../bayesian-optimization-plan.md)_

_Baseline revision: `df44265`_

## Outcome

Add `examples/optimization_chain/` as a small deterministic workflow that runs through the public
CLI without downloads. The example will document bounded execution, resume, artifact inspection,
and reproducibility from a clean checkout.

## Example model

The system will contain three feed-forward components: declared input data, a configurable
transform, and a scalar score. A checked CSV will provide a short predictor series and target
values.

The search space will include:

- categorical `architecture`, with `linear` and `nonlinear` choices;
- continuous `gain`;
- integer `stages`; and
- continuous `curvature`, active only for the nonlinear architecture.

The deterministic evaluator will calculate predictions from the CSV, maximize negative root mean
square error, and constrain absolute bias. The linear configuration with gain 1.25 and two stages
will be the known feasible optimum. The nonlinear term will prevent that architecture from matching
the target exactly. Configurations whose gain and stage count exceed a declared product threshold
will return `model_failure` with the normal evaluator cost.

## Files

Create:

- `system.yaml`, containing the three-component directed acyclic graph;
- `optimization.yaml`, containing the complete run and mixed search space;
- `evaluator.py`, containing the system-aware evaluator factory;
- `input.csv`, containing all evaluator data;
- `expected-result.json`, containing the analytic optimum and the expected seeded Sobol
  recommendation; and
- `README.md`, containing commands for a bounded start, resume, JSON output, artifact inspection,
  and two-run comparison.

All paths will resolve from `optimization.yaml`. The input CSV will be listed in `input_files` so its
bytes are part of the durable run identity.

## Tests

Add a focused example test that:

1. loads the system and run specification from the checked files;
2. verifies the graph order, parameter kinds, condition, declared input, and analytic optimum;
3. verifies the controlled failure classification directly;
4. runs three evaluations through the CLI, resumes to the terminal budget, and preserves the first
   ledger prefix;
5. compares the final recommendation with `expected-result.json`; and
6. runs two fresh studies and requires byte-identical ledgers and recommendation files.

The example test will use only the default Pixi environment and temporary output directories.

## Verification gate

Item 4 is complete only when the focused example test, the full default and Bayesian suites, lint,
whitespace, and scoped Waterology checks pass after independent review. The seeded example must
match its checked expected result, and two fresh CLI runs must produce the same ledger and
recommendation bytes.

The parent plan and status document will be updated only after this evidence exists.
