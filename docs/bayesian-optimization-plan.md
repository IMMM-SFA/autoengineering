# Bayesian optimization implementation plan

_Status: In progress; items 1 through 4 complete_

_Branch point: `262a984`_

This plan completes the Bayesian optimization layer in two milestones. Release A finishes the
whole-system optimizer and makes it safe to use from the command line. The research milestone then
adds function-network optimization. Release A does not depend on the function-network work and
should be integrated separately.

The current implementation already provides immutable study specifications, typed search spaces,
an append-only observation ledger, deterministic random and Sobol policies, reproducible model
evaluation, a constrained BoTorch backend, provenance artifacts, and a sequential budget
controller. The current status and verification evidence are recorded in
[`bayesian-optimization-status.md`](bayesian-optimization-status.md).

## Scope

Release A covers sequential, single-objective, constrained optimization of a complete feed-forward
model system. Each observation executes the complete system. Random, Sobol, SMAC, and BoTorch
policies share one study contract and evaluator budget.

The research milestone adds component surrogates and component-scoped evaluations. Its first
version remains limited to acyclic systems and scalar surrogate outputs. Array and time-series
outputs must declare scalar features before surrogate fitting.

The following capabilities remain outside this plan:

- asynchronous or batch evaluation;
- multi-fidelity optimization;
- feedback cycles or multidisciplinary inner solves;
- safety constraints;
- multi-objective Pareto optimization; and
- automatic representation learning for functional outputs.

## Implementation order

Complete the work in this order:

1. harden recovery and durable identity;
2. define the public run configuration;
3. add the `optimize` command;
4. add a self-contained example;
5. implement the Release A benchmark gate;
6. document and review Release A;
7. add the function-network representation;
8. implement full-observability function-network BO;
9. implement partial-observability function-network BO; and
10. complete the research comparison and documentation.

Do not begin function-network implementation until Release A passes its recovery, replay, and
benchmark gates.

## 1. Harden recovery and durable identity

The `OptimizationStudy` constructor currently obtains a start timestamp from an existing manifest,
reconciles pending work, and rewrites artifacts. It must prove that existing state belongs to the
requested study before changing any durable file.

### Implementation

- Add an immutable run identity with:
  - the study specification and its canonical hash;
  - the search-space representation and its canonical hash;
  - the backend name and stable constructor configuration;
  - the ledger path and committed snapshot hash;
  - input artifact hashes;
  - the study seed; and
  - the original start timestamp.
- Give optimizer backends a stable identity representation separate from mutable diagnostics and
  fitted state. Do not use `state_dict()` as constructor identity.
- Bind the ledger to the study directory. Reject a ledger path that points outside the directory or
  differs from the path recorded in the manifest.
- Validate the manifest, backend snapshot, pending record, and ledger under the study lock before
  calling `_reconcile_pending()` or `_update_artifacts()`.
- Add the run identity hash and original start timestamp to pending records.
- Treat the manifest as the commit marker. Write the backend snapshot, recommendation, and report
  first, then atomically write the manifest last.
- Distinguish the following recovery states:
  - new study with no durable control artifacts and an empty ledger;
  - clean study whose ledger matches the committed manifest;
  - interrupted evaluation with an uncommitted pending action;
  - interrupted result commit where the pending result is the only ledger extension; and
  - corrupt or incompatible state.
- Permit repair only when the pending record proves the exact transition from the committed ledger
  snapshot. Otherwise raise `StudyRecoveryError` without changing existing files.
- Preserve the original start timestamp across every valid resume. Record a new end timestamp only
  when the controller reaches a terminal stop reason.

### Tests

Add regression tests for:

- study, seed, search-space, encoding, backend, backend configuration, ledger path, input hash, and
  start timestamp mismatches;
- missing, symlinked, malformed, or schema-incompatible control artifacts;
- ledger changes with no matching pending record;
- interruption before evaluation, after result persistence, after ledger append, and during
  replaceable artifact writes;
- a valid resume that preserves study identity, recommendation, and prior ledger bytes; and
- recovery failure that leaves every existing artifact unchanged.

