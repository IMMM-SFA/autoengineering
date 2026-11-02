# Part 5 second-host implementation increment

This increment implements the existing Part 5 section 5.6 requirement. It does not
authorize live calls. The full Part 5 objective and all data/privacy/platform gates
remain unchanged.

## Current evidence

Claude Code 2.1.310 is installed. Local `--version` and `--help` completed without
a prompt or inference. Their bytes and executable hash are saved under
`examples/utility/verification-platform-inventory-v1`. The help advertises print,
JSON output, JSON schema, tool selection, strict MCP configuration, setting-source
selection and no session persistence. Its dollar cap is described for API usage.
That flag is not evidence of a subscription cost cap.

The current HostSelection accepts only fake and Codex hosts. Claude cannot be
labelled as Codex or passed through a second model configuration to satisfy the
requirement. A genuine new host transport and truthful capability records are
needed before any conformance request is presented for execution.

The local Docker daemon is OrbStack on Linux ARM64. The cached official Python
3.12 image is also ARM64. These read-only inventory checks do not qualify the
required Linux x86-64 target, start a container or select Docker for execution.
A Docker image pull, new runtime, remote job or live provider call was not performed.

## Implementation and acceptance

1. Inspect the complete existing HostSelection/HostCapabilities serialization,
   host factories, scheduler checks, boundary qualifications, credential handling,
   recovery and cost joins before editing. Add a versioned host profile while
   preserving exact v1/v2 records and previous source evidence. Unimplemented or
   unqualified profiles must refuse before dispatch.
2. Implement an application-owned Claude transport using the pinned executable,
   explicit model/configuration and inspected supported flags. Workers cannot
   supply commands, flags, settings, plugins, MCP servers or credentials. Verify
   the actual output contract against primary documentation and preserve bounded
   raw bytes. Do not invent successful event/usage fields from an assumed schema.
3. Reuse the existing supervisor, permanent physical reservations and original
   completion recovery. Preserve timeout, interruption, malformed output, unknown
   request intent, unknown cost and unverified-stop states. Completed replay may
   read original evidence but never obtains a new allowance or a second call.
4. Keep role/tool envelopes and scientific grants unchanged. Tools disabled in a
   CLI are not an OS privacy boundary. Qualify the actual execution/response
   boundary with synthetic private canaries and explicit resource/permission
   checks. Credential availability is separate from authentication and boundary
   qualification. Never print or persist credentials.
5. Test the new transport offline with authored streams and bounded local fake
   executables. Cover all roles, wrong model/version, malformed/multiple results,
   usage absence, output ceilings, cancellation, loss before/after completion,
   attempted tool/configuration injection and original-record replay. Authored
   fixtures do not qualify an actual Claude call.
6. Prepare one concrete live conformance package with exact executable/model,
   boundary profile, role cases, repair/interrupt cases, aggregate request/time/
   transcript limits, data grants, usage/cost treatment and new output directory.
   Resolve operator model/authentication choices and obtain explicit live-call
   authority only after that package and implementation are reviewable. Part 3
   allowances do not carry over. Do not run a utility matrix as conformance.
7. Record actual evidence or a named blocker. Bind the measured limitations and
   preserve all failed runs. Passing conformance is not a second-host utility
   comparison, a private scorer qualification or Linux evidence.

Keep this implementation separate from unchanged development matrix records.
Run focused host/scheduler/recovery and documentation tests, then relevant broad
checks after source changes. Add a source inventory, update the audit and handoff,
and retain the exact live approval boundary. No commit or push is implied.

The inspected help also states that `--bare` skips keychain/OAuth authentication
and accepts an API key or an explicit apiKeyHelper. The existing supervisor
rejects credential environment variables and persists its non-secret environment.
Preserve that prohibition. A future bare profile needs an explicit trusted helper
or broker credential interface, with no secret in the process job, command,
transcript or public identity. Subscription support cannot be inferred from bare
mode or its API dollar flag. Resolve this authentication profile before live work.

## Transport foundation checkpoint

`agents/hosts/claude.py` now implements primitive version 1.2 with pinned version/
executable/helper code, fixed bare-mode options, an explicit OS-wrapper callback,
process supervision, original-job recovery and strict structured-result parsing.
The supervisor and existing HostSelection/HostCapabilities/scheduler gates are
unchanged. The raw primitive is not an admitted Host implementation.

Focused regressions passed 111 tests. They use authored executables only. Real
Claude activity remains help/version inspection, not inference. Primary source
notes and raw failures are under verification-second-host-v1.

