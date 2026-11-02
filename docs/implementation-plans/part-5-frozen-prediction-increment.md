# Part 5 protected frozen prediction increment

Status: candidate grant/replay, local inference, composite orchestration and nested
receipt verification implemented. Protected runtime qualification remains open. No private runtime registration,
private-data admission or execution authority is added. The full
[Part 5 plan](part-5-utility-confirmation.md) remains the objective.

## Observed interface gap

`ContainerRMSEScorer` accepts a precomputed prediction vector. Its identity includes
that artifact's hash. It neither imports nor executes a model. The fixed scorer
worker must retain this narrow contract. `ConfirmationService` reserves and records
confirmation access before calling the scorer. Its legacy grant permits one
scoring start. `ConfirmationContainerExecution` binds one physical container to that
grant and result. None of these interfaces accounts for a preceding model run.

The supplied learned routing registration can already infer from verified v2 state
without fitting data. Scripted routes now archive that state. A protected inference
stage between the frozen selection and private vector scorer remains missing.

`CompositeConfirmationGrant` now dispatches through schema
`utility-confirmation-grant-v2` and reserves exactly two starts. Its
`FrozenRoutingInference` binds selected state, runtime metadata, known-exposure NPZ
driver metadata, original seed and bounded time/output. Validation permits a daily
extension with unchanged historical dates, warmup and variable semantics. It reads
no driver arrays. Site/training profile hashes and the frozen selection must match.
The task must request `protected_frozen_routing_score`. Existing vector-only
services refuse execution and recovery before reservation/access; legacy score
receipts cannot complete a composite attempt. This contract is not an admitted
inference/scoring runtime.

The candidate `FrozenRoutingExecutor` now runs the fixed supplied worker through
the existing supervisor. It requires the original composite reservation/access,
pins source/lock metadata and publishes one atomic suite claim before driver reads.
Another workspace cannot reuse that grant. The staged job has no driver-root or
label-root path and includes only the declared NPZ plus verified code/fit metadata.
Shape-based NPZ limits apply before array allocation. The worker verifies the numeric
fitting prefix, replays the frozen model without fitting, retains all states/fluxes,
and applies the fixed physical checks before emitting the existing prediction
vector schema.

Original supervisor/result evidence supports recovery without either driver copy
or a new model call. Corrupt jobs/results and unverified stop refuse. Cancelled
suites permit observation of original completion but no new inference. These are
authored local-process checks. The candidate identity explicitly records an
unqualified boundary. OS privacy, memory/CPU limits, whole-preparation deadlines,
pre-launch recovery and protected runtime qualification remain open.

The candidate composite service now preserves the reserved parent identity while
publishing an explicit subordinate vector grant after inference. Registration binds
both implementations, input grant, environment identities, label hash, partition
and outcome. A public create-only transition precedes inner label access. Receipts
and cold readers verify the original archived inference closure and nested scoring
identity. Failures retain nonnumeric statuses and skip label scoring. Saved result
recovery starts neither stage. A stage that never completed remains unresolved.
Partial accounting retains verified inference work and unknown scoring work.
Authored fixed-worker tests exercise the chain with explicit unqualified execution
metadata. They establish no private OS/container boundary or real data admission.

The [prepared environment inputs](../../examples/utility/prepared-inference-environment-v1/README.md)
now bind a preserved wheel to the existing default Linux x86-64 lock closure:
49 archives and 265,399,717 compressed bytes. The offline preparer and pinned reader
import no wheel code and acquire, install and execute nothing. Twenty-seven focused
tests cover rejection, interruption, no overwrite and reconstructed metadata.
Dependency constraints are retained from the lock, not independently re-solved.

This package has no image identity or execution authority. The cached fixed scorer
profile admits ARM64. The v1 inference job also binds executor identity to the host
interpreter and checks the original workspace digest. A versioned guest transport
and actual Linux image/resource qualification remain necessary. Proposed bounds
in the input review are not measured limits. Existing scorer allowlists and v1
inference jobs remain unchanged.

Candidate guest transport now uses `utility-frozen-inference-job-v2`. V1 keeps its
original fields, host-interpreter binding and path scope. V2 binds a pinned guest
profile/environment and uses an opaque grant/executor/nonce scope. The fixed worker
checks actual interpreter identity, environment metadata and wheel source hashes
before selected-state/model/driver reads. Guest profiles are explicitly unqualified;
the worker cannot attest OCI identity or enforce resource/privacy policy.

An 83-test regression covers v1 execution/recovery, guest metadata and composite
accounting. A later 47-test cold/input check covers parsing without runtime or file
access. Guest relocation tests use authored Linux observations and stop before
science. Legacy execution archives refuse guest jobs. No default executor or CLI
activates the guest contract. The [successor input package](../../examples/utility/prepared-inference-environment-v2/README.md)
contains the new wheel; its image identity remains absent. Qualified guest dispatch,
original container proofs, guest execution/archive receipts and actual boundaries
remain open. The original package is preserved.