### Completion gate

A compatible invocation resumes exactly once and retains the original identity. An incompatible
invocation raises `StudyRecoveryError` before any write. Replaying the same completed ledger with a
fresh process produces the same recommendation and canonical artifacts, excluding an explicitly
recorded end timestamp.

## 2. Define the public run configuration

The Python API and CLI need one serializable contract. The search space currently has an internal
provenance serializer but no public deserializer.

### Implementation

- Add canonical `to_dict()`, `from_dict()`, `to_yaml()`, and `from_yaml()` methods for
  `SearchSpace` and its parameter types.
- Add an immutable `OptimizationRunSpec` that contains:
  - `StudySpec`;
  - `SearchSpace`;
  - policy name and policy options;
  - evaluator factory entry point;
  - declared input files; and
  - optional target value and invocation evaluation limit.
- Keep the policy name separate from `StudySpec.backend`. The existing field identifies the
  whole-system or function-network architecture, while the policy selects random, Sobol, SMAC, or
  BoTorch behavior.
- Reject unknown fields and duplicate parameter names. Preserve scalar types and declaration order.
- Resolve paths relative to the run specification file.
- Hash the system YAML, run specification, evaluator source, and every declared input before
  starting the controller. Store those hashes as input artifact provenance.
- Do not collect environment variables or undeclared files as implicit inputs.

### Tests

- Round-trip all parameter types, scales, conditions, policies, and scalar category types.
- Reject unknown keys, invalid policy options, unsafe paths, and missing declared inputs.
- Confirm that semantically different specifications produce different hashes.
- Confirm that repeated serialization is byte stable.

### Completion gate

The CLI and Python API can load the same run specification. Its canonical form and input hashes are
stable across fresh processes.

## 3. Add the `optimize` command

Add a command that starts or resumes one durable optimization study:

```text
autoengineering optimize system.yaml optimization.yaml \
  --workdir outputs/study-name \
  --max-new-evaluations 10

autoengineering optimize system.yaml optimization.yaml \
  --workdir outputs/study-name \
  --resume
```

### Implementation

- Register random, scrambled Sobol, and whole-system BoTorch policies through a small policy
  factory. Keep SMAC in the benchmark package unless it proves suitable as a supported policy.
- Require `--resume` when the destination already contains study state. Refuse accidental
  replacement.
- Reject `--resume` when no study state exists.
- Allow one invocation to stop after a bounded number of new evaluations without marking the study
  terminal.
- Preserve budget, target, finite-space, and insufficient-balance stop reasons.
- Print the work directory, stop state, evaluation count, evaluator cost, and recommended
  configuration. Provide JSON output for automation.
- Produce a concise dependency error when BoTorch is requested outside the Bayesian environment.
- Keep the base `autoengineering.optimization` import free of Torch, BoTorch, GPyTorch, and SMAC.

### Tests

Use Click's test runner to cover new runs, bounded invocations, valid resume, incompatible resume,
budget exhaustion, target attainment, evaluator failure, missing dependencies, and text or JSON
output.

### Completion gate

A CLI study can be stopped and resumed without changing its prior ledger or identity. The same run
specification and seed produce the same action sequence and recommendation.

## 4. Add a self-contained example

Create `examples/optimization_chain/` with a small feed-forward system that has:

- continuous, integer, categorical, and conditional parameters;
- one scientific constraint;
- one controlled model-failure region;
- a known feasible optimum; and
- no network or external data dependency.

Include the system YAML, optimization YAML, evaluator module, input data, expected result, and a
README showing start, bounded stop, resume, and artifact inspection. Keep execution short enough for
the normal test suite.

The Leaf River example may provide an additional applied demonstration, but it must not become a
release gate because its first run downloads data.

### Completion gate

A clean checkout can run the example through the CLI. Two fresh runs with the same seed produce the
same ledger and recommendation.

## 5. Implement the Release A benchmark gate