Cost tracking uses per-model counters for whole-call normalized totals. Top-level
counters remain separate diagnostics, not a fallback for missing model breakdowns.
Crash zeroes become unknown normalized work. SDK dollar fields remain explicitly
client estimates and billed cost remains unknown. Native request/turn/solver work
must not be inferred from these token values. Future host/cost integration must
retain usage completeness and this cost basis.

Next: implement and qualify the actual boundary/profile, truthful versioned host
admission and scheduler/factory/cost integration. Then prepare the complete live
conformance package and resolve model/authentication choices before requesting
live execution authority. These requirements have not been replaced by the raw
transport tests or by the earlier Codex qualification.

The final foundation checks passed 112 focused regressions and all 52 installed
fixtures, including loss after saved completion with a prelaunch-bound job digest.
CLI JSON mode and the API helper have not been exercised with an actual inference.
The next profile must keep reported usage completeness and estimated-versus-billed
cost separate through scheduler and cost joins. Its live proposal must distinguish
hard request/time/byte limits from the client's estimated-USD budget. Do not claim
that the SDK flag alone guarantees a bound on the final invoice.

The added host module changes host_source_identity even though existing record
formats are unchanged. Earlier live pins retain their original source scope and
must not be rewritten or reused under changed source. Bind the next actual host
profile to the new source snapshot and qualify it before admitting live execution.

## Candidate Claude macOS boundary checkpoint

The new `claude_policy.py` renders an explicit deny-default policy with a private
home, read-only worker packet, fixed runtime/helper/executable paths and bounded
localhost endpoint ports. The actual v5 kernel probe passed all 14 syscall controls,
Claude help startup and direct pinned-helper startup with a synthetic fixture.
No inference, real credentials or production admission was involved.

Raw failed attempts, source copies and the final receipts are archived under
`examples/utility/verification-claude-policy-v1` and `development/claude-policy-vN`.
The numeric endpoint grammar failure and missing public ICU startup dependency are
preserved. The final probe binds host source identity
`86b89bd3d3f2dade5fe0cad06650a72267a4536d0e7db2d675b55e216d9fcb8d`.
Prior qualification records keep their original identities.

Focused host/process/policy checks passed 128 tests. Twelve archive checks passed
both in the checkout and using the existing installed wheel outside it. The actual
saved probe was reconstructed with checkout access, processes, sockets and optional
model/provider imports blocked. The archive reader verifies recorded stop evidence,
not current process state. It cannot grant host admission.

Next work remains actual Claude helper-hook/controlled-peer integration, permission,
resource and lifecycle qualification, truthful host records and scheduler/factory/
cost integration. External API traffic needs a separately qualified broker. IPv6,
UDP, DNS/TLS, preferences/shared memory, process environment privacy and Linux are
unqualified. Only after these requirements and model/authentication choices are
resolved can a concrete live conformance package request execution authority.
The full Part 5 scope and independent-data/scorer requirements remain unchanged.

## Native Claude controlled-peer checkpoint

The actual native helper hook and structured-output roundtrip now work against an
application-owned loopback peer with synthetic input and authentication. Final v7
records exactly one peer request, successful structured output and a verified stop.
No provider or scientific model ran. Reported token and dollar values are authored
fixture data. They are not cost/utility evidence or actual role conformance.

Transport 1.4 binds an integer-only local endpoint through fixed settings. It puts
both temporary-directory settings in the isolated home. The supervisor admits the
non-secret CLAUDE_CODE_TMPDIR only when it equals explicit HOME. Credentials remain
forbidden in environment records. Policy 1.4 grants the measured /bin/sh launcher,
/bin/bash delegate and public selector, without granting /bin as a read/exec tree.
The native result requires explicit terminal completion to accept a StructuredOutput
tool_use stop. Plain text and incomplete/error/tool-usage results remain rejected.

All failures are archived, including the temp override, shell/delegate and native
terminal-result discoveries. The final policy probe also passed its 14 syscall
controls on host source identity
8402762a4b9dbbb4292a08e502997a8d54e5ffd6418153825a8a41fbe5eaf07f.
The offline native reader checks pinned raw evidence and never executes an archive.
Its eight regressions passed. A fresh wheel matched all 181 current core Python
files, passed 100 installed authored fixtures, and reconstructed the actual final
native/policy archives with original-source opens, sockets and processes blocked.
The initial installed interpreter-alias setup failure remains recorded.

