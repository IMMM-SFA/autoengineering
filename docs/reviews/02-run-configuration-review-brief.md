# Item 2 run configuration review brief

_Prepared: 2026-09-04_

_Base revision: `8e4624c`_

## Scope

Review the uncommitted item 2 changes in the isolated worktree against
`docs/bayesian-optimization-plan.md` and
`docs/implementation-plans/02-public-run-configuration.md`.

The review covers:

- public parameter and `SearchSpace` dictionary and YAML serialization;
- strict `OptimizationRunSpec` validation and immutable state;
- policy name and option separation from the study architecture;
- safe path resolution relative to the run specification;
- evaluator factory loading and source discovery;
- exact hashing of the system YAML, run specification, evaluator source, and declared inputs; and
- focused tests in `tests/test_optimization_run_spec.py`.

## Review questions

1. Do all schemas reject unknown or ambiguous input while preserving declaration order and scalar
   types?
2. Can any accepted path escape its intended root, pass through a symlink, or omit a required file?
3. Are evaluator loading and policy options sufficient for the later CLI without importing Bayesian
   dependencies from the base optimization package?
4. Do the canonical and exact byte hashes cover every declared input and exclude undeclared state?
5. Do the tests establish stable serialization and hashes across fresh processes?

## Ownership and constraints

The reviewer owns only `docs/reviews/02-run-configuration-review.md`. Do not edit implementation,
tests, plans, or other review files. Other work may be present in the worktree, so do not revert or
replace changes. Do not commit, push, use the network, or run long benchmark jobs.

Report findings by severity with exact file and line references. Include the checks run and any
residual risks. A clean review must state that no implementation defect remains.

## Current focused evidence

- `pixi run python -m pytest tests/test_optimization_spec.py
  tests/test_optimization_run_spec.py -q -p no:cacheprovider`: 60 passed.
- `pixi run lint`: passed.
