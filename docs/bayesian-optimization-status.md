# Bayesian optimization implementation status

_Status date: 2026-09-04_

The branch `codex/bayesian-optimization-implementation` contains the optimization contracts,
reproducible baselines, evaluator integration, whole-system BoTorch backend, sequential budget
controller, hardened recovery layer, public run configuration, command, example, approved Release
A benchmark gate, and complete Release A documentation. It does not yet provide function-network
Bayesian optimization.

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
| 8. CLI and Release A benchmark gate | Complete | The run specification, command, example, SMAC comparison, raw scientific audit, and frozen release criteria pass. |
| 9. Function-network representation | Complete | Immutable functions, local parameters, couplings, scalar observations, costs, scopes, verified NPZ traces, and deterministic training-table replay are implemented. |
| 10. Full-observability function-network BO | Not implemented | Fit component surrogates and propagate intermediate observations through the system graph. |
| 11. Partial-observability function-network BO | Not implemented | Select the configuration and component evaluation using cost-aware value of information or knowledge gradient methods. |
| 12. Documentation and research provenance | In progress | Release A API, CLI, assumptions, limitations, examples, and benchmark interpretation are complete. Function-network literature correspondence remains for item 10. |

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

### Item 3: public optimization command

Signed implementation commit `4f6034f` adds `autoengineering optimize` for new and resumed random,
Sobol, and whole-system BoTorch studies. Configuration and input validation precede durable state
creation. Resume intent, symlink boundaries, optional dependencies, invocation limits, evaluator
failures, and terminal reasons have explicit behavior. Text and JSON summaries use one locked
controller snapshot, including the number of evaluations completed by that invocation.

The independent review in
[`reviews/03-optimize-command-review.md`](reviews/03-optimize-command-review.md) found no remaining
implementation defect after its findings were fixed. Its final focused checks passed 178 tests with
22 skips in the default environment and 92 tests with one skip in the Bayesian environment.

### Item 4: self-contained optimization example

Signed implementation commit `5a257d0` adds a deterministic three-component optimization chain
with categorical, continuous, integer, and conditional parameters. It has an absolute-bias
constraint, a controlled model-failure region, and a unique analytic feasible optimum. The checked
files include local input data, the seeded Sobol result, bounded start and resume commands, and
artifact inspection instructions.

The independent review in
[`reviews/04-self-contained-example-review.md`](reviews/04-self-contained-example-review.md) found no
remaining implementation defect. A public CLI probe matched the expected result and all four input
hashes. Two fresh runs produced byte-identical ledgers and recommendation files.

### Item 5: Release A benchmark gate

Decision 0001 freezes five problems, five methods, 30 seeds, 10 evaluations per run, and the
release thresholds. Decision 0002 records evidence corrections found by independent review without
changing those definitions. The corrected implementation through `c38d6ca` produced 7,500 raw
evaluation records and 750 complete runs with no run errors, invalid configurations, or budget
overruns.

All 600 native runs replay exactly, all 150 SMAC runs complete, and the raw scientific audit reports
zero issues. BoTorch met every pooled and problem-specific regret criterion. Three of 750 post-warm
suggestions used unresolved fallbacks, below the aggregate and run-specific limits. The independent
review in [`reviews/05-release-a-benchmark-review.md`](reviews/05-release-a-benchmark-review.md)
found no remaining implementation defect.

### Item 6: Release A documentation and review

Signed revision `6661004` adds the optimization guide, current README and agent entry points, a
complete example index, and structural documentation tests. Independent review corrected public
imports, commands, package extras, path semantics, noise wording, and example network claims.

Fresh Git archives passed on macOS 26.5 ARM and Ubuntu 24.04 x86-64 with the same locked Python,
Ruff, BoTorch, SMAC, and Torch versions. The Linux gate found and fixed a cross-platform Ruff lock
difference, floating-point reconstruction at about 1e-16, and a test fixture that inherited the
host umask. The [item 6 review](reviews/06-release-a-documentation-review.md) records the exact
revisions, corrections, and platform results.

### Item 7: function-network representation

Signed evidence revision `1eccf3c` adds the immutable function-network schema without changing the
core `System` classes. It validates components, entry points, local parameter domains, ports,
couplings, scalar reducers, observation scopes, costs, terminal outcomes, and DAG order. System and
component actions publish arrays to verified NPZ traces and scalar values to the ledger.

Fresh ledger readers reconstruct equal component training tables from current and parent artifact
hashes. Review corrected an import cycle, incomplete parameter validation, missing scalar coupling
requirements, and incorrect inference of component inputs when source arrays override parent
artifacts. The [item 7 review](reviews/07-function-network-representation-review.md) records the
contracts, corrections, evidence, and retained limits.

## Work required for Release A

Release A is whole-system Bayesian optimization. It treats one execution of the complete model
chain as the expensive observation. It does not require function-network or partial-observation
methods.

### CLI and example

The `optimize` command and its self-contained checked example are complete.

### Benchmark release gate

The Release A benchmark gate is complete. Its raw records, summary, report, decisions, and machine
gate are checked under `benchmarks/release_a/results/` and `docs/decisions/`.

### Documentation and review

The optimization guide, Python and CLI entry points, example index, agent instructions, independent
review, and two-platform archive gate are complete.

## Research layer after Release A

The current `SystemBayesBackend` models the complete chain as one black-box function. The new
function-network representation can record intermediate component outputs and evaluate a declared
component, but it does not fit component surrogates or decide which subsystem to query. Stages 10
and 11 remain to add those methods.

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

The latest Item 7 worktree gate was verified on 2026-09-04 at signed evidence revision `1eccf3c`.
The checked benchmark gate records clean execution revision `63cbdca`, whose source hash also
applies to `1eccf3c` because the latter changes only checked benchmark results.

| Check | Result |
| --- | --- |
| `pixi run test` | 404 passed, 23 skipped |
| `pixi run -e bayes test-bayes` | 426 passed, 1 skipped, 5 dependency warnings |
| `pixi run lint` | Passed |
| `git diff --check` | Passed |
| `pixi run -e bayes benchmark-release-a` | Passed, including raw reconstruction |
| Optional dependency isolation | Passed, including both public import orders |
| Function-network focused checks | 107 passed |
| Waterology constraints | 7 of 7 passed on the touched documentation |

The Bayesian warnings are Torch, Pyro, SMAC, and ConfigSpace notices from dependencies.

## Integration state

The implementation remains isolated on `codex/bayesian-optimization-implementation`. All Release A
items pass, but this task continues through the research layer before integration. No push,
publication, or merge has been performed.