A separate candidate `GuestInferenceArchive` now binds original job/environment,
suite claim, launch/policy, start/stop/cleanup, result capture and output hashes.
The reader takes explicit runtime/source pins and never observes a daemon or
restarts inference. Unknown lifecycle time remains unknown. Failed transport or
capture cannot supply a scoring vector. Authored projections passed a 133-test
compatibility regression and a later 72-test guest/archive check. These are record
consistency checks, not actual OCI/OS evidence. Existing local archives remain
closed to guest jobs, and no service/launcher integrates the new archive yet.
Actual producer qualification, image/environment assembly, enforced boundaries
and private runtime admission remain open.

## Implementation requirements

1. Add a versioned composite confirmation contract. Preserve existing vector-only
   grants and receipts exactly. Reserve two scientific starts for the composite
   profile: one model inference and one private vector score. Record each physical
   process/container separately. Reserve time, array/output limits and other admitted
   resource bounds before either stage. Training and host-call allowances stay zero.
2. Bind the inference input grant to the frozen suite/cell/selection, selected model
   and fit, original fitting seed, declared driver artifact, daily axis and outcome
   partition. Verify the complete selection barrier before opening reserved drivers.
   A verified baseline follower retains its source fit and seed. Do not infer a
   new-site or new-task capability from chronological replay.
3. Supply the fixed trusted inference worker with only verified model sources, fit
   closure and permitted drivers. Never pass labels or a directory containing labels.
   Replay warmup and state from declared initial conditions, preserving the fitting
   driver prefix and initialization. Any extension of the selected time axis needs
   an explicit, validated replay contract. No fitting, interpolation, new preprocessing
   or implementation selection may occur during confirmation.
4. Retain all model states/fluxes required for physical checks before reducing output
   to a prediction vector. Bind that vector to model, partition and frozen selection
   hashes using the existing vector schema. Scientific/model/infrastructure failures
   remain distinct; they cannot become numeric scores or trigger a fallback model.
5. Register one immutable composite identity covering both fixed implementations,
   input grants, source/environment closures, outcome and qualified boundaries.
   The inner vector scorer's identity becomes known after predictions exist. Add an
   explicit parent/child execution binding and offline verifier for that transition.
   Do not silently substitute its digest for the originally reserved scorer identity.
6. Persist intent before each process start and private-byte access. Commit inference
   outputs and original start/stop proof before entering the label-scoring stage.
   Recovery reads original evidence only. A completed inference is never repeated;
   uncertain starts remain charged and block retry. A completed public score replays
   without another model run, label read or scoring process.
7. Qualify the actual inference boundary separately from the fixed stdlib vector
   scorer. The current cached scorer image and its 64 MiB profile do not establish
   a NumPy/SciPy model runtime. Keep the existing scorer image/worker allowlists
   unchanged. Prepare any additional environment as a concrete package before
   requesting installation, image acquisition or other new authority.

## Acceptance evidence

Use authored inputs first. Exercise the actual frozen model and existing score
worker through the composite contract. Verify physical checks and score parity,
no optimizer or fitting intent, zero fitting-label access, wrong seed/model/axis/
partition refusal, output/resource failures, cancellation and loss at every stage
boundary. Confirm that every replay retains original counts and hashes. Cold
readers must reconstruct both executions without drivers, labels, model imports,
processes or network access. Preserve assigned-cell denominators and unknown costs.

A mock boundary can establish orchestration behavior only. Actual OS/runtime
qualification and admitted data/partitions are separate gates. No real independent
labels, live hosts, remote jobs, new image pulls or independent comparison matrix
are authorized by this increment.

## Transport correction: one-shot stdio bootstrap, 2026-10-30

The candidate direct-worker policy cannot rely on Docker archive operations to
populate or recover the worker's tmpfs. Moby documents separate tmpfs storage for
its archive filesystem view, and Docker removes tmpfs contents on stop. The
candidate v2 policy therefore uses one-shot stdin with the fixed bootstrap and
returns bounded result artifacts on stdout before exit. This is a new pinned
policy identity; original direct-worker records are preserved.

