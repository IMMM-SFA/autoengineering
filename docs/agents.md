# Bounded worker workflows

The experimental `autoengineering agents` commands run a supplied-candidate workflow with a
scripted fake host or explicitly configured qualified native adapter. Codex/subscription
and the provisional Claude/API adapter have separate profiles. Four serial roles coordinate investigation, configuration and independent
review above the existing scientific campaign controller. The controller owns admission,
calibration, eligibility, selection and confirmation. The [final Part 3 audit](reviews/part-3-final-audit.md)
records implementation, source/platform pins, completed live gates and retained failures. Codex runs require a qualified native profile and prepared
lease supplied by the trusted caller. Offline qualification grants no live-call authority. An explicit fake-host
generated run can prepare source through the trusted API below, then create a separately budgeted
campaign after review. The controller executes that frozen registration through the isolated backend.

The recorded macOS ARM64 profile passed all six live conformance cases and a matched Leaf River
pilot. Scripted, single-agent and four-role routes completed 38 measured starts each and selected
the same Hargreaves configuration, with comparison RMSE 3.1378289080395643. Agent routes added
calls and elapsed time without objective gain. NSE and KGE remained negative, and independent
confirmation was not attempted. The final audit retains earlier failed attempts and their costs.

## Offline example

From the repository root with the default Pixi environment:

```sh
pixi run python -m examples.agent_campaign.run --output outputs/scripted-agent-campaign
```

This creates a fresh synthetic campaign, worker run specification and private worker journal. It
uses the existing supplied scalar adapter. Its scientific result can be compared with the direct
campaign workflow. The scripted replies are fixtures, not an LLM or evidence that multiple roles
improve research quality.

To use the CLI over a prepared campaign:

```sh
pixi run python -m examples.agent_campaign.run --output outputs/agent-cli --prepare-only
pixi run autoengineering agents validate outputs/agent-cli/agent-run.json \
  --campaign outputs/agent-cli/campaign
pixi run autoengineering agents run outputs/agent-cli/agent-run.json \
  --campaign outputs/agent-cli/campaign --workdir outputs/agent-cli/worker
pixi run autoengineering agents status outputs/agent-cli/worker
pixi run autoengineering agents report outputs/agent-cli/worker --format markdown
pixi run autoengineering agents resume outputs/agent-cli/worker \
  --campaign outputs/agent-cli/campaign
```

`run` requires a fresh worker directory and an explicitly selected campaign. `resume` uses the
stored worker identity and limits. `--max-new-evaluations` limits scientific starts during that
invocation. It cannot enlarge frozen campaign allowances. Use `agents cancel WORKDIR --campaign
CAMPAIGN` to queue worker and scientific cancellation intents. Queued intent does not establish
that a host or scientific process stopped. `status` and `report` need only the worker directory.

CLI stdout is JSON except for an explicitly selected Markdown report. Progress goes to stderr.
Exit 2 indicates invalid input or an incompatible identity. Exit 4 indicates a visible workflow
stop or unresolved execution. A valid negative scientific outcome is a completed workflow.

## Single-agent comparator

The [implementation design](implementation-plans/part-3-single-agent.md) records the versioned
contracts and memory rule.

In frozen matched comparisons, `comparison_policy.next_proposal_candidate_id` names the
required next proposal. The same policy exposes already proposed IDs to both routes. A baseline
evaluation does not consume a candidate proposal. Proposal eligibility gaps describe missing
source or interface prerequisites. Declared calibration, candidate evaluation and scientific
checks occur later through the controller and remain untested at proposal time.

The supplied-only single-agent route uses one persona for proposal, configuration, self-review
and freeze decisions. It uses the same controller, supplied catalogue, scientific checks and
budgets as the four-role route. It makes no separate orchestrator calls. Self-review is advisory
and is reported as `self_review`, without an independence claim.

```sh
pixi run python -m examples.agent_campaign.run \
  --workflow-route single_agent --output outputs/scripted-single-agent
```

Use `--prepare-only` to create its campaign and run file without execution. The ordinary
`agents validate`, `run`, `resume`, `status` and `report` commands select the route from that
immutable run file. There is no CLI override that can change an existing run's route.

| Route | Run schema | Templates | Task/grant schema | Handoff schema | Review context |
| --- | --- | --- | --- | --- | --- |
| `four_role` | 1.0 | Original four | 1.0 | 1.0 or generated 1.1 | Fresh reviewer invocation |
| `single_agent` | 1.1 | `single_agent` | 1.1 | 1.2 | The same persona reviews its work |

Version 1.0 serialization stays unchanged. Version 1.1 requires explicit
`workflow_route: single_agent` and its separate template/policy hashes. The
`single_agent_spec(template, run_id=...)` helper derives that worker identity while retaining
scientific binding and limits. Generated source is outside this supplied-pool comparator.
The host conformance preparation still requires the four-role template.

The single persona receives the same approved scientific summaries plus at most four of its
own normalized handoffs, with an 8 KiB aggregate history limit. Whole items that do not fit are
omitted and their invocation IDs are recorded. The full journal retains them. Raw transcripts,
private labels and source workspaces are excluded. An ID mentioned in history does not grant
access to an old artifact. Review findings cannot override executed scientific eligibility.
The broker checks the current stage and candidate allowance before staging an agent proposal.

The synthetic scripted example uses four calls for one candidate and freeze, versus seven for
four roles. Both reach the same controller decision with two numerical executions. This is
integration evidence. It does not establish a model's quality, subscription cost or practical
benefit. [Fresh Leaf River preparation](implementation-plans/part-3-matched-comparison.md)
captures three new scientific manifests without model execution. An authored synthetic driver
now verifies all three routes and shared scientific accounting. The native comparison path and
authorized live evidence remain separate work.

`check_single_agent_fixture` exercises the public CLI with a pinned actual native profile and
authored replies. Supply `--output`, `--executable`, `--qualification-root` and
`--qualification-digest`. It uses four native clients and two synthetic executions, preserves
the scripted template in `agent-run.json`, writes the derived native spec separately, and checks
unchanged resume/status. It opens no credential and contacts no provider. Streamed model/usage
metadata are authored fixture values, not real-model or availability evidence.

## Contracts, permissions and recovery

`AgentRunSpec.from_file` reads strict JSON with a 64 KiB limit. Unknown fields, duplicate keys,
unsupported versions, nonfinite numbers and boolean resource limits fail validation. Records copy
and freeze nested values. Prompt, source, runtime, requested model, authentication, permissions,
campaign identity and limit changes require a new worker identity. Dispatch verifies current
host source bytes, runtime and template hashes. Changed capability receipts cannot silently resume
a run. Run duration starts at its durable creation event.

Each physical invocation begins with a committed reservation. Prompts, raw responses, normalized
handoffs, parse failures and completion receipts have separate digest-verified artifacts. Repair
invocations consume persistent task and run allowances. Completed roles are replayed without a
new host call. Uncertain reservations block further dispatch until reconciled.

The prompt includes the complete inner handoff contract, derived from the record fields. It
describes required fields, types, nested records and allowed outputs, with the current task,
invocation, role, revision, grants and supplied implementation choices bound explicitly. Both
workflow routes receive it, including generated-source tasks. The contract has a 32 KiB limit
and counts toward the existing total prompt limit. The scheduler persists the exact prompt and
rechecks the deadline after preparation, before reserving a host call. Strict record parsing,
grant checks, scientific phase checks and the controller remain authoritative. The native
transport's outer string envelope is separate from this inner contract.

