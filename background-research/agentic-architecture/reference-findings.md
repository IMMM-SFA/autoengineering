# Reference implementation findings

Only the mechanisms below were inspected. No source was copied into Autoengineering. The three
repositories were cloned read-only into temporary directories, without installing their dependencies
or running their hosted-model experiments. All revisions were resolved on October 25, 2026.

| Reference | Exact revision | License | Evidence level |
| --- | --- | --- | --- |
| [Modelica suppliers](https://github.com/jfrochte/agents-as-modelica-suppliers/tree/2bb12fe700fd943bd5eb8406893bc8d61f7a1d78) | `2bb12fe700fd943bd5eb8406893bc8d61f7a1d78` | MIT, Jorg Frochte, 2026 | Code inspected; pure conformance helper executed |
| [G-Sim](https://github.com/samholt/generative-simulations/tree/72b5d51a7790b8b2ebc87973ee5e9d21aa818ece) | `72b5d51a7790b8b2ebc87973ee5e9d21aa818ece` | MIT, Samuel Holt, 2025 | Code inspected; model experiments not executed |
| [TusoAI](https://github.com/Alistair-Turcan/TusoAI/tree/04a02f80bd3e84907e78654203642043de45e71f) | `04a02f80bd3e84907e78654203642043de45e71f` | MIT, Alistair Turcan, 2026 | Code inspected; optimization not executed |

## Modelica: acceptance outside the worker

`src/commission.py:prepare`, `agent_command`, and `sandbox` build the issued task and Linux
bubblewrap namespace. Fitting/validation files are mounted, while test data, references, and the
repository are absent. `acceptance/grade.py:grade` combines separate conformance, behavior,
parameter, invariant, variant, and report checks. Some conformance decisions require a client's
recorded reading; absence stays pending. `reference-conformance.json` records a direct execution
of pending, rejected, and accepted cases from `acceptance/conformance.py`.

The full example needs Linux/bubblewrap, OpenModelica, its standard library, OMPython, NumPy/SciPy,
and a signed-in agent host. It was not run on this Mac. A run leaves the issued task, model/report,
and agent logs. The inspected commissioning entry point starts runs; a compatible campaign resume
protocol was not established. The paper's results are not reproduced by the pure helper test.

Adopt separate executable acceptance with an explicit unavailable state. The smallest test is a
numerically attractive output failing a physical check. Adopt staged data plus actual filesystem
restrictions, tested by protected read/write probes. Defer the Modelica execution stack until a
coupled-model task needs it. MIT permits reuse with attribution, but no reuse is needed here.

## G-Sim: separate structure from fitting

`agents.py:initialize_agent` chooses parameter-optimization behavior. Its generation loop submits
`complete_SimStep_code` function calls, deduplicates completions, and retains generation dictionaries
with validation loss and optimized parameters. `utils/llm_tools.py` passes generated simulator code
to the environment's numerical evaluation, then records training/validation/test losses and fitted
parameters. `save_agent_state` stores dialogue snapshots; this is not evidence of Autoengineering's
compatible ledger recovery contract.

Dependencies include hosted OpenAI calls, Torch/JAX-related methods, Gym, SBI, PySINDy, and dataset
packages. These were inspected in `requirements.txt` and setup instructions, not installed. Adopt
one child study per supplied structure and retain fitted identities. Our equal-budget family study
and resume test execute that separation without introducing G-Sim as a dependency. Defer generated
simulator code until sandboxed admission exists. Do not adopt validation loss alone as acceptance.

## TusoAI: retain intervention history

`tusoai/optimization.py` exposes `load_history`, reconstructs candidates/functions from saved
records, and writes history under a run-specific history directory. `_dm_load_functions_from_history`
checks for a file, parses candidate entries, and selects by accuracy/runtime information. It is
history-based continuation; the inspected path does not establish immutable task identity or
exactly-once physical execution. Dependencies include Anthropic/OpenAI clients, requests,
scikit-learn, PyMuPDF, NumPy, and matplotlib. No provider calls were made.

Adopt persisted rationale, source identity, outcomes, and unsuccessful attempts. The smallest
falsifying test is an interrupted worker whose next legal action cannot be reconstructed. Our
worker-disappearance test checks that property. Keep Autoengineering's existing child ledger.
Defer large parallel search and literature mutation because one supplied candidate suffices here.

## Harness evidence

[Official Codex noninteractive documentation](https://learn.chatgpt.com/docs/non-interactive-mode)
and installed `codex exec --help` establish JSON events, output schemas, read-only execution,
ephemeral runs, and CLI invocation. [Claude's official headless documentation](https://code.claude.com/docs/en/headless)
establishes print mode and programmatic invocation. Installed versions and capability limits are
in `host-capabilities.csv`. Read-only execution does not protect comparison files from reads by
itself. The separate repository-denial sandbox was therefore tested and applied to live workers.

Codex was authenticated through ChatGPT. The worker runner removes API-key/base-URL overrides and
ignores user provider configuration. Three live role calls completed without tool events. They
returned token usage after completion, crossing the observed limit. No second host was launched.
A second executable's presence is only a plausible portability target, not a portability result.