Sources checked for this design decision:
[Moby filesystem view](https://github.com/moby/moby/blob/master/daemon/containerfs_linux.go)
and [Docker tmpfs lifecycle](https://docs.docker.com/engine/storage/tmpfs/).
No actual daemon behavior was qualified by reading these sources.

The codec and worker-side bootstrap now exist. They validate the complete frozen
input closure before extraction, actual interpreter/installed wheel before model
access, one fixed worker invocation and bounded canonical result capture. Saved
readers do not relaunch. Current tests use authored streams, worker stubs and
lifecycle observations. A real host mismatch refuses before extraction. Offline
input package v3 contains the new sources without granting execution authority.

The next owner implementation must attach before the single container start,
commit intent before every external side effect, half-close stdin after the one
request, parse Docker's bounded output frames and retain original lifecycle proof.
It must enforce the original deadline and owner-loss cleanup independently of the
guest. Validate native output, backpressure, cancellation and loss at each boundary
on the actual pinned daemon/image before admission. No ordinary file copy into
an archive view, restart or second model invocation may stand in for this path.
Actual installation, image assembly and execution require their separate authority.

The owner-side Unix attach transport now implements the bounded HTTP upgrade,
Docker frame reader, one verified stdin transfer, half-close and original absolute
I/O deadline. Authored peers and owned native Unix sockets exercise this path.
[Moby's stream copier](https://github.com/moby/moby/blob/master/daemon/internal/stream/attach.go)
supports the non-TTY/`StdinOnce` configuration without interpreting binary input as
detach keys. Actual pinned-daemon behavior still requires qualification. The owner
must bind this transport to identity preflight, durable intents, the single start
and independent watchdog/cleanup. A transport timeout does not supply stop proof.

The creation prefix now checks the original suite/owner and charged access, pins
server/image preflight to create intent and records the original CREATE response
before interpreting it. A successful response can bind the created event. Known
warnings remain adverse evidence; a missing response remains unknown. Observe-only
reconciliation cannot create or start another container. Actual start dispatch is
still unavailable until the independent watchdog, stop and cleanup path exists.
The new HTTP client is tested with authored projections and owned Unix peers,
including absolute deadlines for trickled headers and bounded chunked bodies.
This is not qualification of a real daemon or its mount/resource enforcement.

A candidate detached watchdog now arms from the original reviewed unstarted
creation and uses an anonymous owner pipe plus the original absolute deadline.
It owns only cleanup of the exact original CID/image/labels, with durable intents
before kill/removal and explicit absent, unverified or foreign-refused outcomes.
A saved terminal outcome cannot dispatch cleanup again. Parent disarm requires
completed journal cleanup and fresh daemon absence. Its cold reader verifies saved
observations without new models, API calls or clocks. Authored Unix peer and actual
local child-process tests are separate from actual container/runtime admission.
Start/attach integration, stopped-to-parent reconciliation, initialization recovery
and pinned daemon/image/resource/privacy qualification remain open.

The candidate single-start controller now binds independent watchdog readiness and
completed attach to the original start intent. It captures the START response
projection before interpretation, sends frozen input once and captures output before
observing stop and requesting cleanup. Surviving owners retain measured duration;
interrupted recovery cannot replace missing original timing. Saved reconciliation
can finish only lifecycle transitions supported by original watchdog observations.
It never sends another CREATE, START, attach or model request. Missing start/stop
proof remains incomplete. Later cancellation prevents a complete transport verdict
without rewriting an earlier stop event. The manifest-last completion reader works
from a relocated owner archive.

The dispatch path is still an explicit candidate interface, outside the default
executor/service and scorer allowlist. Actual pinned-daemon/image, installation,
resource/privacy qualification, final inference archive/service integration and
initialization reconciliation remain open. These software fixtures do not admit
independent tasks or authorize their labels, acquisition or scientific matrix.

The v2 guest inference archive now binds original dispatch completion and journal
commitments to start/stop/cleanup projections, capture and permitted outputs. The
publisher validates the original private owner before exporting bounded public
metadata. Raw OCI observations, private paths and driver capsules remain private.
Cold verification requires an explicit publisher pin and reconstructs successful
stdio capture digests from public bytes. It never reads the private owner, original
drivers or labels. Interrupted publication can finish from saved evidence without
new physical execution. Cancellation after an observed stop cannot supply scoring
outputs. Missing lifecycle evidence stays unarchived and charged. V1 records and
local-archive/scorer admission remain unchanged. The guest executor facade and
composite-service integration are still required before runtime qualification and
independent confirmation.

The candidate guest executor facade now joins original charged access, initialization,
input packaging, creation, single-start dispatch and archive publication. A single
initialization record freezes nonce, claim, owner scope, implementation/runtime/
publisher pins and original deadline before reserved-driver reads. Matching partial
metadata can be completed without source/driver scopes, new time or daemon access.
Initialization repair cannot dispatch science, and intended attempts cannot execute
again from another workspace. Input reads now accept the facade's cancellation and
deadline check without changing default callers.

Saved dispatch completion supports archive recovery. A fresh recovery-only facade
loads original registration from public metadata, holds no source/driver/API scope
and refuses execution. Published results replay after original work and drivers
are removed. Incomplete preparation/creation remains charged rather than retried.
Early owner loss before watchdog arming can leave an unstarted resource requiring
explicit cleanup. Synchronous filesystem calls remain uninterruptible; checks prevent
late dispatch after return. These limits and actual runtime/privacy qualification
remain open alongside composite-service integration and independent confirmation.

A separate v2 guest composite registration/service now binds the guest facade and
its runtime/publisher/policy to the existing vector scorer. Vector and local services
refuse it before access. The unchanged parent grant reserves both stages. Original
inference evidence and completed initialization precede the create-only handoff to
the prediction-specific inner grant. Failed inference cannot authorize scoring.
Recovery can finish original publication but never start an unfinished inner score.
Guest accounting records the two container stages separately and preserves unknown
scoring/total counts and durations after loss. V1 registration, local receipts and
local counts remain unchanged. The new service remains an unqualified candidate
outside default activation. Actual runtime/privacy, data admission and scientific
confirmation remain open.

Original creation cleanup now handles failures before watchdog ownership. It binds
original response/name/CID, image and owner labels under the original suite/owner
writers and charged access. Cancellation/resource drift does not prevent owned
cleanup. One fixed 10-second plan, durable target and kill/removal intents prevent
new allowances or repeated mutations after interruption. Unknown CREATE plus named
absence stays unresolved. Unverified removal remains charged. Cleanup blocks
scientific/journal advancement and cannot produce an inference receipt. Existing
watchdog ownership prevents a competing cleanup owner. The facade attempts scoped
early cleanup while preserving its original error. Late unresolved creation and
interrupted watchdog startup still require explicit resolution, alongside actual
runtime/privacy and independent scientific qualification.


## Original watchdog startup cleanup reconciliation

`reconcile_startup_cleanup` and the guest facade's explicit
`cleanup_watchdog_startup` resolve an original unstarted owner after interrupted
arming. They require the original suite/owner writers and charged access. The
watchdog holds a separate cleanup lease throughout its lifetime. Reconciliation
refuses a live lease, and a delayed child sees cleanup evidence before publishing
readiness. No replacement worker, attachment, START or scientific allowance is
created. The facade preserves its original error and charges.

The first cleanup fixes a window bounded by ten seconds and the original plan's
cleanup cap. Its reason and consumed kill/removal intents survive interruption.
Expiry produces uncertainty without an API call. Missing legacy timing evidence
refuses a new allowance. Saved outcomes bind the window digest, while old completed
records omit the new optional field and retain their bytes. A start intent is
refused once cleanup evidence exists. Saved replay needs no current runtime or
clock. These are authored fixture checks, not runtime/privacy qualification.

The previous extracted wheel and prepared v4 inputs retain their original source
scope and predate this increment. Current installed/platform/host qualification,
strict filesystem timing, unknown late creation/uncertain removal resolution and
independent admission, thresholds and scientific comparison remain open.


## Offline image context materialization

The new administrative `guest_image_context` tool copies only the recipe's
preexisting pinned payloads and files. It validates all inputs before creating
output and rechecks bytes during bounded streaming copies. An explicit private
parent-directory creation step corrected the first run's three permission failures.
Partial copies cannot be overwritten or resumed. The manifest is committed last.
The cold reader checks the exact closure, rejecting changed payloads/recipes/proof,
extra files/directories, symlinks and authority promotion even after repinning.

The final context/image/environment scope passed 61 cases in 2.68 seconds. Guarded
relocated fixture replay passed with original input scopes removed, file reads
confined to the saved context and writes/processes/sockets/clocks denied. Positive
copies use authored bytes and fixture installer metadata, not real packages. The
production recipe was checked against an empty cache and refused missing inputs
before output creation without acquisition or execution. Its first proof harness
had a script-path import error; both that failure and the corrected result remain
retained. Evidence is in `examples/utility/verification-guest-image-context-v1/`.

The prior image plan and prepared v5 wheel remain unchanged. Their core scope is
224 files and the wheel contains 315 Python sources. The new host materializer is
not in that wheel and has no installed-package qualification. Real archives remain
unacquired. A bounded build runner, actual-daemon handlers and separate diagnostic
profiles remain required. No image/container/model/provider, fitting or independent
confirmation ran. The full default suite was not rerun. Part 5 remains incomplete.


## Actual pinned archives and production build context

The new downloader binds an archive-only request to its source, original target
scope, exact HTTPS origin, filename/length/hash list and original deadline. GET
intents are persisted before requests. Redirects, fallback origins and automatic
retries are prohibited. A cache is consumed before the first GET. Interrupted
attempts cannot renew their allowance. Lost final acknowledgement preserves the
original completion. Cold verification checks the exact evidence/file closure.

The final related check passed 85 cases in 3.12 seconds. Tool approval review then
allowed the concrete 50-file archive-only request. All 49 locked package archives
and the micromamba installer passed exact length/hash checks: 272,387,807 payload
bytes in 8.871 seconds. No code was installed or run from those files. A real
production context was materialized and verified, copying 275,243,466 pinned file
bytes. Both outputs are private and ignored by targeted Git rules. No locks,
historical evidence or existing outputs were rewritten.

A fresh isolated administrative reader verified relocated copies of the real
cache and context with original-scope reads, writes, execution, network, clocks,
source probes and array loads denied after code initialization. Installer headers
also meet the recipe's extraction bounds: 58 members, 18,553,507 declared bytes,
and one regular 18,292,808-byte executable member. No file was extracted/executed.
Evidence is in `examples/utility/verification-guest-archive-download-v1/`.

The preceding image plan and runtime wheel retain their original identities and
224-core/315-source scope. The new host downloader/context helper is not in that
wheel. Archive acquisition does not change its authority/admission fields.
Installation, base-image acquisition/build and execution require their separate
authority. A bounded build runner and actual-daemon/diagnostic handlers remain
required. Installed/platform/host, runtime/privacy and independent scientific
qualification remain open. Full default tests were not rerun. Part 5 is incomplete.

## Actual image and interpreter checkpoint

V4 image assembly now completed from the pinned offline inputs. Its Linux amd64
package/core import smoke passed on the local ARM64 OrbStack host. The actual
build and a relocated guarded completion reader are recorded in
`examples/utility/verification-guest-build-actual-v1/`. Future corrected image-build
versions have user approval within their established scope and limits.

A separate fixed metadata probe then observed CPython 3.12.13, Linux x86-64,
isolated execution and the expected installed identity source. It recorded one
container start and original-container absence. Its unqualified profile and
guarded saved replay are in `examples/utility/verification-guest-identity-v1/`.
That observation is a separate reserved operation. It does not consume or satisfy
one of the preserved 26 control cases, or admit a private execution boundary.

The remaining implementation sequence is:

1. Define the fixed diagnostic policy for memory, PIDs, workspace, read-only root,
   network and host-canary controls. Bind exact code, image, caps and cleanup.
2. Bind the observed Python profile to authored frozen-inference fixtures and
   implement the six preflight and fourteen inference/lifecycle handlers.
3. Prepare the complete matrix against those fixed handlers. Retain the original
   20-create/15-start proposed scope and record separate discovery work explicitly.
   Any changed scope gets a new identity and its own authority/accounting.
4. Execute the actual controls under their bounded local-runtime scope. Unknown
   creates, starts or removal outcomes retain charges and block automatic retry.
5. Qualify the full inference/scoring chain before private registration. Preserve
   independent task admission, frozen selections and scientific authority as
   separate requirements of the full Part 5 plan.


## Reviewable local image-build request

The new administrative build helper verifies the saved production context and
pins an installed client and local Unix endpoint using filesystem metadata only.
It prepares six fixed commands for daemon/builder metadata, one immutable base
pull, base verification, one local image build and final original-ID inspection.
An empty Docker configuration and minimal environment exclude ambient remote
builder selection, credentials, secret forwarding, SSH and image pushes. Driver,
endpoint and target-platform checks precede acquisition. Failed jobs remain
consumed and cannot resume or obtain a fresh allowance automatically.

All 103 related cases passed in 5.43 seconds. Docker/build metadata are authored.
Real owned Python client fixtures cover success, timeout and output overflow.
Cold completion validation uses saved request/source/intents/logs/image metadata
without probing a live client, endpoint, source or clock. It does not independently
attest Docker or validate every incidental client cache file. Local CLI help and
filesystem metadata were inspected without contacting the daemon.

`examples/utility/prepared-guest-build-v1/` contains the concrete request and private
ignored machine bindings. No work directory, daemon call, image acquisition,
installation or build has occurred. The proposed job has one 1,200-second client
deadline, 16 MiB per-command logs, one base pull and one build. Base compressed
layers total 45,269,741 bytes, with actual transport usage/retries unknown. CPU and
memory flags are per-step and daemon-dependent. Disk is not quota-enforced and
client termination does not prove daemon cancellation or owner-loss cleanup.

The runtime plan reserves installation/image assembly/execution for separate
authority. That approval is now the next required action for the concrete job.
The image remains an unqualified candidate even if assembly succeeds. Actual
runtime/private, installed/platform/host, diagnostic and independent scientific
requirements remain open. The runtime wheel retains its prior 224-core/315-source
scope and does not contain this host helper. Full default tests were not rerun.
Part 5 remains incomplete.

## Resource diagnostic checkpoint

The six separate fixed resource handlers are implemented and have actual local
evidence against the built candidate. Memory OOM, PID cap, workspace capacity,
read-only root, network denial and host-canary absence passed with one start each
and original-container absence. A prior environment refusal created one extra
unstarted container. Its failed original cleanup and subsequent separate
administrative removal remain preserved. Combined diagnostic counts are seven
creations and six starts. See the
[resource checkpoint](../../examples/utility/verification-guest-resources-v1/README.md).

Saved replay verifies original source/configuration, start/terminal observations
and cleanup metadata without a daemon. A fresh guarded reader checked relocated
proofs. These normal completions do not establish unexpected owner-loss,
cancellation or deadline behavior. The original 26-case proposal and its proposed
budget remain unchanged. Any complete successor matrix must explicitly retain
these separate attempts and bind its own exact scope.

Next, correct inherited-image environment handling in the production inference
policy without changing legacy receipt meanings. Then implement the six preflight
and fourteen fixed-inference/lifecycle controls, assemble the complete successor
matrix, and qualify the inference/scoring chain. Independent task admission and
scientific authority remain separate requirements of the full Part 5 plan.

The environment correction is now implemented in a derivative image rather than
a changed production policy. The original cached filesystem is copied into a
scratch final stage with the exact allowed environment and required provenance
labels. Existing strict checks pass. One metadata container observed its expected
CPython identity and was confirmed absent. Core source and the frozen wheel are
unchanged. The prior failed derivative request remains consumed with no tag/build
mutation. See the
[derivative checkpoint](../../examples/utility/verification-guest-image-environment-v1/README.md).
The complete resource, preflight and inference/lifecycle matrix must bind this
new image and retain all earlier attempts separately. No private admission follows
from its build or interpreter metadata.

## Actual derivative inference checkpoint

Six resource controls now passed against the derivative, with six starts and
original-container absence. The production executor also completed one actual
frozen inference using a previously fitted authored fixture. Its forcing is
explicitly exposed. Fit/seed, source closure, one start, four physical checks,
cleanup and saved recovery are bound in the
[actual smoke evidence](../../examples/utility/verification-guest-inference-smoke-v1/README.md).
No new fitting, scoring or independent confirmation occurred. A fresh process
recovered a portable public proof without source/driver/work roots or model
imports. Core source and the frozen wheel are unchanged.

This smoke is a separately counted operation. It is not the proposed numerical
parity case: no separate reference prediction was computed. Keep all consumed
preparations and executions. Next implement the fixed preflight and failure
handlers using the authenticated frozen fixture, prepare the complete successor
matrix and obtain its remaining evidence. Then qualify the full inference/scoring
chain before private registration. Four-family task/partition/threshold admission
and independent comparative execution remain separate requirements.

The authenticated, exposed fixture is retained in
`examples/utility/verification-guest-inference-smoke-v1/authored-fixture.tar.gz`.
Its selection barrier, code closure and driver hash were checked without new
fitting or model execution. Future controls can use this fixture instead of
depending on the original temporary test directories. The consumed successful
smoke must not be restarted or silently credited to an unverified parity case.


## Separate parity and preflight evidence

A separately reserved native reference now reuses the successful guest smoke's
frozen fit, seed, axis and exposed drivers. It adds one native inference and no
guest, fitting or scoring starts. Tolerances were saved before execution. All
seven outputs and the prediction vector passed. Prediction JSON was not exactly
equal. The [saved checkpoint](../../examples/utility/verification-guest-prediction-parity-v1/README.md)
retains the original producer, supervisor, job, results and arrays. Its reader
recomputes parity without either model execution. This later evidence does not
change the earlier smoke's original scope or count.

Six [fixed preflight controls](../../examples/utility/verification-guest-preflight-controls-v1/README.md)
now produced exact refusals before array/driver access, daemon requests, sockets
or process launches. Expected exceptions were fixed before execution. Parent
composite reservations remain charged. This verifies production facade preflight
behavior under guards. It does not qualify the actual daemon's adverse lifecycle
paths. The original 26-case proposal remains preserved. Implement and freeze the
remaining adverse-output, cancellation, owner/watchdog-loss and lost-response
handlers before their execution. Private scoring and task admission remain open.


## Actual cancellation after creation and before start

Two [actual local cancellation controls](../../examples/utility/verification-guest-cancellation-controls-v1/README.md)
passed against the derivative image using fresh copies of the exposed frozen
fixture. Each created one container and started none. Cancellation after the
original `created` event used production creation cleanup. Cancellation at the
persisted `start_intent` used the production watchdog, which reported cancellation
and absence. Both paths verified original ownership and deleted once without a
kill. Separate actual GETs observed both exact container IDs absent. No fitting,
model, scoring or provider work ran. Parent reservations remain charged.

The saved production cleanup readers verified the original plans, observations,
mutation intents and absence records. A 93-file public archive retains owner and
API proof, including the original transfer tars with known exposed meteorological
drivers. It includes no fitting or private labels. Fresh guarded replay passed
from copied proof and verified archive extraction without separate suite/source/
driver roots. After initialization it permitted only saved content reads and
blocked writes, imports, clocks, array loading, sockets and processes. The initial
cold invocation failed to import example helpers. Both its log and the corrected
results remain. No package-installation or OS attestation claim follows.

The successor `examples/utility/qualification-state-guest-v2.json` preserves the
original proposal and v1 evidence map. It records 15 separately evidenced cases
and 11 remaining adverse daemon cases. Running cancellation, owner/watchdog
loss, adverse output, lost responses and the private inference/scoring chain
remain open. Scientific task specifications and independent utility remain
separate requirements.


## Producer acknowledgment loss after real CREATE and START

Two [actual local acknowledgment-loss controls](../../examples/utility/verification-guest-response-loss-v1/README.md)
passed using the exposed frozen fixture. A wrapper saved successful real daemon
responses, then withheld them before the executor received them. This is producer
response loss, not a network outage. Two containers were created and one started.
Both original containers and the watchdog PID were confirmed absent. CREATE loss
retained `create_intent`; production nonce-bound cleanup found and removed the
original resource without another CREATE. START loss retained `start_intent`; the
production watchdog cleaned the original started resource after exception-driven
owner-pipe closure. This does not establish actual owner-process-kill behavior.

Both original grants refused redispatch with zero API requests. No model result
was observed. The one START remains charged and inference elapsed time remains
unknown. Parent reservations stay unfinished. There was no fitting, private
scoring or provider work in these actual controls. Saved transfer, raw withheld
response, ownership, cleanup and absence proof replayed from a verified 92-file
archive under a fresh guard without separate suite/source/driver roots. After
initialization the reader denied external content reads, writes, imports, clocks,
array loading, sockets and processes. Dependencies were inherited before guarding.

`examples/utility/qualification-state-guest-v3.json` preserves the preceding maps
and original proposal. It records 17 separately evidenced cases and nine remaining
adverse daemon cases. `examples/utility/guest-qualification-accounting-v2.json`
retains 20 creations, 16 container starts and one native reference in its explicit
scope. Three inference starts are charged, including one with unknown model work
and no result. The register excludes build internals and authored test fixtures.
It creates no allowance, refunds nothing and does not complete the original
matrix, private runtime, task admission or independent scientific comparison.


## Exact owned owner/watchdog process loss

Four [actual local process-loss controls](../../examples/utility/verification-guest-owner-loss-v1/README.md)
passed with four creations and two STARTs. Three owners were killed by their
exact Popen handles. The fourth owner killed its own exact ready watchdog handle,
then observed production START refusal and startup cleanup. All original
containers and watchdog PIDs were confirmed absent. No replacement watchdog,
CREATE, START, fitting, scoring or provider call was used for recovery.

Owner loss before watchdog readiness occurred after the saved original plan and
before child spawn. Explicit parent startup cleanup was required. It does not
establish autonomous pre-watchdog cleanup. Running-owner loss occurred after an
actual running START and before input transfer. It does not establish a kill
during model computation. After-capture owner loss preserved the actual model
result and recovered it through the production recovery-only facade without new
inference. Lifecycle time remains unknown. All original starts and unfinished
parent composite reservations retain their charges.

A verified 328-file archive preserves process identities, markers, signal intents,
terminal codes, owner/API/cleanup proof, original known-exposure input tars and
one public saved-result suite. It includes no fitting or private labels. A fresh
guarded reader replayed all four proofs and the captured success without
original work or separate driver/source roots. After initialization it denied
external content reads, writes, imports, clocks, array loading, sockets and
processes. Dependencies were inherited before the guard.

`examples/utility/qualification-state-guest-v4.json` retains the original proposal
and preceding maps. It records 21 separately evidenced cases and five remaining
adverse daemon cases: running cancellation and four adverse-output controls.
The scope limits above remain part of their evidence. The new cumulative register,
`examples/utility/guest-qualification-accounting-v3.json`, retains 24 creations,
18 container starts and one native reference across its listed operations. Five
inference starts are charged. Three model completions are observed and total
model work remains unknown. This does not admit a private runtime, complete the
whole matrix or establish independent utility.


## Running cancellation and saved nonnumeric failure

An [actual running guest cancellation](../../examples/utility/verification-guest-running-cancellation-v1/README.md)
passed with one creation and one START. It required an original observed running
state, then cancelled before input transfer. The production watchdog recorded
cancellation and absence. A separate actual GET confirmed the original container
absent, and its watchdog PID was confirmed absent. This is not evidence of
cancellation during model computation.

The original receipt recovered as `infrastructure_failure`, with no model result
or prediction vector and with unknown lifecycle time. The original START stays
charged, the parent reservation stays unfinished and redispatch refused without
an API request. No new model, fitting, scoring or provider call was used for
recovery. A verified 157-file archive retains the original transfer, owner/API/
cleanup and public failed-receipt proof. Fresh guarded replay required no original
work or separate source/driver roots. After initialization it denied external
content reads, writes, imports, clocks, array loading, sockets and processes.

`examples/utility/qualification-state-guest-v5.json` preserves the original proposal
and prior maps. It records 22 separately evidenced cases with their scope limits.
Four adverse-output cases remain: physical veto, invalid numeric output, oversized
stdout and malformed stdio. The new cumulative register,
`examples/utility/guest-qualification-accounting-v4.json`, retains 25 creations,
19 container starts and one native reference in its explicit scope. Six inference
starts are charged. Three have model completions and three have no model result.
Total model work and missing lifecycle time remain unknown. The broader G1-G8
requirements, private qualification and independent comparison remain open.


## Actual authored guest-to-scorer execution

The [actual composite archive](../../examples/utility/verification-guest-composite-actual-v1/README.md)
now records one production guest inference followed by one production fixed-scorer
container under a single two-start, 94-second parent grant. Both original containers
were observed absent. The score agrees with independent arithmetic on the public
prediction vector and mask. Saved confirm/recover calls reused the committed result.
The drivers and labels are authored fixtures. No fitting, actual observations,
providers or automatic retries were involved.

The guest is Linux amd64 under local ARM64 emulation. The separate score container
is ARM64. This verifies their application-owned chain on the existing local runtime;
it does not establish independent x86 hardware, private admission or a general
cross-platform release. A fresh guarded public reader reconstructs one score and
both stages of costs from 103 copied public files without private files or model
execution. The reader is checkout based, not an installed-wheel qualification.

The accounting successor is `guest-qualification-accounting-v5.json`: 27 container
creations, 21 starts, seven charged inference starts, one new scoring start and one
native reference in its cumulative scope. Three charged inference starts still have
no observed model result. Old uncertainty and unfinished reservations remain charged.
Synthetic label hashes were read during trusted preparation; exact byte-read counts
were not instrumented. This result closes the actual synthetic composite smoke gap,
not the four remaining adverse-output cases or independent scientific confirmation.


The actual composite regression is terminal: 62 passed in 201.28 seconds, zero
failures, errors or skips. The earlier restricted run retains 21 passes, eight
failures and 33 setup errors. A fresh scope with local supervisor/Unix-peer access
passed without source changes. Nineteen documentation tests, repository lint and
whitespace checks also passed. The guarded public reader's fourth initialization
configuration passed before any unguarded suite replay. All preceding failed logs
remain preserved. Current source pins are in
`examples/utility/source-inventory-guest-composite-actual.json`. Core and frozen
guest source bytes remain unchanged. The evidence map v6 adds the actual chain
separately and keeps all four adverse-output cases open.


## Actual fixed-worker numeric overflow refusal

The [numeric control](../../examples/utility/verification-guest-numeric-control-v1/README.md)
now exercises the unchanged guest image with finite, ordered authored forcing.
The 140-row replay retains all 120 selected-prefix rows, including the exact
original 80-row fitting prefix. Only the final 20 temperature rows change. They
are numerical stress inputs that overflow the fixed Hamon exponential, not
admitted meteorological observations. No frozen model, fit or image changed.

One container returned a committed `model_failure` with no output arrays,
predictions or physical-check results. It was observed absent afterward. Saved
recovery matches the original failure. A second execute refuses before a daemon
request. No fitting, scoring, provider call or automatic retry occurred. The
original two-start parent reservation remains unfinished. Model duration is unknown
and stays null. The first preparation confused fitting and selection-prefix lengths;
it refused without a launch and was preserved. Corrected preparation used a fresh
scope and checked those identities separately.

The related regression passed 73 tests with zero failures, errors or skips. A fresh
guarded reader reconstructs the failure from 96 copied public files without model
imports, original drivers, NumPy archive loads, processes, network, clocks, writes
or unrelated file reads. This remains checkout-based verification. Source inventory
`source-inventory-guest-numeric-control.json` records unchanged 224 core and 315
frozen guest sources. Linux amd64 still runs under local ARM64 emulation.

Evidence map v7 records this one actual `invalid_numeric_output` control and leaves
physical veto, oversized stdout and malformed stdio open. It does not promote the
whole original matrix or candidate runtime. Accounting v6 retains 28 creations,
22 container starts, eight charged inference starts, one scoring start and one
native reference in its cumulative scope. Three started inference attempts still
have no model result. Unknown earlier work, original evidence and reservations
remain charged. Private admission, independent real tasks and full Part 5 remain open.


## Actual malformed-frame and oversized-stream diagnostics

The [output diagnostics](../../examples/utility/verification-guest-output-diagnostics-v1/README.md)
run two separately named fixed producers on the cached derivative image. The
production bootstrap header parser rejects a malformed result magic. The production
attach reader rejects an actual oversized stdout stream. It accepted 68,222,976
bytes before a subsequent frame declaration crossed its bound. The rejected
declaration was 68,255,744 bytes. No raw output stream is retained. Both original
containers were observed absent after ownership-checked cleanup.

These are two diagnostic starts and zero scientific/model, fitting or scoring
starts. The frozen image and inference executor's command allowlist are unchanged.
The new profile uses the existing resource restrictions, an aggregate 120-second
cap and a 40-second producer self-timeout. Owner-loss cleanup is not qualified.
The first consumed request passed an aggregate deadline to a per-call transport
and refused before CREATE. A fresh request uses bounded metadata-call deadlines.
All original refusal evidence is preserved.

The offline reader checks explicit caller request/source/parser pins, saved command
and ownership, accepted/declared byte counts, one START and cleanup evidence. It
executes no saved source. The 166-test related regression passed without failures,
errors or skips. A fresh process initializes code explicitly from the checkout,
then reconstructs the two cases with unrelated reads, writes, new imports, models,
processes, sockets, clocks and NumPy archive loads denied. This is checkout-based
verification. The initial cold-reader import failure and tamper-fixture setup
failures remain preserved separately.

Source successor `source-inventory-guest-output-diagnostics.json` records the new
controller/reader and tests. All 224 core and 315 frozen guest sources remain
unchanged. Accounting v7 retains 30 container creations and 24 starts in its
cumulative scope. Inference/scoring counts and earlier uncertainty remain unchanged.
The first request's unused diagnostic reservation is not reusable authority.

Evidence map v8 distinguishes actual-daemon diagnostic evidence from the literal
fixed-model-worker profile. Physical veto still has no actual-daemon case. The
oversized and malformed cases have actual diagnostic evidence, but all three exact
fixed-worker cases remain open. The original proposal was not completed as a whole.
Runtime/private admission, independent real tasks and the full Part 5 goal remain open.
