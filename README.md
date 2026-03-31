# Autoengineering

AI-assisted systems engineering for complex model chains.

Autoengineering helps you systematically identify, evaluate, and improve components within multi-model systems. Define your system as a graph of connected components, validate each against baselines, rank improvement opportunities, and swap in better implementations -- then quantify the gain.

## Installation

Requires [pixi](https://pixi.sh/) for environment management.

```bash
cd autoengineering/
pixi install
pixi run install
```


## Quick Start

1. Install the `autoengineering` package:
   ```bash
   cd autoengineering/
   pixi install
   pixi run install
   ```

2. Run an example:

```bash
# Simple 3-component hydrology chain
pixi run python examples/hydro_chain/run_workflow.py

# Signal processing chain (synthetic, no domain knowledge needed)
pixi run python examples/signal_chain/run_workflow.py

# Predator-prey ODE system (Lotka-Volterra)
pixi run python examples/lotka_volterra/run_workflow.py

# Real-data hydrology: Leaf River, MS (fetches USGS/NOAA data)
pixi run python examples/leaf_river/run_workflow.py
```

3. Or invoke the auto-engineer agent in Claude Code to walk through the workflow interactively.

## The Workflow

The autoengineering workflow has four steps:

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

### 4. Improve

Swap a component with an improved implementation, re-validate, and compare:

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

## CLI Reference

All commands are available via `pixi run autoengineering <command>`.

| Command | Description |
|---|---|
| `describe <system.yaml>` | Print full system description (components, connections, execution order) |
| `graph <system.yaml>` | Print Mermaid diagram |
| `components <system.yaml>` | List all component names and types |
| `validate <system.yaml> -c <name> -b <baseline.csv> -s <simulated.csv>` | Validate a component against baseline data |
| `report <system.yaml> -r <results.json>` | Generate analysis report from saved validation results |

## Examples

### `hydro_chain/` -- Simple Hydrology

A 3-component chain (precipitation generator, rainfall-runoff, reservoir). Demonstrates the basic workflow with synthetic data and a full model swap.

### `signal_chain/` -- Signal Processing

A 3-component chain (signal generator, low-pass filter, threshold detector) using simple math. Demonstrates swapping a moving-average filter for an exponential moving average. No domain expertise required.

### `lotka_volterra/` -- Predator-Prey ODEs

A coupled ODE system (prey growth, predation, predator dynamics) demonstrating sub-component replacement. Swaps the Type I functional response (linear, unbounded) for Type II (Holling disc equation, saturating). Uses `scipy.integrate.solve_ivp`.

### `leaf_river/` -- Real-Data Hydrology

A 5-component rainfall-runoff model for the Leaf River near Collins, MS (USGS gage 02472000). Uses real USGS streamflow and NOAA weather data fetched via public REST APIs. Demonstrates:

- Two rounds of improvement (PET method swap + runoff/routing improvements)
- Both full model replacement and sub-component parameter tuning
- Cascading improvement quantification (upstream fixes improve downstream metrics)
- Monotonic improvement: NSE 0.23 -> 0.25 -> 0.39 across rounds

Data is cached locally after first download -- subsequent runs complete in seconds.

## Auto-Engineer Agent

The package includes a Claude Code agent (`.claude/agents/auto-engineer.md`) that can walk through the workflow interactively. The agent combines systems engineering expertise with the `autoengineering` Python package to help identify and implement improvements.

## System Definition Format

The YAML system definition supports:

- **Components**: Named model components with typed input/output ports and arbitrary metadata
- **Connections**: Directed edges between components specifying which output port feeds which input port
- **Port types**: `timeseries`, `gridded`, `scalar`, `binary`, or any custom string
- **Metadata**: Arbitrary key-value pairs for parameters, methods, sources, etc.

See `examples/leaf_river/system.yaml` for a fully specified 5-component example.

## Development

```bash
pixi run test          # Run tests (34 tests)
pixi run lint          # Run ruff linter
pixi run install       # Reinstall package in development mode
```

## License

BSD-3-Clause. Copyright (c) 2025, Battelle Memorial Institute.
