# Part 3 single-agent comparator

This implements the one-agent route required by section 11 of the original
[Part 3 plan](part-3-multi-agent-system.md). It does not complete the matched comparison or
authorize a model, measured-data run or new scientific allowance.

The existing four-role contracts and serialized version 1.0 run files remain unchanged. Add
an explicit version 1.1 run with `workflow_route: single_agent`, one `single_agent` template
and a separate tool-policy digest. Its supplied-only task/grant version is 1.1 and its typed
handoff version is 1.2. Reject route/version mixing and generated source. Retain the existing
host protocol, private grants, journal, scheduler, repair limits, controller and source identity.

One persona may propose, configure, review its own work, freeze or stop. It cannot delegate,
change science or increase allowances. The trusted broker still checks the legal scientific
phase, candidate identity, supplied configuration, citations and executed review checks. Reuse
the existing controller transitions and campaign request envelopes. A proposal or freeze is one
agent decision. Configuration and self-review need no separate orchestrator invocation. Report
one agent, its actual invocation count and self-review explicitly. Do not claim independent review.

Both routes receive the same approved scientific summaries. The single persona also receives
at most four of its own normalized previous handoffs, with an 8 KiB aggregate history limit.
Include whole handoffs only and report omitted IDs. Never include raw transcripts, private labels,
source workspaces or new numerical feedback. Freeze this memory rule in the prompt/source identity.
The full journal preserves decisions omitted from a later prompt. Unknown usage remains unknown.

Implementation sequence:

1. Add strict versioned records, a single-agent prompt, policy and scheduler/store checks.
   Verify legacy serialization, route binding, exact grants, action/output matching and repairs.
2. Add a broker route over the same controller transitions and approved summary builder.
   Verify one-persona history, no orchestration calls, scientific parity, blocking self-review,
   invalid candidates, interrupted actions and acknowledgment recovery without duplicated work.
3. Expose the route through the existing validate/run/resume/report commands and an offline
   synthetic example. Verify CLI parity, immutable route identity, read-only imports and package
   installation. An authored fixture proves integration only.
4. Requalify the installed native boundary for the final source. Exercise the same single-agent
   protocol with actual native clients and authored replies, without credentials or providers.
   Preserve the distinction between native transport and real model evidence.

Both routes now receive the complete inner output contract in the model-visible prompt, derived
from the authoritative record fields and bound to the current task and grants. The scheduler
rechecks the deadline after preparing the prompt. Offline tests cover plain JSON replies,
supplied and generated output records, exact grants and invalid fields. Authored native replies
still do not establish real-model usability. Strict parsing and bounded repair remain unchanged.

Then implement the matched driver and fresh Leaf River preparation under the comparison design.
All routes must retain the same candidate pool, fitting seeds, scientific rules and aggregate
allowances. Their actual numbers of host calls may differ and must be reported. No practical
benefit, live-model availability or independent measured-data confirmation follows from these tests.
