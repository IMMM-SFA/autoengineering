# Item 4 self-contained example review

_Reviewed: 2026-09-04_

_Base revision: `df44265`_

## Must fix

None. No implementation defect remains in the reviewed item 4 diff.

## Should fix

None.

## Looks good

- The system is a valid three-component directed acyclic chain from checked observations through a
  configurable transform to scalar metrics (`examples/optimization_chain/system.yaml:1`). The run
  specification declares categorical, continuous, integer, and conditional continuous parameters,
  with curvature active only for the nonlinear architecture
  (`examples/optimization_chain/optimization.yaml:23`).
- The objective and constraint are scientifically interpretable for this synthetic regression:
  maximize negative RMSE subject to absolute bias no greater than 0.3
  (`examples/optimization_chain/optimization.yaml:4`,
  `examples/optimization_chain/evaluator.py:39`). The controlled instability region returns
  `model_failure` with the normal model-run cost when gain times stages exceeds 6.8
  (`examples/optimization_chain/evaluator.py:31`).
- The documented analytic optimum is unique. For the linear branch, squared RMSE is
  `0.5 * (gain - 1.25)^2 + 0.01 * (stages - 2)^2`, so only gain 1.25 and two stages attain zero.
  The nonlinear branch cannot attain zero because its residual at predictor zero is never zero for
  an allowed integer stage count. The optimum is feasible with zero absolute bias
  (`examples/optimization_chain/input.csv:1`,
  `examples/optimization_chain/expected-result.json:2`).
- The evaluator reads only the checked local CSV through a path relative to its source. The run
  specification declares `input.csv`, and an independently generated manifest contained exactly
  the system, run specification, evaluator source, and CSV hashes
  (`examples/optimization_chain/evaluator.py:5`,
  `examples/optimization_chain/optimization.yaml:54`). No network or undeclared runtime data access
  is present.
- The checked seeded Sobol recommendation comes from the public CLI path, not a test-only policy.
  The focused test performs a three-evaluation start, resumes the same study to 12 evaluations,
  preserves the ledger prefix, compares the terminal result with `expected-result.json`, and
  compares two fresh ledgers and recommendations byte for byte
  (`tests/test_optimization_example.py:87`).
- The README distinguishes the analytic optimum from the sampled Sobol recommendation and provides
  repository-root commands for bounded start, resume, JSON output, artifact inspection, and two-run
  comparison (`examples/optimization_chain/README.md:7`,
  `examples/optimization_chain/README.md:15`,
  `examples/optimization_chain/README.md:33`,
  `examples/optimization_chain/README.md:44`). Those commands rely only on the declared Pixi
  environment and standard tools available on the project's supported macOS and Linux platforms.

Checks run on the final saved state:

- `pixi run pytest -q tests/test_optimization_example.py -p no:cacheprovider`: 2 passed.
- `pixi run ruff check --no-cache examples/optimization_chain/evaluator.py tests/test_optimization_example.py`: passed.
- `pixi run ruff format --check examples/optimization_chain/evaluator.py tests/test_optimization_example.py`: 2 files already formatted.
- `git diff --check`: passed.
- Independent repository-root CLI probe: bounded start completed 3 evaluations with
  `invocation_limit`; resume completed 12 evaluations with `max_cost`; two fresh runs produced the
  expected recommendation and byte-identical ledgers and recommendation files.
- Independent provenance probe: all four manifest input hashes matched the exact bytes of
  `system.yaml`, `optimization.yaml`, `evaluator.py`, and `input.csv`.

## Suggestions

- The full default and Bayesian suites and the scoped Waterology checks were not rerun in this
  bounded review. They remain completion gate evidence, not observed implementation defects.
- The example is deterministic and intentionally small. It demonstrates the controlled failure
  branch directly, but seed 41 does not sample that branch in the checked 12-evaluation run.
