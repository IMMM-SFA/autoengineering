# Item 8 implementation plan: full-observability function-network BO

_Parent plan: [`bayesian-optimization-plan.md`](../bayesian-optimization-plan.md)_

_Baseline revision: `467e424`_

## Outcome

Add an optional BoTorch backend that fits independent scalar Gaussian process models for declared
component outputs, propagates posterior samples through the function network, and selects only
complete system evaluations. Validate predictive moments, constraint probability, calibration,
deterministic replay, and closed-loop regret against the existing whole-system backend under a
frozen synthetic protocol.

## Current state

Item 7 provides an immutable function-network schema, strict validation against `System`, verified
NPZ traces, scalar ledger observations, and deterministic component training tables. It has no
surrogate model or acquisition policy. `SystemBayesBackend` remains the supported Release A method
and imports BoTorch only from its optional module.

The Item 8 backend will consume only successful system-scope rows reconstructed from Item 7
artifacts. Component actions and partial observation remain outside this item.

## Backend boundary

Add `optimization/full_network_backend.py`. This module alone will import Torch, GPyTorch, and
BoTorch. The base `autoengineering.optimization` import will remain free of Bayesian dependencies.
Users will import `FullNetworkBayesBackend` from its module, matching the existing
`SystemBayesBackend` boundary.

The constructor will require:

- a `StudySpec` with backend `function_network_full`;
- the global `SearchSpace`;
- a validated `FunctionNetworkSpec` and matching `System`;
- minimum initial observation count;
- candidate-pool size;
- posterior sample count;
- GP fitting retry count; and
- deterministic acquisition seed controls.

Validate that the study objective, direction, constraints, and cost unit match the network. Require
the global search-space names and domains to match the qualified component parameters. Reject any
component-scope ledger entry because full observability learns only from complete system actions.

## Component surrogate model

Build one fitted component model group for every executable component with declared scalar outputs.
Fixed source components will use an empirical constant posterior rather than an artificial tunable
input. For every other component:

1. reconstruct successful system-scope training rows from the verified ledger and NPZ artifacts;
2. encode local categorical values by declaration order and local integer or continuous values by
   their declared scale and bounds;
3. append upstream coupling scalar features in topological and declaration order;
4. standardize each upstream feature from the component training rows, using unit scale for a
   constant feature;
5. fit one independent `SingleTaskGP` for each declared scalar output in double precision;
6. use `Standardize` for each output; and
7. apply deterministic, known, or learned noise using the same floor and interpretation as the
   whole-system backend.

The first version assumes conditional activity is determined entirely by fixed global
configuration values. It will omit inactive local parameters from the component input vector and
record the active schema in diagnostics. A training set that mixes incompatible active schemas
will fail explicitly and fall back rather than pad an undeclared input.

Record component name, input feature order, output order, row count, input scaling, fit attempts,
noise mode, warnings, and failures. Do not serialize fitted model objects. Rebuild them from the
ledger during replay.

## Posterior propagation

Expose a deterministic prediction method for tests and reports. For each global configuration:

1. process components in validated topological order;
2. hold local design values fixed across posterior samples;
3. use declared constant source observations directly;
4. construct each downstream input from local values and the sampled upstream scalar outputs;
5. draw component output samples with independent base-normal samples derived from the study seed,
   ledger fingerprint, component, output, configuration, and requested sample count; and
6. select terminal objective and constraint samples from their declared component outputs.

Return immutable terminal samples and a diagnostic record. Use float64 throughout. The same
configuration, ledger bytes, and sample count must return byte-identical arrays from fresh backend
instances. Record the independence assumption: output GPs and component innovations are
independent conditional on sampled upstream values.

## Acquisition and recommendation

Keep the public optimizer protocol unchanged. `suggest` will:

- use the deterministic scrambled Sobol policy until the minimum successful system observations
  exist;
- fit component models from a single ledger snapshot;
- construct a deterministic, globally valid candidate pool from the existing search space;
- propagate posterior samples for every candidate;
- calculate constrained Monte Carlo expected improvement in the declared objective direction;
- rank candidates by acquisition value with canonical configuration tie breaking;
- return only `EvaluationScope.SYSTEM` actions; and
- avoid configurations already present in the ledger or current batch.

The recommendation remains the highest-ranked successful feasible system evaluation. A propagated
prediction must never be returned as an observed recommendation.

Use bounded retries for fitting and candidate scoring. Fall back to the deterministic Sobol policy
for insufficient rows, incompatible schemas, nonfinite posterior values, fitting errors, or an
exhausted candidate pool. Diagnostics must retain every warning and fallback reason with component
context. Unexpected malformed ledger or artifact errors remain visible and must not be converted to
a sampling fallback.

## Numerical validation

Add test-only affine posterior fixtures whose component means and variances have closed forms. With
65,536 fixed posterior samples, require:

- terminal mean absolute error at most `0.02`;
- terminal variance absolute error at most `0.03`;
- terminal constraint probability absolute error at most `0.02`;
- nonnegative finite variance for every case; and
- byte-identical repeated samples from fresh instances.

