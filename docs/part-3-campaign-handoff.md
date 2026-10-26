# Part 3 campaign handoff

The local campaign interface is experimental. Part 3 should attach bounded agent roles and a
production host adapter to the locally qualified Part 2 contract.
The [verification record](reviews/part-2-workflow-contracts-progress.md) states the evidence and limits.
No host SDK, installed plugin, external worker or live model comparison is required by Part 2.

## Tool boundary

Use `autoengineering.campaign.records.Request` and `Response` as the version `1.0` JSON contract.
Use the [payload table](campaigns.md#requests-and-replay) for exact operation fields. Requests are
bounded at 64 KiB. Scientific commands require a trusted local broker. A default
`CampaignService` grants no scientific execution authority.

An invocation sends a campaign ID, logical request ID, expected revision, operation and payload.
Keep the original envelope unchanged on retry. A duplicate committed request returns its original
response. An edited handoff needs a new request ID and a `repair_of` reference. The controller
owns scientific rules and revision transitions. An agent's rationale cannot override checks,
change a frozen budget, or supply its own recommendation without supporting observations.

The broker stages author-supplied `CandidateProposal` and `CandidateSnapshot` records through
`stage_record`. Agent tools receive the resulting digest IDs. This staging function is a trusted
local API, not an endpoint for arbitrary uploads or generated executable code. Admitting a new
implementation requires an explicitly registered trusted adapter and verified source closure.

## Artifact permissions

The host adapter must enforce an explicit artifact whitelist. Possession of a digest does not
confer file access. Worker-visible artifacts should be limited to:

- the scoped task summary, allowed intervention IDs, interface metadata and resource limits;
- supplied proposal/snapshot summaries with implementation and source identities;
- permitted fitting diagnostics and scalar checks;
- typed tool responses, decision reasons and approved evidence summaries.

Keep private observation arrays, source caches that contain comparison labels, scratch paths,
process logs, full controller-state artifacts and child work directories evaluator-owned. Some
state and source artifacts contain private paths or data references. Do not expose them merely
because a controller response mentions an artifact ID. Read-only status/report APIs need no
observation bytes, scientific imports or network access.

## Host authority

A worker must not receive shell, arbitrary import, code upload or filesystem traversal capabilities
through this API. The trusted broker launches only supplied local adapters. Its POSIX subprocesses
provide lifecycle control and are not a sandbox. The host must preserve that trust boundary and
must not describe process separation as arbitrary-code isolation.

The host may submit proposals and request authorized scientific work within the frozen campaign.
It cannot increase execution allowances, change fitting data, relabel exposed data as confirmation,
resume a different scientific identity, rewrite observations, or reopen selection after confirmation.
Cancellation uses the independent inbox so it can be queued while the event writer supervises work.
A queued request is not evidence that the process group has stopped.

Scientific evidence binds the resolved campaign, supplied implementation, adapter, input/source
hashes, parameter space, policy, seed and environment lock. Host/model metadata belongs to a
separate future worker-invocation record. Switching hosts with unchanged admitted scientific
snapshots must not invalidate existing scientific results.

## Provenance hooks

Retain each dispatched prompt, resolved model identity, tool envelope and returned role artifact
as immutable artifacts before reporting a handoff complete. Link them from the worker invocation
to the campaign request/event IDs. Preserve both the host's raw response and the normalized record.
An invalid response is evidence, not a reason to overwrite the original artifact.

Record optional token/cost observations only when supplied. Unknown values stay null. Strict token
ceilings and support for additional model providers remain deferred scope decisions. Do not
silently substitute zero tokens, zero cost, or a different model identity.

`StudyLink` and `AttemptRecord` remain separate from worker invocations. A logical retry must not
create a new physical model start unless the controller explicitly reserves a new attempt. Unknown
physical work requires reconciliation before automatic continuation. Existing child recovery's
zero-cost infrastructure failure does not erase the outer attempt or uncertainty.

Before adding a production host, exercise its permission checks, malformed handoffs, duplicate
requests, cancellation, response loss and repair exhaustion against the same local fixtures.
Compare usability separately from scientific improvement. The deterministic package, not the
agent narrative, decides eligibility and selection.
