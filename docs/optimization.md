# Whole-system optimization

Autoengineering Release A supports sequential optimization of a complete feed-forward model
system. Each proposed configuration runs the whole evaluator once and produces one durable action
and result record. The optimizer does not yet fit separate component surrogates or choose a
component to evaluate.

The no-network [`optimization_chain`](../examples/optimization_chain/README.md) example is the
shortest complete workflow. The checked
[Release A benchmark report](../benchmarks/release_a/results/report.md) tests mixed and conditional
spaces, constraints, noise, model failures, variable costs, replay, and optimizer quality.

## Installation

Install the base environment for random and scrambled Sobol search:

```sh
pixi install
```

Install the Bayesian environment for BoTorch and the SMAC benchmark dependency:

```sh
pixi install -e bayes
```

The project installs its local package in editable mode through `pixi.toml`. No separate install
task is required. Importing `autoengineering.optimization` in the base environment does not import
Torch, BoTorch, GPyTorch, or SMAC. The optional BoTorch module is loaded only when the `botorch`
policy is selected. SMAC remains a benchmark comparator and is not a public optimization policy.

Outside Pixi, use the matching package extras in a Python 3.12 environment:

```sh
python -m pip install -e .
python -m pip install -e '.[bayes]'
python -m pip install -e '.[bayes,benchmark]'
```

The `bayes` extra enables the public BoTorch policy. The `benchmark` extra adds SMAC, so the full
benchmark installation needs both extras.

## Run contract

An optimization invocation needs three paths:

- a system YAML file;
- an optimization YAML file; and
- a new or resumable work directory.

The optimization file is a strict serialization of `OptimizationRunSpec`. Unknown fields are
rejected. See the checked
[`optimization.yaml`](../examples/optimization_chain/optimization.yaml) for a complete file.
Its top-level fields are:

| Field | Meaning |
| --- | --- |
| `schema_version` | Run schema, currently `1.0`. |
| `study` | Objective, scientific constraints, budget, noise mode, architecture, and seed. |
| `search_space` | Ordered categorical, continuous, and integer parameters. |
| `policy` | `random`, `sobol`, or `botorch`. |
| `policy_options` | Integer BoTorch settings; empty for random and Sobol. |
| `evaluator_factory` | A `module:callable` that receives the loaded `System` and returns an evaluator. |
| `input_files` | Files included in run identity and resolved from the optimization file directory. |
| `target_value` | Optional objective value that ends the study once attained. |
| `max_new_evaluations` | Optional invocation limit that can be overridden by the CLI. |

`study.backend` must be `system` in Release A. The policy field is separate: the architecture says
what is modeled, while the policy says how the next complete-system configuration is selected.
The function-network backend names are reserved for the later research layer and are rejected by
the Release A command.

### Paths and loading

The run YAML must be a regular file, not a symbolic link. YAML loading rejects duplicate keys.
Path handling is:

| Input | Resolution base | Validation |
| --- | --- | --- |
| Relative system YAML | Run file directory | Normalized forward-slash path, no parent traversal, symlink components, or nonregular file. |
| Declared `input_files` | Run file directory | Same confinement and file checks as a relative system path. |
| Local evaluator module | Run file directory | Dotted `module:callable` name with no symlinked path component or source. |
| Installed evaluator module | Python environment | Importable `module:callable` with a discoverable regular source file. |
| Work directory | Command working directory | Explicit new or resume intent; no symlinked path component. |

An absolute system path is accepted only when it names a regular nonsymlink file. Relative system,
input, and local evaluator paths cannot escape the run file directory. The run identity hashes the
resolved system, run YAML, evaluator source, and every declared input.

### Search spaces

Parameter declaration order is part of the durable encoding.

- Categorical parameters preserve the scalar type and listed category order.
- Continuous and integer parameters use closed bounds and `linear` or `log` scale.
- A numeric parameter can declare `active_when` conditions on earlier categorical parameters.
- Inactive numeric parameters are omitted from the configuration and use a separate mask in the
  encoded vector.
- Conditional categorical parameters are unsupported.

The controller validates every proposed configuration before evaluation. Small finite spaces can
be enumerated to prove exhaustion. Larger or continuous spaces use bounded duplicate-rejection
scans and stop in the explicit `finite_space_exhausted` terminal state rather than returning an
observed point.

### Objectives, constraints, failures, and cost

Release A has one objective with direction `maximize` or `minimize`. Scientific constraints compare
named result outcomes with `>=` or `<=` thresholds. Safety constraints, multiple objectives, batch
evaluation, and asynchronous evaluation are outside this release.

