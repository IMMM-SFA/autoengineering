# Repository guidance

Read `~/AGENTS.md` for personal conventions. Run commands from this repository's root. Use the
Waterology writing-style skill for prose and research-software-quality skill for changes and
verification. Use an isolated worktree when another session is active.

Autoengineering is a work in progress. Read [README.md](README.md) for the current scope,
[workflow.md](docs/workflow.md) for architecture and execution, and
[roadmap.md](docs/roadmap.md) for planned work. The graph, runnable adapters, replacement loop, and
optimization controller exist. A unified model DAG, harness, dynamic web app, and general model
improvement selection and training workflow remain unfinished.

## Commands

Pixi manages Python 3.12 environments on macOS ARM and Linux x86-64. The local package is installed
in editable mode.

```sh
pixi install
pixi run lint
pixi run test
pixi install -e bayes
pixi run -e bayes test-bayes
pixi run -e bayes benchmark-release-a
pixi run -e bayes benchmark-full-network
```

Run a focused test or an example:

```sh
pixi run pytest tests/test_validate.py::TestMetrics::test_rmse_perfect -v
pixi run python examples/signal_chain/run_workflow.py
```

The [example index](examples/README.md) lists checked examples, requirements, and outputs.
Additional examples are being developed separately. Do not describe them as available until they
are integrated.

## Implementation rules

- Preserve copy semantics in `swap_component` and `System.to_networkx`.
- Use type annotations, `from __future__ import annotations`, and dataclasses where appropriate.
  Format Python with Ruff at line length 100.
- Add relevant tests for new component behavior, metrics, and execution contracts.
- Keep heavy optimization dependencies optional. Base imports must work without Torch or SMAC.
- Check both validation and retention semantics before describing an improvement. Thresholds in
  the replacement loop are not hard acceptance constraints.
- Read [optimization.md](docs/optimization.md) before changing configuration, budgets, ledgers, or
  recovery. Preserve immutable run identity and explicit failure and fallback states.
- Distinguish whole-system BO, full-observability function-network BO, and experimental partial
  observability. Read [BO status](docs/bayesian-optimization-status.md) before making evidence claims.
- Keep frozen protocols, decisions, raw evidence, failed runs, and provenance conflicts intact.
  Documentation changes do not authorize another research run or a relaxed gate.

The [model improvement criteria](docs/model-improvement.md) are proposed guidance. Do not describe
`rank_opportunities` or BO acquisition as an implemented selector for statistical, ML, or deep
surrogate replacements.

## Attribution and commits

The project uses BSD-3-Clause with Battelle Memorial Institute attribution. Preserve
[NOTICE](NOTICE) and vendored licenses. Follow the user's Git identity and signing instructions.
Do not infer publication, push, or merge authority from a review or a passing test.
