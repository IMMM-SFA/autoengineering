# Item 9 decision-pool remediation plan

_Status: Approved for execution on 2026-09-04_

_Date: 2026-09-04_

## Outcome sought

Run one preregistered correction to the terminal decision pool without changing the problems,
seeds, evaluator budgets, metrics, or acceptance thresholds in
[Decision 0007](../decisions/0007-partial-network-benchmark.md). Item 9 remains experimental unless
the corrected comparison passes every frozen criterion twice.

This plan does not authorize Item 10. It preserves all original and remediation evidence,
including the adverse 16-candidate development matrix.

## Evidence at the boundary

The candidate-generation development matrix completed all 40 runs and passed 10 of 12 criteria.
The value policy selected a system action at all 39 post-warm decisions. It therefore selected
neither controlled branch component and failed `controlled_informative_component` with left 0 and
right 0.

The policy improved median regret area over random by `0.0014498890245697449` on
`informative_chain` and `0.00029282913842992864` on `informative_branch`. Both improvements were
smaller than the required `0.005`. The result is preserved under
[`candidate-generation/development`](../../benchmarks/partial_network/candidate-generation/development/).

The value calculation currently scores direct system improvement over 16 action configurations.
It evaluates the terminal value after a component observation over four independent decision
configurations. In the branch diagnostics, recomputing the highest component score at each
component-eligible decision ranks `left` first nine times, `right` first four times, and `terminal`
first twice. The controlled component direction remains visible within the component candidates,
but every maximum system score exceeds the corresponding maximum component score.

This evidence supports a finite-pool resolution hypothesis. It does not show that a larger
decision pool will pass the benchmark.

## Proposed protocol

Use the existing isolated worktree and locked Pixi `bayes` environment. Preserve the linear loop.
The adverse candidate-generation matrix is the baseline and must not be rerun or replaced.

Before any new comparison, add and sign Decision 0009 with this exact correction:

- retain both Decision 0007 problems, seeds 0 through 4, study seed mapping, warm observations,
  eight-unit cost budget, 12-action limit, methods, metrics, and all 12 numeric criteria;
- retain the system-refresh reservation and common antithetic fantasy sampler;
- retain `candidate_pool_size=16` for all three partial methods;
- change `decision_pool_size` from 4 to 16 for all three partial methods;
- retain `posterior_samples=16`, `fantasy_samples=4`, two fit attempts, a maximum component streak
  of two, cost quantile 0.9, and zero value threshold;
- retain the full-network method's existing 16-candidate and 64-posterior-sample configuration;
  and
- record the corrected source hashes, signed execution revision, environment, and decision hash.

Sixteen is fixed because it matches the action-pool and full-network candidate counts already
declared. No other decision-pool size may be tested on the benchmark seeds.

The proposed extension permits at most two new full matrices:

1. one development matrix from the signed Decision 0009 implementation; and
2. one replacement matrix only if the development matrix passes every criterion.

A failed development matrix ends this extension and retains Item 9 as adverse evidence.

## Fixed execution contract

- Development command:
  `pixi run -e bayes bash autoresearch-decision-pool.sh development`
- Conditional replacement command:
  `pixi run -e bayes bash autoresearch-decision-pool.sh replacement`
- Environment: local isolated worktree and locked Pixi `bayes` environment
- Loop: linear
- Maximum full matrices: two, with the second conditional on a complete first pass
- Status interval: after each problem-seed-method group and at each evidence gate
- Evidence root: `benchmarks/partial_network/decision-pool/`

## Owned files

The extension may change only:

- `docs/decisions/0009-partial-network-decision-pool.md`;
- `src/autoengineering/benchmarks/partial_network/runner.py`;
- `tests/test_partial_network_benchmark.py`;
- `autoresearch-decision-pool.md`;
- `autoresearch-decision-pool.jsonl`;
- `autoresearch-decision-pool.sh`;
- new evidence under `benchmarks/partial_network/decision-pool/`;
- Item 9 status, guide, parent-plan, and review documents after a passing replacement; and
- this implementation plan if review finds a factual error before execution.

Do not modify Decisions 0007 or 0008, any prior evidence directory, the partial-network backend,
or either baseline implementation.

## Implementation sequence

### 1. Freeze the extension

Add Decision 0009 with the protocol above, a source-hash inventory, and hashes for all prior Item 9
evidence. Commit the decision before changing the benchmark setting.

Gate: the decision is signed, the worktree is clean, and its numeric thresholds match Decision
0007 byte for byte.

### 2. Change terminal decision resolution

Update the focused benchmark contract test to expect 16 decision-pool points and the unchanged
settings for every other field. Confirm the test fails only because the current value is four.
Change only `PARTIAL_SETTINGS["decision_pool_size"]`.

Gate: focused benchmark and backend tests pass, lint passes, identity and raw diagnostics report 16
action and 16 decision points, and the source diff contains no other policy or criterion change.

### 3. Verify before compute

Create the bounded controller and ledger. Run the partial backend and benchmark test groups, the
Waterology constraints on touched files, `git diff --check`, and signed-commit verification.
Confirm the new evidence root is absent and every prior evidence hash still matches.

Gate: every structural check passes from a clean signed revision. Do not run performance preflights
on the five benchmark seeds.

### 4. Run the development matrix

Run the fixed development command once. Publish the standard evidence directory atomically and
write a sibling companion manifest. Treat a scientific gate failure as a completed experiment.

Record all 40 runs, raw actions and results, acquisition scores, seeds, costs, stop reasons,
component selections, summaries, gate results, source hashes, package versions, and the signed Git
revision.

Gate: the raw stream reconstructs exactly and the immutable evidence is committed regardless of
outcome.

### 5. Decide once

Evaluate all 12 Decision 0007 criteria separately. Do not tune the pool, sampler, thresholds, or
seed set after reading the matrix.

- If any criterion fails, record the adverse result, keep Item 9 experimental, and stop.
- If every criterion passes, sign a replacement declaration that identifies the development
  evidence and run the one reserved replacement matrix without further source changes.

Gate: only a complete pass may proceed to the replacement run.

### 6. Verify a passing replacement

If authorized by the prior gate, reconstruct the replacement from raw records and run lint,
default tests, Bayesian tests, Release A reconstruction, Item 8 reconstruction, Item 9
reconstruction, Waterology constraints, whitespace checks, signed-commit verification, and a fresh
signed-archive review.

Gate: every repository check and every scientific criterion passes at one signed revision. Only
then may Item 9 change to complete and Item 10 begin.

## Stop conditions

- Do not relax or reinterpret a Decision 0007 threshold.
- Do not replace, edit, or omit adverse evidence.
- Do not compare additional decision-pool sizes on the benchmark seeds.
- Do not change the action pool, posterior samples, fantasy samples, sampler, or selection rule.
- Do not let component observations update terminal incumbents or recommendations.
- Do not exceed the evaluator-cost or action budget.
- Do not use the reserved replacement run after a failed development matrix.
- Do not begin Item 10 unless the replacement passes every Item 9 gate.

## Completion gate

This remediation is complete only when either:

1. the development matrix fails and its immutable adverse evidence is committed with Item 9 still
   experimental; or
2. the development and replacement matrices both pass all 12 frozen criteria, every raw artifact
   reconstructs, and all repository checks pass at one signed revision.

Only the second outcome completes Item 9 in the parent plan.
