# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

`autoengineering` is a Python package for AI-assisted systems engineering of **multi-model chains**. It helps identify, validate, rank, and swap components within a system of connected models, then quantify the gain. The package is paired with a Claude Code agent (`.claude/agents/auto-engineer.md`) that drives the workflow interactively. Read `concept.md` for the conceptual framing.

Run commands from the repository root.

## Commands

Pixi manages environments on macOS ARM and Linux x86-64:

```bash
pixi install
pixi run lint
pixi run test
pixi install -e bayes
pixi run -e bayes test-bayes
pixi run -e bayes benchmark-release-a
```

Run a single test:

```bash
pixi run pytest tests/test_validate.py::TestMetrics::test_rmse_perfect -v
```

Run component workflow examples:

```bash
pixi run python examples/signal_chain/run_workflow.py     # synthetic, no domain knowledge
pixi run python examples/leaf_river/run_workflow.py       # real data, checked cache needs no network
```

Run the no-network optimization example:

```bash
pixi run autoengineering optimize system.yaml examples/optimization_chain/optimization.yaml \
  --workdir outputs/optimization-chain --max-new-evaluations 3
pixi run autoengineering optimize system.yaml examples/optimization_chain/optimization.yaml \
  --workdir outputs/optimization-chain --resume
```

CLI (installed as `autoengineering`, also `pixi run autoengineering <cmd>`):
`describe`, `graph`, `components`, `validate`, `report`, `candidates`, `improve`, `experiments`, and
`optimize`. The optimize command takes a system YAML, optimization YAML, and explicit work
directory. See `docs/optimization.md` before changing its run or recovery contract.

Run the automated research loop end-to-end:

```bash
pixi run python examples/leaf_river/run_auto_research.py   # reproduces NSE 0.23 -> 0.39 via auto_improve
```

## Architecture and execution boundary

The original component workflow separates structural system descriptions from numeric example
models:

- A `System` (`system/graph.py`) is a NetworkX `DiGraph` of `Component` objects loaded from YAML.
  Components contain metadata, typed ports, and an arbitrary metadata dictionary.
- Numeric example models live under `examples/<name>/models/`. Workflow scripts wire them together
  and pass arrays to `validate_arrays()`.

The component workflow runs models, validates arrays, ranks opportunities, swaps a component, and
runs the chain again. The `research/` runner is the package path that executes declared component
callables.

### Packages

1. **`system/`** - Define. `System.from_yaml()` / `to_yaml()`, graph queries (`topological_order`, `upstream_of`, `downstream_of`), and rendering (`describe()`, `to_mermaid()`).
2. **`validate/`** - Validate. `validate_arrays(name, observed, simulated, metrics, thresholds)` returns `ValidationResult` dataclasses. Metrics live in the `METRICS` registry in `compare.py`: `rmse`, `bias`, `relative_bias`, `correlation`, `nse`, `kge`.
3. **`analyze/`** - Analyze. `rank_opportunities()` groups results by component and scores improvement potential (higher = more room to improve); `generate_report()` produces a markdown/JSON report.
4. **`execute/`** - Improve. `swap_component(system, target, replacement)` returns a **new** `System` with one component replaced and all connections preserved.
5. **`research/`** - Research and bounded component improvement. `runner.run_component` and
   `build_feedforward_runner` execute declared models. `ExperimentTree` records lineage, and
   `auto_improve` runs the swap, execute, validate, and decide loop.
6. **`optimization/`** - Durable whole-system optimization. Strict run and search-space schemas feed
   random, scrambled Sobol, or optional BoTorch policies. `OptimizationStudy` owns budgets, the
   append-only ledger, recovery, recommendations, and reports. Release A evaluates the complete
   system for every action. It does not implement function-network or component-level Bayesian
   optimization.

### The runnable contract (how models get executed)

`research/runner.py` executes a component through `Component.metadata["runnable"]`. The dictionary
round-trips through YAML and survives `swap_component` copies. It supports Python callables and
commands with an `.npz` input/output contract. `build_feedforward_runner` wires a feed-forward
system. Chains with glue arithmetic can provide a handwritten `run_chain`.

### Metric direction convention (important when adding metrics or thresholds)

Pass/fail direction is not uniform. In `validate_arrays`, metrics `nse`, `kge`, `correlation` pass when `value >= threshold` (higher is better); all others pass when `abs(value) <= threshold` (closer to zero is better). `rank_opportunities` additionally floors the score to 0.6 when `nse` or `kge` drops below 0.5. Any new metric must be slotted into the correct side of this convention in both files.

## Conventions

- Immutability is enforced by design: `swap_component` and `to_networkx` return copies; never mutate a `System` in place when a transform is expected to be pure.
- Use type annotations with `from __future__ import annotations` for new function signatures. Use
  dataclasses for result and data-transfer types.
- Format with `ruff` (line length 100). Python 3.12.
- New components/metrics should come with tests in `tests/` (mirrors the `system`/`validate`/`analyze` split) and, where it demonstrates the workflow, a worked example under `examples/`.

## License / attribution

BSD-3-Clause, Battelle Memorial Institute. Personal-laptop git identity (`Cam Bracken <cameron.bracken@pm.me>`) - see the parent `~/projects/CLAUDE.md`.