See examples/utility/verification-claude-loopback-v1/README.md for commands and
source-specific limits. The broad agent test run remains active at this checkpoint.
The original study's 15634 pinned files are unchanged. Old production pins retain
their original source scope and cannot be reused or rewritten for changed source.

A production upstream broker, truthful host records/admission, scheduler/factory/
cost integration, full runtime/privacy/lifecycle qualification and actual authorized
LLM conformance remain unfinished. The diagnostic peer has no upstream. Independent
data/custody, a qualified scorer, final protocol/cost/effort and Linux x86-64 remain
open. This checkpoint does not close G6 or the full Part 5 objective.

Native lifecycle closeout on the same core bytes: actual timeout, cancellation and
output-limit probes all stopped after one authored-peer request. Completed replay
added zero requests and reproduced the original process, parsed result and job.
After active supervisor death, the watchdog stopped the group, the completion
remained missing, and recovery refused without a new job. Its outcome stays
unknown_owner_loss. A separate fault after saved completion recovered only the
prelaunch-bound original result with zero added jobs. These local synthetic checks
do not supply real model conformance or production integration/qualification.

The all-agent regression run completed: 939 passed in 1175.53 seconds with fixed
core source. Its exact collection and terminal receipt are preserved. This is not
a new full default/Bayes run or a frozen science matrix. All independent-data,
scorer, protocol, platform, live-call and full Part 5 completion requirements remain.

## Durable Anthropic exchange increment

Next implement an application-owned Anthropic Messages exchange. Preserve existing
Responses exchange manifests and behavior. Rebuild outbound requests from the
frozen role prompt, model, schema and token cap. Native system text, metadata,
cache instructions, tools and transport settings must never become upstream input.
The upstream callback receives no native headers. It reserves one attempt before
dispatch, saves bounded complete raw response bytes, rejects tools and incomplete
output before delivery, and returns a newly built StructuredOutput stream only
after full validation. Missing usage stays unknown. Provider cache categories,
normalized totals and native CLI counters remain separate evidence.

Test reservation/fault windows, saved-byte recovery, conflicting repeats, malformed
results, model mismatch, forbidden content, incomplete usage and output bounds
without network or credentials. This increment supplies no production host/profile
admission and authorizes no provider call. Extend the loopback endpoint and host
integration only after the durable exchange contract is verified.

## Durable Anthropic exchange checkpoint

The new Messages exchange and endpoint now have distinct policy identities while
preserving existing Responses record shapes. They rebuild the frozen role request,
reserve one attempt before dispatch, retain bounded raw JSON, reject incomplete/
wrong-model/tool output and construct a new StructuredOutput stream only after
validation. Exact saved requests replay without another callback. Reported usage
is preserved separately for rejected handoffs. Missing categories stay unknown.

The combined source check passed 222 tests. Two actual native CLI probes through
the durable endpoint and an authored callback completed with verified stops and
unchanged recovery. Each recorded two HTTP connection attempts, one accepted
exchange and one callback. The missing-cache probe shows SDK zero-fill while the
broker keeps unknown totals. These are synthetic counters, not provider work.
No real key, provider, science or independent partition was accessed.

Evidence: examples/utility/verification-anthropic-exchange-v1. The final source
identity is b595972dc5e2e20320bb5b4b1c960c42b3dc7d98cd7ea8c103308e30dc83ced8.
Earlier source pins remain unchanged. A real upstream and credential/runtime
qualification, host records/admission, scheduler/factory/cost integration, actual
LLM conformance and all other full Part 5 gates remain open. Authentication profile
preference has been requested without granting or requesting live-call authority.

Durable exchange verification closeout: the fresh default suite passed 2016 tests
with 106 optional skips in 2145.54 seconds. All 364 frozen source/test files were
unchanged. Installed checks passed 46 exchange cases under a deny-all-sockets
guard and 13 endpoint cases under a separate loopback-only guard. The initial
combined guard mismatch is retained. Installed readers checked caller-pinned
archive bytes and recovered complete, missing-cache, owned-command and six failed/
uncertain exchange cases with original opens, sockets and subprocesses denied.
Optional scientific packages and the Anthropic SDK were absent.

The owned-command native probe verified both process stops and original response
recovery. Its incorrect initial driver enum is retained alongside the corrected
fresh run. Six fault fixtures explicitly observed zero replay callbacks while
preserving reservations and unknown states. These are authored local checks with
zero actual provider calls. The full Part 5 objective remains incomplete.

## Fixed API upstream increment

