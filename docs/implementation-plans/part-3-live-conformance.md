# Part 3 live conformance and development comparison

Status: proposed execution design, not authorized. No command in this document reads an
existing authentication cache or contacts a provider. The CLI and native boundary have offline
evidence. Real authentication, provider conformance and the Leaf River comparison remain
unattempted. This design needs a resolved preparation/runner package before an approval request.

The parent [Part 3 plan](part-3-multi-agent-system.md) remains the acceptance contract. This
document separates the small host check from the measured-data comparison so a failure cannot
silently spend the second phase's allowance.

## Proposed host selection

Use the explicitly selected installed Codex 0.155.1 executable that passed the version 1.3
native boundary. Its SHA-256 is
`26d4d42df9846aaeedce4a9c8c7cfa9e209fc8710fb2ab2b972a151c79463600`.
Propose `gpt-5.5` and subscription authentication because the offline native protocol was tested
with that catalog entry. No real model availability, resolved identity or account access has
been verified. Do not substitute another executable, model, API key or login method on failure.

The preserved CLI-only source-bound qualification is
`/private/tmp/part3-configured-cli-20261027/native/qualification.json`, with pin
`48c52049f1b9150b95d73d7a4700fa1b938dca5436336008a3dbbcc09bc7c1a5`.
Implementation changes require new qualification before dispatch. A live packet must bind its
final source/runtime/profile hashes and fresh output roots, not inherit an older qualification
because its observations look similar.

The user must select the exact existing managed-cache file and expected account for the
separately authorized lease preparation. Neither has been inspected or inferred. The prepared
lease remains outside the repository, worker tree, scientific campaign and qualification root.
Use an owner-private destination, a distinct lease ID and a declared lifetime of at most
900 seconds. Never persist a credential hash, refresh a cache or fall back to another source.
The account value belongs in private preparation input, not a public report or checked document.

## Host conformance ceiling

Proposed aggregate ceilings for one authorized conformance batch:

| Resource | Ceiling |
| --- | --- |
| Physical host invocations | 16 |
| Logical role tasks | 12 |
| Repair invocations | 2 total, at most 1 for a task |
| Worker wall time | 30 seconds for each invocation |
| Batch wall time | 720 seconds |
| Combined native stdout/stderr | 65,536 bytes for each invocation |
| Persisted prompt/response transcripts | 1,048,576 bytes total |
| Staged workspace | 65,536 bytes for each invocation |
| Synthetic scientific starts | 2 total |
| Leaf River or other measured-data starts | 0 |

The batch counter must reserve before launching each native client. Preflight failure, timeout,
cancellation, malformed output and lost acknowledgment consume the original reservation. Count
all fixed-worker request intents separately. A request intent means a request may have been sent,
not proof of provider acceptance. Native retries cannot reserve another upstream dispatch for
the same invocation. There is no extra allowance for fixing a failed case.

The case allocation is deliberately below the aggregate host ceiling. One simple structured
response uses at most one invocation. The complete supplied-candidate synthetic four-role path
uses at most seven. Timeout, cancellation and supervisor interruption each use at most one.
At most two invocations are reserved for malformed handoff/repair behavior. The remaining three
are unused capacity, not automatic retry authority. A runner must stop if a required case cannot
be exercised within these caps. Changed code or a rerun needs its own approved packet.

Required evidence:

1. Prepare one explicit real lease after authorization. Record only preparation status, lease
   ID, declared expiry, authentication mode and scope. Distinguish local shape/expiry checks
   from actual server validity. Do not print cache contents or account/token values.
2. Complete one structured text response under the pinned native policy and fixed subscription
   worker. Record requested/resolved model, request/response artifacts, supplied usage, native
   and upstream ownership, elapsed time and both stop proofs. A missing resolved identity is
   an incomplete conformance result, not permission to copy the requested name into it.
3. Complete all four roles over the supplied synthetic candidate with the normal CLI. Require
   typed handoffs, configuration binding before dispatch, the expected controller decision and
   exactly two synthetic scientific starts. Replay must start no native or scientific work.
4. Exercise cancellation, timeout and owner interruption separately. Retain the actual point
   reached, request-intent uncertainty, original reservation and any missing usage/duration.
   If a response completes before interruption, report that the intended in-flight case was
   not exercised. Do not relabel completion as interruption or retry automatically.
5. Recover saved output or verified abandoned failure without a replacement model request.
   Missing ownership or failed process observation remains pending. Local group termination
   does not establish that remote provider computation stopped.
6. Verify malformed handoffs cannot reach a scientific tool. Any repair has a new invocation
   and uses the same task/run ceilings. Preserve failed outputs and all controller decisions.

