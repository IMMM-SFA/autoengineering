# Part 1 investigation results

The supplied-candidate workflow is executable and recoverable through both deterministic control
routes. One live Codex subscription campaign completed. The architecture choice remains conditional
because resource enforcement, active cancellation, an installed host plugin, and second-host
portability do not yet meet the plan's mandatory gates.

Start with the [decision and Part 2 backlog](decision.md). Supporting artifacts:

- [Baseline audit](baseline-audit.md), [execution map](execution-map.md), and [baseline manifest](baseline/manifest.json).
- [Frozen numerical task](task.yaml), [acceptance](acceptance.md), and [responsibilities](responsibilities.md).
- [Pinned reference findings](reference-findings.md), [host inventory](host-capabilities.csv), and [reference helper result](reference-conformance.json).
- [Comparison](comparison.md), [raw runs](comparison/runs.csv), [failure matrix](test-matrix.csv), and [integration effort](integration-effort.md).
- [Real recovery record](reference-recovery/recovery.json), [filesystem probes](boundary.json), and [live stop receipt](live/summary.json).
- [Executable sketches and reproduction commands](../../examples/agentic_architecture_pilot/README.md).

Gate A qualifies Leaf River only as an orchestration fixture. Gate B passes for the frozen routing
checks and executable decision. Gate C is partial: Codex was exercised; a second host was only
inventoried. Gate D passes the deterministic contract and limited filesystem probes, with general
mediation unfinished. Gate E passes the supplied-candidate replay requirement but not a complete
live plugin/standalone comparison. Gate F fails strict token enforcement and has untested active
cancellation. Gate G delivers an unresolved decision and dependency-ordered handoff, as the plan
allows. These statuses must not be described as unconditional architecture acceptance.

The final numerical count is 308 of the 320-execution ceiling. The observed live-token threshold
was exceeded within the third call and stopped the next call. Further live investigation needs a
new budget and corrected pre-call accounting. Existing BO research results and gates were preserved.