Implement a separately supervised, single-send Messages worker using a named
prepared API lease. Pin the API version and host/route. Validate the exact rebuilt
request before reading the lease. Keep real keys outside native client roots and
Git checkouts. Persist send intent before the possible request, retain conservative
unknown states on interruption, and never refresh, retry, redirect or fall back to
another authentication mode. The existing CommandUpstream owns local process time,
output and stop evidence. Local stop does not prove remote work stopped.

Use only synthetic leases and authored loopback/TLS peers for development checks.
Verify header/body limits, deadline, reflected-key redaction, malformed/private
files, expired leases, tampered source/policy, cancellation and original replay.
This implementation does not authorize reading a real credential or making a
provider call. Authentication preference and complete live conformance remain
separate unresolved choices.

## Fixed API upstream checkpoint

The explicit private API lease and fixed isolated Messages worker are implemented.
The lease reserves before reading and cannot be reused. The worker validates the
request before reading the lease, pins the helper source and API version, verifies
TLS, records send intent and never retries, redirects or refreshes. Original
response recovery does not open the lease. Every receipt keeps remote stop
unverified. Shared private-file opening now refuses FIFOs without blocking.

The final regressions passed 299 tests, including exact isolated command refusals,
verified local stops and original-byte recovery through an owned loopback TLS
fixture. Production command verification rejects the fixture routing shim.
Installed checks passed 52 cases under strict socket/process denial and six under
a separate loopback/process fixture policy. All 187 core wheel files matched.
Evidence and preserved failures: verification-anthropic-upstream-v1. Source:
5996c60747b6a39355a994d2cd7cf7b830c7088151f2640f05fd9770cf1a00ae.

No production host was admitted, real credential read or provider called. The
operator's authentication preference remains unresolved. Full boundary/resource
qualification, versioned records, scheduler/factory/cost integration and actual
authorized conformance remain required. The full Part 5 objective is unchanged.

## Owned Claude composition checkpoint

The native primitive, durable exchange, endpoint stops and broker usage now produce
one bound transport result. An immutable native job binding precedes the launch
gate. Original recovery and append-only stop captures perform no relaunch. Damaged
bindings still close the owned listener. Upstream process/remote stop remains a
caller obligation. Broker counters and native estimated costs remain separate.

Combined checks passed 169 tests. The installed wheel matched all 188 core Python
files and passed 24 composition cases. Actual Claude Code completed under the
candidate macOS policy with one authored callback and verified local stops.
Recovery returned the same result with zero added callbacks. Source:
bf795307c0b31643daa37651c6ea91fbbd1f2adc44c1fe5c4606c91f4a9b8eca.
Evidence and initial failures: verification-claude-composition-v1.

Host records, production admission, factory/scheduler/cost joins, full qualification
and actual authorized model conformance remain required. Part 5 is incomplete.


## Claude host/profile integration checkpoint

The provisional Claude/API adapter now has distinct version 3.0 selection,
capability schema 1.1 and configuration binding schema 1.1. Legacy fake/Codex
serialization and configuration digests remain unchanged. A separately versioned
qualifier requires every source/runtime/executable/model/API/limit binding and raw
indexed check. No actual Claude profile has been qualified by these fixtures.

Serial CLI/factory/scheduler dispatch, typed role validation, original-result
recovery and permanent batch accounting are implemented. The installed CLI
completed seven authored calls across all four roles. Resume added no calls or
changed worker bytes. Batch lost-acknowledgement recovery retained one charge.
Broker unknowns remain explicit. Native estimated USD and zero-filled counters
never replace them. Capabilities disclose the current platform, authentication,
remote-stop, billing and resource-cap limitations.

The final wheel matched all 190 core Python files and passed 29 installed checks.
The CLI test requires an explicitly exported repository fixture producer, public
lock and byte-identical source/resource mirror. Initial missing-producer and
missing-closure-layout failures are retained. This is not wheel-only preparation.
Evidence: examples/utility/verification-claude-host-v1. Source identity:
dd06d8ff96bed0d21b40134a4271307dce1d7a4552f8b28ffa19ce12da45e88b.

The fresh default suite is running under original session 5875. Source/test bytes
are fixed. Actual qualification, Claude conformance preparation/handler and live
model authority remain open. The existing conformance commands keep their Codex
protocol. Real task routes, full cost/effort, independent data/custody, scorer,
protocol and Linux requirements remain incomplete. No real credential or provider
was accessed. This checkpoint does not close G6 or the full Part 5 objective.


## Host increment verification closeout

