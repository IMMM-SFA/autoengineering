# Part 1 architecture investigation sketch

This is an executable investigation, outside the public package API. It compares the same fixed
Leaf River supplied-candidate task through a JSON CLI and direct standalone calls. It does not
install a host plugin or implement a general campaign system. The
[investigation index](../../background-research/agentic-architecture/README.md) explains the evidence
and unresolved requirements.

From this checkout after `pixi install`:

```sh
# Fresh outputs only. Runs six deterministic trials, 228 routing executions.
pixi run python -m examples.agentic_architecture_pilot.compare outputs/part1-comparison
# One request at a time, with evaluator privileges held by the calling process.
echo '{"id":"diagnose","tool":"diagnose","payload":{}}' | \
  pixi run python -m examples.agentic_architecture_pilot.control outputs/part1-single
# Deterministic standalone route. Existing compatible requests reconcile on repeat.
pixi run python -m examples.agentic_architecture_pilot.control outputs/part1-reference --replay
# Verify the checked investigation evidence without numerical reruns.
pixi run python -m examples.agentic_architecture_pilot.verify background-research/agentic-architecture
```

The five-step tool sequence is diagnose, submit the fixed candidate, evaluate, review the returned
decision, and decide. `state` exposes the next legal step and `cancel` prevents further starts.
Every request has exactly `id`, `tool`, and `payload`. The control process keeps durable state
outside the agent session, checks source/task/input identity, and owns both numerical studies.

A host integration can broker this CLI from a protected evaluator process. The worker receives
only a staged brief and returned tool responses. Never give an untrusted worker the evaluator's
filesystem privileges. `boundary.py` demonstrates macOS repository-denial probes. Linux needs a
separately tested boundary. No MCP dependency or plugin registration is required for the sketch.

The optional `scripts/agentic_architecture_workers.py` uses the user's explicitly authorized Codex
subscription. Its checked live run stopped at its observed token threshold after one completed
campaign. Do not rerun it as ordinary verification: it invokes live model calls and its recorded
investigation budget is nearly consumed. The source and task limits are evidence, not targets to
relax. Its schema asks for role, candidate, decision, and rationale. The implementer describes the
parameter adapter; it does not execute or install generated code.

The control prototype uses POSIX advisory locks and was exercised on macOS ARM64. Scientific
functions remain trusted. Model failures from arbitrary supplied code, a public worker RPC service,
active-child cancellation, an append-only campaign journal, strict token reservation, and complete
second-host operation remain unfinished requirements for Part 2.