The evaluator returns `EvaluationResult`. A successful result must contain the objective and every
constraint outcome to train BoTorch. `scientific_infeasible`, `model_failure`, `timeout`, and
`infrastructure_failure` remain explicit ledger states. They are not converted to convenient
objective values. The BoTorch backend excludes non-success results from model fitting, reports the
exclusion counts, and uses its deterministic Sobol fallback when usable data are insufficient.

Every result records a nonnegative evaluator cost in the study's declared unit. The controller
will not start work when its conservative next-cost estimate exceeds the remaining budget. Terminal
states are `max_cost`, `max_evaluations`, `target_attained`, `finite_space_exhausted`, and
`insufficient_remaining_budget`. A bounded invocation that has not reached a terminal state reports
`invocation_limit` and can be resumed.

### Noise modes

`NoiseSpec` has three modes:

- `deterministic` uses the larger of the declared noise floor and float64 machine epsilon;
- `known` requires a standard error for the objective and every constraint outcome in each usable
  successful result; and
- `learned` lets each Gaussian process learn its observation noise.

Exact repeated configurations are aggregated before fitting. Known independent standard errors
are combined for the mean. If a required known standard error is missing, BoTorch records
`known_noise_missing_standard_error` and uses Sobol rather than silently changing the noise model.

## Policies and fallbacks

`random` draws seeded pseudorandom samples without returning an observed configuration. `sobol`
uses a scrambled SciPy Sobol sequence projected onto valid conditional configurations. Both
policies reconstruct their sequence from the immutable study and durable ledger.

`botorch` fits one Gaussian process for the objective and one for each constraint, then uses
constrained log noisy expected improvement. Its optional integer settings and defaults are:

| Option | Default | Purpose |
| --- | ---: | --- |
| `min_initial` | 6 | Usable observations required before fitting. |
| `num_restarts` | 8 | Acquisition optimization restarts. |
| `raw_samples` | 128 | Initial acquisition samples. |
| `max_categorical_assignments` | 128 | Maximum categorical combinations enumerated for acquisition. |
| `candidate_retry_limit` | 3 | Warning, acquisition, or invalid-candidate retries before fallback. |

Categorical combinations are enumerated only up to `max_categorical_assignments`. Exceeding the
limit, insufficient usable observations, missing known errors, fit failures, classified optimizer
warnings, acquisition failures, and invalid candidates all produce recorded diagnostics and a
deterministic Sobol fallback. A fallback is visible evidence, not a successful BoTorch acquisition.

## Command-line workflow

The command signature is:

```text
autoengineering optimize [OPTIONS] SYSTEM_FILE OPTIMIZATION_FILE
```

`--workdir` is required. Optional controls are `--max-new-evaluations`, `--resume`, and
`--format text|json`.

Run commands from the repository root. Start the checked example with a bounded invocation:

```sh
pixi run autoengineering optimize system.yaml examples/optimization_chain/optimization.yaml \
  --workdir outputs/optimization-chain --max-new-evaluations 3
```

Resume the same durable study:

```sh
pixi run autoengineering optimize system.yaml examples/optimization_chain/optimization.yaml \
  --workdir outputs/optimization-chain --resume
```

Use the Bayesian environment when the run selects `policy: botorch`:

```sh
pixi run -e bayes autoengineering optimize system.yaml optimization.yaml \
  --workdir outputs/bayesian-study
```

Add `--format json` for automation. Text and JSON output report the work directory, terminal or
invocation state, total and new evaluation counts, evaluator cost, status counts, and current
recommendation.

A nonempty destination requires `--resume`. Resume requires recognizable study state. A new run
cannot replace an existing directory, and resume validation occurs on a disposable copy before
missing advisory lock files are recreated in the real study.

## Python workflow

The same run file and construction helpers are public Python APIs:

```python
from pathlib import Path

from autoengineering.optimization import ObservationLedger, OptimizationRunSpec, OptimizationStudy
from autoengineering.optimization.command import build_backend
from autoengineering.system.graph import System

run_path = Path("examples/optimization_chain/optimization.yaml")
run = OptimizationRunSpec.from_yaml(run_path)
system_path = run.resolve_system_file("system.yaml", run_path)
system = System.from_yaml(system_path)
evaluator = run.load_evaluator_factory(run_path)(system)
backend = build_backend(run)
workdir = Path("outputs/python-study")
ledger = ObservationLedger(workdir / "observations.jsonl")

study = OptimizationStudy(
    run.study,
    run.search_space,
    backend,
    ledger,
    evaluator,
    workdir,
    target_value=run.target_value,
    input_artifact_hashes=run.input_artifact_hashes(
        system_path="system.yaml",
        specification_path=run_path,
    ),
)
result = study.run_result(max_new_evaluations=3)
print(result.recommendation.to_dict())
```

