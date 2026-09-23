# Item 3 implementation plan: optimize command

_Parent plan: [`bayesian-optimization-plan.md`](../bayesian-optimization-plan.md)_

_Baseline revision: `99bf677`_

## Outcome

`autoengineering optimize` will start or resume one whole-system optimization study from a system
YAML file and the public run specification. The command will validate and hash every input before
creating the work directory, enforce explicit new or resume intent, run a bounded sequential study,
and print a stable text or JSON summary.

## Command contract

Add this command shape:

```text
autoengineering optimize system.yaml optimization.yaml \
  --workdir outputs/study-name \
  --max-new-evaluations 10

autoengineering optimize system.yaml optimization.yaml \
  --workdir outputs/study-name \
  --resume
```

The invocation limit option overrides the optional limit in `OptimizationRunSpec`. It limits only
new evaluations in this process. It does not mark a study terminal unless the study reaches a
budget, target, finite-space, or insufficient-balance stop condition.

New mode requires an absent or empty destination. Resume mode requires recognizable study state.
A symlinked destination is always rejected. All configuration, input, evaluator, policy, and
dependency checks occur before controller construction.

## Construction sequence

1. Load `OptimizationRunSpec` and resolve the system YAML relative to that file.
2. Load the `System`, evaluator factory, and evaluator callable.
3. Hash the system, matching run specification, evaluator entry module, and declared inputs.
4. Construct random, scrambled Sobol, or BoTorch through a small policy factory.
5. Create `ObservationLedger` and `OptimizationStudy` with the resolved target and input hashes.
6. Run the effective invocation limit and render the durable result.

Random and Sobol remain base dependencies. Import `SystemBayesBackend` only inside the BoTorch
policy branch. If its optional dependencies are missing, raise a concise Click error that names the
Bayesian Pixi environment. Release A rejects non-system study architectures.

## Output

Text output will report the resolved work directory, terminal or invocation-limited state,
evaluation count, total evaluator cost and unit, and recommended configuration. JSON output will
contain the same fields plus the complete recommendation record. Both formats derive counts and
cost from one locked view of the committed ledger after the run.

## Tests

Use Click's isolated filesystem runner to cover:

- new random and Sobol runs;
- bounded nonterminal invocation and exact resume;
- rejection of existing destinations without `--resume` and missing state with `--resume`;
- incompatible resume with unchanged artifact bytes;
- budget, target, finite-space, and insufficient-balance stops;
- evaluator failure conversion and reporting;
- text and JSON output;
- invalid evaluator factory output;
- BoTorch construction in the Bayesian environment and its base-environment dependency error; and
- a base import probe proving optional Bayesian and SMAC modules remain unloaded.

## Verification gate

Item 3 is complete only when the command and Python construction use the same run contract and
input hashes, prior ledger bytes and identity survive resume, repeated seeds reproduce action
sequences and recommendations, and all focused, default, Bayesian, lint, whitespace, and
Waterology checks pass after the final edit.

The status document will be updated only after this evidence exists.

## Completion evidence

Item 3 was implemented in signed commit `4f6034f`. The command validates its complete run contract
before creating durable state, preserves explicit new and resume intent, and returns a consistent
summary from the controller's locked result snapshot. The independent review in
[`03-optimize-command-review.md`](../reviews/03-optimize-command-review.md) found no remaining
implementation defect after its findings were corrected.

The final gate at `4f6034f` produced:

- `pixi run test`: 332 passed, 22 skipped;
- `pixi run -e bayes test-bayes`: 353 passed, 1 skipped, with two upstream Torch deprecation
  warnings;
- `pixi run lint`: passed;
- `git diff --check`: passed; and
- scoped Waterology constraints: 7 of 7 passed.