The shared batch ledger and native/scientific reservation adapters are implemented and tested
offline. `BatchSpec` freezes concrete case and aggregate limits, and its private runtime manifest
binds the creation time. Individual `AgentRunSpec` limits still do not enforce the batch total.
The conformance-specific proposal capture is now implemented. It preserves the worker template,
freezes the six case definitions and captures only the original public scalar scientific inputs.
It creates no runtime directory or clock. The serial Python runtime now implements text, roles,
timeout, cancellation, owner-loss and malformed handoffs. It binds the original
preparation/runtime pins and preserves reservations across recovery. Public run, resume and
read-only status commands expose this protocol without changing its ceilings. Owner-loss holds
the fixed upstream worker before its launch gate, records bound interruption intent, terminates
only its owned supervisor group and reconciles through both independent watchdogs. No credential
preflight or provider request occurs in that case. Unknown native usage, model, duration and
transcript bytes remain unknown and charged. This is local preflight interruption evidence,
not a claim of in-flight provider recovery.
The malformed handler uses a separate two-call, one-task worker with one repair. It requires
the intended invalid inner payload, its recorded rejection and fixed-worker proof before repair.
It passes only after a valid typed stop handoff, with no scientific actions or starts.
All handlers and public commands are implemented. No real provider case has run. Positive handler tests use explicit authored provider attestations, while an actual
native reply without fixed-provider proof is rejected by the unmodified gate.
A typed approval file is not a substitute for the user's actual authorization.
The offline authored fixtures establish configuration/accounting integration only.

The accounting increment uses one private, hash-linked batch journal. A case begins before
its work, each host/scientific start consumes a permanent reservation, and only a recorded
observation with verified local stop can clear pending work. The journal records known usage
without turning missing usage into zero. Transcript reservations retain their ceiling until
observed bytes are known. A shared operation lock spans physical work, while short writer locks
protect commits. Reopening a batch cannot reset its start time, identity, cases or allowances.
The trusted case runner remains responsible for interpreting the physical receipts. A batch
counter alone does not prove that a protocol case passed or authorize a provider request.
The runtime clock starts at `BatchStore.create`, not at approval. Prepare a frozen specification
for review, then instantiate its absent runtime directory only after execution is authorized.

## Matched Leaf River comparison

Execute the matched live comparison only after host conformance passes. Its offline preparation,
validation and dry run proceed before the live authorization request. Freeze three new campaigns: scripted
broker, one agent and four serial roles. Keep the candidate pool, data, seeds, parameter bounds,
calibration policy, scientific checks, stopping rules and aggregate allowances identical.
The single-agent route still uses the same typed broker operations and artifact mediation.
It must not obtain private labels, extra tools or more numerical feedback than the role route.

Use the existing hydrology development case with Hamon and Hargreaves PET, soil bucket and
linear reservoir. Its current direct protocol performs 38 physical executions: two defaults,
32 Sobol fitting calls, two selected comparison calls and two causality checks. Propose a new
ceiling of 38 for each route, 114 for the three-route comparison, with common seed 17 and the
existing scientific thresholds unchanged. Before approval, a new source-separated profile
builder must prove this accounting and bind the exact candidate/data/source bytes without
executing the model. Do not regenerate or overwrite the checked Part 2 profiles.

Propose equal host ceilings of 20 invocations, 16 tasks, four repairs total, at most two repairs
for a task, 30 seconds for a worker and 600 seconds for each live route. Each route has
1,048,576 transcript bytes and a 65,536-byte staged workspace ceiling. Scripted calls are
reported separately from provider calls. The two live routes share a proposed aggregate cap
of 40 physical host invocations. These proposed caps do not authorize any current dispatch.

The invalid-candidate case must change only a declared intervention or interface property so
the intended admission check rejects it before numerical use. Freeze that mutation and its
expected failure reason. Rejecting it must not weaken scientific criteria or erase the host
work used to propose it. The interrupted-worker case must retain its charged invocation and
recovery evidence, with no duplicate model/scientific work. Allocate both cases inside the
matched ceilings rather than granting one route free tests or extra feedback.

Report route completion, valid/invalid handoffs, candidate rejection, recovery, human actions,
wall time, physical scientific starts, requested/resolved model and known/unknown usage. Include
the controller's chosen configuration, objective and every scientific constraint. Distinguish
fresh evaluations from replay. Preserve neutral or adverse differences. A completed single
comparison establishes feasibility and observed overhead, not general practical value.

The data retain January-March 2019 warm-up, April-September fitting, October-December development
comparison and the known exposure of 2020. Independent measured-data confirmation remains
`confirmation_not_attempted`. A relatively accepted model may still have negative NSE/KGE.
No repeated study, role-removal matrix or generated-code comparison is included in these caps.
Generated implementations need a separately frozen comparison after the supplied-pool study.

## Work before approval

The conformance handlers, owner interruption, public execution/recovery commands and
[single-agent route](part-3-single-agent.md) are implemented offline. Both workflow routes now
receive the complete inner handoff contract in their prompts. Implement the matched comparison
driver. [Fresh source-separated Leaf River preparation](part-3-matched-comparison.md) now
captures three new manifests without scientific execution. Retain offline dry-run evidence
for the full driver, including intended
invalid-candidate rejection and accounting. Then present the
exact source/profile pins, commands, output roots, account-source choice and combined ceilings
as a reviewable authorization request. Do not ask for live authority while those required
preparations remain unfinished.
