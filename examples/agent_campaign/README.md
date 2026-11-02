# Scripted worker campaign

The single-agent comparator is available through
`python -m examples.agent_campaign.run --workflow-route single_agent --output <fresh-root>`.
It uses one persona, a version 1.1 run, a version 1.2 typed handoff and advisory self-review.
Its four-call synthetic workflow reaches the same scientific decision and two executions as
the seven-call four-role fixture. History contains at most four normalized own decisions and
8 KiB. This is scripted integration, not evidence of agent utility or a live matched study.

`check_single_agent_fixture.py` accepts `--output`, `--executable`, `--qualification-root` and
`--qualification-digest`. It uses the actual pinned native policy, four native clients, authored
replies and two synthetic scientific starts. It retains the scripted template, writes the native
specification to a separate file and verifies unchanged CLI resume/status. No real credential,
provider or model is used. The observed model/usage values come from the authored stream.

`check_conformance_preparation.py` verifies proposal capture and inspection with an actual pinned
native profile and tripwires against worker/model dispatch. It starts no runtime clock and opens
no lease. Supply `--output`, `--executable`, `--qualification-root` and `--qualification-digest`.
All six handlers and pinned run/resume/status commands are implemented. Readiness does not grant
execution authority. See
[review preparation](../../docs/agents.md#conformance-review-preparation).

`check_conformance_provider_gate.py` uses the same arguments, then runs one actual native text
probe with an authored reply. It expects the runtime to reject that reply as real provider
conformance, stop before science, retain the charged call and replay unchanged. A fixture pass
means the intended failed verdict was preserved. No real lease or provider is used.

`check_conformance_malformed_fixture.py` uses the same arguments to check the actual native
transport, schema rejection, one repair and unchanged replay. It explicitly stubs preceding
case verdicts, provider proof and replies. Those preceding cases do not execute. A pass concerns
local malformed/repair integration only, with no real credentials, providers or science.

`check_conformance_owner_fixture.py` uses the same arguments to run the unmodified owner-loss
handler through the CLI. Only preceding zero-work verdicts are authored. The actual native client
and fixed upstream worker stop after supervisor interruption, with the upstream gate still closed
before credential preflight. Unknown native duration, model, usage and transcript bytes stay
unknown. Replay/status start no work. This fixture contacts no provider and starts no science.

`check_conformance_cli_provider_gate.py` checks the public run/startup/refusal/resume/status
path with the actual pinned native CLI and one authored response. The provider gate is unmodified.
A pass preserves the expected failed runtime verdict, charged call and unchanged replay.

`check_batch_fixture.py` combines four roles and a direct text case under one shared batch.
It uses an actual pinned native profile, eight native clients, authored replies and two trusted
synthetic scientific starts. No real credential or provider is used. Supply `--output`,
`--executable`, `--qualification-root` and `--qualification-digest`. The batch, worker and campaign
counts must survive replay without new work. See [batch allowances](../../docs/agents.md#shared-batch-allowances).

`check_configured_cli_fixture.py` runs validate, four roles and unchanged resume through the
public CLI with an actual pinned native profile. Only the upstream replies are authored. It
starts seven native clients, records the host configuration binding before dispatch and performs
two synthetic scientific attempts. Supply a fresh output root, the exact executable,
`--qualification-root` and `--qualification-digest`. It reads no real lease and makes no provider
call. See [explicit host configuration](../../docs/agents.md#explicit-cli-host-configuration).

`check_brokered_scheduler_fixture.py` exercises four serial roles through the experimental version
2.1 adapter with the installed Codex executable and actual macOS policy. By default it stubs
qualification and uses authored responses, with no real credentials or provider calls. Run it
with a fresh root:

```sh
pixi run python -m examples.agent_campaign.check_brokered_scheduler_fixture \
  --output outputs/brokered-scheduler-fixture \
  --executable /absolute/path/to/eligible-native-candidate
```

The receipt distinguishes seven native client starts and two synthetic scientific attempts from
zero provider calls. Replay must leave the saved tree unchanged. This fixture does not qualify a
native profile or enable production dispatch. Supply both `--qualification-root` and
`--qualification-digest` to verify an actual native profile without the qualifier stub. Replies
remain authored, and the explicit executable must match the profile.
See the [worker guide](../../docs/agents.md).
The strict policy grants no preference services or shared memory. The exact tested 0.155.1 local
binary passed offline, while the 0.164.0 candidate failed. The fixture never changes the global CLI
or silently chooses another version. Omitting `--executable` uses the current `PATH` selection.

`check_native_policy_canaries.py` compiles a fixed trusted C probe with the existing Apple command
line tools and checks the adapter's actual macOS policy. It uses synthetic private files and
local TCP/Unix listeners. Its executable replaces the native CLI executable in the policy, so it
provides partial permission evidence and always reports `host_qualified: false`.

```sh
mkdir -m 700 outputs/native-policy
pixi run python -m examples.agent_campaign.check_native_policy_canaries \
  --output outputs/native-policy/run
```

Use a fresh output root with a short path for the Unix socket. Save the receipt's SHA-256 after
review. Supplying `--expected-digest` with that pin verifies saved evidence without rerunning the
compiler or canaries. Recovery still performs bounded runtime inventory and process inspection.
This command reads no real credential and makes no model or scientific call.
Version 1.3 includes CoreFoundation, shared-memory and process-environment canaries. Both
synthetic preference reads and the unrelated shared-memory mapping must be denied. All original filesystem/network checks
remain required. The temporary shared-memory object is removed, including on an error. Earlier
diagnostic fixtures that grant preference services or shared memory do not qualify this profile.

`qualify_native.py` produces the complete offline native profile from actual permission,
native protocol, lifecycle and byte/time bound probes. Its output includes a digest-bound raw
artifact index. It uses synthetic local endpoints and credentials, never a real auth cache or
provider. Supply the explicit installed candidate and a fresh root under a private parent:

```sh
pixi run python -m examples.agent_campaign.qualify_native \
  --output outputs/native-policy/qualification \
  --executable /absolute/path/to/eligible-native-candidate
```

Review the evidence before using the resulting qualification digest. A native profile does not
authorize live requests or establish real provider conformance.

For strict native transport checks, select the candidate explicitly and add
`--owned-native --strict-native-policy` to `check_brokered_codex_fixture`. With
`--process-upstream --subscription-fixture`, scenarios `text`, `tool`, `lost_ack`, `timeout` and
`cancel` use only a synthetic cache/lease and authored HTTP. Cancellation starts after the authored
server receives its request and stops upstream before the server releases its body. It preserves
unknown usage and never recovers a successful response from a cancelled worker.

`check_owned_codex_death_fixture` also accepts `--executable` and `--strict-native-policy`. It
kills only its own fixture supervisor, verifies both owned groups and the endpoint stop, and
requires missing completion to remain unsuccessful. These checks do not prove remote cancellation
or supply a qualified production profile. Use fresh output directories for every case.

`check_abandoned_scheduler_fixture` verifies journal recovery after owner death using the actual
explicit native candidate and strict package policy. It stubs qualification and holds the fixed
subscription worker before credential preflight. It kills only its supervisor, verifies both
owned groups stopped, and reconciles the charged invocation as `host_failure` with unknown usage
and duration. Repeating recovery changes no physical transport bytes and launches no new work.

```sh
pixi run python -m examples.agent_campaign.check_abandoned_scheduler_fixture \
  --output outputs/abandoned-scheduler-fixture \
  --executable /absolute/path/to/eligible-native-candidate
```

The parent directory must be owner-private and the output fresh. The absent synthetic lease is
never opened, and no provider request is possible. This is not production qualification or proof
of remote cancellation. Missing or corrupt ownership/result proof remains pending.

Run the offline example with the default Pixi environment:

```sh
pixi run python -m examples.agent_campaign.run --output outputs/scripted-agent-campaign
```

The output directory must be fresh. The example uses four serial scripted roles, an existing
supplied scalar adapter, and the deterministic scientific controller. It writes a resolved
scientific specification, worker run file and verified private journals. It executes no live
host, generated code or Leaf River qualification.

Use `--prepare-only` to stop before worker dispatch, then use `autoengineering agents run` over
the saved specification and explicit campaign. See the [worker guide](../../docs/agents.md) for
commands, recovery, cancellation and report reconstruction. The
[implementation audit](../../docs/reviews/part-3-implementation-progress.md) records current limits.

`fixture.py` separates the scientific source closure from worker code. `scripted.py` exports the
packaged deterministic replies used by both the CLI and integration tests. These replies establish
contract parity only. They do not establish practical value from role separation or independent
scientific confirmation. Actual live conformance and measured Leaf River results are tracked
separately in the [final audit](../../docs/reviews/part-3-final-audit.md).

`qualify_container.py` runs nine fixed, trusted boundary probes against an existing local official
Python 3.12 Docker image. It requires a fresh output directory under a private parent and does not
download images. Its receipts qualify the tested execution boundary only. They grant no scientific
admission or live provider authority. See the worker guide for the current limits.

`check_interface_fixture.py` uses a pinned qualification to test the fixed interface driver over
authored code. It reserves at most ten container starts and expects seven: two scalar cases, two
daily-vector cases, input mutation, a loop that exhausts CPU, and a wrong fixture value.
Supply `--qualification-root`, the trusted receipt SHA-256
as `--qualification-digest`, and a fresh `--output` under a private parent. It retains and verifies
each receipt, including expected failures and skipped cases. It does not register an adapter or
execute a scientific campaign. Unit fixtures and expected values are separate from acceptance data.

`check_registration_fixture.py` prepares a registration from exact passing checks and an explicit
fixture review. It executes the standalone adapter from the original bundle and a copied bundle
after moving the original checking directories aside. It expects four container starts, makes no
provider call and claims no human author approval. Use the same qualification and fresh-output
arguments as the interface fixture. This does not activate a campaign backend or make a scientific
selection.

`check_container_recovery_fixture.py` checks two authored probes using the same qualification and
fresh-output arguments. It recovers a completed result without another execution, then kills the
owner of a sleeping container and verifies the separate container stop. It preserves missing output
as missing, verifies removal of both owned containers, and makes no provider call or campaign run.

`check_generated_campaign_fixture.py` uses the same pinned qualification and fresh-output arguments.
It reserves five container starts and two scientific fixture evaluations. After checking the
registration and its copy, it freezes a private version 2 source profile and runs a parameterless
native baseline plus the isolated candidate. It interrupts the controller before committing the
saved candidate result, then recovers that result and completes without another execution. Its
comparison value is a separate public authored fixture, not a changed scientific benchmark. It
claims no human approval, live worker generation, independent confirmation or scientific benefit.

`check_generated_handoff_fixture.py` exercises a fake-host version 1.1 source response through
capture, fixed interface checks, separately pinned fixture approval and a linked campaign. It
reserves three container starts and three scientific fixture evaluations across both campaigns,
and expects eleven fake-host invocations. The successor runs four roles including an independent
review with exact source/check context. It verifies that the parent remains unchanged, both
campaign budgets stay separate, completed replay launches no work and all owned containers are
removed. Use the same qualification and fresh-output arguments. No provider or live host is called.

`check_preparation_recovery_fixture.py` verifies CLI `resume` over saved, unacknowledged source
checks. It reserves two container starts and one scientific fixture evaluation. It first verifies
that missing qualification evidence leaves recovery pending, then supplies the pinned directory
and recovers without another check, host call or scientific evaluation. Completed replay leaves
the journals unchanged. The fixture verifies both exact container IDs are removed. Use the same
qualification and fresh-output arguments as the other fixtures.

`probe_command_profile.py` is an offline macOS host-boundary investigation. It uses the installed
Codex sandbox and synthetic filesystem canaries with all CLI process-tree networking denied
externally. It currently reconstructs a failed startup composition and exits nonzero. Its approved
read must pass before denial probes can qualify. It does not activate a host, use real credentials
or make a provider call. See the [host boundary plan](../../docs/implementation-plans/part-3-host-boundary.md).

`probe_external_boundary.py` tests a single external macOS boundary without nesting the native
CLI sandbox. Its 15 checks cover approved reads, installed CLI startup, child processes, private
files, symlinks, workspace/scratch writes and local TCP/Unix sockets. Network positive controls
use the same filesystem restrictions and differ only in network authority. The final offline
fixture passed. This does not qualify a networked host or activate scheduler dispatch.

`probe_external_codex.py` goes further by running the installed `codex exec` with one owned local
fake Responses endpoint and no authentication. The external policy permits only that endpoint.
Its default text fixture now completes with read-only Codex preference dependencies and a catalog
entry verified in the installed executable. This chooses offline metadata, not a live model.

The service uses the reusable `TextExchange` boundary: only the exact approved prompt and trusted
schema reach the authored upstream callback. Native client context and tools are omitted. The
response is retained and validated before delivery. Text and blocked-tool cases now use the
package's `TextEndpoint`, with a scoped route, bounded HTTP input and separate stop receipts for
listener, handler and local callback. `--scenario tool_control` deliberately bypasses
that response check and runs one authored scratch-only command. `--scenario blocked_tool` keeps
the same client execution permissions but blocks the identical tool response before delivery.
The control must create its marker and the blocked case must leave it absent. These are explicit
offline diagnostic commands and do not activate a production scheduler host.

The fake service rejects unexpected authentication, endpoints, request envelopes and duplicates.
Both probes take `--output` under an existing private parent and require a fresh directory. They
do not use real credentials, call a provider or run a scientific campaign. See the host boundary
plan for the initial failed probes and remaining platform, credential and lifecycle gates.

`check_brokered_codex_fixture.py` exercises the version 2 package transport with the installed
CLI, a captured external macOS policy and an authored local response. Select `--scenario text`,
`tool`, `lost_ack` or `timeout` and supply a fresh `--output` under an existing private parent.
The lost-acknowledgment case recovers saved evidence. The timeout case first preserves an active
callback as unresolved, then releases the fixture callback, captures a verified stop and recovers
without another call. All four cases replay unchanged. No real authentication, provider or
scientific evaluation is involved, and these fixtures do not enable production dispatch.

Add `--process-upstream` to run the authored response in an independent supervised process.
This path uses a fixed standard-library fixture, private input/output files and no network.
The timeout case stops that process at its absolute deadline. Saved successful response bytes
and watchdog stop receipts are checked without another process launch. This option qualifies
neither a real provider transport nor the native CLI's behavior after supervisor death.

Add `--owned-native` to select the opt-in version 2.1 native profile. It uses an independent
watchdog and inherited owner pipe. `check_owned_codex_death_fixture.py --output <fresh-directory>`
kills an offline installed-CLI supervisor during an authored upstream request, verifies that both
groups and the endpoint stop, and checks that missing native completion cannot become success.
It uses the same external macOS boundary and makes no real provider or scientific call.

Add `--subscription-fixture` with both ownership options to exercise the fixed subscription
worker through an explicitly authored HTTP connection factory. It prepares a lease from a
synthetic managed-cache file
outside the client directories and sends one request to a loopback fixture. No real auth cache
or production HTTPS endpoint is used. The timeout fixture has a separately recorded 1.5-second
budget so that it can exercise an in-flight request. Client artifacts are checked for fixture
credential values, and the upstream must stop before the fixture server is released. These
records cannot pass the production subscription decoder as a real HTTPS exchange.
The source file must remain unchanged, refresh/ID-token fields must stay out of the lease, and
all four synthetic credential values must stay out of client artifacts. Separate loopback TLS
tests use a private ephemeral CA without changing the system trust store.

Fresh matched Leaf River preparation is available without model execution:

```sh
mkdir -m 700 outputs/matched-leaf
pixi run python -m examples.agent_campaign.prepare_leafriver \
  --output outputs/matched-leaf/proposal
pixi run python -m examples.agent_campaign.prepare_leafriver \
  --output outputs/matched-leaf/proposal --verify <printed-preparation-sha256>
```

The parent must already be private, and the proposal directory must be absent. Preparation
captures three fresh campaign specifications and their inputs, verifies the checked historical
cache and records the planned 38 executions for each route. It starts no campaign, model,
host or clock and reads no credential. Verification is read-only. `execution_ready: false`
records the missing matched driver. These manifests do not authorize live execution. See the
[comparison implementation design](../../docs/implementation-plans/part-3-matched-comparison.md)
for remaining driver, synthetic dry-run and authorization requirements.

The synthetic matched driver uses fabricated weather and labels, the same supplied PET
implementations, and authored responses for all three routes:

```sh
pixi run python -m examples.agent_campaign.synthetic_comparison \
  --leaf-preparation outputs/matched-leaf/proposal \
  --leaf-digest <leaf-preparation-sha256> \
  --output outputs/matched-leaf/synthetic-proposal \
  --runtime-root /absolute/private/synthetic-runtime
pixi run python -m examples.agent_campaign.comparison run \
  --preparation outputs/matched-leaf/synthetic-proposal \
  --preparation-digest <synthetic-preparation-sha256> \
  --max-new-cases 1 --max-new-evaluations 1
pixi run python -m examples.agent_campaign.comparison resume \
  --preparation outputs/matched-leaf/synthetic-proposal \
  --preparation-digest <synthetic-preparation-sha256> \
  --runtime-digest <runtime-sha256-printed-on-stderr>
pixi run python -m examples.agent_campaign.comparison status \
  --runtime /absolute/private/synthetic-runtime \
  --runtime-digest <runtime-sha256>
```

Both proposal and runtime must be absent under existing private parents. The startup receipt
records the runtime pin before dispatch. A final stderr receipt reports newly charged starts
and logical calls. Omitting pause flags completes all three synthetic routes, with a shared
114-start ceiling. Status reads saved journals and verdicts without loading arrays or starting
work. This synthetic driver cannot select a real host or run measured data. The separate native
driver below requires completed real-provider conformance and separate execution authorization.

New synthetic preparations are version 1.1 and bind the separated execution/status sources.
The same `comparison status` command also reads saved version 1.0 evidence. It imports no
host, scheduler, scientific controller or supplied model. Preparation uses the core bounded
NPZ reader before allocating arrays and rejects object, complex and oversized inputs. A new
source version requires a fresh proposal; existing runtime identities are preserved.

Native comparison preparation is available without native dispatch or measured execution:

```sh
pixi run python -m examples.agent_campaign.native_comparison \
  --leaf-preparation /absolute/private/leaf-proposal \
  --leaf-digest <leaf-preparation-sha256> \
  --conformance-preparation /absolute/private/conformance-proposal \
  --conformance-digest <conformance-preparation-sha256> \
  --worker-template /absolute/private/native-worker-template.json \
  --host-config /absolute/private/host.toml \
  --output /absolute/private/native-proposal \
  --runtime-root /absolute/private/future-native-runtime
```

The host template must be supplied-only, four-role, and bound to the same host/model/profile
as the captured conformance proposal. The output and future runtime must be absent under
private parents. Preparation copies and verifies inputs and reports the frozen 0/20/20
physical-host and 38/38/38 scientific ceilings. It does not read the lease, start a runtime,
call a model or authorize execution. The report explicitly returns `execution_ready: false`.
Version 1.1 captures the native runtime, interruption, proof and status sources as well as its
recipe. Changed driver bytes require a fresh preparation. The earlier 1.0 proposal stays intact.

After separately authorizing real-provider conformance and the measured comparison, use:

```sh
pixi run python -m examples.agent_campaign.native_run run \
  --preparation /absolute/private/native-proposal \
  --preparation-digest <native-preparation-sha256> \
  --host-config /absolute/private/host.toml \
  --conformance-runtime-digest <completed-real-conformance-runtime-sha256>
pixi run python -m examples.agent_campaign.native_run resume \
  --preparation /absolute/private/native-proposal \
  --preparation-digest <native-preparation-sha256> \
  --host-config /absolute/private/host.toml \
  --conformance-runtime-digest <same-conformance-runtime-sha256> \
  --runtime-digest <native-runtime-sha256-printed-on-stderr>
pixi run python -m examples.agent_campaign.native_run status \
  --runtime /absolute/private/native-runtime \
  --runtime-digest <native-runtime-sha256>
```

The runner verifies the actual conformance preparation, specification, journal head and report
before creating the comparison clock. Resume requires those same pins and unchanged source and
configuration. `--max-new-cases` and `--max-new-evaluations` pause work within the original limits.
Startup and newly charged work are printed on stderr; JSON stdout reports cumulative evidence.
Status needs neither credentials nor host/model imports.

Each live route starts with one trusted supervisor interruption before credential preflight.
It consumes one task and one host invocation within that route's twenty-call allowance. Both
owned native/upstream process groups must stop, and recovery retires the original invocation
as `host_failure`, retaining unknown usage, duration and transcript cost. No replacement call
is launched for that control. The scripted case performs no native interruption. All routes
reuse the same static invalid-interface control and supplied candidate order.

Each later native role call needs fixed-worker response evidence and the provider's observed
model and usage. A prior conformance pass alone cannot establish those. Failed or unresolved
calls remain visible. Native reports use a separate evidence kind, retain exposure and
`confirmation_not_attempted`, and make no claim of role superiority or scientific utility.
Offline authored tests are separate from actual provider and measured-data evidence.

The managed-cache lease helper permits at most 900 seconds. That lifetime is shorter than the
combined worst-case batch deadlines. Each fixed worker checks expiry before its request and
rejects an expired lease. There is no automatic refresh, account fallback, deadline extension or
uncharged retry. Actual account/source selection and lease timing belong in the separate run
authorization; preparation does not establish server validity or that every allowed call fits
within one lease.

The native qualifier also accepts `--model NAME --model-catalog PATH`. The optional catalog
must describe exactly that model and fit 65,536 bytes. It is explicit trusted metadata, captured
and hashed in the qualification and each invocation. The runtime never discovers a catalog or
changes the chosen model. Catalog metadata does not enter the approved provider prompt. A
catalog that requires disabled tools can still fail qualification. Preserve that failure rather
than ignoring the native error event. Source changes require fresh qualification and preparations.