Use `OptimizationRunSpec.to_dict()`, `to_yaml()`, and `sha256` to inspect or serialize the strict
run contract. `SearchSpace` and each parameter type also provide stable dictionary and YAML round
trips.

## Durable state and recovery

The work directory contains:

| Artifact | Role |
| --- | --- |
| `observations.jsonl` | Append-only action and result ledger. |
| `manifest.json` | Commit marker with run identity, ledger hash, inputs, runtime, totals, and derived artifact hashes. |
| `backend-state.json` | Replayable backend identity and latest diagnostic state. |
| `recommendation.json` | Current feasible recommendation or an explicit absence reason. |
| `optimization-report.md` | Human-readable recommendation, evidence, diagnostics, and verification commands. |
| `.study.lock`, `observations.jsonl.lock` | Advisory single-writer lock files. |
| `pending-*.json` | Exact interrupted transition proof, present only while a transition needs reconciliation. |

Replaceable artifacts are written first and `manifest.json` is written last. The manifest binds the
study, typed search space, policy constructor settings, ledger path and committed bytes, declared
input hashes, seed, and original start timestamp. Resuming with a different run file, system,
evaluator source, declared input, seed, search space, policy, policy options, or ledger path raises
`StudyRecoveryError` before existing state is changed.

Recovery distinguishes a new empty study, a clean committed study, an interrupted evaluation, an
interrupted result commit, and corrupt or incompatible state. A pending record is accepted only
when it proves the exact transition from the committed ledger snapshot. Compatible work is applied
once. Ambiguous state is retained for inspection and rejected.

## Release A benchmark

Run the checked gate in the Bayesian environment:

```sh
pixi run -e bayes benchmark-release-a
```

When `benchmarks/release_a/results/` exists, this command does not rerun or replace it. It reads
`raw-records.jsonl`, recomputes the exact matrix and scientific fields, regenerates the summary,
report, and gate in memory, checks their bytes, and exits nonzero on any mismatch or failed
criterion.

The benchmark compares fixed candidate order, random, scrambled Sobol, SMAC, and BoTorch on five
problems and 30 seeds. The [frozen decision](decisions/0001-release-a-benchmark.md) defines the
problems and numeric criteria. The [evidence correction](decisions/0002-release-a-evidence-corrections.md)
records why the first passing trial was invalidated and how the replacement run was audited. The
checked outputs are:

- [`raw-records.jsonl`](../benchmarks/release_a/results/raw-records.jsonl), the evaluation evidence;
- [`run-summary.csv`](../benchmarks/release_a/results/run-summary.csv), one row for every run;
- [`report.md`](../benchmarks/release_a/results/report.md), distributions and criteria; and
- [`gate.json`](../benchmarks/release_a/results/gate.json), the machine decision and provenance.

The checked gate applies only to Release A whole-system optimization. It does not establish skill
for unobserved systems, forecast settings, safety constraints, component surrogates, or partial
observability.

## Function-network boundary

The experimental function-network layer now represents local design parameters, coupling inputs
and outputs, scalar surrogate features, observation availability, evaluation costs, terminal
outcomes, and permitted scopes. It validates these immutable records against a `System` without
changing the core schema. System and permitted component actions write arrays to digest-bound NPZ
artifacts and scalars to the observation ledger. Fresh ledger readers can reconstruct deterministic
component training tables from those files.

The checked [function-network example](../examples/function_network/) demonstrates representation,
evaluation, parent artifact reuse, and replay in the default environment. The public records are
available from `autoengineering.optimization`, including `FunctionNetworkSpec`,
`FunctionNetworkEvaluator`, and `reconstruct_component_training_tables`.

This layer does not yet fit component surrogates or provide a function-network Bayesian policy.
The Release A command still accepts only whole-system optimization. Do not describe a
`SystemBayesBackend` run as function-network optimization, component Bayesian optimization,
multi-fidelity optimization, or partial-observability optimization. The remaining research work is
tracked in the [`Bayesian optimization plan`](bayesian-optimization-plan.md).