External actions hold a separate operation lease. The journal writer is held only for preparation
and result commits, so it remains available during a host call, scientific request or staging call.
Competing dispatch and recovery fail while the operation lease has a live owner. The OS releases
that lease if its owner exits, and the saved reservation still requires reconciliation. A leftover
lease file is not evidence of a running action. Cancellation uses its independent inbox throughout.

The worker-run deadline also applies during scientific requests. A timer forwards cancellation to
both inboxes when the original run deadline expires. New tasks, staging and scientific requests
stop after expiry. Recovery obtains an already committed scientific response first using the exact
saved envelope. An uncommitted request is cancelled before numerical work. Evaluation and
confirmation check queued cancellation before reserving new execution.

Status and reports include immutable deadline notices with the original deadline, action identity,
forwarded intents and bounded failure codes. A later successful forward can explicitly reconcile a
failed notice while preserving it. Queued intents do not certify process stop. The scientific
supervisor records that evidence separately. The deadline timer runs in the broker process. If the
broker dies, scientific work still requires the existing ownership and recovery checks.

The broker constructs summaries from an explicit field allowlist. Roles receive approved scalar
metrics, checks, interfaces, exposure flags and the supplied catalogue. They do not receive array
labels, full controller state, checkpoints, child work directories or private source paths.
Referenced digests confer no additional read authority. Source instructions cannot change role
operations or grants. The reviewer receives its own task and submitted rationale, without earlier
role transcripts or implementer scratch history.

Summary version 1.1 also identifies each evaluated configuration and model, the declared
calibration policy and parameter space, and committed calibration study links. With calibration,
catalogue parameters are starting values. The trusted controller can fit the declared parameters
before evaluating the selected configuration. Reviewers must use that evaluated configuration
and its study linkage rather than treating starting values as the fitted result. No child paths,
checkpoints or additional read grants are exposed. The confirmation policy is explicit. Pending
downstream acceptance or confirmation is not itself a missing pre-review prerequisite, and no
review can claim those later gates passed before they execute.

The journal saves an exact scientific request before dispatch. Lost responses replay the original
envelope and obtain its original response. Staging recovery matches committed bytes before
creating another checkpoint. Scientific errors stop the workflow instead of changing revisions
and blindly retrying. The controller's physical execution and repair limits remain independent.

Blocking reviewer findings pause deterministic review. A trusted caller can use
`CampaignBroker.dispose_review` with a reason and the unchanged review context. This records a
separate immutable disposition. Workers cannot create it. A favorable or disposed review never
overrides executed scientific eligibility checks.

## Evidence reports

Reports reconstruct worker history from the verified journal, without importing a host or scientific
controller and without reading scientific arrays. They distinguish raw output, normalized handoffs
and parse failures. They include role access grants, request history, original reviewer findings,
trusted dispositions, invocation allowances, unknown usage and the latest scientific receipt.
That receipt records the selected configuration, objective, physical attempts, cost uncertainty,
remaining committed capacity and confirmation status. It is the last broker-recorded revision,
not an inspection of later external changes to the scientific campaign.

Markdown artifact links are relative to the worker directory. Reports are private operator
artifacts and are not automatically granted to workers. Unknown usage remains unknown. Observed
token stops do not guarantee an in-flight token ceiling, and subscription cost is not inferred.

## Scientific source identities

New profiles can declare the shipped `campaign/scientific-closure-v1.json` source allowlist. The
controller verifies its bytes and every listed scientific module. Worker modules and prompts are
outside this closure. Shared scientific changes require a new campaign identity. Historical
profiles retain their whole-package checks and original hashes. They cannot resume under changed
shared sources. Current tests resolve fresh synthetic specifications instead of rewriting the
checked Part 2 manifests.

From a linked worktree using the main checkout's environment, set `PYTHONPATH` to the worktree's
`src` and put that environment's `bin` on `PATH`. Campaign process tests need local process
inspection. A sandbox that denies `ps` prevents their ownership checks from qualifying.

## Process and source-workspace prototypes

The process supervisor has a launch gate: it records the nonce, PID, process group and start
identity before the trusted executable can start. It captures bounded stdout and stderr, stops
owned descendants on timeout or cancellation, and retains uncertain outcomes for reconciliation.
A trusted executable fake-host fixture tests this path through the scheduler. It is not an
untrusted-code sandbox or a provider host. Invocation version 1.1 stores raw, final and stderr
channels separately. Version 1.0 serialization remains unchanged so earlier journals remain readable.
Version 1.2 adds a separate recovery receipt. Recovery can normalize verified saved raw output or
reconstruct a checksummed, stopped physical execution without another host call. Missing ownership,
changed bytes and uncertain descendants leave the reservation pending.

