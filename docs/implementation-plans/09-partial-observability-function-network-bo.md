# Item 9 implementation plan: partial-observability function-network BO

_Parent plan: [`bayesian-optimization-plan.md`](../bayesian-optimization-plan.md)_

_Baseline revision: `22343c9`_

## Outcome

Add a research backend that chooses either a complete system evaluation or one declared component
evaluation. Rank component observations by a finite-pool, one-step value of information divided by
their predicted evaluator cost. Preserve exact parent-artifact lineage, mixed-scope recovery,
observed-only recommendations, and the Release A system-only behavior.

## Current state

Item 8 provides calibrated independent component Gaussian processes, deterministic posterior
propagation, constrained expected improvement over complete configurations, and a passing
full-observability comparison. Item 7 already evaluates permitted component actions and reconstructs
their verified NPZ traces into component training rows.

Three boundaries still enforce system-only optimization:

- `_BaselineBackend._next_index_and_observed` rejects component ledger rows;
- `OptimizationStudy.ask` and `_validate_entries` reject component actions; and
- `FullNetworkBayesBackend` fits only system-scope rows and proposes only complete configurations.

`FunctionNetworkEvaluator` can execute a component action when the caller supplies earlier parent
artifact references. Its context is immutable, so a durable study also needs a ledger-backed
resolver that rebuilds those references after each commit and after process recovery.

## Scope and retained limits

The first partial backend keeps the Item 8 assumptions: an acyclic function network, declared scalar
surrogate outputs, independent output Gaussian processes, independent component innovations, one
sequential action at a time, and no safety constraints. It does not add batch scheduling,
multi-fidelity controls, functional-output models, correlated output models, feedback loops, or
automatic source-data acquisition.

Component actions will use upstream arrays from one earlier successful system trace. They may vary
only the selected component's local parameters. Chaining a component artifact directly into a
later component action is deferred because it requires a separate policy for compatible partial
state assembly. This limit keeps the candidate lineage explicit and prevents construction of a
surrogate-only system result.

## Scoped backend and controller contract

Add a narrow protocol used only when `StudySpec.backend` is `function_network_partial`. The partial
backend will provide methods to:

- validate every mixed-scope ledger action and its configuration;
- validate a proposed action against the current ledger and earlier parent artifacts;
- estimate the proposed action cost from its scope and component;
- report the minimum remaining affordable action cost; and
- report a marginal-value stop reason after a model-based scoring pass.

Keep `OptimizerBackend` unchanged so existing system backends and test doubles retain their public
contract. `OptimizationStudy` will require the scoped methods only for partial mode. System mode and
full-observability mode will continue to reject component actions.

For a system action, validate the complete global `SearchSpace`. For a component action, require the
selected component to permit component scope, accept exactly its active qualified local parameters,
and require a parent artifact from an earlier successful system action when it has upstream
couplings. Reject foreign parameters, future or failed parents, duplicate parent IDs, and a parent
trace that lacks any direct upstream port.

Extend the controller cost check in partial mode:

1. sum measured cost over every committed action, regardless of scope;
2. estimate system cost as the larger of the sum of declared component costs and the 90th
   percentile of prior successful system costs;
3. estimate component cost as the larger of its declared cost and the 90th percentile of prior
   successful costs for that component;
4. filter unaffordable actions inside the backend before selection; and
5. reject a backend result whose estimated cost exceeds the remaining budget before writing a
   pending action.

Add `marginal_value_below_cost` as a terminal stop reason. A partial backend may use it only after a
successful feasible system recommendation exists. The configured minimum value per cost and all
cost-estimation settings must be part of backend identity and replay.

The existing pending-action record already serializes scope, component, local configuration, parent
IDs, seed, and result. Reuse that transition format. Extend recovery tests to prove component actions
survive interruption before evaluation, after result persistence, after ledger append, and before
manifest replacement without duplicate work.

## Ledger-backed parent artifacts

Add a callable evaluator adapter beside `FunctionNetworkEvaluator`. Before each component
evaluation it will scan the committed ledger in order, resolve relative artifact paths against the
ledger directory, require unique IDs, and construct `ParentArtifactReference` records only from
earlier successful results. The existing runner will re-read the selected bytes, confirm SHA-256,
and enforce NPZ resource limits before invoking component code.

The adapter must not mutate the ledger or copy arrays into JSON. A resumed process with the same
ledger bytes must reconstruct the same parent registry. Changed, missing, symlinked, oversized, or
unsafe traces remain explicit failures and never become a sampling fallback.

