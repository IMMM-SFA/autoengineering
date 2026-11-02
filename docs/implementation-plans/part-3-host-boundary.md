# Production host boundary

__Status:__ implementation remains open. No live provider call, real credential inspection,
installation or global configuration change is authorized by this plan.

The parent [Part 3 plan](part-3-multi-agent-system.md) requires a production host, separate from
the qualified generated-code container boundary. The current Codex transport and event parser
remain prototypes. Rejecting a tool event after execution is not a privacy boundary.

## Current evidence

A fresh sanitized `--version` / `exec --help` inventory found `codex-cli 0.164.0` with executable
SHA-256 `f074c44dfc697b4790284a0f839e090c87f5e54b24b7803be85e46f63a90dc5a`.
Inventory and raw help:
`/private/tmp/part3-current-codex-inventory-fx1fotfo/`.
The probe used nonexistent `HOME` and `CODEX_HOME` locations and made no model request.

The installed help says `--ignore-user-config` skips `CODEX_HOME/config.toml` while authentication
still uses that home. `--ignore-rules` skips user/project execpolicy rules. It must not be treated
as proof that all project context, hooks, plugins or MCP surfaces are disabled.

The current [permission profile documentation](https://learn.chatgpt.com/docs/permissions) states:

- Legacy `--sandbox` settings override ordinary named profiles. The current prototype always
  supplies `--sandbox read-only`, so it cannot gain a restricted profile merely by adding config.
- Profiles constrain sandboxed local commands. Their network proxy does not govern Codex model,
  authentication or other service traffic, hosted search, MCP servers, apps or browser surfaces.
- A restricted profile can deny root reads and grant minimal runtime paths plus the staged
  workspace. A network-enabled profile also needs an active proxy to enforce domain rules.

These are documented capabilities, not qualification evidence for this application. Permission
profiles are beta. Version, effective configuration and enforcement must be checked together.

The [authentication documentation](https://learn.chatgpt.com/docs/auth#alternative-model-providers)
describes custom-provider OpenAI authentication through a proxy. The
[self-hosted security guidance](https://developers.openai.com/api/docs/guides/agents-api/environments/security#broker-third-party-access)
describes keeping secrets outside an untrusted environment through a trusted proxy. This supports
investigating a brokered credential design. It does not establish subscription endpoint details,
authorize reading an account's credentials or prove a local proxy implementation works.

## Required implementation and gates

1. Resolve an explicit versioned launch profile for the installed CLI. Do not combine named
   profiles with the legacy sandbox argument. Keep old transport receipts and their identities
   readable. Record exact effective options, executable bytes and policy bytes.
2. Stage only approved brief/schema/source bytes. Use a private host home with no ambient user
   configuration, history or unrelated credentials. Independently verify every context/tool surface
   that the installed client can activate. Source generation can remain a bounded text response.
3. Qualify command filesystem restrictions with private canaries for checkout, evaluator, labels,
   credentials, symlink traversal and writes. Verify the actual platform mechanism, not a prompt
   or event-filter claim. Block privilege escalation and undeclared subprocess/tool authority.
4. Enforce client service egress separately from command network policy. Use an external OS or
   broker boundary with fixed approved endpoints. Verify direct connections, localhost/private
   services, Unix sockets and bypass attempts. Keep real credentials out of worker-readable
   artifacts, prompts and transcripts. Prefer a credential broker if the client/tool separation
   cannot meet that condition. Do not guess subscription protocol details.
5. Exercise the actual installed CLI against a deterministic local fake service when possible,
   including malicious tool requests and canary reads. Use only synthetic authentication. Qualify
   startup, bounded capture, timeout, cancellation, parent death, saved-output recovery and
   duplicate-request exclusion. Retain unsupported cases and failed probes.
6. Expose the production scheduler adapter only after its boundary receipt is pinned and verified.
   Keep physical host invocations, any observable service requests, token uncertainty and scientific
   attempts separate. Do not silently translate a transport retry into a free new model call.
7. Prepare a concrete live conformance packet with explicit model, account/auth mode, host-call
   allowance, time/output limits and stop/recovery cases. Obtain the separate live authority required
   by the parent plan before using real authentication or calling a provider. Then complete the
   matched single-agent/four-role Leaf River design under its own approved scientific budget.

The existing macOS generated-code memory-limit failure remains adverse evidence. It does not
qualify this host boundary. The generated-code Docker qualification and authored CLI/source
fixtures cannot substitute for host isolation, real-host conformance or the matched pilot.

## Command profile composition probe: failed

`examples.agent_campaign.probe_command_profile` stages synthetic brief, label, credential and
symlink canaries in a private home/workspace. It selects a restricted native profile without a
legacy sandbox argument. An outer Seatbelt policy denies all networking for the complete CLI
process tree. The existing owned-process supervisor bounds time/output and records stop receipts.
It cannot qualify service egress or real authentication, even if its filesystem probes pass.

The final probe at `/private/tmp/part3-command-profile-20261026/final-probe` failed its approved
read before reaching a privacy test: `sandbox-exec` reported `sandbox_apply: Operation not permitted`.
The positive control is mandatory. Remaining denial cases are marked not attempted, not passed.
The exact probe source, policy, config, process ownership and raw result are retained there.

Direct network-denied echo controls passed with and without a new session. The combined
Codex/native-profile invocation failed independently of the supervisor, also with and without a
new session. Controls are recorded in `controls.json` and `composition-controls.json` under the
same parent. These observations establish failure of this composition in the tested environment.
They do not establish a general platform limitation or a working privacy boundary.

Do not remove the network restriction or reinterpret startup failure to obtain a passing score.
Investigate a single externally enforced host boundary, or another composition that passes an
approved baseline under the full intended restrictions. Native-profile documentation alone cannot
close this gate. Live scheduler dispatch remains disabled.

## Single external boundary: initial evidence

`examples.agent_campaign.probe_external_boundary` uses one deny-by-default Seatbelt policy around
the complete process tree. It grants staged workspace reads, scratch writes, exact probe binaries
and required system runtime reads. It grants no Mach services, ambient home, checkout, evaluator
or private source access. The exact root-directory read required for runtime startup does not
grant descendant reads. System curl also requires the exact public OpenSSL configuration file.
These grants were isolated with fixed-command controls before testing private canaries.

The final fixture at `/private/tmp/part3-external-20261026/verified` passed 15 checks in 1.00 seconds:
approved brief, installed CLI version, child approved read, private label/credential/evaluator
reads, checkout source, symlink escape, child private read, workspace write denial, scratch write,
and TCP/Unix socket controls and denials. Each network control runs the same fixed local HTTP
command under the same filesystem restrictions, with a separate network-enabled control policy.
Each listener received exactly its one control request. All launched processes and both listeners
stopped. No provider or real authentication was used. The receipt keeps host qualification false.

`examples.agent_campaign.probe_external_codex` selects a custom offline provider with an owned
fake Responses service and no authentication. The external policy permits only the selected
localhost port. Codex's internal command sandbox is bypassed inside this external boundary to
avoid the failed nested composition. This option is not exposed by the production scheduler.
The [custom-provider documentation](https://learn.chatgpt.com/docs/config-file/config-advanced#custom-model-providers)
supports configuring a base URL and wire protocol. An authored response does not establish real
provider or subscription compatibility.

The final client fixture at `/private/tmp/part3-external-20261026/client-verified` failed with
`Failed to synchronize managed preferences (code -32600)`. It launched one bounded client,
stopped it, and observed zero fake-service requests and zero provider calls. Earlier controls
separately identified supported Seatbelt localhost syntax and the exact `/etc` symlink read needed
to observe the checked-absent system requirements file. Raw results remain in the same parent.
The temporary Codex home also produces a helper-alias warning, which remains visible.

The [managed-configuration documentation](https://learn.chatgpt.com/docs/enterprise/managed-configuration#locations-and-precedence)
confirms that macOS managed preferences are a separate configuration layer. It does not establish
which missing operation caused this failure or justify a general preference/service grant.
The next step is to identify and bound those startup dependencies, then exercise the real client
against the fake service, including malicious tool requests. General Mach access, ambient home
reads and removal of egress restrictions are not acceptable fixes. Socket grants, tool surfaces,
credential separation, process/resource limits and the full host lifecycle still need qualification.

Two further diagnostic policies remain separate from the example's default policy. A grant for
read-only `com.openai.codex` preferences plus the two exact cfprefsd service names still failed
before a request. Adding Apple's `apple.cfprefs.` read-only shared-memory dependency allowed
client startup and one fake-service response. See `client-managed-read` and `client-managed-shm`
under `/private/tmp/part3-external-20261026/`. Exact diagnostic scripts and policies are archived
with their receipts. Neither grants preference writes or general Mach lookup.

The second diagnostic exited zero but still failed the adapter gate: Codex emitted an error item
because `part3-offline-fixture` has no catalog metadata. The event parser correctly rejected that
transcript. The saved request advertised eight tools, including command execution, image reading,
multi-agent and goal tools. No tool was requested by the authored response. This establishes an
offline request/response path, not a permitted-tool boundary. The next client fixture must use
explicit offline model metadata without weakening error parsing, and test malicious tool requests
under an enforceable policy. Preference-domain and shared-memory access also need their own
negative checks before any production qualification.

## Pre-delivery text exchange

The current offline fixture completes cleanly with `gpt-5.5` catalog metadata found in the exact
installed executable. This is a local authored service, not evidence of access to that model.
The initial `gpt-6.1-sol` attempt required an unavailable Code Mode helper. Its error remains
preserved. Optional execution features are disabled using the installed feature inventory.
Native requests still advertise tools, so configuration alone is not treated as enforcement.
The [catalog documentation](https://learn.chatgpt.com/docs/model-catalogs) explains why names and
capability metadata must match the client. No helper was installed and no account was queried.

`hosts.response_boundary` checks a complete SSE response, bounded to 512 KiB, before returning any
normalized client bytes. It rejects actionable items, unsupported events, malformed streams,
contradictory usage and oversized text. It rebuilds a text-only stream from approved assistant
content. Raw upstream bytes remain separate from normalized bytes. This is a deliberately bounded
single-turn transport boundary, not a general streaming gateway or agent runtime.

`hosts.text_exchange.TextExchange` binds an invocation, source identity, model, approved prompt
and output schema in a private immutable manifest. It rebuilds the upstream request from those
approved inputs, with no native tools, ambient client context, cache keys or client metadata.
It saves a one-request dispatch intent before invoking the trusted upstream callback. Saved raw
responses can be verified and normalized after acknowledgment loss. Unknown outcomes never retry
the callback. Changed requests, source drift, corrupt records and orphan response artifacts fail
visibly. Oversized responses retain a bounded prefix. Transport error text is not persisted because
it may contain credentials. The callback's credential, timeout and egress enforcement remains a
separate caller responsibility.

The final fixtures are under `/private/tmp/part3-host-guard-20261026/`:

- `final-text` completed the installed CLI through the reusable exchange. One local service request
  produced one authored upstream response. Only the exact approved brief/schema reached that callback.
- `final-control` deliberately bypassed response validation with execution enabled inside the OS
  boundary. The authored tool response created its scratch marker, and its follow-up request was
  rejected. Both observed HTTP attempts remain visible.
- `final-blocked` used the same client execution permissions. The exchange retained and rejected
  the identical tool response before delivery. No marker or actionable client response was produced.

All three processes stopped. No real authentication, provider call or scientific evaluation occurred.
The control is diagnostic only. Production scheduler dispatch remains disabled. The response guard
does not qualify preference/shared-memory privacy, local endpoint authentication, provider routing,
resource ceilings, parent-death handling or cancellation of an upstream request. Those checks,
the versioned production scheduler adapter, live conformance and matched pilot evidence remain open.

## Packaged invocation endpoint

`hosts.text_endpoint.TextEndpoint` now serves the durable exchange, without provider credentials
or a built-in provider connection. It binds loopback only and an opaque invocation route. Reports
retain the route digest rather than the bootstrap URL. It rejects credential headers, foreign
routes/hosts, duplicate lengths and unsupported framing. Headers are limited to 16 KiB, body bytes
to 512 KiB and accepted connections to a frozen count. One absolute input deadline applies across
request line, headers and body, including slowly dripped bytes. Exact request retries can replay
saved normalized bytes without another upstream callback.

Shutdown closes the owned listener and client socket and records listener, handler and local
callback states separately. A callback still running after the stop deadline leaves stop unverified.
A callback returning does not prove remote provider computation stopped. The current thread-based
endpoint must not be mistaken for hard callback supervision or parent-death qualification.

Ten endpoint tests cover route/framing limits, credential-safe rejection, exact retries, request
exhaustion, absolute read deadlines, active-callback uncertainty, partial-header shutdown and
transport errors. The installed CLI passed through the package endpoint in
`/private/tmp/part3-endpoint-20261026/final-text` and `final-blocked`. The separate `final-control`
retains the authored scratch-write positive control. All local stop flags are true in the two
package-endpoint fixtures. One local request invoked one authored callback in each case. No
provider or scientific call occurred.

The final default suite passed 949 tests with 65 skips. An installed-wheel smoke verified replay
and two HTTP requests with one callback. Its first bind attempt was denied by the outer task
sandbox. The same wheel passed with explicit loopback access and fresh runtime directories.
Evidence: `/private/tmp/part3-endpoint-install-k5jk8dcw/receipt.json` and
`/private/tmp/part3-endpoint-20261026/source-snapshot.json`.

Next, add a separately versioned brokered CLI transport and recovery decoder, retaining the old
transport contract. It must bind the endpoint, exchange and native process receipts, apply the
whole invocation deadline, and preserve unverified callback stops. Hard broker ownership and
parent-death behavior need their own tests. The trusted upstream transport still needs fixed
endpoint/credential policy and bounded, unretried requests. Only after those checks and host
qualification can the production scheduler and live conformance packet advance. No live authority
is inferred from these local fixtures.

## Version 2 brokered CLI transport

`hosts.codex_brokered` now composes the CLI supervisor, package endpoint and durable exchange.
The original version 1 transport is unchanged. Version 2 requires separate capability inspection,
a fresh credentialless client home, a caller-supplied OS wrapper and a captured launch manifest.
The wrapper digest identifies a policy; it does not establish qualification. Declared policy bytes
are captured separately. Effective CLI options, native job/input hashes, schema, endpoint binding,
source identity, model and output/time limits participate in recovery.

The exchange has an internal ID derived from the physical nonce and invocation directory. A reused
logical call number in another run cannot substitute its exchange. Native output must match the
validated broker text, and reported model/usage come from the saved upstream response. Unknown
cache counts are not replaced with client zeroes. Whole invocation timing includes preparation.
An explicit 0.2-second stop grace is recorded and counted in elapsed time. Exceeding the deadline
cannot produce a successful handoff.

Read-only recovery verifies native completion and process-group absence, endpoint metadata,
linked stop captures, original outcome, schema/prompt and exchange policy. Corrupt or foreign
receipts fail. Later endpoint stop captures can resolve an active callback without rewriting the
original uncertain outcome. No CLI, callback or provider is invoked by recovery. Missing native
completion or an unverified native stop still requires separate ownership reconciliation.

Four installed-CLI fixtures passed under `/private/tmp/part3-brokered-20261026/`: `final-text`,
`final-tool`, `final-lost-ack` and `final-timeout`. The last case first reported
`reconciliation_required`, then recovered the original timeout after the authored callback was
released and stopped. Each final fixture used one client and one authored callback. Every replay
left the saved tree unchanged. No real provider, authentication or scientific evaluation was used.

The final default suite passed 965 tests with 65 skips. The installed wheel recovered all four
outcomes without new calls. Evidence is in `source-snapshot.json` under the fixture parent and
`/private/tmp/part3-brokered-install-zd7jmnkm/receipt.json`.

This SDK is not registered with the production scheduler. Hard broker process ownership,
parent-death handling and the fixed upstream credential/network/deadline policy remain next.
Then bind the qualified adapter into worker records and recovery, finish platform qualification,
and prepare the separately authorized live conformance and matched Leaf River comparison.

## Owned upstream command and independent watchdog

`hosts.command_upstream` now supplies a one-shot trusted command callback for `TextExchange`.
It records a fresh nonce and fixed argument vector, hashes the declared executable/source files,
uses private request/response files and a sanitized environment, and rejects changed sources.
Executable and declared script paths are resolved before capture and launch. Retargeting their
original symlinks cannot select a different executable or script.
The absolute monotonic deadline includes preparation. Captured diagnostics are limited to 8 KiB
and accepted response bytes to 512 KiB. A failed, late, partial, empty, symlinked or oversized
response cannot become a successful delivery. Existing attempts cannot launch again.

The opt-in supervisor starts a standalone watchdog before opening its launch gate. The trusted
trampoline retains its nonce-bearing group leader while descendants remain, including through
SIGTERM. The watchdog checks PID, PGID, start time and nonce before each signal. Owner loss or
deadline expiry triggers bounded TERM/KILL cleanup. An observation or ownership failure records
uncertainty instead of signaling an unrelated group. Version 1 and the version 2 native-client
supervision mode remain unchanged. Native-client parent death still needs a separate increment.

Read-only recovery verifies watchdog job/receipt/source bindings and current group absence.
Complete upstream recovery also checks command/environment, request/response hashes, response
ownership and acceptance before the deadline. Lost final acknowledgment can recover saved response
bytes. Missing response receipts remain unresolved even when a watchdog proves the local group
stopped. Local stop evidence cannot establish remote provider cancellation or reconstruct usage.

The installed CLI passed four fixtures with `--process-upstream` under
`/private/tmp/part3-owned-upstream-20261026/`: `final-text`, `final-tool`, `final-lost_ack` and
`final-timeout`.
The timeout case stopped its authored process without a manual callback release. All final local
stop checks passed, and replay changed no fixture bytes. The isolated installed wheel also
recovered each fixture and ran one new authored command. No real provider, credential, scientific
run or production scheduler dispatch was used. Source archives and exact fixture receipts are
in that directory's `source-snapshot-final.json`. Installed evidence is at
`/private/tmp/part3-owned-upstream-final-install-rf3g1z84/receipt.json`.
Earlier pre-resolution fixtures and source snapshots remain alongside the final evidence.

The fixed provider implementation, credential policy and egress allowlist are still missing.
The command primitive provides local lifecycle supervision and bounded capture, not filesystem,
network, disk, CPU, memory or remote-compute containment. Complete host qualification and
production integration remain required before live conformance or the matched Leaf River pilot.

### Next lifecycle acceptance checks

Before enabling watchdog supervision for the native client, define a new transport profile and
recovery contract. Preserve the current native job schema. A startup deadline or missing watchdog
readiness must produce a recoverable terminal or explicitly uncertain record without opening the
launch gate. An owner callback that blocks past the deadline must not launch native work later.
Use an inherited pipe lease for owner loss so watchdog behavior does not depend only on PID and
second-resolution process start time. Keep nonce/start/group checks before target signals.

Exercise parent death before readiness, before the launch gate, during native execution and during
an upstream request. Check all surviving groups and endpoint state independently. Test a target
that exits while descendants remain, TERM-resistant descendants, competing supervisor cleanup,
failed ownership observation and lost final receipts. Missing native completion must not turn a
watchdog stop into a fabricated successful role response. Recovery cannot relaunch either side.
Only after these cases and the real transport policy pass can scheduler registration advance.

## Native profile 2.1 and inherited owner lease

The opt-in `owned_native=True` SDK path selects `codex-text-2.1`. Its native command uses the same
watchdog supervisor as the upstream command. The default version 2.0 native job and version 1
behavior remain unchanged. Recovery derives the expected native job schema from the profile,
requires the owner-lease fields for 2.1, and rejects a downgraded or foreign job.

The owner alone retains the write end of an anonymous pipe. Only the trusted trampoline and
watchdog inherit its read end. Command executables inherit neither end. EOF detects owner loss
without depending on owner PID/start-time reuse. The worker checks the lease while waiting for
the launch gate and immediately before launching. An independent watchdog is ready before the
gate can open. It still checks the target nonce, start time and process group before signaling.
A closed lease with no watcher yet cannot authorize the command to start.

Known trampoline spawn errors now record a stopped failure with no process identity. Failed
watchdog spawn/readiness records its direct child's verified stop or known failed spawn in an
immutable abort receipt. Startup deadline expiry returns a timeout, and a late ownership callback
or newly queued cancellation cannot open the gate. Abort recovery requires the gate to remain
absent and verifies job/source bindings and current group absence. Callback exceptions still
retain failure evidence and propagate. None of these cases can produce a successful role response.

The installed CLI passed `final-text`, `final-tool`, `final-lost_ack` and `final-timeout` with
`--owned-native --process-upstream`. `final-death` kills the actual offline fixture supervisor
during an authored upstream request. Both process groups stop, the endpoint socket closes, and
recovery refuses missing native completion. These are local lifecycle observations, not remote
provider cancellation or live scientific evidence. Source archives and receipts are under
`/private/tmp/part3-owned-native-20261026/`.

The 118-test focused host suite passed. An isolated installed wheel rechecks the saved trees and
both death-probe stop receipts, refuses missing completion, and runs one new authored command.
Production registration remains disabled. The fixed provider transport and credential/egress
policy, full host resource/privacy qualification, pending worker reconciliation and independently
authorized live conformance/pilot remain unfinished.

## Fixed subscription worker and synthetic credential checks

The [official authentication documentation](https://learn.chatgpt.com/docs/auth) distinguishes
ChatGPT subscription sign-in from API-key access. The
[official gateway route](https://learn.chatgpt.com/docs/enterprise/sign-in-with-chatgpt-through-a-gateway)
identifies the Codex backend and bearer/account headers. The new worker fixes its HTTPS destination
to `chatgpt.com:443/backend-api/codex/responses`. It does not switch to an API key or a different
provider. This is protocol implementation evidence, not proof of account access or service acceptance.

`ScopedSubscriptionUpstream` creates a source-bound policy and uses the existing owned command
supervisor. A separate, explicitly supplied lease file remains outside the attempt and declared
client roots. No existing auth cache is selected or opened. The worker opens physical directory/file
descriptors without symlink traversal and requires an owner-private, regular, single-link file.
It checks the lease ID and declared expiry. Token refresh, native auth-cache conversion and real
credential preparation remain unfinished. The lease format belongs to this package, not Codex.

The standard-library worker sends one approved, digest-bound request. It checks the model, exact
request fields, user brief shape, no tools, `store: false` and strict output-schema format.
It uses certificate/hostname verification and TLS 1.2 or later, inherits no proxy environment,
and implements no redirect, authentication refresh or HTTP retry. There is no CLI endpoint override.
The production HTTPS path has not been executed. These code-level restrictions do not qualify the
OS network boundary or actual TLS behavior against the service.

Incoming headers are limited to 16 KiB, decoded response bytes to 512 KiB and total HTTP parser
bytes to their sum, including chunk framing/trailers. Ambiguous framing and compressed responses
are rejected. Credential reflection is checked both as raw bytes and decoded SSE JSON, including
no-space, multiple-space and multiline data fields. Response bytes are written only after checks.
Error bodies and raw exception text are not persisted. Static phase/status/byte receipts retain
request uncertainty and unknown usage. An intent is not proof that the provider accepted a request.

The installed CLI passes text, tool rejection, lost acknowledgment and in-flight timeout through
an explicitly authored loopback HTTP factory with synthetic credentials. That test factory is not
available through the production worker CLI and its records fail the production subscription
decoder's fixed-command check. Each fixture checks that client artifacts contain no synthetic
credential values. The 0.5-second development timeout stopped during preflight with zero HTTP
requests and is preserved. A fresh 1.5-second fixture proves an actual authored request timed out
and stopped before the server was released. No frozen scientific gate or resumed budget changed.

The final focused host suite passed 156 tests. Read-only decoder unit tests supply the separate
process proof explicitly, so they do not count as production HTTPS recovery evidence. Actual owned
worker tests cover an authored connection, reflection rejection, slow headers, failed lease and
cancellation. The installed wheel replays the four saved fixture trees, refuses to label the authored
factory as production, and runs the actual fixed worker only through a deliberately invalid lease
preflight. Full production HTTPS, real credential preparation, OS egress/resource qualification,
worker dispatch/reconciliation and separately authorized live conformance/pilot remain required.

## Explicit source preparation, recovery and loopback TLS

The [official managed-auth CI guide](https://learn.chatgpt.com/docs/auth/ci-cd-auth) documents the
managed ChatGPT cache fields and leaves refresh to native Codex. `prepare_subscription_lease`
therefore accepts only an explicitly supplied absolute source, expected account, expiry and
client roots. It never selects `~/.codex`, reads environment credentials, logs in, refreshes,
updates the source or contacts a service. Real-cache compatibility is still unverified.

The parser recognizes a bounded managed-cache field set and rejects API-key/external-token modes,
unknown fields, missing refresh metadata, account mismatch, source rotation and unsafe files.
This package's independent policy requires a refresh timestamp no more than seven days old and
an explicitly declared lease longer than 30 seconds and no longer than 900 seconds. These bounds
do not prove actual token expiry or server validity. Refresh/ID-token fields are not copied.
Source and destination stay outside declared client roots. Lease destinations cannot be in Git
checkouts. A fresh destination is reserved before reading secrets and never reused after failure.
The source remains unchanged, and commit receipts contain no credential value or secret hash.

`recover_prepared_subscription_lease` reads only the prepared lease and its scope-bound commit
receipt. It never reopens the managed cache, changes expiry, selects another account, refreshes
or writes files. Missing/partial receipts, expired leases and copied foreign scopes are rejected.
The original caller's account and expiry expectations remain required during recovery.

Real loopback TLS tests use a private ephemeral fixture CA. They add that CA only to the test
connection's context and leave certificate/hostname verification enabled. The approved request
succeeds over TLS, while an untrusted CA and a hostname mismatch fail before the HTTP fixture
observes a request. The receipts still retain conservative request uncertainty and unknown usage.
This is local TLS evidence, not production endpoint, system trust-store or account qualification.
No global CA configuration changes, real auth reads or production requests were made.

All four offline installed-CLI fixtures now prepare their synthetic lease from a synthetic managed
cache, verify unchanged source bytes, exclude refresh/ID tokens from the lease, and exclude every
synthetic credential value from client artifacts. Their authored HTTP factory remains distinct
from the production transport. The isolated wheel repeats 32 preparation/recovery/TLS tests and
replays the four saved trees without another native client or provider request.

Next, bind the remaining native host qualification and capability evidence to the actual runtime
(including OS/TLS environment), finish worker dispatch and pending-invocation reconciliation behind
that gate, and assemble the concrete live-conformance/pilot approval packet. The original plan
requires bounded host time/transcripts/workspace and separate generated-code resource enforcement.
The generated Docker boundary's frozen memory/CPU/process gates remain unchanged. Do not add an
unrelated host memory gate or relax an existing generated-code gate to advance this increment.

## Qualification-gated scheduler adapter

The experimental `BrokeredCodexHost` now connects the owned version 2.1 transport to the serial
scheduler. The run selection pins a native qualification digest before dispatch, and the journal
checks each capability receipt against it. Legacy selections keep their original serialization.
The adapter stages fresh client directories, uses the package's fixed macOS policy, wraps strict
transport output around the core role handoff and preserves separate raw/normalized artifacts.
Preparation consumes the original deadline. Provider-aware recovery verifies the original
context and restores saved model/usage without another native client or provider request.

The native-profile reader binds the source, policy, exact binary, OS/Python/TLS environment, public
trust roots and limits. It verifies pinned attestation reports and all referenced artifacts. It
does not run probes, and authored reports do not establish OS permissions. Current decoder tests
and adapter fixtures explicitly substitute qualification. No production profile is available.

An actual installed-CLI fixture ran all four serial roles through the scheduler with the fixed
macOS policy and authored responses. Seven client invocations produced two synthetic scientific
attempts. Replay started no new work. The receipt reports `host_qualified: false`, no real
credentials and zero provider calls. This proves offline integration, not live conformance.

Next, implement and review the real qualification procedure. It must exercise private-file and
symlink canaries, disallowed TCP/Unix endpoints, credential separation, tool-response rejection,
lifecycle faults and the declared time/transcript/workspace bounds. The writable native home and
the required preference service access need explicit privacy and size evidence. Incomplete
parent-death receipts must stay pending until ownership and outcome are safely reconciled.
Then wire explicit qualification/lease configuration into the CLI and prepare the frozen
live-conformance/pilot approval packet. The public CLI remains closed until those gates pass.

## Synthetic syscall evidence

`hosts.native_canaries` now compiles a fixed trusted C probe with the existing compiler driver.
Unrestricted controls prove that the synthetic paths and TCP/Unix listeners work. The same probe
under `render_native_policy` passes fifteen permission checks, including private/cache/lease
reads, outside/workspace writes, symlink escapes, forbidden TCP/Unix connections and another
executable. Allowed brief/home/endpoint controls succeed. Only permission errors count as denials.
All private canaries remain unchanged, listeners and owned groups stop, and no provider is used.

The policy's executable literal names the probe instead of Codex. This is partial policy evidence,
not native-client qualification. A pinned reader verifies raw artifacts, exact commands and
environments, source/runtime/binary bindings and watchdog/process stops. It performs public runtime
inventory and process inspection but reruns no compiler or canary. Foreign scopes and corrupted
artifacts fail. Neither this reader nor the native-profile reader upgrades partial evidence into
a qualified profile. The public CLI dispatch gate is unchanged.

The remaining preference review should start from the pinned upstream implementation. The
[0.164.0 macOS loader](https://github.com/openai/codex/blob/rust-v0.164.0/codex-rs/config/src/loader/macos.rs)
accepts only forced values for `config_toml_base64` and `requirements_toml_base64` in
`com.openai.codex`. It checks whether each value is forced before copying it, then checks again
afterward. Ordinary user defaults are excluded. This source audit does not establish the current
machine's managed state or prove preference-service isolation. A possible next step is a bounded
boolean-only absence check that never copies preference values, followed by actual service-boundary
tests. Do not infer absence, read real values or broaden the existing grants from this audit alone.

## Preference isolation result and strict candidate

The follow-up measurements identified a real capability excess. The broad `apple.cfprefs.*`
read grant allowed the confined syscall probe to map an unrelated synthetic object with that
prefix and verify its public payload. No real preference object or credential was read. The
0.164.0 client completed the authored workflow without `user-preference-read`, but startup failed
when shared-memory reads were removed or limited to metadata. The policy language rejected a
`preference-key` filter. A boolean managed-preference absence check would not contain the broader
shared-memory capability, so that proposed workaround was not implemented.

An inventory found an existing 0.155.1 executable with all required brokered flags. A fresh
four-role fixture with that explicit binary passed with every preference-service and shared-memory
grant removed. No binary was installed and no global selection changed. The exact SHA-256 is
`26d4d42df9846aaeedce4a9c8c7cfa9e209fc8710fb2ab2b972a151c79463600`.
This establishes offline interoperability for that binary, not general release compatibility or
provider/model access. Existing worker runs cannot change their pinned executable on resume.

The fixed package policy now grants no preference reads, cfprefsd lookup or shared memory. The
new 1.2 qualification schema requires denied private/workspace CoreFoundation reads and denied
unapproved shared-memory access. Eighteen actual permission observations passed. Their unrestricted
controls prove that the synthetic plist sources and shared-memory object work. The owned object
is removed, and recovery checks its absence without creating or mapping another object.

The earlier 1.1 prototype required a successful CoreFoundation read of its workspace plist. The
strict policy denied that API along with the private read, while retaining ordinary approved file
reads and working native text. Version 1.2 therefore specifies a different, stricter service scope:
all preference-service reads are forbidden. The original filesystem/network requirements remain.
Both failed 1.1 records are preserved, and neither the earlier policy nor the 0.164.0 candidate is
reported as passing. No scientific or historical benchmark criterion changed.

Next, complete lifecycle/transport qualification using this exact binary and strict policy, assemble
the source-bound native profile, and then expose explicit pinned configuration in the CLI. Real
credential/provider conformance and the matched pilot still require their concrete approval packet.

## In-flight abandonment reconciliation

The adapter can now retire a verified abandoned invocation as `host_failure` with unknown model,
usage and duration. The original call remains charged. Both source-bound watchdog proofs must
establish group absence and the same original supervisor identity. A successful PID/start-time
observation must establish owner death. Native ownership must match the worker journal, and the
saved approved request must match the exact fixed upstream request/command. No old port is
contacted and no PID is signalled. The physical evidence is unchanged.

The subscription verifier restricts the worker to its exact package path and three declared
sources before reading attempt sources. It rejects extra files and credential aliases, without
opening the lease or response. The production adapter also checks the original model, lease ID
and credential-path metadata. Existing completed SDK records keep their normal decoder and
corruption checks. The new branch covers in-flight death before native/SDK result commits. Gaps
without complete ownership proof remain pending, rather than causing a replacement call.

The actual explicit 0.155.1 native fixture passed this journal path under the strict policy. The
upstream stayed gated before credential preflight, no provider request was possible, and both
groups stopped after killing only the fixture supervisor. Qualification was stubbed. This is
recovery evidence, not a qualified native profile or real-provider conformance. Next, assemble the
complete profile and wire pinned configuration into the CLI, retaining visible pending states
for any physical gap that still lacks proof.

## Offline native profile assembled

The version 1.3 producer now passed all nine groups for the explicitly selected installed
0.155.1 binary. The policy also denies cross-process inspection, including the new synthetic
environment read. A bounded index binds 407 raw files. The four-role scheduler verified the
actual profile without a qualifier stub, with seven authored replies and no provider call.
The final source and qualification pins are in the
[implementation audit](../reviews/part-3-implementation-progress.md#executed-native-qualification-and-independent-upstream-stop-proof).

Qualification exposed an upstream-stop gap: callback return did not prove worker termination.
The adapter now requires a fresh, independently bound watchdog proof before releasing the
invocation. Later recovery can verify a stop without rewriting the original uncertain receipt
or inventing successful bytes. Incomplete ownership still leaves the invocation pending.

The public CLI remains disabled for production hosts. Next, expose explicit pinned configuration,
prepare the concrete live conformance packet and obtain its separate authority before touching
real authentication or a provider. The Leaf River comparison needs its own frozen allowance.
An offline native profile does not establish real-provider behavior or remote cancellation.

## Explicit CLI configuration implemented

Validate, run and resume now accept `--host-config` with strict TOML metadata for the pinned
profile and prepared lease. The CLI never discovers a credential, refreshes it or selects an
endpoint override. It checks selection, native limits and scope before creating a worker run.
An immutable second journal event binds normalized configuration metadata and capabilities
before activity. Resume rejects changed configuration, and later invocations must match it.
The actual native profile passed the public CLI's four-role path with authored replies only.

The [live execution design](part-3-live-conformance.md) proposes concrete host and scientific
ceilings and lists the remaining counter/runner/comparison work. It grants no live authority
and is not an executable approval packet. Real account/cache compatibility and provider/model
behavior have not been checked.
