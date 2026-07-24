# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

`autoengineering` is a Python package for AI-assisted systems engineering of **multi-model chains**. It helps identify, validate, rank, and swap components within a system of connected models, then quantify the gain. The package is paired with a Claude Code agent (`.claude/agents/auto-engineer.md`) that drives the workflow interactively. Read `concept.md` for the conceptual framing.

Note: this repo lives at `autoengineering/autoengineering/` — the inner directory is the actual git repo and package root. Run all commands from there.

## Commands

Environment is managed with **pixi** (osx-arm64 only). All tooling runs through pixi tasks:

```bash
pixi install          # create the environment
pixi run install      # pip install -e . (editable)
pixi run test         # pytest tests/ --junitxml=results.xml
pixi run lint         # ruff check src/ tests/ examples/
```

Run a single test:

```bash
pixi run pytest tests/test_validate.py::test_rmse -v
```

Run an example end-to-end (each prints all four workflow steps):

```bash
pixi run python examples/signal_chain/run_workflow.py     # synthetic, no domain knowledge
pixi run python examples/leaf_river/run_workflow.py       # real USGS/NOAA data, cached after first run
```

CLI (installed as `autoengineering`, also `pixi run autoengineering <cmd>`):
`describe`, `graph`, `components`, `validate`, `report`, `candidates`, `improve`, `experiments` — all take a `system.yaml` (or, for `experiments`, an `autoresearch.jsonl`) as the first argument.

Run the automated research loop end-to-end:

```bash
pixi run python examples/leaf_river/run_auto_research.py   # reproduces NSE 0.23 -> 0.39 via auto_improve
```

## Architecture — the key mental model

**The package describes and evaluates systems; it does not execute the actual models.** This separation is the central design fact and easy to miss:

- A `System` (`system/graph.py`) is a NetworkX `DiGraph` of `Component`s loaded from YAML. Components carry only *metadata* — name, `model_type`, typed input/output `Port`s, and an arbitrary `metadata` dict. There is no numeric computation inside a `Component`.
- The real numeric models live **in the example scripts**, not in the package. Each `examples/<name>/` has a `models/` package (e.g. `pet_hamon.py`, `rainfall_runoff.py`) with plain functions that take and return numpy arrays. The `run_workflow.py` script wires those functions together, runs the chain, and feeds the resulting arrays into the package's `validate_arrays()`.

So the data flow in a workflow script is: **run real models → get arrays → `validate_arrays()` → `rank_opportunities()` → `swap_component()` → re-run → compare.** The YAML/`System` is the structural map; the `models/` functions are the substance.

### The four-step pipeline (mirrors the four `src/autoengineering/` subpackages)

1. **`system/`** — Define. `System.from_yaml()` / `to_yaml()`, graph queries (`topological_order`, `upstream_of`, `downstream_of`), and rendering (`describe()`, `to_mermaid()`).
2. **`validate/`** — Validate. `validate_arrays(name, observed, simulated, metrics, thresholds)` returns `ValidationResult` dataclasses. Metrics live in the `METRICS` registry in `compare.py`: `rmse`, `bias`, `relative_bias`, `correlation`, `nse`, `kge`.
3. **`analyze/`** — Analyze. `rank_opportunities()` groups results by component and scores improvement potential (higher = more room to improve); `generate_report()` produces a markdown/JSON report.
4. **`execute/`** — Improve. `swap_component(system, target, replacement)` returns a **new** `System` with one component replaced and all connections preserved.
5. **`research/`** — Research + auto-improve. Bridges Analyze to Improve. `runner.run_component` / `build_feedforward_runner` **execute** models (the one place the package runs models, not just describes them); `candidates.Candidate` + `load_candidates` are the deep-research → loop bridge; `experiment.ExperimentTree` records the lineage; `loop.auto_improve` runs the bounded swap→run→validate→decide loop; `provenance.write_report` emits the evidence-first report. No LLM calls — the research half lives in `.claude/skills/`. Adapts feynman.is + openresearch-cli (see `NOTICE`).

### The runnable contract (how models get executed)

`research/runner.py` executes a component via `Component.metadata["runnable"]` — a free-form dict, so **no `Component` schema change** was needed and it round-trips through YAML and survives `swap_component`'s deepcopy. Shape: `{kind: python|command, entry: "module:callable" | "cmd {inputs} {outputs}", inputs: [...], outputs: [...], params: {...}, sys_path: "."}`. The `python` kind imports and calls the entry with the named input arrays; the `command` kind uses an `.npz` I/O contract. `build_feedforward_runner` wires a whole feed-forward system; chains with glue arithmetic (e.g. Leaf River's `recharge = precip - aet`) hand-write `run_chain` and call `run_component` on the swappable components (see `examples/leaf_river/run_auto_research.py`).

### Metric direction convention (important when adding metrics or thresholds)

Pass/fail direction is not uniform. In `validate_arrays`, metrics `nse`, `kge`, `correlation` pass when `value >= threshold` (higher is better); all others pass when `abs(value) <= threshold` (closer to zero is better). `rank_opportunities` additionally floors the score to 0.6 when `nse` or `kge` drops below 0.5. Any new metric must be slotted into the correct side of this convention in both files.

## Conventions

- Immutability is enforced by design: `swap_component` and `to_networkx` return copies; never mutate a `System` in place when a transform is expected to be pure.
- All function signatures use type annotations with `from __future__ import annotations`; dataclasses for result/DTO types.
- Format with `ruff` (line-length 100). Python 3.11+.
- New components/metrics should come with tests in `tests/` (mirrors the `system`/`validate`/`analyze` split) and, where it demonstrates the workflow, a worked example under `examples/`.

## License / attribution

BSD-3-Clause, Battelle Memorial Institute. Personal-laptop git identity (`Cam Bracken <cameron.bracken@pm.me>`) — see the parent `~/projects/CLAUDE.md`.