Add fitted synthetic checks on held-out configurations for one smooth chain and one constrained
branched network. Pool 90 percent posterior intervals across problems and seeds. Require empirical
coverage from `0.75` through `1.00`, finite predictive moments, and constraint-probability Brier
score at most `0.20`. Report each metric separately. Do not substitute one metric for another.

## Preregistered closed-loop comparison

Before running the comparison, add decision record
`docs/decisions/0003-full-network-benchmark.md` with the protocol below and its exact source hashes.
Do not change the problems, seeds, budgets, or thresholds after results exist.

Use two deterministic scalar-output networks:

1. _smooth chain_: two tunable nonlinear components with an interior unconstrained optimum; and
2. _constrained branch_: two upstream tunable components feeding a terminal component with one
   active feasibility threshold.

Compare `FullNetworkBayesBackend` with `SystemBayesBackend`. Both methods receive the same four
scrambled-Sobol initial system observations for each problem and seed. Each closed loop uses ten
complete system evaluations, seeds `0` through `9`, identical evaluator cost, deterministic noise,
and sequential suggestions. Use 64 acquisition candidates and 128 posterior samples for the full
network backend. Keep the existing whole-system constructor defaults except set `min_initial=4`.

Freeze these acceptance criteria:

- 40 of 40 runs complete without invalid configurations, budget overruns, artifact errors, or
  replay differences;
- all actions from both methods have system scope;
- the full-network pooled median final normalized regret is no more than `0.05` above the
  whole-system median;
- on each problem, the full-network median final normalized regret is no more than `0.10` above the
  whole-system median;
- the full-network pooled median normalized regret area is no more than `0.05` above the
  whole-system median;
- unresolved full-network fallbacks affect at most 5 percent of post-warm suggestions overall and
  at most 15 percent on either problem; and
- the separate held-out coverage and Brier criteria above pass.

These are matching criteria, not a claim that the network method must dominate. Preserve a null or
adverse result. If any criterion fails, keep the backend experimental, document the failed metric,
and investigate before Item 9.

## Evidence artifacts

Add `benchmarks/full_network/` with deterministic problem definitions, method adapters, runner,
summary reconstruction, and a command that either creates a new absent result directory or verifies
checked evidence. Publish:

- `raw-records.jsonl` with one row for every system evaluation and acquisition decision;
- `run-summary.csv` with final regret, regret area, scope, replay, and fallback fields;
- `calibration.json` with held-out interval and constraint-probability records;
- `gate.json` with every frozen criterion and provenance;
- `report.md` with problem-specific and pooled results, including null or adverse findings; and
- the decision hash, source hash, clean Git revision, lock information, and package versions.

Exclude timing from scientific replay equality. Keep timing in raw evidence and summaries for
diagnosis. Reconstruct every summary and gate field from raw records during verification.

## Tests

Add focused tests for:

- constructor agreement among study, network, system, cost unit, and search space;
- strict rejection of component-scope observations and unsafe or changed trace artifacts;
- one model per executable component and declared scalar output;
- deterministic local and upstream input encoding;
- affine posterior mean, variance, constraint probability, and sample replay;
- fitted held-out interval coverage and Brier-score reconstruction;
- system-only suggestions, global configuration validity, duplicate exclusion, and batch order;
- deterministic suggestions and diagnostics from fresh instances;
- observed-only recommendations;
- each classified fallback and bounded retry;
- state and identity serialization without model objects;
- base import isolation and concise missing-extra errors; and
- raw benchmark reconstruction, decision and source hashes, frozen criteria, and adverse-result
  retention.

## Ordered implementation

1. Implement strict constructor contracts, component table preparation, feature encoding, and
   diagnostics.
2. Add independent scalar GP fitting and deterministic model-state reconstruction tests.
3. Implement topological posterior propagation and pass the affine numerical checks.
4. Implement global candidate scoring, system-only suggestions, recommendation, and fallbacks.
5. Add closed-loop unit tests with small deterministic networks.
6. Commit decision 0003 with the exact protocol and hashes before any benchmark run.
7. Implement the evidence runner and raw-to-gate reconstruction.
8. Run the held-out calibration and 40-run closed-loop comparison once from a clean signed
   revision.
9. Preserve the evidence regardless of outcome and compare it with the frozen criteria.
10. Update the optimization guide, status record, parent-plan evidence, and Item 8 review.
11. Run lint, default tests, Bayesian tests, the Release A gate, the full-network evidence gate,
    scoped Waterology checks, whitespace checks, and a fresh signed-archive review.

Do not begin Item 9 until the numerical, calibration, replay, and preregistered comparison gates all
pass. Do not add component actions to the controller in this item.

## Completion gate

Item 8 is complete only when component models fit from verified full-observation tables, posterior
propagation passes each separate numerical check, acquisition returns only reproducible system
actions, recommendations remain observed, the frozen calibration and regret criteria pass, raw
evidence reconstructs exactly, optional dependency isolation remains intact, and all repository
gates pass at one signed revision.