Original default session 5875 completed with exit zero: 2127 passed and 106 skipped
in 1811.17 seconds. All 363 pinned source/test files were unchanged. Current-source
limited kernel/help and actual native-composition probes also passed, with one
authored callback, verified local stops and zero replay callbacks. A trusted driver
additionally measured all 19 synthetic syscall controls with the Claude renderer,
including owned environment, synthetic plist and shared-memory controls. The shared
object was unlinked and owned carrier stopped. Executable substitution and runtime
renderer hooks remain explicit. Actual preference-service privacy and complete
host qualification remain unverified. No real preferences, key or provider was read.

Terminal records, raw driver source, byte archives and source bindings are under
examples/utility/verification-claude-host-v1. Earlier running-status paragraphs are
historical checkpoints. This closeout applies to source identity
dd06d8ff96bed0d21b40134a4271307dce1d7a4552f8b28ffa19ce12da45e88b.
Task/exposure reconciliation changed metadata only. No independent task, private
scorer, protocol, Linux, actual-model conformance or full Part 5 gate is closed by
these checks. Next software work includes independent wind-resource ingestion and
its protected confirmation path, plus the Claude conformance package/handler.


## Claude conformance preparation increment

The versioned preparer now accepts the explicit Claude 3.0/API profile under
preparation schema 1.1 and a separate protocol digest. It captures only the fixed
public scalar campaign after checking the caller-pinned qualification and host
configuration. No credential is opened, runtime created or clock started. The six
cases retain fixed outer allowances of thirteen host calls and two science starts.
API criteria preserve remote-stop uncertainty and separate local stop evidence.

All Claude execution handlers remain missing. Inspection reports them and returns
execution_ready false. Direct runtime creation and resume refuse before batch
allocation. Cross-profile schemas, protocol/case pins and host configurations are
refused. Existing Codex preparation and runtime regressions are checked separately.
Actual qualification, a complete executable live package and explicit live authority
remain open. This is preparation software only and does not close G6 or Part 5.


## Claude conformance runtime increment

Runtime schema 1.1 now selects BatchClaudeHost for text, all four roles, timeout,
cancel and malformed-output repair. A separate fixed-Anthropic evidence reader
binds original model/lease/path, API version, route, intent and response bytes.
It opens no credential and dispatches no work. Local stopping and remote
completion stay separate. Missing usage categories stay unknown. Runtime origin
versions distinguish the existing Codex path from the new API path.

Owner loss remains unimplemented. The ordered runtime stops before it and the
report stays incomplete. The malformed handler is checked in isolation after an
explicit unit-only owner verdict. That test does not establish owner-loss behavior.
A missing implementation prevents live_conformance_complete even if fixture case
verdicts all say passed. Positive authored provider-proof stubs are also rejected
as live evidence. Actual qualification and any live calls remain separate gates.


## Claude owner-loss implementation

The remaining conformance handler now holds the fixed API worker before lease
preflight and interrupts only its owned supervisor. Claude's separate abandoned
reader verifies original native inputs/job binding, API exchange/request, fixed
worker sources, both watchdogs and absence of their shared supervisor. It never
launches, signals, opens a lease or contacts an old endpoint. Partial completed
records need their normal decoder. Unknown usage, duration and resolved model
remain unknown and the permanent reservation remains charged.

All six Claude handlers are implemented. execution_ready describes that software
availability, not actual qualification or live authority. Authored native/profile
and provider-proof fixtures remain distinct from the owned worker/watchdog tests.
No actual provider or real credential is used. The complete Part 5 gates remain
open, including actual qualification and independent scientific confirmation.


## Owned CFPreferences domain observation

A new current-source diagnostic targets one generated synthetic user-domain key.
The control can read it with the native private HOME environment; the substituted
probe under the Claude policy cannot. Owned processes stop. The key is cleared.
Asynchronous plist flush initially prevented bounded empty-file deletion. Original
failures remain. Caller-pinned cleanup reconciliation verifies original process
and control records, removes only the empty owned file, and starts no new probe
or CFPreferences call. Watchdog process-observation helpers remain explicit.
All generated domain files are now absent.

Claude qualification 1.1 requires preferences.owned_user_domain_canary_not_visible
in addition to the previous checks. Version 1.0 and a missing service-domain check
are refused. Codex requirements are unchanged. This substitutes a canary executable
and does not qualify actual native preference behavior or a complete host. No
actual qualification, key, provider or independent confirmation was used.

The final 135 profile/host/preparation/canary/documentation checks and Ruff passed.
Raw controls, failures, cleanup receipts and source snapshots are preserved under
examples/utility/verification-claude-preferences-v1. Full Part 5 remains incomplete.
