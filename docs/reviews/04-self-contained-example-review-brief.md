# Item 4 self-contained example review brief

_Prepared: 2026-09-04_

_Base revision: `df44265`_

## Scope

Review the uncommitted item 4 changes in the isolated worktree against
`docs/bayesian-optimization-plan.md` and
`docs/implementation-plans/04-self-contained-example.md`.

The review covers every file in `examples/optimization_chain/`, the focused test in
`tests/test_optimization_example.py`, and no earlier implementation item.

## Review questions

1. Is the example a valid feed-forward system with continuous, integer, categorical, and
   conditional parameters?
2. Does the evaluator have a defensible scientific constraint, a controlled model-failure region,
   and the unique known feasible optimum claimed by the documentation?
3. Are all data local and declared in the durable input hashes, with no network or hidden runtime
   dependency?
4. Does the checked expected result follow from the seeded public run specification rather than a
   test-only execution path?
5. Do bounded start, resume, and two fresh runs establish prefix preservation and byte-identical
   ledgers and recommendations?
6. Can a clean checkout follow every README command without relying on undeclared setup?

## Ownership and constraints

The reviewer owns only `docs/reviews/04-self-contained-example-review.md`. Do not edit the example,
tests, plans, or other review files. Other work is present in the worktree, so do not revert or
replace changes. Do not commit, push, use the network, or run long benchmark jobs.

Report findings by severity with exact file and line references. Include the checks run and any
residual risks. A clean review must state that no implementation defect remains.

## Current focused evidence

- `pixi run pytest -q tests/test_optimization_example.py`: 2 passed.
- Ruff format and lint checks on the example evaluator and test passed.