The original plan specified five problems and 30 seeds per method, but its problem definitions and
numeric criteria were lost. Record the replacement definitions and pass criteria in a short decision
document before running comparative experiments. Do not select thresholds after inspecting the full
results.

### Problem suite

Implement five problems that exercise different supported contracts:

1. a smooth continuous problem;
2. a constrained continuous problem with a nontrivial feasible region;
3. a mixed continuous, integer, and categorical problem;
4. a conditional hierarchical space with family-specific parameters; and
5. a feed-forward model chain with noise, constraints, failures, and heterogeneous evaluator costs.

Each problem must declare its optimum or a reproducible high-accuracy reference solution, evaluator
cost, budget, constraints, and deterministic seed mapping.

### Methods

Compare:

- fixed candidate order;
- random search;
- scrambled Sobol search;
- SMAC; and
- `SystemBayesBackend`.

Use common seeds, common initial observations where the method permits them, and the same evaluator
budget. Implement SMAC behind its optional dependency boundary and translate its configurations and
results through the same benchmark problem protocol.

### Measurements

Record the following for every method, problem, and seed:

- normalized feasible regret against cumulative evaluator cost;
- final feasible regret;
- cost to first feasible configuration;
- scientific constraint violations;
- model, timeout, and infrastructure failures;
- optimizer overhead;
- fallback events; and
- replay consistency.

Write raw JSONL records, a summary CSV, and a Markdown report. Do not retain only aggregate plots.

### Release criteria

The preregistered gate must include:

- zero invalid configurations;
- zero evaluator-budget overruns;
- exact replay for the native backends;
- successful completion for all expected problem, method, and seed combinations;
- explicit limits on unresolved acquisition fallbacks; and
- numeric feasible-regret criteria against random and Sobol search.

SMAC should serve as an external comparison. A SMAC failure caused by unsupported problem semantics
must be reported, not silently removed from the comparison.

Add a command such as:

```text
pixi run -e bayes benchmark-release-a
```

The command must exit nonzero when a release criterion fails.

### Completion gate

The raw records reproduce the summary, all native methods replay, and the preregistered release
criteria pass at the candidate integration revision.

## 6. Document and review Release A

### Documentation

- Add an optimization guide covering installation, configuration, Python API, CLI, artifacts,
  recovery, and benchmark interpretation.
- Document sequential execution, categorical enumeration limits, noise modes, constraints, and
  acquisition fallbacks.
- Explain the difference between whole-system optimization and the later function-network research
  layer.
- Update the README, CLI reference, example index, and auto-engineer instructions.
- Replace hard-coded test counts in documentation with commands or current generated evidence.

### Verification

Run at the same final revision:

```text
pixi run lint
pixi run test
pixi run -e bayes test-bayes
pixi run -e bayes benchmark-release-a
```

Verify fresh environments on macOS ARM and Linux. Review recovery behavior, optional dependency
isolation, benchmark fairness, raw-to-summary reproducibility, and scientific interpretation.

### Release A stop condition

Do not integrate the branch into `main` until recovery, replay, default tests, Bayesian tests, lint,
and the benchmark gate all pass at the same revision. Keep function-network changes out of the
Release A integration.

## 7. Add the function-network representation

Add an immutable optimization representation without changing the core `System` schema until the
new contract is proven.

### Representation

Define records for:

- component functions and their component names;
- local design parameters;
- coupling inputs and outputs;
- declared scalar surrogate outputs;
- observation availability;
- expected or measured evaluation costs;
- terminal objectives and constraints; and
- permitted system and component evaluation scopes.

Validate the representation against the existing `System` graph. Require unique component and port
names, valid parameter ownership, complete coupling bindings, an acyclic execution order, and
compatible data types and units where those are declared.

Store intermediate arrays in verified NPZ artifacts. Keep artifact identifiers, hashes, scalar
features, outcomes, and costs in the ledger. Do not embed large model output arrays in JSONL.

### Tests

- Round-trip the complete representation through canonical YAML and JSON.
- Reject cycles, unknown components, dangling couplings, duplicate ownership, and incompatible
  observation declarations.
