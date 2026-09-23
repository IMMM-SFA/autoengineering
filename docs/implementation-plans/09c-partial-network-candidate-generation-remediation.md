# Item 9 candidate-generation remediation plan

_Status: Approved for execution on 2026-09-04_

_Date: 2026-09-04_

## Outcome sought

Run one preregistered correction to the partial-network action pool without changing the problems,
seeds, evaluator budgets, metrics, or acceptance thresholds in
[Decision 0007](../decisions/0007-partial-network-benchmark.md). Item 9 remains experimental unless
the corrected 40-run comparison passes every frozen criterion.

This plan does not authorize Item 10. It preserves the original adverse evidence and all completed
remediation iterations.

## Evidence at the boundary

The original comparison failed `complete_matrix` and `random_component_control`. Reserving one
complete-system refresh repaired every invalid stop. Common antithetic fantasy draws then passed
the controlled-component criterion. The strongest result is
[`iteration-03`](../../benchmarks/partial_network/iterations/item9-remediation/iteration-03/): 11 of
12 criteria pass, but partial and random have equal median regret area on both problems.

| Problem | Partial median regret area | Random median regret area | Difference |
| --- | ---: | ---: | ---: |
| `informative_chain` | 0.146864 | 0.146864 | 0.000000 |
| `informative_branch` | 0.279599 | 0.279599 | about 0.000000 |

The required difference is at most `-0.005` on either problem and at most `0.10` on the other.
The chain seed 1 run finds a near-optimal warm incumbent, but later candidates do not improve it.
The branch seed 3 run improves only at total cost 8, so that observation cannot reduce regret area.

The current partial configuration scores two complete action points and evaluates component value
over four terminal decision points. This is a deliberately small finite approximation. BoTorch's
acquisition optimizer uses raw samples and multiple restarts because the acquisition surface is
nonconvex, and its knowledge-gradient tutorial uses a larger raw candidate set to locate the
terminal value. Fixed base samples make Monte Carlo acquisition comparisons deterministic and
easier to optimize. See the
[BoTorch optimization guide](https://botorch.org/docs/v0.17.1/optimization),
[BoTorch acquisition guide](https://botorch.org/docs/acquisition), and
[one-shot knowledge-gradient tutorial](https://botorch.org/docs/next/tutorials/one_shot_kg).
The underlying terminal-value interpretation follows Frazier, Powell, and Dayanik (2008),
<https://doi.org/10.1137/070693424>.

These sources support a candidate-coverage hypothesis. They do not prove that a larger pool will
pass this benchmark.

## Proposed protocol

Use the existing isolated worktree and locked Pixi `bayes` environment. Preserve the linear loop.
The existing Iteration 03 result is the baseline and must not be rerun or replaced.

Before any new comparison, add and sign Decision 0008 with this exact correction:

- retain both Decision 0007 problems, seeds 0 through 4, study seed mapping, warm observations,
  eight-unit cost budget, 12-action limit, methods, metrics, and all 12 numeric criteria;
- retain the system-refresh reservation and common antithetic fantasy sampler from Iteration 03;
- change `candidate_pool_size` from 2 to 16 for all three partial methods;
- retain `decision_pool_size=4`, `posterior_samples=16`, `fantasy_samples=4`, two fit attempts, a
  maximum component streak of two, cost quantile 0.9, and zero value threshold;
- retain the full-network method's existing 16-candidate configuration; and
- record the corrected source hashes, signed execution revision, environment, and decision hash.

Sixteen is fixed because it matches the preregistered full-network candidate count. It increases
partial action coverage without introducing a value selected from the observed results. All
partial controls receive the same pool size so action availability remains comparable.

The proposed extension permits at most two new full matrices:

1. one development matrix from the signed Decision 0008 implementation; and
2. one final replacement matrix only if the development matrix passes every criterion.

Do not test other pool sizes on the benchmark seeds. A failed development matrix ends this
extension and retains Item 9 as adverse evidence.

## Owned files

The extension may change only:

- `docs/decisions/0008-partial-network-candidate-generation.md`;
- `src/autoengineering/benchmarks/partial_network/runner.py`;
- `tests/test_partial_network_benchmark.py`;
- `autoresearch-candidate-generation.md`;
- `autoresearch-candidate-generation.jsonl`;
- `autoresearch-candidate-generation.sh`;
- new evidence under `benchmarks/partial_network/candidate-generation/`;
- Item 9 status, guide, parent-plan, and review documents after a passing replacement; and
- this implementation plan if review finds a factual error before execution.

Do not modify Decision 0007, `benchmarks/partial_network/results/`, or any existing directory under
`benchmarks/partial_network/iterations/`.

## Implementation sequence

### 1. Freeze the extension

Add Decision 0008 with the protocol above, an explicit source-hash inventory, and the existing
adverse-result hashes. Commit the decision before changing the benchmark setting.

Gate: the decision is signed, the worktree is clean, and its numeric thresholds match Decision
0007 byte for byte.

### 2. Change candidate coverage

Write a focused failing test that expects 16 partial action-pool points for each partial method and
the unchanged settings for every other field. Change only `PARTIAL_SETTINGS["candidate_pool_size"]`.
Confirm backend identity and raw acquisition diagnostics report the selected pool size.

Gate: focused benchmark and backend tests pass, lint passes, and the source diff contains no other
policy or criterion change.

### 3. Verify before compute

Run the partial backend and benchmark test groups, the Waterology constraints on touched Python
files, `git diff --check`, and signed-commit verification. Confirm that the benchmark output path is
absent and the original evidence hashes still match.

Gate: every structural check passes from a clean signed revision. Do not run performance
preflights on the five benchmark seeds.

### 4. Run the development matrix

Run one fixed command in the local `bayes` environment. The runner must create an absent evidence
directory atomically and must treat a scientific gate failure as a completed experiment rather
than an execution error.

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
then may the Item 9 status change to complete and planning for Item 10 begin.

## Stop conditions

- Do not relax or reinterpret a Decision 0007 threshold.
- Do not replace, edit, or omit adverse evidence.
- Do not compare additional candidate-pool sizes on the benchmark seeds.
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
