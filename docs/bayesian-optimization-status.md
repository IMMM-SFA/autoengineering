# Bayesian optimization implementation status

_Status date: 2026-09-04_

The branch `codex/bayesian-optimization-implementation` contains the optimization contracts,
reproducible baselines, evaluator integration, whole-system BoTorch backend, sequential budget
controller, hardened recovery layer, and public run configuration. It does not yet provide an
optimization command, benchmark release gate, function-network optimization, or complete
documentation.

## Recovery context

The original worktree and approved implementation plan were stored in a Codex task directory in
OneDrive. That directory disappeared before the worktree was relocated. Git retained the branch
through commit `ac0a02b`, so the committed implementation was recovered in a local worktree.

An independent review of `ac0a02b` identified additional resume identity and provenance checks.
Those fixes existed only as uncommitted changes in the missing worktree and were not recoverable
from Git's saved index. Item 1 of the current plan reimplemented and extended those checks in signed
commit `b3dcdd4`.

## Implementation stages

| Stage | Status | Evidence or remaining work |
| --- | --- | --- |
| 1. Reproducible environment | Complete | `pixi.toml`, `pixi.lock`, and optional `bayes` dependencies provision BoTorch 0.17.2 and SMAC 2.x. |
| 2. Study and search space contracts | Complete | Immutable objectives, constraints, budgets, noise assumptions, and typed mixed or conditional parameters are implemented. |
| 3. Observation records and ledger | Complete | Evaluations use frozen JSON records and an append-only, locked JSONL ledger. |
| 4. Deterministic baselines | Complete | Random and scrambled Sobol policies replay from the declared seed and durable ledger. |
| 5. Evaluator integration | Complete | System evaluation, artifact durability, path validation, resource limits, and failure classification are implemented. |
| 6. Whole-system BoTorch backend | Complete | The backend supports constrained mixed-variable optimization, conditional projection, noise modes, deterministic replay, diagnostics, and bounded fallbacks. |
| 7. Budget controller and provenance | Complete | Canonical identity, exact transition replay, manifest-last commits, and bootstrap, action, and terminal recovery passed independent review. |
| 8. CLI and Release A benchmark gate | In progress | The strict run specification is complete at `ff472f8`. Add the optimization command, end-to-end example, benchmark harness, SMAC comparison adapter, and release criteria. |
| 9. Function-network representation | Not implemented | Represent component functions, couplings, observations, costs, and graph evaluation scopes. |
| 10. Full-observability function-network BO | Not implemented | Fit component surrogates and propagate intermediate observations through the system graph. |
| 11. Partial-observability function-network BO | Not implemented | Select the configuration and component evaluation using cost-aware value of information or knowledge gradient methods. |
| 12. Documentation and research provenance | In progress | This status record and item 1 and 2 reviews exist. The API, CLI, examples, assumptions, limitations, benchmark evidence, and literature correspondence remain incomplete. |

## Completed plan items

### Item 1: recovery and durable identity

Each study now binds the study specification, search space and encoding, backend constructor
identity, in-directory ledger path and bytes, input hashes, seed, and original start timestamp.
Bootstrap, action, and terminal control records protect every durable transition. Recovery validates
and replays uncommitted changes before writing, commits the manifest last, and preserves terminal
state across clean resumes. Optimizer backends use a declared read-only ledger interface during
replay.

The independent review in [`reviews/01-recovery-review.md`](reviews/01-recovery-review.md) found no
remaining implementation defect. Its focused checks passed with 119 tests and 21 skips in the
default environment, and 120 tests in the Bayesian environment.

### Item 2: public run configuration

Signed implementation commit `ff472f8` adds strict typed dictionary and YAML serialization for
search spaces and parameters. `OptimizationRunSpec` combines the study, search space, policy,
evaluator entry point, declared inputs, target, and invocation limit. It resolves local inputs
relative to the run file, rejects duplicate YAML keys and path escapes, isolates local evaluator
imports, and hashes only the matching run file and explicitly named inputs.

The independent review in
[`reviews/02-run-configuration-review.md`](reviews/02-run-configuration-review.md) found no remaining
implementation defect after six findings were fixed. Its final focused check passed 69 tests, lint,
and the base import dependency probe.

## Work required for Release A

Release A is whole-system Bayesian optimization. It treats one execution of the complete model
chain as the expensive observation. It does not require function-network or partial-observation
methods.

### Add the CLI and example

Add an `optimize` command that uses the shared run specification to start or resume a study, select
a policy, enforce a budget, and write durable recommendation and provenance artifacts. At least one
example should run the complete workflow from a declared system and search space.

### Implement the benchmark release gate

The approved plan calls for five benchmark problems and 30 seeds per method. The comparison set is:

- fixed candidate order;
- random search;
- scrambled Sobol search;
- SMAC; and
- the whole-system BoTorch backend.

The benchmark should compare feasible regret or objective quality against evaluator cost. It
should also record constraint violations, failures, optimizer overhead, and replay consistency.
SMAC is provisioned as a dependency but no SMAC adapter or shared benchmark harness exists.

### Complete documentation and review

Update `README.md`, the Python API reference, CLI reference, examples, and the auto-engineer agent
prompt. Explain the optional dependency boundary and distinguish whole-system BO from the later
multi-model research layer. Record limitations for categorical enumeration, sequential execution,
noise assumptions, and acquisition fallback behavior.

Run an independent Release A review after the controller, CLI, example, and benchmark work. Then
run lint, the default and Bayesian test environments, and the benchmark gate before integration.

## Research layer after Release A

The current `SystemBayesBackend` models the complete chain as one black-box function. It cannot
yet use intermediate component outputs or decide which subsystem to query. Stages 9 through 11
would add that capability.

The research sequence should start with a graph representation that separates design variables,
coupling variables, component outputs, observation availability, and evaluation cost. A
full-observability backend can then test whether component surrogates improve efficiency when all
intermediate outputs are available. Partial-observability experiments should follow only after the
full-observability representation and benchmarks are stable.

This separation matches the background review in
`background_research/multi-model-system-optimization.md`: whole-system BO, multi-fidelity BO, and
multi-model or function-network BO solve related but distinct problems. Asynchronous scheduling
and multi-fidelity evaluation remain outside Release A.

## Verification evidence

The latest post-review gate was verified on 2026-09-04 at signed item 2 commit `ff472f8`.

| Check | Result |
| --- | --- |
| `pixi run test` | 305 passed, 21 skipped |
| `pixi run -e bayes test-bayes` | 326 passed, 2 dependency warnings |
| `pixi run lint` | Passed |
| `git diff --check` | Passed |
| Waterology constraints | 7 of 7 passed |

The Bayesian warnings are Torch JIT deprecation notices from dependencies.

## Integration state

The implementation remains isolated on `codex/bayesian-optimization-implementation`. Integration
into `main` should wait until all Release A items pass. Function-network work begins only after the
Release A recovery, replay, and benchmark gates pass.
