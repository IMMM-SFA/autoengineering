# Item 9 acquisition reassessment and proposed common-utility correction

_Status: Proposed; approval required before implementation or compute_

_Date: 2026-09-04_

## Decision needed

Replace the partial policy's asymmetric action scores with one common terminal decision utility for
system and component observations. This is an algorithm change, not another finite-pool adjustment.
No code change, benchmark run, replacement run, or Item 10 work is authorized by this proposal.

If this proposal is not accepted, Item 9 remains experimental and the parent plan stops before
Item 10.

## Evidence at the boundary

The completed remediation series exceeds the three-fix reassessment threshold. The strongest
small-pool result passed 11 of 12 criteria. The two pool corrections each passed 10 of 12 criteria.
All adverse evidence and thresholds remain unchanged.

| Evidence | Action pool | Decision pool | Value-policy selections | Failed criteria |
| --- | ---: | ---: | --- | --- |
| `iteration-03` | 2 | 4 | branch left 2, right 0 | `random_component_control` |
| `candidate-generation/development` | 16 | 4 | system 39 of 39 scored decisions | `controlled_informative_component`, `random_component_control` |
| `decision-pool/development` | 16 | 16 | system 34 of 40; six component actions | `controlled_informative_component`, `random_component_control` |

The six component actions in the last matrix were one chain `upstream`, four chain `terminal`, and
one branch `terminal`. The branch value policy selected neither controlled `left` nor controlled
`right`. Its value minus random regret-area differences were
`-0.0014498890245697726` on the chain and `-0.00029282913842992864` on the branch. Neither met the
frozen `-0.005` improvement.

Increasing the decision pool was not a no-op. Among the 39 scored decisions shared with the prior
matrix, 25 maximum component scores and 12 selected actions changed. In the final matrix, 27 of 40
scored decisions had a positive component value. The system score still exceeded the component
score at most decisions. The median ratio of the maximum system score to the maximum positive
component score was 2.76.

## Architectural finding

The current policy compares two different utilities. For observed incumbent `b`, complete
configuration `x`, and component observation `a`, it uses

```text
system_score(x) = EI_D(x) / system_cost

component_score(a) =
  (E_z[max_x EI_(D union z)(x)] - max_x EI_D(x)) / component_cost
```

The system score values the terminal result obtained by the action. The component score values only
the incremental information above the current next-system-evaluation opportunity. Pool resolution
can change both estimates, but it cannot make their decision horizons equivalent. This asymmetry
was explicit in the original Item 9 design, so it is not an implementation defect that can be fixed
by changing a constant.

## Proposed common utility

Define a terminal decision utility that includes the observed incumbent and one future complete
system decision. Let `s` be `1` for maximization and `-1` for minimization:

```text
b(D) = best observed feasible value of s * objective

I_D(x) = E[max(s * objective(x) - b(D), 0) * 1(feasible(x)) | D]

U(D) = b(D) + max_x I_D(x)
```

For every affordable action `a`, regardless of scope, use the same one-step preposterior value:

```text
KG(a) = E_z[U(D union {(a, z)}) | D, a] - U(D)

score(a) = max(KG(a), 0) / predicted_cost(a)
```

For a component action, the incumbent does not change and this reduces to the existing component
calculation. For a system action, each fantasy conditions every observed scalar component output at
the proposed complete configuration. A feasible terminal fantasy may update the observed incumbent
inside `U`; an infeasible fantasy may not. This gives both scopes the same terminal decision horizon
while preserving observed-only final recommendations.

The policy remains a finite-pool, one-step knowledge-gradient adaptation. It does not score a
surrogate prediction as an observed result. It retains the existing system-refresh reservation,
maximum component streak, conservative costs, and sequential controller.

## Fixed correction contract

If approved, add and sign Decision 0010 before changing executable code. The decision must freeze
the equations above and retain:

- both Decision 0007 problems, analytic truth, seeds 0 through 4, study seed mapping, shared warm
  observations, eight-unit evaluator-cost budget, and 12-action limit;
- all four methods and all 12 Decision 0007 criteria without textual or numeric change;
- `candidate_pool_size=16` and `decision_pool_size=16` for every partial method;
- 16 posterior samples, four common antithetic fantasies, two fit attempts, a maximum component
  streak of two, cost quantile 0.9, and zero marginal-value threshold;
- the full-network comparator and both mixed-scope controls without behavior changes; and
- every original, iteration, candidate-generation, and decision-pool evidence artifact.

Add a stable acquisition-contract identifier to backend identity and durable state. A study created
under the old asymmetric score must fail compatibility checks rather than resume under the new
policy.

Do not evaluate an alternative utility, pool size, sampler, threshold, seed set, problem, cost, or
budget on the benchmark seeds.

## Owned files

The proposed correction may change only:

- `docs/decisions/0010-partial-network-common-utility.md`;
- `src/autoengineering/optimization/partial_network_backend.py`;
- `tests/test_partial_network_backend.py`;
- `tests/test_partial_network_benchmark.py`;
- focused recovery tests if required by the acquisition identity change;
- `autoresearch-common-utility.md`;
- `autoresearch-common-utility.jsonl`;
- `autoresearch-common-utility.sh`;
- new evidence under `benchmarks/partial_network/common-utility/`;
- Item 9 status, guide, parent-plan, and review documents only after a passing replacement; and
- this proposal if review finds a factual error before execution.

Do not modify Decisions 0007 through 0009, prior evidence, benchmark problems, gate reconstruction,
the full-network backend, or either control policy.

## Implementation sequence

### 1. Freeze the algorithm change

Create Decision 0010 with the common-utility equations, fixed settings, unchanged criteria, source
inventory, and hashes for all prior Item 9 evidence. Record that the earlier asymmetric algorithm
remains an adverse result rather than relabeling it.

Gate: the decision is committed and signed, the worktree is clean, every Decision 0007 criterion
matches byte for byte, and all earlier evidence hashes match.

### 2. Specify common-utility behavior

Add focused failing tests before implementation. They must prove:

- system and component candidates use the same `U(D)` baseline;
- a system fantasy conditions every scalar output observed at system scope;
- only a feasible system fantasy may update the incumbent used by `U`;
- a component fantasy cannot update the observed incumbent;
- system score is no longer raw expected improvement;
- a no-information component cannot beat an otherwise equal system decision through cost scaling;
- a cheap informative component can outrank a system action in a nonbenchmark analytic fixture;
- deterministic fantasy streams, canonical tie breaking, diagnostics, and replay remain stable; and
- the acquisition-contract identifier prevents an incompatible durable resume.

Gate: each new test fails for the intended missing behavior and existing Item 9 tests still pass.

### 3. Implement symmetric preposterior scoring

Factor `U(D)` into one helper. Retain the current exact Gaussian component conditioning. Add system
fantasy conditioning in topological order using the proposed configuration, the fantasy's upstream
outputs, and every scalar output observable at system scope. Hold fitted hyperparameters fixed.

Record the baseline utility, fantasy utilities, raw difference, clamped value, Monte Carlo standard
error, predicted cost, score, scope, and all seeds. Use the existing affordability and refresh
rules. Do not change component eligibility, lineage, recommendation, or stop semantics.

Gate: the focused tests, all partial-network tests, lint, Waterology constraints, identity checks,
and deterministic replay pass. The source diff contains no benchmark or control change.

### 4. Verify without benchmark-seed performance inspection

Exercise the analytic fixtures and a reduced closed loop on a nonbenchmark seed. Verify cost,
lineage, observed-only recommendations, recovery, and raw diagnostic reconstruction. Do not inspect
performance on seeds 0 through 4.

Gate: structural checks pass from a clean signed revision, the new evidence root is absent, and all
prior evidence digests still match.

### 5. Run one development matrix

Use one fixed command:

```text
pixi run -e bayes bash autoresearch-common-utility.sh development
```

The controller must create the standard evidence atomically under
`benchmarks/partial_network/common-utility/development/` and write a sibling manifest. Scientific
failure is a completed experiment.

Gate: all 40 runs are recorded, raw evidence reconstructs exactly, and the immutable evidence is
committed regardless of outcome.

### 6. Decide once

Evaluate all 12 Decision 0007 criteria separately. If any criterion fails, preserve the result,
keep Item 9 experimental, and end algorithmic remediation. If every criterion passes, sign a
replacement declaration and run exactly one replacement matrix without another source change:

```text
pixi run -e bayes bash autoresearch-common-utility.sh replacement
```

Gate: only a complete development pass authorizes the replacement.

### 7. Verify a passing replacement

If the replacement is authorized and passes, reconstruct it from raw records. Then run lint,
default tests, Bayesian tests, Release A reconstruction, Item 8 reconstruction, every Item 9
reconstruction, Waterology constraints, whitespace checks, signed-commit verification, and a fresh
signed-archive review at one revision.

Gate: every repository check and scientific criterion passes at one signed revision. Only then may
Item 9 become complete and Item 10 planning begin.

## Experiment limit and stop conditions

This proposal permits at most one development matrix and one conditional replacement matrix. It
permits no benchmark-seed preflight. A failed development matrix ends Item 9 remediation rather
than opening another incremental correction.

- Do not relax, reinterpret, or replace a Decision 0007 criterion.
- Do not omit, edit, or overwrite adverse evidence.
- Do not tune the common utility after observing the development matrix.
- Do not let component observations update the terminal incumbent or recommendation.
- Do not exceed the measured evaluator-cost or action budget.
- Do not use the replacement run after a failed development matrix.
- Do not begin Item 10 until a replacement passes every Item 9 gate.

## Completion gate

The proposed correction is complete when either its development result is preserved as adverse or
both matrices pass and all evidence reconstructs. Only the second outcome completes Item 9 in the
parent plan.
