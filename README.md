# Autoengineering

Systems engineering tools for complex model chains.

Autoengineering helps identify, evaluate, and improve components within systems of connected
models. Define a system graph, validate components against baselines, rank opportunities, research
replacement implementations, swap them in, and quantify the result.

It also supports durable whole-system optimization. Random and scrambled Sobol search are available
in the base environment. BoTorch provides constrained Bayesian optimization in the optional
Bayesian environment. The [optimization guide](docs/optimization.md) defines the Release A scope,
run contract, recovery behavior, and checked benchmark evidence.

Two research capabilities extend the component improvement loop. _Deep research_ finds cited
candidate replacements, and _auto research_ runs a bounded loop that tests each candidate and keeps
improvements. These adapt [feynman.is](https://feynman.is) and alphaXiv's
[openresearch-cli](https://github.com/alphaXiv/openresearch-cli). See [`NOTICE`](NOTICE).

## Installation

Requires [pixi](https://pixi.sh/) for environment management.

```sh
pixi install
```

Install the optional BoTorch and SMAC dependencies when working with Bayesian optimization or its
benchmark:

```sh
pixi install -e bayes
```

Pixi installs this package in editable mode. There is no separate install task.

For a Python environment not managed by Pixi, install the matching package extras:

```sh
python -m pip install -e .
python -m pip install -e '.[bayes]'
python -m pip install -e '.[bayes,benchmark]'
```


## Quick Start

1. Install the environment with `pixi install`.

2. Run an example from the repository root:

```bash
# Simple 3-component hydrology chain
pixi run python examples/hydro_chain/run_workflow.py

# Signal processing chain (synthetic, no domain knowledge needed)
pixi run python examples/signal_chain/run_workflow.py

# Predator-prey ODE system (Lotka-Volterra)
pixi run python examples/lotka_volterra/run_workflow.py

# Real-data hydrology: Leaf River, MS (uses checked USGS/NOAA data)
pixi run python examples/leaf_river/run_workflow.py

# Durable whole-system optimization (synthetic and no network access)
pixi run autoengineering optimize system.yaml examples/optimization_chain/optimization.yaml \
  --workdir outputs/optimization-chain
```

See the [example index](examples/README.md) for requirements and outputs. You can also invoke the
auto-engineer agent in Claude Code to walk through either workflow interactively.

## The Workflow

The component improvement workflow has five steps:

### 1. Define

Describe your system as a YAML file listing components, their inputs/outputs, and connections:

```yaml
system:
  name: My Model Chain
  components:
    - name: component_a
      model_type: generator
      inputs: []
      outputs:
        - name: signal
          direction: out
          data_type: timeseries
    - name: component_b
      model_type: transform
      inputs:
        - name: signal
          direction: in
          data_type: timeseries
      outputs:
        - name: result
          direction: out
          data_type: timeseries
  connections:
    - source: component_a
      target: component_b
      port_from: signal
      port_to: signal
```

Load and inspect with the CLI or Python API:

```bash
pixi run autoengineering describe system.yaml
pixi run autoengineering graph system.yaml
```

### 2. Validate

Run each component and compare outputs against baseline data (observed measurements or a reference model). The package computes standard metrics and flags components that fail thresholds.

```python
from autoengineering.validate.compare import validate_arrays

results = validate_arrays(
    "my_component",
    observed_data,
    simulated_data,
    metrics=["rmse", "bias", "nse", "kge"],
    thresholds={"nse": 0.5, "kge": 0.5},
)
```

Or via CLI:

```bash
pixi run autoengineering validate system.yaml \
    -c my_component -b observed.csv -s simulated.csv
```

### 3. Analyze

Rank components by improvement potential. Components with failing metrics score higher:

```python
from autoengineering.analyze.metrics import rank_opportunities

ranked = rank_opportunities(all_validation_results)
for opp in ranked:
    print(f"{opp['component']}: score={opp['score']} -- {opp['summary']}")
```

Generate a full markdown or JSON report:

```python
from autoengineering.analyze.report import generate_report

report = generate_report(system, all_validation_results)
print(report)
```

### 4. Research (find candidates)

For the weakest component, deep research investigates better replacement models and
writes swap-ready **candidates** (each honoring the component's ports, with a
`runnable` block, a rationale, and citations). This is driven by the
`deep-research-candidates` skill; the resulting `candidates.yaml` is the bridge to
the loop:

```yaml
target: pet_estimator
candidates:
  - name: pet_estimator
    model_type: evapotranspiration
    description: Hargreaves PET using Tmax/Tmin.
    rationale: Corrects the summer underestimation of temperature-only methods.
    sources: [https://doi.org/10.13031/2013.26773]
    metadata:
      runnable: {kind: python, entry: "models.pet_hargreaves:hargreaves_pet",
                 inputs: [tmean, tmax, tmin, doy], outputs: [pet]}
```

### 5. Improve (auto research loop)

Run the bounded loop: each candidate is swapped onto the current-best system,
executed, validated, and kept only if it improves. Results form an experiment tree
(baseline immutable, "grow down not sideways") with an evidence-first report:

```python
from autoengineering.research import auto_improve, load_candidates, write_report

tree = auto_improve(
    system, run_chain, observed,           # run_chain(system) -> {output: array}
    validate_output="routing.streamflow",
    candidates=load_candidates("candidates.yaml"),
    metrics=["rmse", "bias", "nse", "kge"],
    thresholds={"nse": 0.4, "kge": 0.4},
    target={"nse": 0.5}, max_iterations=20, workdir="outputs", slug="my-system",
)
write_report(tree, system, "my-system", "outputs")
```

Or swap a single known-better component directly:

```python
from autoengineering.execute.swap import swap_component

new_system = swap_component(system, "old_component", improved_component)
# Re-run the chain with the new system, re-validate, compare metrics
```

## Python API Reference

### System Definition

```python
from autoengineering.system.graph import System
from autoengineering.system.component import Component, Port
```

**`System`** -- NetworkX-backed directed graph of components.

| Method | Description |
|---|---|
| `System.from_yaml(path)` | Load system from YAML file |
| `system.to_yaml(path)` | Save system to YAML file |
| `system.add_component(name, ...)` | Add a component to the system |
| `system.get_component(name)` | Get a component by name |
| `system.connect(source, target, ...)` | Connect two components |
| `system.topological_order()` | Components in execution order |
| `system.upstream_of(name)` | All ancestors of a component |
| `system.downstream_of(name)` | All descendants of a component |
| `system.describe()` | Markdown description of the system |
| `system.to_mermaid()` | Mermaid diagram of the system |
| `system.to_networkx()` | Get the underlying NetworkX DiGraph |

**`Component`** -- A model component with typed input/output ports.

| Method | Description |
|---|---|
| `Component.from_dict(data)` | Create from dict |
| `component.add_input(name, ...)` | Add an input port |
| `component.add_output(name, ...)` | Add an output port |
| `component.to_markdown()` | Markdown description |

### Validation

```python
from autoengineering.validate.compare import validate_arrays, validate_component
```

**`validate_arrays(component_name, observed, simulated, metrics=None, thresholds=None)`**

Compare two arrays and compute metrics. Returns a list of `ValidationResult` objects.

Available metrics: `rmse`, `bias`, `relative_bias`, `correlation`, `nse` (Nash-Sutcliffe), `kge` (Kling-Gupta).

**`ValidationResult`** -- Dataclass with fields:
- `component` -- Component name
- `metric` -- Metric name
- `value` -- Computed value
- `threshold` -- Pass/fail threshold (optional)
- `status` -- `"pass"`, `"fail"`, `"warn"`, or `"info"`

### Analysis

```python
from autoengineering.analyze.metrics import rank_opportunities
from autoengineering.analyze.report import generate_report
```

**`rank_opportunities(validation_results)`** -- Rank components by improvement potential. Returns a sorted list of dicts with `component`, `score`, `failing_metrics`, and `summary`.

**`generate_report(system, validation_results, format="markdown")`** -- Generate a full analysis report in markdown or JSON format. Includes system overview, diagram, validation results, and ranked improvement opportunities.

### Component Swapping

```python
from autoengineering.execute.swap import swap_component
```

**`swap_component(system, target_name, replacement)`** -- Create a new `System` with one component replaced. All connections are preserved. The replacement can be a `Component` object or a dict.

### Research

```python
from autoengineering.research import (
    Candidate, load_candidates, save_candidates,
    run_component, build_feedforward_runner,
    auto_improve, ExperimentTree, write_report,
)
```

**`run_component(component, inputs)`** -- Execute a component's `metadata["runnable"]` (a `python` module:callable or a `command`) on named input arrays; returns named output arrays. This is the one place the package executes models rather than only describing them.

**`build_feedforward_runner(system, source_arrays)`** -- Build a `run_chain(system)` callable that walks a feed-forward system in topological order, executing each runnable component and passing arrays along edges. For chains with glue arithmetic, hand-write `run_chain` instead (see the Leaf River example).

**`Candidate`** -- A proposed replacement: `name`, `model_type`, `description`, `metadata` (incl. `runnable`), `rationale`, `sources`. `to_component()` feeds `swap_component`. `load_candidates` / `save_candidates` round-trip a `candidates.yaml`.

**`auto_improve(system, run_chain, observed, *, validate_output, candidates, metrics, thresholds, target, max_iterations, workdir, slug)`** -- The bounded loop. Swaps each candidate onto the current-best system, executes, validates, keeps improvements, and returns an `ExperimentTree`. Writes `autoresearch.md`, `autoresearch.jsonl`, and a `CHANGELOG.md` entry.

**`write_report(tree, system, slug, workdir)`** -- Evidence-first report (`<slug>.report.md`) plus a provenance sidecar (`<slug>.provenance.md`).

### Whole-system optimization

```python
from autoengineering.optimization import (
    FunctionNetworkEvaluator,
    FunctionNetworkSpec,
    ObservationLedger,
    OptimizationRunSpec,
    OptimizationStudy,
    SearchSpace,
    reconstruct_component_training_tables,
)
from autoengineering.optimization.command import build_backend
```

`OptimizationRunSpec` loads and validates the strict optimization YAML contract. `SearchSpace`
represents mixed and conditional parameters. `ObservationLedger` stores append-only actions and
results. `OptimizationStudy` applies budgets, recovery rules, and artifact commits. `build_backend`
constructs the selected random, Sobol, or optional BoTorch policy.

See the [optimization guide](docs/optimization.md) for a complete Python workflow and the limits of
Release A whole-system optimization.

### Function-network representation

`FunctionNetworkSpec` is an immutable description of component functions, local parameters,
couplings, scalar observations, costs, terminal outcomes, and evaluation scopes. It validates
against a `System` without changing the core schema. `FunctionNetworkEvaluator` records system or
permitted component actions using scalar ledger outcomes and verified NPZ traces.
`reconstruct_component_training_tables` rebuilds deterministic scalar tables from those durable
observations.

The validated full-observability component-surrogate backend is available from
`autoengineering.optimization.full_network_backend`. It requests only complete system evaluations
and passes its frozen research gate, but it is not part of Release A. See the checked
[`function_network`](examples/function_network/) example, the
[optimization guide](docs/optimization.md#full-observability-research-backend), and the
[full-network evidence](benchmarks/full_network/results/report.md).

## CLI Reference

All commands are available via `pixi run autoengineering <command>`.

| Command | Description |
|---|---|
| `describe <system.yaml>` | Print full system description (components, connections, execution order) |
| `graph <system.yaml>` | Print Mermaid diagram |
| `components <system.yaml>` | List all component names and types |
| `validate <system.yaml> -c <name> -b <baseline.csv> -s <simulated.csv>` | Validate a component against baseline data |
| `report <system.yaml> -r <results.json>` | Generate analysis report from saved validation results |
| `candidates <system.yaml> -c <name> [-o out.yaml]` | Scaffold a `candidates.yaml` for a component |
| `improve <system.yaml> -C <candidates.yaml> --chain <mod:factory> -b <obs.csv> -O <output>` | Run the auto-research loop |
| `experiments <autoresearch.jsonl>` | Render a saved experiment tree |
| `optimize <system.yaml> <optimization.yaml> --workdir <path>` | Start or resume a durable whole-system optimization study |

## Examples

The [example index](examples/README.md) lists every checked example, its network requirements, and
the command to run it.

### `hydro_chain/` -- Simple Hydrology

A 3-component chain (precipitation generator, rainfall-runoff, reservoir). Demonstrates the basic workflow with synthetic data and a full model swap.

### `signal_chain/` -- Signal Processing

A 3-component chain (signal generator, low-pass filter, threshold detector) using simple math. Demonstrates swapping a moving-average filter for an exponential moving average. No domain expertise required.

### `lotka_volterra/` -- Predator-Prey ODEs

A coupled ODE system (prey growth, predation, predator dynamics) demonstrating sub-component replacement. Swaps the Type I functional response (linear, unbounded) for Type II (Holling disc equation, saturating). Uses `scipy.integrate.solve_ivp`.

### `leaf_river/` -- Real-Data Hydrology

A 5-component rainfall-runoff model for the Leaf River near Collins, MS (USGS gage 02472000). It
uses checked USGS streamflow and NOAA weather data. The fetcher can refresh missing cache files
from the public REST APIs. The example demonstrates:

- Two rounds of improvement (PET method swap + runoff/routing improvements)
- Both full model replacement and sub-component parameter tuning
- Cascading improvement quantification (upstream fixes improve downstream metrics)
- Monotonic improvement: NSE 0.23 -> 0.25 -> 0.39 across rounds

The checked cache lets a fresh checkout run without network access.

`run_workflow.py` does the swaps by hand; **`run_auto_research.py`** does the same
thing through the bounded `auto_improve` loop, reading `candidates.yaml` and writing
an experiment tree + evidence-first report (reproducing NSE 0.23 -> 0.39
automatically).

### `optimization_chain/` -- Whole-system optimization

A deterministic three-component chain with categorical, continuous, integer, and conditional
parameters. It demonstrates bounded execution, resume, durable artifacts, scientific constraints,
and reproducibility without network access.

## Auto-Engineer Agent

The package includes a Claude Code agent (`.claude/agents/auto-engineer.md`) that can walk through the workflow interactively. The agent combines systems engineering expertise with the `autoengineering` Python package to help identify and implement improvements.

### Research skills

Three skills under `.claude/skills/` drive the research half of the workflow (they
run through whatever agent drives them -- provider-agnostic):

- **`deep-research-candidates`** -- given the weakest component, investigate better
  replacement models and emit a swap-ready `candidates.yaml` plus a cited brief.
- **`auto-research-loop`** -- run the bounded `auto_improve` loop over those
  candidates and produce an evidence-first report.
- **`multi-hop-lit-search`** -- follow citation chains to reach connected literature
  a single search misses.

These adapt feynman.is (MIT) and alphaXiv's openresearch-cli; see [`NOTICE`](NOTICE).

## System Definition Format

The YAML system definition supports:

- **Components**: Named model components with typed input/output ports and arbitrary metadata
- **Connections**: Directed edges between components specifying which output port feeds which input port
- **Port types**: `timeseries`, `gridded`, `scalar`, `binary`, or any custom string
- **Metadata**: Arbitrary key-value pairs for parameters, methods, sources, etc.

See `examples/leaf_river/system.yaml` for a fully specified 5-component example.

## Development

```bash
pixi run lint
pixi run test
pixi run -e bayes test-bayes
pixi run -e bayes benchmark-release-a
pixi run -e bayes benchmark-full-network
```

The checked [Release A benchmark report](benchmarks/release_a/results/report.md) records the current
whole-system evidence. Remaining research is tracked in the
[Bayesian optimization status](docs/bayesian-optimization-status.md).

## AI assistance

Development and review of the Bayesian optimization branch used OpenAI Codex with GPT-5.

## License

BSD-3-Clause. Copyright (c) 2025, Battelle Memorial Institute.