- Reconstruct component training records from verified trace artifacts.
- Confirm that representation imports do not require Bayesian dependencies.

### Completion gate

A function network can be validated, serialized, evaluated, and replayed without a surrogate
backend. The same durable observations reconstruct the same component training tables.

## 8. Implement full-observability function-network BO

The full-observability backend receives declared intermediate observations from every complete
system execution.

### Implementation

- Fit one surrogate for each component using local parameters and upstream coupling values.
- Model only declared scalar outputs in the first version.
- Propagate posterior samples through the network in topological order.
- Derive terminal objective and constraint samples from the propagated system output.
- Optimize an acquisition function over the global configuration while continuing to request only
  system-scoped evaluations.
- Implement `FullNetworkBayesBackend` through the existing optimizer protocol and optional Bayesian
  dependency boundary.
- Record component fit diagnostics, posterior propagation settings, warnings, and fallbacks.

### Validation

- Use synthetic networks whose component functions and propagated uncertainty are known.
- Check posterior mean, variance, constraint probability, and calibration separately before closed
  loop optimization tests.
- Compare full-observability BO with `SystemBayesBackend` under identical complete-system
  observations and evaluator budgets.

### Completion gate

Posterior propagation passes numerical checks, replay is deterministic, and the backend meets
preregistered regret or calibration criteria. If it does not improve or match whole-system BO, keep
it experimental and investigate before partial-observability work.

## 9. Implement partial-observability function-network BO

Partial observability allows the optimizer to choose both a configuration and the component to
evaluate.

### Controller and ledger changes

- Permit component-scoped actions only when the study selects partial function-network mode.
- Estimate remaining evaluator cost by component and scope. Do not use a system-only cost estimate.
- Preserve parent artifact identifiers and verify their hashes before reuse.
- Keep component observations distinct from terminal objective observations.
- Base final recommendations only on successful whole-system evaluations. Never present a surrogate
  prediction as observed system performance.

### Acquisition

- Define the candidate decision as component, local configuration, and required parent artifacts.
- Implement a cost-aware, one-step knowledge-gradient or value-of-information policy.
- Compare expected improvement in the terminal decision with the predicted cost of each component
  evaluation.
- Add a marginal value versus marginal cost stop rule alongside budget and target stopping.
- Provide random and cost-aware component-selection baselines.

### Validation

- Test action lineage, artifact reuse, cost accounting, and crash recovery for component actions.
- Use synthetic networks where the most informative component and relative costs are controlled.
- Check that the policy selects cheaper informative evaluations and still schedules enough complete
  system evaluations to support an observed recommendation.

### Completion gate

The method respects lineage and total budget, produces reproducible actions, and improves terminal
decision quality per evaluator cost under preregistered criteria. Unsupported observation patterns
must fail explicitly.

## 10. Complete the research comparison and documentation

Compare whole-system, full-observability, and partial-observability methods on the same function
network suite. Preserve raw evaluation and acquisition records. Report null or adverse results
without changing the estimand or gate after the run.

Document:

- which algorithms correspond directly to published linked-GP, multi-model BO, knowledge-gradient,
  or value-of-information methods;
- which algorithms are adaptations introduced by this project;
- observation and independence assumptions;
- scalar-output limitations;
- cost-model sensitivity;
- fallback behavior; and
- cases where whole-system BO remains preferable.

Update `bayesian-optimization-status.md` after each accepted gate. Mark individual stages complete
only when their stated tests and evidence exist.

## Integration checkpoints

Use four review checkpoints:

1. _Recovery contract:_ approve durable identity and the recovery state machine before exposing the
   CLI.
2. _Benchmark decision:_ approve problem definitions, estimands, and numeric criteria before the
   30-seed run.
3. _Release A:_ integrate whole-system optimization only after all release gates pass.
4. _Research layer:_ review the function-network representation, full-observability evidence, and
   partial-observability evidence as separate decisions.

Each checkpoint should identify the exact revision, commands, environment lock, raw evidence paths,
and unresolved limitations.
