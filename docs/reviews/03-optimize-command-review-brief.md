# Item 3 optimize command review brief

_Prepared: 2026-09-04_

_Base revision: `99bf677`_

## Scope

Review the uncommitted item 3 changes in the isolated worktree against
`docs/bayesian-optimization-plan.md` and `docs/implementation-plans/03-optimize-command.md`.

The review covers:

- safe system path resolution through `OptimizationRunSpec`;
- random, Sobol, and optional BoTorch policy construction;
- `autoengineering optimize` new and resume intent;
- evaluation limits, terminal states, summaries, and failure reporting;
- compatibility between CLI construction and the existing recovery identity; and
- focused tests in `tests/test_optimization_cli.py`.

## Review questions

1. Can invalid configuration, input, evaluator, dependency, or destination state create or alter a
   work directory?
2. Does resume preserve committed ledger bytes and the original identity while rejecting a changed
   run contract without mutation?
3. Is `--max-new-evaluations` invocation scoped, including zero, and distinct from durable terminal
   conditions?
4. Are text and JSON summaries derived only from committed ledger state and truthful for evaluator
   failures and empty recommendations?
5. Does the base command import avoid Torch, BoTorch, GPyTorch, and SMAC?

## Ownership and constraints

The reviewer owns only `docs/reviews/03-optimize-command-review.md`. Do not edit implementation,
tests, plans, or other review files. Other work is present in the worktree, so do not revert or
replace changes. Do not commit, push, use the network, or run long benchmark jobs.

Report findings by severity with exact file and line references. Include the checks run and any
residual risks. A clean review must state that no implementation defect remains.

## Current focused evidence

- `pixi run pytest -q tests/test_optimization_cli.py`: 14 passed, 1 skipped.
- `pixi run -e bayes pytest -q tests/test_optimization_cli.py`: 14 passed, 1 skipped, with two
  dependency deprecation warnings.
- Ruff checks on the touched Python files passed.
- `git diff --check` passed.