## Mixed-scope component models

Refactor only the reusable seams in `FullNetworkBayesBackend`:

- check `spec.backend` against the concrete backend name;
- select training rows through an overridable scope hook; and
- expose deterministic fit and propagation helpers without changing Item 8 behavior.

Add `PartialNetworkBayesBackend` in its own optional-dependency module. It will fit each component
from all compatible successful system and component rows reconstructed from verified artifacts.
Source constants remain system-derived. A component model must have the configured minimum row
count and one compatible active feature schema. Missing component rows, incompatible schemas,
nonfinite values, fit errors, and classified numerical failures produce explicit diagnostics. The
backend may request system warm starts when component models are not ready, but it must not discard
valid component observations.

Duplicate component input rows will be aggregated before fitting. Measured costs remain action
provenance and will not be summed across the component rows reconstructed from one system action.

## Candidate actions

Build deterministic finite pools from the study seed and ledger fingerprint:

- complete system configurations from the global Sobol pool;
- eligible component names in network topological order;
- local configurations projected from the same global Sobol points; and
- earlier successful system artifacts in ledger order that contain every direct upstream input for
  the selected component.

A component candidate is the tuple `(component, local configuration, parent artifact ID)`. Source
components and outputs not observable at component scope are ineligible. Exclude exact prior action
tuples and duplicates within the proposed batch. Keep system and component action IDs in one
monotone `eval-NNNNNN` sequence.

Use complete system actions for the initial warm observations. Also set a configurable maximum
component-action streak. Once reached, the next affordable action must be a system action. This
ensures the ledger continues to contain observed terminal outcomes and prevents a surrogate-only
recommendation.

## One-step value of information

Use the knowledge-gradient definition as a one-step preposterior value calculation. For data `D`,
an observed incumbent `f_best`, and a fixed complete-system decision pool `X`, define

```text
V(D) = max over x in X of E[max(sign * (f(x) - f_best), 0) * 1(feasible) | D].
```

The expectation is the same constrained Monte Carlo improvement used by Item 8. For a component
candidate `a` with possible scalar observation vector `z`, define

```text
VoI(a) = E[V(D union {(a, z)}) | D, a] - V(D).
```

Approximate the outer expectation with a fixed number of deterministic posterior fantasies. For
each fantasy, condition only the selected component's fitted output models with BoTorch's exact
Gaussian conditioning while holding fitted hyperparameters fixed. Propagate the conditioned network
over the same decision pool and posterior sample seeds. Clamp only negative Monte Carlo roundoff to
zero. Record the raw difference, Monte Carlo standard error, fantasy count, decision-pool size, and
all seeds.

Score a component action as `VoI / predicted component cost`. Score a system action as constrained
expected improvement at that configuration divided by predicted system cost. Select the greatest
finite score with canonical scope, component, parent, and configuration tie breaking. A score is a
decision aid, not an observed result.

The implementation follows the one-step knowledge-gradient utility of Frazier, Powell, and Dayanik
(2008), <https://doi.org/10.1137/070693424>. The adaptation from alternative measurements to
component observations and the finite-pool Monte Carlo approximation are repository-specific and
will be labeled as such.

## Marginal value stop rule

Expose `minimum_value_per_cost` as a nonnegative constructor setting. After warm start and only when
an observed feasible system recommendation exists, stop when every affordable system and component
candidate has an upper confidence bound on value per cost at or below this threshold. Use
`estimated value + 1.96 * Monte Carlo standard error` for the bound. A zero threshold disables
economic early stopping except when all estimated values and uncertainty are zero.

Distinguish this stop from exhausted search space and insufficient remaining budget. Record the
threshold, maximum bound, selected candidate class, and cost estimates in diagnostics and durable
backend state.

## Baselines

Add two benchmark-only mixed-scope policies that share candidate validation and cost estimates:

1. a deterministic random selector over affordable system and component candidates; and
2. a cheapest-informative selector that ranks eligible component observations by propagated
   terminal variance contribution divided by predicted cost, with the same system refresh rule.

Both baselines must keep observed-only recommendations and exact action replay. Do not present them
as equivalent to knowledge gradient.

## Preregistered validation

Before any full comparison, add decision 0007 with source hashes and a frozen synthetic protocol.
Use two deterministic networks:

1. a chain where a cheap upstream component controls most terminal uncertainty while the terminal
   component is expensive; and
2. a branch where one cheap branch is informative near the feasibility boundary and the other is
   low value.

