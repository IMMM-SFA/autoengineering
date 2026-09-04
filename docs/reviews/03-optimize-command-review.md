# Item 3 optimize command review

_Reviewed: 2026-09-04_

_Base revision: `99bf677`_

## Must fix

None. No implementation defect remains in the reviewed item 3 diff.

## Should fix

None.

## Looks good

- New and resume intent is explicit. Work directory validation rejects occupied new destinations,
  absent or structurally incomplete resume destinations, symlinked path components, symlinked
  durable artifacts, and nonregular lock files before constructing the real controller
  (`src/autoengineering/optimization/command.py:25`,
  `src/autoengineering/optimization/command.py:60`,
  `src/autoengineering/optimization/command.py:98`). If an advisory lock is missing, recovery is
  validated in a disposable copy before the real controller recreates it
  (`src/autoengineering/optimization/command.py:119`,
  `src/autoengineering/optimization/command.py:150`).
- System paths resolve relative to the checked run specification, and the run, system, evaluator
  entry module, and declared inputs are bound to the same validated run contract before controller
  construction (`src/autoengineering/optimization/run_spec.py:314`,
  `src/autoengineering/optimization/run_spec.py:383`).
- Random and Sobol remain base imports. BoTorch is imported only in its selected policy branch, with
  a concise environment instruction when optional dependencies are absent. Release A rejects other
  study architectures (`src/autoengineering/optimization/command.py:36`).
- Invocation limits are process scoped, including zero. A bounded call records a durable stop only
  when it has reached a budget, target, insufficient balance, evaluation count, or finite space
  boundary. The finite space check is side effect free and optional, so the controller does not ask
  for an unrecorded action and does not expand the public backend protocol
  (`src/autoengineering/optimization/controller.py:429`,
  `src/autoengineering/optimization/controller.py:466`,
  `src/autoengineering/optimization/backend.py:164`). The original protocol compatibility and
  no-extra-suggestion regressions are at `tests/test_optimization_system.py:102` and
  `tests/test_optimization_system.py:137`.
- Evaluator exceptions and invalid result IDs or cost units become committed infrastructure failure
  observations instead of leaving a pending action. Other ordinary configuration and factory
  exceptions become concise Click errors (`src/autoengineering/optimization/controller.py:448`,
  `src/autoengineering/cli.py:154`).
- Text and JSON summaries use `total_evaluator_cost` and are built from one locked post-invocation
  view. Counts, terminal state, and recommendation therefore describe the same committed ledger
  prefix, while `new_evaluation_count` records only this invocation's work
  (`src/autoengineering/optimization/controller.py:181`,
  `src/autoengineering/optimization/controller.py:474`,
  `src/autoengineering/optimization/command.py:134`). The simulated interleaving regression is at
  `tests/test_optimization_cli.py:218`.

Checks run on the final saved state:

- `pixi run pytest -q tests/test_optimization_cli.py tests/test_optimization_recovery.py tests/test_optimization_run_spec.py tests/test_optimization_system.py -p no:cacheprovider`: 178 passed, 22 skipped.
- `pixi run -e bayes pytest -q tests/test_optimization_cli.py tests/test_optimization_system.py -p no:cacheprovider`: 92 passed, 1 skipped. The only output beyond the result was two upstream Torch deprecation warnings.
- `pixi run lint`: passed.
- `git diff --check`: passed.
- A direct runtime protocol probe confirmed that a backend implementing the original five-method
  protocol is still recognized.

## Suggestions

- The full repository test suite and Waterology constraint suite were not rerun in this bounded
  review. They remain completion gate evidence, not observed implementation defects.
- Path and recovery checks were exercised on macOS. Windows lock behavior and adversarial file swaps
  between input validation, import, and hashing remain residual risks outside the focused coverage.
