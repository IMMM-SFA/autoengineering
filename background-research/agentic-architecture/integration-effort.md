# Integration effort and limits

The prototype adds five executable modules plus an initializer under the example, a standalone
live-host runner under `scripts`, and focused contract tests. Numerical and control code share no
new dependencies with the installed package. The JSON CLI incurs repeated Python/import startup;
the direct route keeps that process alive. The live runner currently names Codex, making it a
host adapter rather than proof of interchangeable workers.

Custom code size can be measured with `wc -l examples/agentic_architecture_pilot/*.py
scripts/agentic_architecture_workers.py`. Setup, research, repair, and human intervention minutes
were not separately timed. No fabricated effort estimate is used to rank architectures. Raw run
elapsed times and token receipts are retained, including the unsuccessful first fitting attempt
and the live token stop.

The isolated worktree reused the existing Python 3.12 Pixi environment by explicit executable path
and set `PYTHONPATH=src:.` to load this checkout. It did not copy or modify the environment. An
initial full test invocation lacked that environment's bin directory on PATH, causing a command
runner fixture to miss `python`. Adding the bin directory resolved it. The final run reported
510 passed and 65 skipped, with optional dependencies absent. Ruff passed. macOS ARM64 was the
only platform exercised. No Bayes environment suite, expensive benchmarks, or Linux checks ran.

The scientific data's raw quality flags and source metadata remain unverified. No reference-system
solver benchmark was reproduced. One Modelica conformance helper ran directly. The worker's
ordinary stdout/stderr records contain no tool executions; API credentials were not provided to
workers or saved in reports. The full source audit and filesystem probes are evidence for their
stated scope, not a proof of production sandbox security.

The live runner used the installed Codex default model without recording its resolved model ID.
JSONL receipts expose usage and final messages but not the full model-visible system context.
Command-level user prompts were reconstructed from the exact runner expression and saved feedback
in `live/reconstructed-user-prompts.json`; they were not captured at dispatch. These provenance
limits prevent a claim of a fully auditable model invocation. Part 2 must save prompts before
dispatch and record the resolved model/provider identity.