Compare the Item 8 system-only full-network backend, partial value of information, random component
selection, and cheapest-informative selection. Give all methods identical complete-system warm
observations, total evaluator-cost budgets, analytic truth, and seed mapping. Count actual component
and system costs rather than evaluation count.

Freeze criteria for:

- complete runs with exact raw reconstruction and no invalid lineage or budget overrun;
- byte-identical action replay from fresh backend and evaluator instances;
- selection of the controlled informative component more often than the low-value component;
- at least one post-warm complete system evaluation and an observed feasible recommendation in
  every run;
- partial value of information median final normalized regret and regret area per evaluator cost no
  worse than the system-only method by declared tolerances;
- partial value of information regret area lower than the random component baseline by a declared
  margin on at least one problem and no worse on the other;
- all component cost estimates at or above realized cost, or an explicit documented exceedance;
- bounded fitting, scoring, and system-refresh fallbacks; and
- exact separation of terminal observations from component-only observations.

Choose and record numeric tolerances before the full seed matrix. Retain null or adverse results. If
the criteria fail, keep the partial backend experimental and do not start Item 10.

## Evidence artifacts

Add `benchmarks/partial_network/` with deterministic problems, method adapters, a runner, raw audit,
summary reconstruction, and atomic create-or-verify behavior. Publish raw JSONL actions and results,
run summaries, component-selection summaries, value and cost diagnostics, `gate.json`, and a concise
report. Exclude timing from replay equality but retain it for diagnosis. Bind every derived value to
raw records, decision 0007, source hashes, the clean signed execution revision, lock files, and
package versions.

## Tests

Add focused tests for:

- partial mode as the only controller mode that accepts component actions;
- local configuration validation and monotone IDs across mixed scopes;
- future, failed, duplicate, changed, missing, symlinked, or incompatible parent artifacts;
- dynamic parent-registry reconstruction after a fresh process starts;
- mixed-scope component table fitting without duplicated system costs;
- deterministic candidate pools, fantasy observations, conditioned predictions, values, scores,
  and tie breaking;
- analytic one-step Gaussian value on a finite fixture;
- cost estimates, affordability filtering, component streaks, and the marginal-value stop;
- recovery at every component-action transition boundary;
- observed-only recommendations when component results outnumber system results;
- every fallback and explicit unsupported observation pattern;
- optional dependency isolation and stable identity without fitted objects;
- both mixed-scope baselines; and
- raw benchmark reconstruction, decision and source hashes, frozen criteria, and adverse-result
  retention.

## Ordered implementation

1. Add scoped backend validation and cost hooks, then permit component actions only in partial mode.
2. Add the ledger-backed evaluator adapter and lineage regression tests.
3. Refactor the Item 8 backend seams and fit mixed-scope component tables without changing Item 8
   replay or evidence.
4. Implement deterministic system, component, parent-artifact, and decision pools.
5. Implement exact Gaussian fantasy conditioning, one-step value of information, cost-aware ranking,
   diagnostics, and the marginal-value stop rule.
6. Add the random and cheapest-informative mixed-scope baselines.
7. Add small closed-loop and recovery tests with controlled informative components and costs.
8. Commit decision 0007 with the exact protocol, numeric criteria, and source hashes before the full
   comparison.
9. Implement and run the partial-network evidence package once from a clean signed revision.
10. Preserve the evidence regardless of outcome and compare every frozen criterion separately.
11. Update the status, optimization guide, parent plan, and Item 9 review.
12. Run lint, default tests, Bayesian tests, Release A reconstruction, Item 8 reconstruction, Item 9
    reconstruction, scoped Waterology checks, whitespace checks, signed-commit verification, and a
    fresh signed-archive review.

## Stop conditions

- Do not let component results become terminal objective or constraint observations.
- Do not infer upstream arrays from surrogate means when an action requires a parent artifact.
- Do not use future, failed, changed, or unverified artifacts.
- Do not spend beyond the remaining measured evaluator-cost budget.
- Do not relax Item 8 gates or change its checked evidence.
- Do not begin Item 10 unless the Item 9 lineage, replay, cost, recommendation, and preregistered
  comparison gates all pass.

## Completion gate

Item 9 is complete only when partial mode alone can durably execute mixed-scope actions, every
component observation has verified earlier system lineage, cost-aware one-step value of information
and both baselines replay exactly, total measured cost stays within budget, final recommendations
remain observed complete-system results, the frozen synthetic criteria pass, all raw evidence
reconstructs exactly, and every repository gate passes at one signed revision.
