# Autoengineering

## Project overview

Autoengineering 0.2.0 is a work-in-progress Python toolkit for evaluating and improving systems of connected scientific models. It combines:

- YAML descriptions of directed component graphs;
- numerical validation and heuristic component prioritization;
- executable component-replacement experiments with provenance;
- sequential whole-system parameter and architecture search; and
- experimental function-network Bayesian optimization (BO) research backends.

The package and Click CLI run locally and offline once dependencies and input data are available. The Python package does **not** call an LLM or search the literature. Agent skills under `.claude/skills/` and `.agents/skills/feynman/` handle research and propose candidates; executable implementations must be supplied separately.

There is no web application or common orchestration layer yet. A unified model DAG, general harness interface, interactive app, and automatic selection/training of statistical, ML, or deep-surrogate replacements remain planned. Do not describe those as implemented.

**All BO backends are experimental.** Existing examples do not show consistent gains across problems, held-out prediction, and total runtime. A passing frozen benchmark gate is not evidence of general improvement on a new model.

Start with `README.md`, `docs/workflow.md`, and `docs/optimization.md`. Use `docs/roadmap.md` for planned work, `docs/bayesian-optimization-status.md` for evidence claims, and `examples/README.md` for runnable examples. Documentation under `docs/implementation-plans/`, `docs/decisions/`, `docs/reviews/`, `background_research/`, and root `autoresearch-*` files includes preserved historical research records, not necessarily current interface documentation.

## Technology and configuration

- **Language/runtime:** Python exactly 3.12 (`>=3.12,<3.13`). Pixi declares `osx-arm64` and `linux-64` environments.
- **Packaging:** setuptools with a `src/` layout. `pyproject.toml` defines version 0.2.0 and the `autoengineering = autoengineering.cli:cli` console script.
- **Environment management:** `pixi.toml` and committed `pixi.lock`; the local package is installed editable.
- **Core dependencies:** NetworkX, PyYAML, NumPy, SciPy, pandas, Click, and Rich.
- **Development tools:** pytest and Ruff. Ruff uses a 100-character line length.
- **Optional BO:** BoTorch 0.17.2, plus PyTorch and scikit-learn in the Pixi `bayes` environment.
- **Optional benchmark comparator:** SMAC 2.x. SMAC is not a public CLI search policy.
- **Optional examples:** pvlib, PyWake/TOPFARM, HOPP, BMI, and domain-specific solver/data dependencies in separate Pixi environments.

There is no JavaScript build, generated frontend, container build, or compilation step. setuptools is the package build backend; normal development uses the editable installation supplied by Pixi.

## Repository layout

| Path | Responsibility |
| --- | --- |
| `src/autoengineering/cli.py` | Click commands for graph inspection, validation, reports, candidate scaffolds, replacement experiments, experiment trees, and whole-system optimization. Heavy and optional imports are generally deferred into commands. |
| `src/autoengineering/system/` | `Component`/`Port` records and the NetworkX-backed `System` directed graph, YAML serialization, graph queries, descriptions, and Mermaid output. |
| `src/autoengineering/validate/` | Array metrics, threshold-aware `ValidationResult` records, and baseline comparison. |
| `src/autoengineering/analyze/` | Markdown/JSON reports and heuristic `rank_opportunities` scoring. |
| `src/autoengineering/execute/` | Copy-on-write `swap_component`, preserving graph connections while replacing a component. |
| `src/autoengineering/research/` | Candidate serialization, Python/command component runners, feed-forward execution, experiment trees, bounded keep/revert loop, and provenance reports. |
| `src/autoengineering/optimization/` | Immutable study/run/search-space records, random/Sobol/BoTorch backends, durable ledger and controller, recovery, CLI construction, NPZ-backed function networks, and research backends. |
| `src/autoengineering/benchmarks/` | Release A whole-system, full-network, and partial-network benchmark runners, summaries, and frozen gates. |
| `tests/` | Pytest unit, integration, recovery, security-boundary, example, benchmark, and documentation-contract tests. |
| `examples/` | Synthetic chains, cached Leaf River data, optimization and function-network examples, BMI/local models, larger model comparisons, and three open model chains. |
| `benchmarks/` | Checked raw benchmark records, reports, gates, invalidated runs, and adverse results. Treat these as evidence, not disposable output. |
| `scripts/` | Audits, data-quality/closure checks, and report generation for local, complex, and open-chain examples. |
| `reports/` | Generated model-search figures and the standalone HTML report. |
| `docs/` | Current guides plus preserved plans, decisions, reviews, and research evidence. |
| `.claude/` | Project agent and three research/execution skills. `.agents/skills/feynman/` is vendored upstream skill material with its own guidance and attribution. |
| `.github/` | Currently empty; no checked-in CI workflows. |

## Runtime architecture and contracts

### System definition and execution

