# Item 9 review: partial-observability function-network BO

_Review date: 2026-09-04_

_Execution revision: `aebc741`_

_Evidence revision: `45eab5b`_

## Scope

This review covers component-scoped actions, parent artifact recovery, mixed-observation training,
finite-pool value of information, evaluator-cost accounting, observed-only recommendations,
benchmark controls, deterministic replay, and the preregistered evidence. Item 10 is excluded
because Item 9 did not pass its completion gate.

## Partial-observation contract

`PartialNetworkBayesBackend` may propose either a complete system evaluation or one declared
component evaluation. A component action names one earlier successful system artifact as its
parent. The evaluator reconstructs that artifact from the append-only ledger, verifies its digest,
and exposes only the component's direct upstream ports. Component outputs remain separate from
terminal objective and constraint observations.

The controller checks a conservative scope-specific cost before persisting an action. The backend
fits each scalar output only from ledger rows where that output was observed. It recommends only an
observed feasible system result, limits consecutive component actions, and schedules system
refreshes. Its identity and durable state include the candidate pools, cost settings, seeds,
thresholds, and diagnostics needed for replay.

## Acquisition and controls

The research policy uses deterministic Sobol action and decision pools. It computes one-step
Gaussian fantasy updates on the finite pool, estimates terminal decision improvement, divides the
estimate by conservative evaluator cost, and records Monte Carlo error and seed diagnostics. A
marginal-value stop is available only after an observed feasible system recommendation exists.

Two benchmark-only controls use the same action validation and cost estimates. The random control
selects reproducibly from affordable mixed-scope actions. The cheapest-informative control ranks
propagated variance reduction by predicted cost. Neither control is exposed as a supported public
optimization policy.

## Deterministic and recovery checks

Focused tests cover closed-form Gaussian conditioning, deterministic pool and action replay,
lineage and digest checks, conservative costs, observed-only recommendations, component streaks,
and closed-loop behavior. Recovery tests interrupt component actions before evaluation, after
result persistence, after ledger append, and before manifest replacement. A portable replay check
also confirms that artifact storage paths do not affect subsequent action seeds.

Before the full matrix, the focused default environment passed 134 tests with 21 skips. The
Bayesian environment passed 22 focused tests. Waterology constraints passed 7 of 7 checks.

The post-evidence complete default suite exposed an optional-dependency message defect. Importing
the partial backend without Torch raised the dependency's raw exception instead of the documented
Bayesian-extra guidance. Signed commit `15c79ef` wraps that import consistently with the other
Bayesian backends. The correction does not change execution in the Bayesian environment or the
method evaluated at `aebc741`.

## Frozen comparison

Decision 0007 froze two controlled function networks, four methods, five seeds, four shared Sobol
system observations, an evaluator-cost budget of 8, and a limit of 12 actions. The execution
revision was clean and signed. The evidence contains 40 run-end records, 379 evaluations, 219
post-warm acquisition records, 255 system evaluations, and 124 component evaluations. Every
derived file reconstructs from the raw JSONL evidence.

| Criterion | Result | Value or comparison |
| --- | --- | --- |
| Complete matrix under accepted stops | Fail | 9 runs ended with `search_space_exhausted`, an unaccepted stop |
| Raw reconstruction | Pass | 0 issues |
| Action and result replay | Pass | 40 of 40 runs |
| Parent lineage and direct ports | Pass | 124 component actions, 0 issues |
| System refresh and observed recommendation | Pass | 40 of 40 runs |
| Controlled informative branch | Pass | left selected 2 times, right selected 0 times |
| Final regret tolerance | Pass | pooled partial minus full: -0.001439 |
| Regret-area tolerance | Pass | pooled partial minus full: -0.000103 |
| Random component control | Fail | chain improvement 0.004448, required 0.005; branch difference 0 |
| Conservative costs | Pass | 40 of 40 runs |
| Bounded fallbacks | Pass | 0 of 44 scored decisions |
| Terminal observation separation | Pass | 124 component actions, 0 issues |

All runs completed without a run error, nonfinite value, invalid transition, or measured-cost
overrun. Sixteen stopped at the cost budget, ten at the action limit, five at the marginal-value
rule, and nine after exhausting their finite action pools. The last group does not satisfy the
accepted-stop wording in Decision 0007 and remains failed even though the run records are complete.

The value-of-information policy matched the full-network method on pooled final regret and regret
area. Its median regret area improved over random by 0.004448 on the informative chain, missing the
frozen 0.005 margin by 0.000552. The branch medians were equal. This is a scientific miss, not an
evidence reconstruction or execution error.

## Result and stop state

Item 9 is implemented but does not pass its completion gate. The backend therefore remains
experimental. The raw adverse result is retained under `benchmarks/partial_network/results/`, and
the frozen thresholds are unchanged. Item 10 must not begin under the parent plan unless a new,
predeclared investigation resolves the failed gate without relabeling this result.
