# Bayesian optimization implementation status

_Status date: 2026-09-04_

The branch `codex/bayesian-optimization-layer` contains the optimization contracts,
reproducible baselines, evaluator integration, whole-system BoTorch backend, and a sequential
budget controller. It does not yet provide a user-facing optimization command, benchmark-based
release gate, function-network optimization, or complete documentation.

## Recovery context

The original worktree and approved implementation plan were stored in a Codex task directory in
OneDrive. That directory disappeared before the worktree was relocated. Git retained the branch
through commit `ac0a02b`, so the committed implementation was recovered in a local worktree.

An independent review of `ac0a02b` identified additional resume-identity and provenance checks.
Those fixes existed only as uncommitted changes in the missing worktree and were not recoverable
from Git's saved index. They must be reimplemented before the controller is considered complete.
This document reconstructs the implementation status from the branch history, source tree, tests,
and prior review record.

## Implementation stages

| Stage | Status | Evidence or remaining work |
| --- | --- | --- |
| 1. Reproducible environment | Complete | `pixi.toml`, `pixi.lock`, and optional `bayes` dependencies provision BoTorch 0.17.2 and SMAC 2.x. |
| 2. Study and search-space contracts | Complete | Immutable objectives, constraints, budgets, noise assumptions, and typed mixed or conditional parameters are implemented. |
| 3. Observation records and ledger | Complete | Evaluations use frozen JSON records and an append-only, locked JSONL ledger. |
| 4. Deterministic baselines | Complete | Random and scrambled Sobol policies replay from the declared seed and durable ledger. |
| 5. Evaluator integration | Complete | System evaluation, artifact durability, path validation, resource limits, and failure classification are implemented. |
| 6. Whole-system BoTorch backend | Complete | The backend supports constrained mixed-variable optimization, conditional projection, noise modes, deterministic replay, diagnostics, and bounded fallbacks. |
| 7. Budget controller and provenance | Needs fixes | The sequential ask/evaluate/tell loop, budget checks, crash recovery, manifest, report, and recommendation artifacts exist. Resume identity must be hardened as described below. |
| 8. CLI and Release A benchmark gate | Not implemented | Add the optimization command, end-to-end examples, benchmark harness, SMAC comparison adapter, and release criteria. |
| 9. Function-network representation | Not implemented | Represent component-level functions, couplings, observations, costs, and graph-aware evaluation scopes. |
| 10. Full-observability function-network BO | Not implemented | Fit component surrogates and propagate intermediate observations through the system graph. |
| 11. Partial-observability function-network BO | Not implemented | Select both the configuration and component evaluation using cost-aware value of information or knowledge gradient methods. |
| 12. Documentation and research provenance | In progress | This status record exists. The API, CLI, examples, assumptions, limitations, benchmark evidence, and literature correspondence still need complete documentation. |

## Work required for Release A

Release A is whole-system Bayesian optimization. It treats one execution of the complete model
chain as the expensive observation. It does not require function-network or partial-observation
methods.

### Restore controller resume checks

Before writing replacement artifacts, a resumed study should verify that existing durable state
belongs to the same:

- study specification and seed;
- search space and encoding;
- backend identity;
- observation ledger;
- input artifact hashes; and
- original start timestamp.

Corrupt or incompatible state should raise `StudyRecoveryError`. The controller should not
silently replace a manifest before completing these checks. Regression tests should cover each
mismatch and confirm that a valid resume preserves study identity.

### Add the CLI and an end-to-end example

Add an `optimize` command that can start or resume a study, select a backend, apply objective and
constraint definitions, enforce a budget, and write the durable recommendation and provenance
artifacts. At least one example should run the complete workflow from a declared system and search
space.

The public API and CLI should expose the same study contract. A CLI run must remain reproducible
from its inputs, seed, environment lock, ledger, and manifest.

### Implement the benchmark release gate

The approved plan called for five benchmark problems and 30 seeds per method. The comparison set
was:

- fixed candidate order;
- random search;
- scrambled Sobol search;
- SMAC; and
- the whole-system BoTorch backend.

The benchmark should compare feasible regret or objective quality against evaluator cost. It
should also record constraint violations, failures, optimizer overhead, and replay consistency.
SMAC is provisioned as a dependency but no SMAC adapter or shared benchmark harness currently
exists. Release criteria and the exact benchmark problem definitions must be restored with the
benchmark implementation because the original plan file was lost.

### Complete documentation and review

Update `README.md`, the Python API reference, CLI reference, examples, and the auto-engineer agent
prompt. Explain the optional dependency boundary and distinguish whole-system BO from the later
multi-model research layer. Record limitations for categorical enumeration, sequential execution,
noise assumptions, and acquisition fallback behavior.

Run an independent review after the controller and benchmark changes. Then run lint, the default
test environment, the Bayesian test environment, and the benchmark gate before integration into
`main`.

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

The recovered branch was verified on 2026-09-04 at `ac0a02b` before this status document was
committed.

| Check | Result |
| --- | --- |
| `pixi run test` | 198 passed, 21 skipped in 34.44 seconds |
| `pixi run -e bayes test-bayes` | 219 passed in 62.29 seconds |
| `pixi run lint` | Passed |

The Bayesian test run emitted three warnings from dependencies: two Torch JIT deprecation warnings
and one Pyro invalid-escape `SyntaxWarning`. The default environment also reported that its cached
environment was created for the `m1` architecture while the verification runner exposed `x86_64`.
The checks completed, and `pixi.toml` plus the lock include both `osx-arm64` and `linux-64`, but a
fresh environment check on each supported platform remains appropriate before release.

## Integration state

The implementation remains isolated on `codex/bayesian-optimization-layer`. Integration into
`main` should wait until the Release A items above are complete. Stages 9 through 11 can remain an
experimental follow-on branch if Release A needs to ship independently.