`System.from_yaml()` loads components, ports, metadata, and directed connections into a NetworkX graph. Topological, ancestor, and descendant queries support inspection. `to_networkx()` returns a copy. Port labels alone do not validate units, shapes, timing, or physical semantics.

`research.runner.run_component` reads `Component.metadata["runnable"]`. Built-in kinds are:

- `python`: import a `module:callable` and map positional array inputs and declared outputs;
- `command`: execute a command with temporary NPZ input/output paths.

`build_feedforward_runner(system, source_arrays)` executes an acyclic graph in topological order and returns arrays keyed by `component.port` and bare port names. A custom `run_chain(system)` can implement additional arithmetic or orchestration. The local BMI examples have their own BMI driver; the package-wide runner does not provide a general BMI backend.

`swap_component` creates a new system and retains connections. Preserve its copy behavior and baseline immutability. Compatible port names do not by themselves prove that a replacement is scientifically compatible.

### Validation and replacement experiments

Available metrics are `rmse`, `bias`, `relative_bias`, `correlation`, `nse`, and `kge`. NSE, KGE, and correlation pass at or above their thresholds; other metrics pass when their absolute value is at or below the threshold. `rank_opportunities` is only a shortfall heuristic: it does not establish causal attribution or predict replacement gain.

`research.auto_improve` evaluates a baseline and then tries supplied candidates once, in order, against the current retained system. It records failed and reverted trials. Retention uses strictly increasing fitness: the rounded mean of available NSE/KGE/correlation, otherwise negative absolute RMSE. Thresholds annotate results but are **not** hard retention constraints; inspect all metric tradeoffs before calling a retained candidate an improvement. The loop is bounded by candidate count/target, but does not provide the optimization controller's durable resume, cost accounting, or stochastic-seed control.

### Whole-system optimization

The public `optimize` command supports only the Release A `system` backend with `random`, `sobol`, or optional `botorch` policies. Each action evaluates the complete system. Architecture categories choose only among implementations already supplied by the evaluator; BO does not discover, implement, or train new models.

`OptimizationRunSpec` strictly deserializes the run YAML. It binds the objective, constraints, budget, noise mode, ordered search space, policy/options, evaluator factory, input files, target, and seed. `OptimizationStudy`, `ObservationLedger`, and the controller enforce budgets, explicit result statuses, durable action/result commits, recommendations, and compatible resume.

Important invariants when changing this code:

- Keep run identity immutable. System YAML, run YAML, evaluator source, declared inputs, seed, space, policy/options, and ledger path participate in recovery compatibility.
- Preserve explicit states such as `scientific_infeasible`, `model_failure`, `timeout`, and `infrastructure_failure`; do not silently convert them into objective values.
- Keep unsuccessful results out of BoTorch fitting and preserve visible deterministic Sobol fallback diagnostics.
- Preserve append-only ledger evidence, manifest-last commits, pending-transition reconciliation, advisory single-writer locks, and exactly-once compatible recovery.
- Never rewrite an existing ledger, change policy/budget during resume, relabel prior observations, or relax a frozen criterion to make a run pass.

Read `docs/optimization.md` before changing configuration, budgets, artifacts, ledgers, or recovery.

### Function-network research

`FunctionNetworkSpec` and `FunctionNetworkEvaluator` add immutable component functions, local parameters, scalar observations, couplings, costs, evaluation scopes, and digest-bound NPZ artifacts. Ledger readers reconstruct component training tables and verify parent artifacts.

`FullNetworkBayesBackend` (`function_network_full`) and `PartialNetworkBayesBackend` (`function_network_partial`) are separate research interfaces, not public `optimize` backends. Full-observability BO has a passing frozen research gate. Partial-observability BO failed its frozen gates and remains blocked/experimental. Keep final recommendations grounded in feasible, successful system observations.

## Setup, run, and build-related commands

Run commands from the repository root.

```sh
# Default editable development environment
pixi install

# Base random/Sobol workflow and CLI
pixi run autoengineering --help
pixi run python examples/signal_chain/run_workflow.py

# Optional BoTorch and benchmark dependencies
pixi install -e bayes

# Real-model examples, including BO and BMI dependencies
pixi install -e examples
```

Outside Pixi, use Python 3.12:

```sh
python -m pip install -e .
python -m pip install -e '.[bayes]'
python -m pip install -e '.[bayes,benchmark]'
```

A complete offline optimization example:

```sh
pixi run autoengineering optimize system.yaml examples/optimization_chain/optimization.yaml \
  --workdir outputs/optimization-chain --max-new-evaluations 3
pixi run autoengineering optimize system.yaml examples/optimization_chain/optimization.yaml \
  --workdir outputs/optimization-chain --resume
```

The relative system path is resolved from the optimization file's directory. A nonempty work directory requires `--resume`; use a fresh directory for an unrelated study.

Other useful smoke examples:

```sh
pixi run python examples/leaf_river/run_workflow.py
pixi run python examples/function_network/run_example.py --output outputs/function-network
pixi run -e examples python -m examples.local_models.run \
  --output outputs/local-models-smoke --methods sobol --seeds 0 --evaluations 4
```

Leaf River's checked input cache avoids network access. Some real/open examples download data on first use; consult their READMEs before running them.

## Development conventions

- Write code and documentation in English, matching the existing direct, concrete prose.
- Follow surrounding naming and structure. Use type annotations, `from __future__ import annotations`, and dataclasses for structured records where appropriate.
- Keep lines within Ruff's 100-character limit and run `pixi run lint` for changes under `src`, `tests`, or `examples`.
- Preserve copy semantics for systems, components, arrays, immutable specifications, and baseline inputs. Do not introduce hidden mutation of retained experiments.
- Keep BoTorch, Torch, SMAC, and domain-specific example dependencies optional and lazily imported. Base imports and the default test suite must work without them.
- Add or update tests for changed component behavior, metrics, serialization, execution, failure classification, and recovery contracts.
- Update current guides and example documentation when public behavior changes. `tests/test_documentation.py` checks selected CLI, metadata, import, link, and documentation contracts.
- Keep historical protocols, decisions, reviews, raw records, failed runs, and provenance conflicts intact. Documentation edits do not authorize a new research run or a changed gate.
- Preserve BSD-3-Clause/Battelle attribution, `NOTICE`, and vendored licenses. A review or passing test does not grant commit, push, merge, publication, or deployment authority.

## Testing and verification

Default checks:

```sh
pixi run lint
pixi run test
pixi run -e bayes test-bayes
```

`pixi run test` executes `python -m pytest tests -q -p no:cacheprovider`. Tests use pytest classes/functions, fixtures such as `tmp_path`, NumPy assertions for numerical behavior, and `skipif` for unavailable optional dependencies. Skips in the default environment are expected for optional real-model tests.

Run a focused test with:

```sh
pixi run pytest tests/test_validate.py::TestMetrics::test_rmse_perfect -v
```

Run open-chain tests in their own environments after obtaining required inputs:

```sh
pixi run -e solar python -m pytest tests/test_open_chains.py -q
pixi run -e wind python -m pytest tests/test_open_chains.py -q
pixi run -e hybrid python -m pytest tests/test_open_chains.py -q
```

Frozen benchmark commands:

```sh
pixi run -e bayes benchmark-release-a
pixi run -e bayes benchmark-full-network
pixi run -e bayes benchmark-partial-network
```

These are not interchangeable with ordinary tests:

- With checked output present, Release A and full-network commands reconstruct and verify evidence rather than rerunning it.
- The partial-network command reconstructs a known **failed** gate and is expected to exit nonzero. Do not present that failure as a new regression or delete its evidence.
- New benchmark execution writes only to an absent output directory and requires a clean Git checkout; some protocols also require signed-commit provenance. Verification hashes current source/configuration, so unrelated source changes can make checked-artifact verification fail.
- Do not overwrite checked results or launch expensive replacement matrices merely to make a gate pass. Follow the relevant frozen decision and obtain explicit run authority.

Before finishing a change, run the narrow tests that exercise its contract plus the default lint/test suite when practical. Exercise examples end to end for user-facing workflow changes, not just imports.

## Security and data handling

- Treat system/candidate YAML, evaluator factories, and runnable metadata as trusted executable configuration. Python entries import and execute code; command runnables invoke a shell command. Do not run untrusted candidate or evaluator definitions.
- Optimization run files reject unknown fields and duplicate YAML keys. Relative system/input/local-evaluator paths are confined to the run file directory; parent traversal, symlinked components, and nonregular files are rejected. Preserve these boundaries and work-directory symlink checks.
- NPZ parent artifacts are SHA-256 verified, loaded with `allow_pickle=False`, and subject to path, member, type, and size limits. Do not weaken artifact verification or accept object arrays.
- Preserve finite numeric-output checks, explicit infrastructure/model/scientific failure distinctions, and owner-private artifact directory requirements.
- Core operation needs no API key. External example fetchers use public data sources and verify cached bytes; changed bytes fail integrity checks. Keep held-out data outside optimization and method selection.
- `.env`, virtual environments, and local outputs are ignored. Do not commit credentials or expose them in reports, manifests, logs, or provenance.
- Use new output directories where required. Generated experiment artifacts can contain scientific evidence; do not delete or overwrite them casually.

## CI, release, and deployment

There are no checked-in CI workflows, deployment manifests, server processes, or automated release pipelines. The current deliverable is an installable Python package and local CLI, with scripts/examples producing local artifacts. The dynamic web app remains roadmap work.

Run the documented checks locally. For a fresh research/benchmark publication, follow its protocol's clean-checkout, provenance, and output-publication rules. Do not infer any remote deployment or release process from the local Pixi tasks.
