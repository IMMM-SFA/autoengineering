# Part 3 matched development comparison

This implements section 11 of the [Part 3 plan](part-3-multi-agent-system.md) under the
[bounded live comparison design](part-3-live-conformance.md#matched-leaf-river-comparison).
Preparation, execution and evidence remain separate. No preparation file authorizes a model
request or measured-data execution.

The implementation has four pieces:

1. Capture three fresh Leaf River campaign manifests from the checked Part 2 scientific
   template. Preserve the data, contracts, candidate pool, parameter space, seeds, acceptance,
   checks and exposure. Use the explicit scientific source closure for new identities. Bound
   the complete pool at 38 physical executions for each route and 114 across the comparison.
   Verify all inputs without starting a campaign, host or execution clock.
2. Add the common serial driver for the scripted broker, one persona and four roles. Freeze
   candidate identity/order rules, enforce the shared batch allowances and preserve recovery.
   Both live routes retain the same 20-call, 16-task, four-repair, 600-second ceilings. An
   invalid-candidate case and worker interruption must remain inside those ceilings. Their
   receipts must establish the intended rejection/recovery without extra scientific feedback.
3. Exercise the full driver on an explicitly declared synthetic analogue. Check accounting,
   failure paths, replay and reports without executing the measured Leaf River model. Static
   Leaf River manifest verification and synthetic execution are different evidence.
4. Finish the original requirement audit. Present exact commands, pins, output roots, model,
   account-source choice and combined ceilings for separate live authorization. Live matched
   execution additionally requires passing real-provider conformance. Preserve adverse results.

The first piece is implemented by `examples.agent_campaign.prepare_leafriver`. It verifies the
checked campaign template by SHA-256, audits the historical cache, compares its saved NPZ
arrays with the original data splits, and captures the scientific inputs and audit sources.
The three new names and explicit scientific source closure create separate scientific
identities. Only the execution ceiling changes from the old template, from 64 to 38. Old
manifests, profiles and evidence stay unchanged. Host prompts and modules do not enter the
new scientific closure. The preparation recipe is retained separately.

The static allocation matches the current controller's complete-pool path: one existing
Hamon baseline default, no additional default for that unchanged family, one Hargreaves
default, 16 fitting calls for each family, two fresh selected comparisons and two causality
replays. The total is 38. Failed fitting, scientific rejection or early stops may use fewer
calls. The manifest records an execution ceiling and planned allocation, not observed work.
The driver must still enforce the aggregate allowance and verify actual accounting.

Preparation writes no campaign runtime, worker journal or batch clock. Inspection verifies
caller-pinned metadata, every captured input, all route specifications and their scientific
identities. The old template and cache provenance bind historical audit bytes. Repinning a
changed route cannot relax the frozen science, and repinning an audit cannot invent split
counts or claim that execution occurred. Partial output has no final preparation manifest.

The preserved data use January-March 2019 for warm-up, April-September for fitting and
October-December for development comparison. All 2019 and 2020 observations were exposed
historically. Independent measured-data confirmation remains `confirmation_not_attempted`.
Original HTTP responses and quality flags are absent from the legacy cache. A relatively
accepted model may still have negative NSE/KGE. No practical role advantage follows from
preparation or authored offline responses.

## Synthetic driver implementation

`examples.agent_campaign.synthetic_comparison` now captures an authored synthetic comparison
from the verified Leaf preparation. It uses deterministic algebraic weather and labels for
2001 at a synthetic basin. It copies the same supplied PET equations and scientific engine,
not measured forcing or label arrays. The scientific rules and fitting seed remain common
across all three synthetic routes. The original template, graph and parent preparation are
retained separately. Three captured driver sources and the package identities bind execution
and compatible resume. A manifest is written only after validation and complete capture.

`examples.agent_campaign.comparison` runs the three routes serially, with one shared science
ledger and the existing worker and scientific journals. It fixes the two candidate IDs and
order, rejects early freeze while candidates remain, and preserves an explicit stop. Such
validation errors consume the original repair allowances. Each route runs one positive and
one deliberately invalid static interface check before numerical work. The invalid control
changes only the first output's units and must fail the actual admission validator for
`candidate topology/interface differs`. These are trusted controls, not claimed model mistakes.
They neither consume a candidate slot nor provide additional feedback to workers. Their input
bytes and result are preserved and verified on recovery.

The example supports fresh run, compatible resume, read-only status, a local case cap and a
local numerical pause. These caps do not change the original allowances. A runtime operation
lease prevents competing drivers. Shared scientific reservations are permanent. An unresolved
worker or scientific attempt remains visible and blocks further dispatch. A lost acknowledgment
can replay the original completed handoff without another call. Final verdicts bind both
journal heads, the complete worker report, every comparison/diagnostic evaluation, scientific
selection, known costs, logical calls, repairs and recorded trusted review dispositions. Case
wall time includes pauses and recovery. CLI stderr distinguishes newly charged work from
already recorded work; report totals remain cumulative for the original runtime.

This implementation accepts only authored fake hosts and verified synthetic arrays. It does
not implement the live matched route, account selection, provider-conformance binding or native
worker interruption within comparison allowances. The report always marks real-model evidence
and measured Leaf River execution as not attempted. A completed synthetic batch cannot become
live comparison evidence. Those remaining pieces must be implemented and tested before the
reviewable live authorization request described above.

## Bounded inputs and lightweight status

New synthetic preparations use version `synthetic-matched-comparison-1.1`. They bind five
sources: the CLI facade, execution module, evidence reader, synthetic builder and Leaf
preparation helper. Execution moved to `comparison_runtime.py`; the existing Python names
remain available through the CLI module's lazy exports. Old preparations are retained and
cannot silently resume with changed source bytes. Read-only status supports both 1.0 and 1.1
origins. The existing status command loads no host, broker, scheduler, scientific controller,
domain model or optional host SDK. It can inspect archived evidence without the preparation
or original model inputs.

Synthetic input verification now uses `campaign.artifacts.read_arrays` before comparing exact
expected values. The frozen protocol permits at most five members, 64 KiB compressed bytes,
4 KiB for an individual uncompressed member and 32 KiB total. The core reader checks paths,
digests, member names, NPY headers, object types and declared sizes before NumPy allocation.
The synthetic verifier then accepts real numeric arrays only. These limits cover the fixed
365-day forcing and its shorter fitting/comparison series. Replacing or repinning an unsafe
array cannot start a comparison runtime or clock. Numerical engine limits remain unchanged.

## Native integration still to implement

Freeze native preparation from the verified Leaf proposal, the existing four-role host template,
explicit host configuration and an already captured conformance preparation. Capture all of
those inputs without opening a credential or creating a runtime. Derive three fresh worker
identities against the Leaf scientific identities. The scripted worker uses the fake host;
the other workers use the same qualified native host/model/configuration, with the existing
single-persona policy for that route. Keep the supplied pool, ordering and scientific rules
unchanged.

The native batch must reserve zero physical host calls for the scripted baseline and at most
20 for each live route, with 38 scientific starts for each route and 114 in total. Use the
shared `BatchCodexHost` and `BatchCampaignController` rather than unmetered direct calls. Freeze
the conformance preparation pin, its batch specification and future runtime root. Before
starting the matched clock, require a caller-pinned completed conformance runtime bound to that
same preparation, source, model and configuration. Reject authored attestations and preserve
the observed conformance runtime pin in the new origin record. Do not require an execution
clock to exist at preparation time.

Integrate the existing owned-supervisor interruption before credential preflight. Apply it
inside each live route's original host/task/elapsed/transcript allowances, with a saved intent
and readiness binding. Reconcile the same invocation through the independent watchdogs before
scientific workflow tasks proceed. Retain unknown model, usage, elapsed time and bytes and their
original charges. This proves local preflight interruption, not remote computation stop.
Keep the captured static interface control and its absence of numerical worker feedback.

The execution runner must verify actual fixed-worker provider proof and observed model metadata
for completed native role calls. A conformance pass alone does not turn authored comparison
responses into real-model evidence. Save requested/resolved models, failed calls and scientific
outcomes, including neutral/adverse selections. Add a separate native evidence reader rather
than labeling native results with the authored synthetic report kind. The current fake-only
preparation and report guards must remain strict.

## Native preparation implementation

`examples.agent_campaign.native_comparison` now captures the native proposal described above.
It verifies and copies the frozen Leaf and conformance preparations, the original worker
template and its own recipe. It derives the scripted, one-persona and four-role worker records
against the existing Leaf scientific identities. The same native host/configuration applies
to both live workers. All case limits and aggregate limits are fixed, and native proposal
inspection checks each captured child and exact derived worker again. Capture directories
are private at every level. A final manifest distinguishes a complete proposal from partial
files. No runtime, execution clock or credential lease is created or read.

The read-only prerequisite function requires a caller-pinned completed conformance runtime,
its original captured preparation pin and exact batch specification. It rejects an incomplete
or authored-only report. Even a successful prerequisite check grants no authority and leaves
`execution_ready: false`. Preparation against a qualified native profile is not a real-provider
conformance result or proof of model availability.

Native preparation version 1.1 also captures the runtime, interruption, provider-proof and
status drivers. The new `native_run` entry point keeps status imports separate from execution.
The runtime binds the completed conformance report digest and journal head before starting its
shared clock. Opening a runtime rechecks the same preparation, configuration, source and exact
prerequisite. The original 1.0 proposal is retained; it is not repinned for this new code.

The native runner uses the existing shared scientific controller and matched broker policies.
Before ordinary work in each live case, a separate owned supervisor dispatches a fixed control
task through the same worker journal and batch adapter. The supervisor is interrupted only
after both native and fixed-upstream ownership are recorded, while the credential-preflight
gate remains closed. Independent watchdogs stop those groups. Recovery settles the original
physical reservation and records `host_failure`, with unknown usage, duration and transcript
bytes. The transcript ceiling stays charged. One task and invocation are consumed inside the
original limits; there is no reset or free retry. Unproven readiness or stops prevent further
dispatch. A saved supervisor intent never starts a replacement supervisor.

Native case verdicts retain the same scientific evidence and static negative controls as the
synthetic route. They also capture fixed-worker proof for every later role invocation, including
failed handoffs, and match observed model/usage to the saved response stream. Missing proof
cannot pass the case. Provider-request counts remain unknown when intent is unknown. Confirmed
responses, physical host starts and logical invocations are separate counters. The native reader
verifies the original worker/scientific heads, control input and receipt bytes, provider and
interruption artifact hashes, while importing no host or scientific executor. Successful local
termination still does not establish remote computation termination.

This implementation still needs actual separately authorized real-provider conformance and
the measured comparison. Authored transport, conformance and process fixtures do not satisfy
those requirements. Current-source generated registration qualification is a separate pending
acceptance item, preserved in the completion audit.