The versioned Codex transport checks executable capabilities and authentication mode, builds explicit
CLI arguments, and retains raw events before parsing. It rejects tool-use events under the supplied
role policy. A missing resolved model remains null, and absent usage remains unknown. These parser
checks are not a security boundary against effects that already occurred. Dispatch requires the
qualified version 2.1 boundary described below. The event and output
schema design follows [official OpenAI documentation](https://learn.chatgpt.com/docs/non-interactive-mode)
and is checked against trusted fake executables without provider calls or real credentials.

The experimental text exchange adds enforcement before Codex receives a response. It rebuilds
the upstream request from the frozen role brief and output schema, omits native client context
and tools, reserves one upstream request durably, and validates the complete bounded response
before delivery. Tool items and unsupported streams are rejected. Saved response bytes can be
normalized after a lost acknowledgment without another upstream call. Missing dispatch evidence,
transport uncertainty, changed source and corrupt artifacts stop recovery. Reported usage comes
from the saved upstream response and missing usage stays unknown. This primitive does not qualify
the credential, endpoint, resource or lifecycle boundary. Live scheduler dispatch remains disabled.

`TextEndpoint` now serves that exchange on an invocation-specific loopback route. It rejects
credential headers and ambiguous framing, bounds headers/body/connection count, and enforces one
absolute input deadline even when a client drips bytes. Exact retries may replay a saved reply
without another upstream callback. Other requests cannot change the frozen brief or schema.
Stop receipts distinguish the listener, handler and local callback. A blocked callback leaves stop
unverified, and callback return does not establish that remote provider computation ended. The
installed CLI has passed local authored text and blocked-tool fixtures through this endpoint.
Upstream credentials, provider transport and the production scheduler adapter remain unfinished.

The experimental `codex_brokered` transport adds a separate version 2 path while preserving
version 1. It binds native launch/input/output, endpoint metadata, captured policy bytes and a
exchange bound to the physical nonce. The deadline includes preparation and a bounded stop grace. Successful
text must agree between the CLI and saved broker response. Reported model and usage come from
that response, so missing counts are not replaced by client zeroes. Recovery verifies saved bytes
and current native process-group absence. Later endpoint stop captures can resolve an uncertain
callback without rewriting the original outcome or making another call. This SDK primitive is
not registered as a production scheduler host. The default version 2.0 path retains its original
native lifecycle behavior. The opt-in version 2.1 profile (`owned_native=True`) adds a watchdog
and inherited pipe lease for native execution. Failed startup, expired ownership acknowledgment
and cancellation cannot open the launch gate. Owned stop receipts can prove group termination
after supervisor death. Missing native completion still prevents successful transport recovery.
Real provider conformance and production recovery integration remain open.

`CommandUpstream` can replace the in-process upstream callback with one trusted command.
It passes private request/response paths as arguments, checks declared executable/source hashes,
bounds captured diagnostics and response reads, and enforces an absolute monotonic deadline.
Its process supervisor uses an independent watchdog and inherited owner pipe. EOF detects owner
loss without relying on PID reuse timing. Parent death or deadline expiry stops the
verified group, including descendants that ignore SIGTERM. Existing attempts cannot relaunch.
Read-only recovery checks launch and stop bindings, current group absence, request/response
digests, acceptance time and source identity. Missing response receipts remain uncertain.
These are local lifecycle checks, not a filesystem, network, disk or remote-compute boundary.
OS egress qualification and production integration remain unfinished.

`ScopedSubscriptionUpstream` adds a fixed, one-request Codex subscription worker. It sends only
the approved request to `https://chatgpt.com/backend-api/codex/responses`, with certificate and
hostname verification, no proxy environment, no redirects, no refresh and no retry. This route
and its bearer/account headers are described in the
[official gateway documentation](https://learn.chatgpt.com/docs/enterprise/sign-in-with-chatgpt-through-a-gateway).
This implementation has not made a production HTTPS request.

The worker reads a separately prepared, owner-private lease file outside the declared client
roots. This package format contains `schema_version`, `kind` (`codex-chatgpt-bearer`), `lease_id`,
`bearer_token`, optional-null `account_id`, and `not_after_utc` in UTC. The lease ID must match
the trusted policy, and the declared expiry must cover the deadline plus 30 seconds. These checks
do not establish server validity. No real credential has been opened by the qualification fixtures.

`prepare_subscription_lease` accepts only an explicit absolute source path, expected account,
expiry, fresh destination and declared client roots. It recognizes the managed ChatGPT fields
documented in the [official CI auth guide](https://learn.chatgpt.com/docs/auth/ci-cd-auth).
It never discovers a cache, logs in, refreshes or changes the source. A custom seven-day freshness
limit and 30-to-900-second lease window bound this package's snapshot policy. API-key and external
token modes, unknown fields, account mismatch and source rotation are rejected. The source stays
outside client roots, and a lease destination cannot be in a Git checkout. Refresh and ID-token
fields are not copied. Prepared receipts contain no credential value or secret hash.

`recover_prepared_subscription_lease` verifies the saved lease and scope-bound commit receipt
without reopening its source or writing files. Missing receipts, changed account/expiry, expired
leases and foreign scopes fail. Recovery cannot reseed or extend a lease. The user-selected managed cache and account have supplied actual authorized responses.
A past response does not establish current token freshness or server validity. Refresh belongs to the separately authorized
native Codex owner, consistent with the official guide.

The worker bounds headers, body and HTTP framing, rejects credential reflection in accepted SSE
JSON forms, and writes response bytes only after those checks. Error bodies and raw exception
messages are discarded. Static receipts retain phase, HTTP status, request uncertainty and
unknown usage. Recovery verifies the fixed worker, policy, scope and provider records without
opening credentials or calling the network. Local authored-HTTP fixtures are explicitly distinct
from production HTTPS, credential and OS egress qualification. Additional local TLS tests perform
real verified handshakes with a private fixture CA, including CA and hostname rejection. They do
not establish production peer trust or account access. Actual provider results are recorded separately
in the [Part 3 acceptance inventory](reviews/part-3-completion-audit.md).

`CandidateWorkspace` creates a single-file `adapter.py` workspace from an explicit source allowlist.
The initial interface is `predict(inputs)` with permitted builtins and `math`. Capture retains
immutable source bytes and a patch before static checks, including for invalid source. Capturing or
verifying bytes grants no execution or admission authority. Dependency changes, symlinks, extra files,
module initialization and unsupported calls are visible failures. Static inspection is not a sandbox.

The macOS prototype passes separate trusted probes for denied private reads, writes, symlink escape,
site-package access, network connections and fork. Its resource wrapper cannot set the required
memory limit on the tested machine. It fails before executing candidate code. This is an unqualified
execution backend.

The local Docker boundary passed nine fixed qualification probes on this macOS ARM64 host:
startup, private paths and writes, network, memory, CPU, output, wall time, process count and
supervisor death. The official Python 3.12 image was downloaded once through an isolated Docker
client configuration. Execution pins its immutable image ID, mounts only a derived source export,
and uses a separate watchdog. The boundary never downloads an image automatically.

`examples.agent_campaign.qualify_container` requires an existing local official Python image and a
fresh output directory under a private parent. It runs trusted probes, with no provider calls or
scientific campaigns. `agents.qualification.verify_qualification` reconstructs evidence against a
trusted caller's pinned receipt digest. Worker output cannot approve this digest. Source, platform,
runtime, input, output, ownership and stop evidence must remain compatible. This does not admit an
implementation.

`agents.interface.check_interface` tests an immutable source capture inside that qualified runtime.
It takes explicit public unit fixtures and exact scalar or daily float port contracts. Expected
values remain outside the container. The initial policy permits up to four cases, four input and
output ports, and 128 values in each input or output mapping. Each case runs in a fresh container
with the tested resource limits and a five-second wall deadline. Combined candidate and fixed driver
source must fit 64 KiB. Import paths and test commands are fixed by the trusted runner.

Checks retain failed and skipped cases. `verify_interface` reconstructs a caller-pinned receipt,
checks source and driver bytes, input/output hashes, execution identity and effective container
policy, and recomputes fixture outcomes without executing code. Changing units, source, runtime,
limits or fixture definitions cannot reinterpret an old receipt. The Docker client and server
fingerprints must also match before a new execution can start.

The explicit `examples.agent_campaign.check_interface_fixture` command expects seven container
starts over fixed authored scalar, vector and adverse cases. It reserves ten starts, covering
unexpected passes as well as expected failures. It requires an existing qualification directory and its
trusted SHA-256 through `--qualification-root` and `--qualification-digest`, plus a fresh `--output`
directory under a private parent. It makes no provider call and registers no scientific adapter.
Passing these interface checks does not establish scientific eligibility. Worker handoffs cannot
promote a passing check into an executable campaign entry.

`agents.admission.register_candidate` now prepares an immutable, reviewed registration for a
standalone application registry or a new frozen campaign catalogue. The caller supplies a separate `AdmissionReview` and pins its
digest. Worker handoffs cannot invoke this function or self-admit code. It accepts only passing
interface evidence for the exact source capture and qualification. An explicit allowlist controls
the evidence archive. Extraction rejects traversal, symlinks, compression, excessive members and
file/directory collisions, including case aliases. The archive is limited to 4 MiB and 512 members.

Registration version 1.1 binds the fixed driver and an explicit execution source identity. The
execution closure extends the versioned scientific engine closure with the isolated execution
helpers. Provider adapters and role prompts remain outside it. Version 1.0 metadata remains
readable, but its unbound execution identity cannot authorize a new run. Portable interface evidence
retains its original execution origin in manifest version 1.1. An explicit relocation check verifies
archived bytes and policy without treating that origin as a new execution path.

`adapters.isolated.registration_entry` returns a trusted `AdapterRegistration` for a standalone
`AdapterRegistry`. Its adapter supports one fixed component, exact scalar/daily float contracts,
no tunable parameters and no training. It verifies the complete evidence packet before execution,
exports only source, the fixed driver and supplied forcing, and retains physical receipts after
cleanup. Cleanup alone does not certify a container stop. The authored
`examples.agent_campaign.check_registration_fixture` command checks the entry and a relocated copy
with four bounded container starts. Its caller approval is a fixture, not human author approval.

A new campaign can predeclare one exact `generated-<registration digest>` ID and its four
registration artifacts. Its scientific closure must use version 2, with both versioned manifests,
the complete base engine and the explicit isolated execution helpers. Provider adapters and role
prompts remain excluded. Version 1 remains the default for supplied profiles, and historical
manifests keep their previous source checks. A resumed campaign cannot add a registration.

The initial backend supports one fixed component with the exact reviewed ports, source refs and
empty parameter mapping. Calibration and training are rejected. `linear-fixed` supplies the
parameterless authored scalar baseline used by the integration fixture. The default application
registry still rejects generated IDs unless a compatible campaign and source bundle select them.

`agents.container_recovery.reconcile_container` now checks one execution against trusted source,
input, qualification and deadline bytes without launching it again. It refreshes the local Docker
client/server identity, verifies the immutable container ID, labels, effective policy and export,
and checks any saved result against raw output hashes. Only an exact missing-container diagnostic
counts as absence. Socket, permission and ownership errors remain unresolved. A saved stopped
receipt that conflicts with a live container is rejected before any signal.

With `stop=True`, the caller must first stop the outer owner. Recovery inspects ownership again
before killing a running container or removing an unstarted one, then inspects the result. It
returns separate facts for physical stop, removal and a recovered numerical result. Absence alone
does not settle cost or reconstruct missing output. The helper leaves original receipts unchanged.
The controller now calls this helper after verifying that the native process group is gone.
Before Docker starts, the numerical worker commits the campaign attempt ID/nonce, registration
identity, reserved scratch path and inner container ID/nonce/intent. Normal completion checks
native output against the container's raw result. Finished-result recovery reconstructs that result
without another execution. Cancellation and manual reconciliation cannot finish while the inner
container's stop is unresolved. Separate inner receipts accompany the native supervisor evidence.

`examples.agent_campaign.check_generated_campaign_fixture` exercises trusted registration and this
backend with at most five container starts and two scientific fixture evaluations. It terminates
the controller after the candidate result is saved but before its journal commit, then recovers
the result without a replacement launch. Public scalar fixture values prove integration only.
The fixture makes no live host call and does not qualify live worker generation.

## Source responses and linked campaigns

`AgentRunSpec.execution_mode="generated"` permits fake-host source preparation and the qualified
version 2.1 adapter. Older live adapters fail validation. Actual provider generation remains
unattempted. `CampaignBroker.advance()` stops at `candidate_pending`, before snapshot
admission. The CLI reports `awaiting_source_preparation`; it does not invent public fixtures,
approve a review or change the scientific catalogue.

The trusted caller supplies baseline adapter bytes, an `InterfaceSpec` of public unit fixtures,
and a pinned qualification to `SourcePreparation`. The initial profile requires one component,
empty parameters and no calibration. Baseline wrapper bytes are explicit caller input. Their
workspace manifest digest is the source handoff's `base_snapshot`; the scientific baseline is
bound separately by the originating campaign identity.

```python
from autoengineering.agents.preparation import SourcePreparation

preparation = SourcePreparation(broker, qualification_root, qualification_digest)
prepared = preparation.prepare(baseline=baseline_bytes, specification=public_interface)
# Review the captured source, patch and executed checks before constructing approval.
registration = preparation.register(
    prepared.id,
    review=approved_review,
    trusted_review_digest=approved_review.digest,
    output=registration_root,
)
successor = preparation.fork(
    prepared.id,
    registration_root=registration_root,
    name=new_campaign_name,
    execution=new_execution_spec,
    output=new_output,
)
```

The implementer receives a version 1.1 task and returns a `SourceDraft` containing only
`adapter.py`, the granted baseline digest, fixed dependencies and evidence IDs. It cannot name a
test command, upload files, return executed checks or claim admission. Version 1.0 supplied handoffs
remain readable. The broker writes the bounded response to a private workspace and captures source
and patch before policy checks. Only the captured bytes enter interface execution and registration.
The initial dependency profile permits fixed builtins and `math`, without arbitrary stdlib imports.

Capture and check reservation are worker journal events. Pending checks block another host
dispatch. The existing operation lease excludes a second checker while the writer remains free
for cancellation. The original run deadline and cancellation inbox reach the active container
checks. A failed source is retained without execution. Recovery reuses complete saved checks or
stops and retires partial checks without repeating a possibly launched case. Unknown ownership
keeps the preparation unresolved and retains its reserved allowance. Reported interface reservations
are separate from scientific attempts and host invocations.

Registration requires a separate pinned `AdmissionReview`; the worker cannot invoke it. Forking
requires a new name and an explicit `ExecutionSpec` for the baseline and exact registration ID.
It copies only declared artifacts into a private version 2 source profile, preserves baseline,
data, acceptance and confirmation semantics, and creates the new campaign without executing it.
`generated/origin.json` binds the parent campaign/proposal, worker handoff, captured source, checks,
review and registration into scientific provenance. The parent journal and allowance stay unchanged.
The successor needs its own worker run if the four-role workflow will continue.

Source preparation starts through this Python API. CLI `resume` now reconciles pending preparations
using an explicitly selected qualification directory:

```sh
pixi run autoengineering agents resume outputs/source-worker \
  --campaign outputs/source-origin \
  --qualification-root outputs/boundary/qualification \
  --max-new-evaluations 0
```

Use the directories from the saved run. The qualification digest comes from the stored preparation;
the CLI has no option to replace it. A missing or mismatched qualification leaves the preparation
pending and exits with code 4. Unknown ownership also remains unresolved. Saved checks are reused
without another host invocation or scientific evaluation. Partial checks are stopped or retired
without repeating a potentially launched case. A capture that never reserved checks can start its
original fixed suite, subject to the original deadline and cancellation. `--max-new-evaluations`
limits scientific evaluations; interface checks retain their separate frozen reservation.

Preparation recovery inspects the campaign identity and journal without needing the original
scientific source checkout. It does not advance or mutate the parent scientific campaign. Checked,
registered and forked preparations replay without a qualification argument or new work. Trusted
review and successor creation remain separate actions. `status` includes pending preparation IDs.

The successor reviewer receives the exact captured source, public interface and interface receipt
alongside scientific evaluation summaries. It receives no mutable workspace, private paths,
comparison arrays or implementer transcript. Its findings remain separate from controller decisions.

`examples.agent_campaign.check_generated_handoff_fixture` exercises this API with a fake source
response, explicit fixture approval and a linked four-role campaign. It reserves three container
starts and three scientific fixture evaluations across both campaigns. It expects eleven scripted
host calls and verifies owned-container removal and replay without replacement execution. Use the
same pinned qualification and fresh-output arguments as the other fixtures. It makes no provider
call and claims neither human author approval nor independent scientific confirmation.

## Experimental brokered scheduler adapter

`hosts.brokered_host.BrokeredCodexHost` connects the version 2.1 transport to the serial scheduler.
Its Python constructor requires an explicit qualification directory and digest, prepared lease
path, lease ID and model. The CLI requires explicit `--host-config` on validate, run and resume.
No qualified native profile or credential is shipped, and configuration grants no live-call authority.

The current native-boundary schema is 1.3. Its fixed policy grants no preference-domain reads,
preference-service lookup, POSIX shared-memory access or inspection of other processes. Only
public hardware/OS sysctls and inspection of the client itself are allowed. The installed 0.164.0
candidate failed that boundary. A separately selected, already installed 0.155.1 binary completed the offline
workflow under it. This is evidence for that exact binary and scope, not general support for an
older release. The adapter pins the inventoried executable and never falls back to another version.

A version 2.1 `HostSelection` must pin `qualification_digest` before its first invocation. The
adapter checks the selection against its configuration, and the journal checks the capability
receipt against that pin. Version 1.0 selections retain their original serialized fields and
digests. A changed model, lease scope, qualification, source, runtime or executable cannot silently
resume an invocation.

The native-profile reader verifies caller-pinned, source-bound attestations and their raw artifact
references. It does not execute probes or establish that an observation is true. Evidence must
come from a reviewed qualification procedure. The current reader requires macOS ARM64 and binds
the OS build, Python executable, TLS library, public trust roots, exact Codex executable, boundary
source and declared limits. Its check groups cover filesystem access, symlinks, network, tools,
credential separation, lifecycle, bounds and a native text round trip. Authored decoder fixtures
exercise validation only. They are not qualification evidence. Every check requires one bounded
raw evidence index. The reader verifies its source/runtime bindings, unique paths, aggregate
size and every indexed artifact hash.

The offline producer runs the permission canaries, native text/tool/lost-ack/timeout/cancel
cases, supervisor death, output/schema limits, a slow-body deadline probe and synthetic-secret
artifact scans. Supply the exact installed executable and a fresh output directory under an
owner-private parent:

```sh
pixi run python -m examples.agent_campaign.qualify_native \
  --output outputs/native-boundary/run \
  --executable /absolute/path/to/eligible-native-candidate
```

The producer installs nothing, reads no real credential and makes no real provider call.
It retains failed observations and never retries them into success. Review the saved evidence
before using the emitted digest as a trusted pin. A local native profile grants no live-call
authority and does not establish real provider or scientific conformance.

The adapter stages a fresh workspace and home, renders the fixed macOS policy, and persists the
exact framed prompt before launch. Structured output uses a strict outer object with one string,
`handoff_json`, containing the role response. The scheduler validates the inner role schema and
retains scientific authority. Raw native events, outer transport output and normalized role
output remain distinct. Model identity and usage come from the approved upstream response.

Preparation consumes the original worker deadline. A known setup failure, cancellation or
expired preparation has a durable prelaunch result and starts no native client. Recovery checks
the saved adapter context and versioned transport receipts, restores model/usage and parses saved
bytes without another call. Missing receipts or uncertain ownership leave the invocation pending.
An in-flight owner death can now end as `host_failure` when both owned groups are verified stopped,
the original supervisor is absent and all command/request bindings match. The duration, model
identity and usage stay unknown. Missing completion never becomes success. Other partial startup
or result-commit gaps without this proof remain pending.
Returning from an upstream callback does not prove its separately owned worker stopped.
The adapter requires a bound watchdog stop proof for that worker before releasing the invocation.
A later read-only recovery can record fresh stop proof while preserving the original uncertain
completion. It cannot turn uncertain command output into a successful response.

The offline fixture below uses the installed Codex executable and actual macOS policy. It stubs
qualification and supplies authored responses instead of credentials or a provider connection:

```sh
pixi run python -m examples.agent_campaign.check_brokered_scheduler_fixture \
  --output outputs/brokered-scheduler-fixture \
  --executable /absolute/path/to/eligible-native-candidate
```

Use a fresh output directory. The fixture expects seven native clients across four serial roles,
two synthetic scientific attempts and unchanged replay. Its receipt explicitly reports
`host_qualified: false` and zero provider calls by default. Supply both `--qualification-root`
and `--qualification-digest` to verify a real pinned native profile without the qualifier stub.
The explicit executable must match that profile. Replies remain authored, and the receipt records
the qualification mode. Actual provider conformance and measured Leaf River attempts are
recorded separately in the [acceptance inventory](reviews/part-3-completion-audit.md). These
fixtures do not establish those results.
`--executable` selects only this fixture's candidate. It changes no installation or global CLI
selection. The receipt records the exact executable, version, digest and selection method. Omitting
it uses `PATH`, which may select a client that cannot run under the strict policy.

## Explicit CLI host configuration

Place host metadata in a TOML file under an owner-private directory. It has exactly these five
fields. Paths must be absolute and contain no symlinks. The credential must be a prepared lease
outside the qualification evidence, worker run and scientific campaign directories:

```toml
schema_version = "1.0"
qualification_root = "/absolute/private/native-qualification"
qualification_digest = "<reviewed qualification.json SHA-256>"
credential_path = "/absolute/private/prepared-lease/lease.json"
lease_id = "selected-lease"
```

The run specification separately selects `codex`, `subscription`, adapter `2.1`, the exact
model and the same qualification digest. Unknown fields, duplicate TOML keys, unsupported
versions, oversized configuration and mismatched profiles fail before run creation. The file
contains no access token, account ID or refresh token. It names no endpoint or executable override.
`agents validate` checks the profile and limits without opening the lease or making a model call.

After separate live authorization, supply the same semantic configuration for each command:

```sh
pixi run autoengineering agents validate run.json --campaign campaign --host-config host.toml
pixi run autoengineering agents run run.json --campaign campaign --workdir worker \
  --host-config host.toml --max-new-evaluations 0
pixi run autoengineering agents resume worker --campaign campaign --host-config host.toml \
  --max-new-evaluations 0
```

The zero scientific allowance is intentional in this command illustration. A scientific campaign
needs its separately approved allowance. CLI configuration neither prepares nor refreshes a lease,
discovers an auth cache, installs a client or grants live authority. The selected native executable
comes only from the pinned profile. Missing credentials fail in the fixed transport preflight.

A configuration digest and capability receipt are committed as the second worker journal event,
before tasks, requests or invocations. Resume requires the original binding, including paths and
lease ID, even before the first host call. Only a run with its creation event and no activity can
finish an interrupted binding commit. Existing API runs with activity and no binding are not
silently adopted. All later invocation capabilities must match. Status/report remain read-only
and work without a profile, lease or scientific campaign. Reports expose the binding metadata
digest, never a credential hash.

The actual-profile CLI fixture substitutes only authored upstream replies:

```sh
pixi run python -m examples.agent_campaign.check_configured_cli_fixture \
  --output outputs/configured-cli-fixture \
  --executable /absolute/path/to/eligible-native-candidate \
  --qualification-root /absolute/private/native-qualification \
  --qualification-digest <reviewed-sha256>
```

It checks validate, seven native starts over four roles, two synthetic scientific attempts,
the binding event and unchanged resume. It uses no real credential or provider, and does not
establish live provider or Leaf River conformance.

## Shared batch allowances

`agents.batch.BatchSpec` freezes an aggregate host/scientific allowance, ordered cases,
configuration digests, host capabilities and source/environment identities. It is strict JSON,
with the same 64 KiB envelope bound as other worker records. Cases cannot expand the aggregate
ceilings. A manifest grants no credential, network or scientific execution authority.

```sh
pixi run autoengineering agents batch-prepare batch-spec.json --workdir private-batch
pixi run autoengineering agents batch-status private-batch --expected-digest <batch-digest>
```

The specification must already contain concrete reviewed values. `batch-prepare` creates a new
private runtime ledger and starts its clock, but executes nothing. Prepare the specification
before seeking live approval. Instantiate a live runtime ledger only after that approval so
human review time does not consume the run window. Retain the returned digest, which binds the
specification and immutable creation time. Opening a ledger without a trusted pin permits
inspection, not mutation. `batch-status` imports no host or scientific controller.

The batch journal records a case start, every physical reservation, observations and the case
result. One operation lock spans physical work; short writer locks protect commits. Read-only
inspection and evidence recovery remain separate. A pending reservation blocks every later
host or scientific start and prevents finishing the case. A failed case stops the batch.
Reopening cannot reset allowances, cases or creation time. Reservations and known evidence are
never erased. An identical terminal observation is idempotent, while changed terminal evidence
fails visibly. The trusted runner decides whether a protocol case passed from its receipts.
The counter alone cannot establish that a process ran or a scientific result is correct.

`BatchCodexHost` reserves before native dispatch and binds the batch/case into worker capabilities.
It clips capture to the transcript bytes still available. The byte charge covers the worker
prompt, combined raw capture and final text, rather than a quota over the whole transport/home
directory. Unknown bytes retain the reservation ceiling. Schema staging has its own declared
workspace bound. Request intent, provider acceptance and actual usage remain distinct.
Saved native output recovers through both journals without another launch. A native transport's
`completed` status does not replace the scheduler's typed handoff or task-completion checks.

`BatchCampaignController` reserves before the existing trusted controller starts an evaluation.
It preserves the original scientific interface, acceptance, attempt records and recovery. Opening
the controller with a larger invocation allowance cannot reset the batch's aggregate cap.
Outer reservations remain charged even when the inner campaign records zero cost. Recovery
requires original attempt/receipt bindings and observed group absence. Missing pre-attempt
evidence remains pending. No unknown observation becomes a free retry.

Both adapters check the active case and physical scope. The batch checks its clock again after
reservation commit and immediately before calling the bounded implementation. A delayed commit
that exhausts the window leaves a pending charge and starts no process. Observations and stop
reconciliation may be recorded after expiry, but new work is refused. The owned native/scientific
supervisors retain responsibility for stopping active processes and preserving stop failures.

The offline fixture below combines two serial cases under one real pinned native profile:

```sh
pixi run python -m examples.agent_campaign.check_batch_fixture \
  --output outputs/batch-fixture \
  --executable /absolute/path/to/eligible-native-candidate \
  --qualification-root /absolute/private/native-qualification \
  --qualification-digest <reviewed-sha256>
```

Only replies are authored. Four roles and a direct text case use eight native clients, while
the original synthetic controller performs two scientific attempts. Batch, worker and scientific
replay must preserve these counts and physical bytes. This tests shared accounting, not real
authentication, provider conformance, Leaf River performance or the single-agent comparison.

## Conformance review preparation

The conformance preparation commands capture a reviewable proposal before a runtime or clock
exists. The worker file is a template. Preparation preserves it and creates a distinct
`conformance-roles` specification with the fixed proposed protocol limits. It does not change
the input run's limits, create a worker journal, read the lease or execute a model:

```sh
pixi run autoengineering agents conformance-prepare codex-template.json \
  --campaign unused-synthetic-campaign --host-config host.toml \
  --output private-proposal --runtime-root /absolute/private/future-runtime
pixi run autoengineering agents conformance-inspect private-proposal \
  --expected-digest <conformance.json-sha256> --host-config host.toml
```

The source campaign must be unused and match the public scalar conformance fixture: forcing 2,
prediction 3, supplied linear replacements, the original acceptance rules and known scientific
source closure. Calibration, confirmation, relaxed criteria and extra source/data paths are
rejected before capture. The proposal contains the template, scientific YAML and declared source
and data bytes. Its manifest is committed last. A partial directory cannot be reused.

The preparation pins six cases, their criteria and the shared ceilings: 16 host reservations,
12 logical tasks, two repairs, 720 seconds, 30 seconds for a worker, 1 MiB of journal transcripts,
64 KiB of staged workspace and two synthetic scientific starts. The declared cases allocate
13 host calls, with three unallocated slots. The four-role case permits seven calls without
repairs. A separate malformed-handoff case permits one repair. No measured-data work is included.

Preparation and runtime need private, separate roots. The runtime must be absent.
Preparation verifies the native profile and metadata, without opening the prepared credential.
Inspection checks the caller's manifest pin, every captured artifact, the original template,
fixed limits and source/scientific identities. Supplying `--host-config` also rechecks current
profile and configuration compatibility. It does not start the batch clock or infer approval.

All six execution handlers are implemented. Inspection returns `execution_ready: true` when
the fixed protocol is supported. This states implementation readiness only. A valid preparation
is not a passing case or authorization request. The
[execution design](implementation-plans/part-3-live-conformance.md) lists the remaining work.

The trusted Python `ConformanceRuntime` API creates the declared runtime only on an explicit
execution call. Its origin binds both preparation and runtime digests. Reopening requires both
original pins and the same host configuration. `advance(max_new_cases=N)` limits work for that
invocation without resetting global allowances. All six cases execute in the frozen order. A failed case stops the batch, and unresolved work remains pending.
This API is execution, not live authorization. It has not been run against a real account.

After separate execution authorization, use the preparation's absent runtime root:

```sh
pixi run autoengineering agents conformance-run /absolute/private/proposal \
  --expected-digest <preparation-sha256> --host-config /absolute/private/host.toml
pixi run autoengineering agents conformance-resume /absolute/private/proposal \
  --expected-digest <preparation-sha256> --runtime-digest <runtime-sha256> \
  --host-config /absolute/private/host.toml
pixi run autoengineering agents conformance-status /absolute/private/runtime \
  --expected-digest <runtime-sha256>
```

Run and resume print the original preparation/runtime pins and runtime root to stderr before
case dispatch. Keep that receipt for recovery if the process ends before its final JSON report.
Run and resume accept `--max-new-cases N` to limit that invocation. They retain all original
aggregate ceilings, case order and clock. Zero creates or inspects the pinned runtime without
starting a case. A nonempty runtime requires resume. Exit 2 reports invalid input, exit 3
unresolved work and exit 4 a failed case. Status reconstructs saved evidence without importing
the native host or scientific controller. It does not revalidate today's native profile or
credentials. `live_conformance_complete` requires all six passing case proofs and rejects the
explicit authored-provider attestations used in unit fixtures.

Text and role cases require saved proof from the exact fixed subscription worker, including
scope, request intent, successful response metadata and owned-command recovery. An authored
reply alone fails the provider gate. Resolved model identity must be observed. Supplied usage
is retained, with missing usage left unknown. Provider metadata and direct native captures are
copied into hash-verified case evidence. Role and malformed-case reporting also recheck the
original worker journals.

The timeout probe requests a one-second execution window and requires that the fixed worker
reached its request-intent stage. Cancellation records a durable intent at that stage, then
waits for the native/upstream stop proofs. A completed response or failure before the intended
stage does not count as an exercised case. Both handlers preserve unknown usage, record that
a request may have been sent and leave remote computation stop unknown. No automatic retry is
added. Saved invocation metadata recovers the same native result rather than creating a new call.

Owner-loss runs the native client and fixed upstream worker inside a source-bound supervisor.
The upstream launch callback holds an owned trampoline before it can execute the fixed
subscription command. A readiness receipt
binds the supervisor, native and upstream identities, nonces and pinned job. Only after verifying
that receipt does the trusted parent record interruption intent and terminate its owned
supervisor group. Independent watchdogs stop the native and upstream groups. Recovery verifies
the stopped groups, original inputs and subscription policy, then retires the original native
reservation as host failure. It starts no replacement client. The fixed worker never reaches
credential preflight in this case. Native model, usage and elapsed time remain unknown, and its
transcript ceiling stays charged. A proven native failure before readiness is an unexercised
failed case. A locally stopped transport with an unresolved response remains pending and keeps
its transcript ceiling. Local stop evidence is retained separately from batch settlement.
Missing observations remain pending. This proves local
interruption before preflight, not in-flight provider recovery.

The malformed case has one task, two host calls and one repair. Its initial prompt supplies
only the specific invalid diagnostic contract, without the contradictory ordinary role template
or valid-handoff contract. It verifies the actual provider payload, strict rejection and saved
parse failure, then supplies the ordinary role contract and permits a typed `stop`
handoff. A transport failure, different payload, valid first handoff or missing fixed-worker
proof fails the case without spending the repair. Both calls retain their original outputs,
identities and usage. The scheduler receives no scientific tools or grants. Recovery preserves
the same task and call sequence, and reporting verifies the saved worker evidence.

The actual-profile preparation fixture uses execution tripwires, leaving both the proposal and
input campaign unchanged during inspection:

```sh
pixi run python -m examples.agent_campaign.check_conformance_preparation \
  --output outputs/conformance-preparation-fixture \
  --executable /absolute/path/to/eligible-native-candidate \
  --qualification-root /absolute/private/native-qualification \
  --qualification-digest <reviewed-sha256>
```

`check_conformance_provider_gate` takes the same arguments and executes one actual native text
case with an authored callback. Its expected runtime outcome is failed because fixed-provider
proof is absent. The fixture passes only when that rejection stops further work, keeps the one
charged invocation and replays unchanged. It is adverse offline evidence, not provider conformance.

`check_conformance_malformed_fixture` takes the same arguments and runs the malformed handler
with the actual native policy. It explicitly stubs the zero-work case prefix, provider proof
and replies to isolate local parsing, one repair and replay. Its passing fixture establishes
local transport integration only. It opens no credential, starts no science and cannot establish
provider conformance. The authored prefix does not establish conformance of the other cases.

`check_conformance_owner_fixture` takes the same arguments and runs the unmodified owner-loss
handler through the resume CLI with the actual native profile and fixed upstream command.
Only preceding zero-work case verdicts are authored. It verifies interruption before preflight,
retained unknown cost, stopped groups, and unchanged CLI resume/status. It opens no credential,
contacts no provider and starts no science. A pass covers this local interruption scope only.

`check_conformance_cli_provider_gate` takes the same arguments and exercises public run,
startup receipt, failed provider gate, resume and status with one actual native client. Only
the response is authored. A passing fixture means the unmodified provider gate correctly
rejects that response, keeps the charged call and replays unchanged. It is not live conformance.

## Native policy permission canaries

`hosts.native_canaries.probe_native_policy` runs synthetic permission checks on macOS without a
provider, real credentials or scientific evaluation. It compiles the package's fixed C probe with
the existing `/usr/bin/clang`, runs unrestricted controls, then runs the probe under the exact
policy renderer used by the adapter. The policy's executable literal names the probe instead of
Codex. The receipt records this substitution and always reports `host_qualified: false`.

The controls open synthetic private, checkout, evaluator, cache and lease files. They also prove
that both forbidden listeners work. The confined probe must deny those reads, outside/workspace
writes, symlink escapes, forbidden TCP/Unix connections and another executable. Approved brief
reads, home writes and the designated loopback connection must succeed. Denials count only for
permission errors, so a missing file or dead listener cannot count as a passing boundary check.

Version 1.2 adds synthetic CoreFoundation plist reads and a synthetic POSIX shared-memory object
under the former `apple.cfprefs.*` grant. Unrestricted controls read these fixtures. The confined
probe must deny both preference-service reads, including the staged workspace plist, and the
shared-memory mapping. Ordinary approved file reads remain required. The shared-memory object is
created exclusively, contains only a public canary and is removed on completion or failure. No
real preference value is copied, no preference is written and no existing shared-memory object
is enumerated or mapped. Recovery checks that this fixture's object is absent.

The earlier policy with the prefix grant failed the new shared-memory check. Removing all
preference grants closed that access. Earlier 1.1 evidence and its failure are preserved. Version
1.2 deliberately requires denial of preference services, rather than the 1.1 prototype's
successful workspace preference read. It retains the original filesystem and network requirements
and uses a separately selected native candidate. This does not make the earlier candidate pass.

Version 1.3 adds a clean owned process carrying only a synthetic environment sentinel.
The unrestricted probe must find it, and the confined probe must receive a permission denial.
The probe queries only this explicit PID and returns booleans. It never enumerates or reads
other process environments. The owned child is stopped after both checks.

Use a fresh child of an owner-private directory. A short path is needed for macOS's Unix socket
limit. This command needs the existing Apple command line tools but installs nothing:

```sh
mkdir -m 700 outputs/native-policy
pixi run python -m examples.agent_campaign.check_native_policy_canaries \
  --output outputs/native-policy/run
```

The saved receipt binds the host source, runtime, compiler driver, probe binary, rendered policy,
raw observations and owned process receipts. Pin its SHA-256 after review. To verify saved evidence
without compiling or rerunning the canaries, pass that pin with `--expected-digest`. Recovery checks
all artifact hashes, exact commands/environments, watchdog receipts and current group absence.
It also inventories public trust roots in a bounded clean Python process and uses process
inspection. It does not launch a compiler, native client, permission probe or provider request.

Synthetic permission evidence alone cannot prove the native CLI's complete behavior or qualify
a host. It cannot become a qualified native profile through the profile reader. Native lifecycle,
complete qualification, production configuration and the authorized pilot remain separate gates.

## Abandoned invocation recovery

The registered adapter verifies the fixed subscription worker's path, exact source closure,
model, lease ID and credential-path metadata before inspecting an abandoned attempt. It does not
open the credential, renew the lease or send a request. Extra source files and aliases to the
credential path are rejected. A live worker configuration cannot silently migrate its fixed
worker path to a different package installation. Read-only journal reports remain available.

Recovery binds the native process to its original journal receipt. Both watchdogs must verify
their source, nonce and group stop. Their owner PID/start times must match, and a successful process
listing must establish that the original supervisor is gone. This also establishes loss of its
endpoint thread and socket because the source-bound SDK passes no listener descriptor to its
workers. Recovery neither contacts the old port nor signals a PID.

The approved exchange request must match the saved upstream request exactly. The immutable native
command, prompt, schema, captured policy and fixed upstream command are verified. This initial
path handles owner death before native completion, timing, endpoint-stop or outcome commits.
Existing result records use their normal decoder. Corrupt or missing proof leaves the invocation
pending. No partial record is relabeled as a successful response.

A verified abandonment appends a private recovery receipt and a `host_failure` worker event. The
physical transport tree stays unchanged. The original invocation remains charged. Elapsed time,
resolved model and usage remain null/unknown, with no normalized role output. The run clock and
remaining invocation/repair allowances retain their original limits. Repeating recovery starts no
new native or upstream work. Local stop proof does not establish that remote computation stopped.

The explicit offline fixture below uses a stubbed qualifier and the actual selected native CLI.
It holds the fixed upstream before its launch gate, kills its own supervisor, then reconciles the
journal. A deliberately absent lease is never opened, and no provider request is possible:

```sh
pixi run python -m examples.agent_campaign.check_abandoned_scheduler_fixture \
  --output outputs/abandoned-scheduler-fixture \
  --executable /absolute/path/to/eligible-native-candidate
```

Use a fresh child of an owner-private directory. The fixture reports one native invocation,
`worker_state: host_failure`, unknown usage/duration and `host_qualified: false`. It tests recovery
plumbing and strict native execution, not production authentication, provider cancellation or
scientific improvement.


## Provisional Claude API adapter

`hosts.claude_host.BrokeredClaudeHost` now implements serial scheduler dispatch,
original-result recovery and the same typed role/grant validation. `BatchClaudeHost`
uses the existing permanent physical reservation/observation journal. No actual
Claude production qualification or model conformance is published. The adapter
refuses an absent, incomplete, changed or foreign qualification before a credential
read. An authored decoder fixture is not qualification or live-call authority.

Claude selects `kind: claude`, `auth_mode: api`, `adapter_version: "3.0"` and an
explicit `qualification_digest` in HostSelection. Capability schema 1.1 preserves
measured limitations and `usage_basis: reported_message_fields_only`. Configuration
bindings use schema 1.1. Previous fake/Codex record bytes, capabilities and schema
1.0 configuration digests keep their original formats.

The explicit metadata TOML uses schema 1.1:

```toml
schema_version = "1.1"
host_kind = "claude"
auth_mode = "api"
qualification_root = "/absolute/private/qualified-claude-profile"
qualification_digest = "<sha256-of-qualified-receipt>"
credential_path = "/absolute/private/api-lease/lease.json"
lease_id = "operator-selected-lease"
```

This is metadata, not credential discovery or permission to prepare/read a real
key. The caller must provide a named prepared API lease outside native read scopes,
Git, qualification and scientific/worker directories. Native Claude receives an
invocation-local helper capability. The API worker owns the real key separately.
No key is placed in the native environment, command or transcript.

`claude_profile.verify_claude_profile` requires a separately versioned receipt,
every source/runtime/executable/API/model/limit binding, all check categories and
all indexed raw evidence. Codex receipts cannot be relabelled as Claude. Its
observations are trusted qualifier attestations. Hash verification does not prove
an unperformed canary. No new actual profile is qualified by the unit tests.

The current candidate is macOS ARM64/API only. Native USD is an SDK estimate,
remote stop remains unknown, and the observed-token rule is not a hard provider
cap. Memory, CPU, process-count and native-home disk caps are not enforced by this
candidate. The staged read-only workspace, process time/output and transport byte
bounds must not be described as those broader resource caps. These limitations
remain visible in capability records.

Broker counters, including usage reported for rejected handoffs, enter the worker
and physical journals. Missing cache categories remain unknown. Native SDK
zero-fill and estimated USD never replace broker unknowns or establish billing.
Existing accounting retains uncertainty and permanent charges. Complete monetary,
training/solver and human-effort joins still require the Part 5 study evidence.

The authored CLI rehearsal completes seven role calls, then resumes with no new
calls or changed worker bytes. Batch lost-acknowledgement recovery retains one
physical charge. These are implementation checks, not actual-model or utility
results. Conformance preparation now has a distinct Claude/API schema and protocol.
Actual qualification and live conformance remain separate work.
See [host integration evidence](../examples/utility/verification-claude-host-v1/README.md).


Claude/API conformance preparation uses `host-conformance-preparation-1.1`.
The existing `agents conformance-prepare` and `conformance-inspect` commands accept
an explicit Claude 3.0/API run with host configuration 1.1. They verify the
caller-pinned Claude qualification and capture only the same public synthetic
campaign inputs. Preparation opens no credential, creates no runtime and starts
no batch clock. A real qualified Claude profile is still unavailable.

The six cases are text, roles, timeout, cancel, owner loss and malformed handoff.
Their fixed allowances total thirteen host invocations and two scientific starts.
The Claude protocol has its own digest and API-specific criteria. Codex subscription
proofs cannot qualify it. Runtime schema 1.1 now executes the text, roles, timeout,
cancel and malformed handlers through BatchClaudeHost. The owner-loss case uses
a separate trusted child and fixed Anthropic worker held before lease preflight. It verifies original
Anthropic fixed-worker evidence, exact API send intent and response receipts.
Local stops and remote completion remain separate. Missing token categories stay
unknown. Saved invocation and case-verdict recovery reuse original evidence.

All six handlers are implemented. Inspection's execution_ready field describes
handler availability. It does not attest qualification or authorize live work.
Owner-loss recovery verifies the original native/API watchdogs and shared owner
absence without opening a key, using an old port or launching a replacement.
Duration, usage and resolved model remain unknown. Changed or partial completed
evidence must pass its normal decoder and cannot use abandoned-call recovery.
The owned API worker's closed launch gate proves preflight did not start in this
case. Local stopping still does not prove remote completion in other cases.

An authored six-case run completes and replays without new work. Its qualifier,
native peer and provider-response proofs are test fixtures. It cannot establish
live conformance. The Codex 1.0 preparation/runtime format and execution path remain
supported. Runtime creation is execution and needs the caller's explicit instruction
and qualified profile. Actual qualification and live-call authority remain open.


Claude boundary qualification schema native-claude-api-boundary-1.1 requires the
owned_user_domain_canary_not_visible preference observation. The separate
probe_claude_preferences diagnostic uses a new synthetic CFPreferences domain and
a substituted executable. Its bounded cleanup can require explicit caller-pinned
reconciliation after asynchronous storage flush. That reconciliation verifies
original controls and stopped processes without another preference request.
Existing-domain content is not a test input. Version 1.0 qualification records do
not satisfy the new requirement. Full qualification remains open. Raw scope and
cleanup limits are in examples/utility/verification-claude-preferences-v1.
