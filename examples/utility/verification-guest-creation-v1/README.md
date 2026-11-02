# Candidate daemon preflight and original creation

The new API profile pins an opaque endpoint digest, explicit API version, canonical
server fingerprint, critical implementation hashes, the complete core Python source
digest and owner interpreter identity. Live calls check that identity. The client
uses only Unix sockets and fixed version/image/inspect/create operations. Bounded
HTTP parsing supports content length and chunked JSON with the original absolute
I/O deadline, including header/body trickle. It never follows redirects or retries
an API operation. Canonical saved projections are not raw HTTP or OS attestation.

The creation controller requires the original suite/owner writers, lease, immutable
selection, original charged access, fixed stdin policy and prepared input package.
Preflight verifies the pinned server and image, then observes the original name
absent. Its immutable projection is referenced by the create-intent event before
CREATE is issued. A returned response is captured before interpreting its ID or
warnings. A known successful response is bound to the created event. Missing,
changed or contradictory evidence cannot authorize another CREATE.

Reconciliation only observes the original named, matching, unstarted container.
Absence leaves creation uncertain. Known warnings block reconciliation before any
new request. A genuinely lost response stays null in the event rather than becoming
a clean response. That unknown state is not permission to start. The controller
has no start operation until independent watchdog/stop/cleanup is implemented and
qualified. Neither default confirmation service nor existing scorer is connected.

Inspect validation accepts empty ordinary Mounts with the exact HostConfig.Tmpfs
map, plus the preserved authored single-tmpfs projection. It accepts null empty
collections for specified absent binds/devices/capabilities/ports, but still rejects
any host bind, extra mount or changed resource/security setting. The implementation
choice follows Moby's separate map/ordinary-mount handling:
[inspect data](https://github.com/moby/moby/blob/master/daemon/inspect.go),
[container mount lookup](https://github.com/moby/moby/blob/master/daemon/container/container_unix.go),
[mount registration](https://github.com/moby/moby/blob/master/daemon/volumes.go).
These source observations do not establish actual mount enforcement.

The first creation/attach/observation check passed 158 tests in 40.82 seconds.
Review then found that known CREATE warnings needed durable response capture,
otherwise they could be overlooked by reconciliation. That evidence path was
added; creation/owner checks passed 74 cases in 47.07 seconds. The broader related
regression passed 407 cases in 239.59 seconds. The final 39-case creation check passed
in 34.78 seconds, including suite cancellation and fresh cold replay with models,
arrays, processes, sockets, clocks and unrelated/writable files denied. A separate
native CREATE HTTP serialization case passed in 5.38 seconds.

Fault injection covers preflight persistence, both sides of create intent, both
sides of the API operation, response publication and created-event publication.
Before create intent, metadata checks may repeat without a prior CREATE. Once the
intent is committed, the controller never dispatches CREATE again. Original suite
reservations remain unchanged. Known warnings, foreign containers, running states,
missing/corrupt original projections, changed source/server/image and absent access
refuse. Null collection support does not permit a host bind.

Native Unix peers tested bounded content-length/chunked responses and the exact
fixed CREATE request. They do not create a real container. Positive creation and
recovery use authored API projections. The ordinary baseline fit belongs to shared
test setup; no guest model runs. Cold relocated creation and the prior attach
capsule both replay. Optional response references are omitted from legacy events,
preserving their original bytes and hashes.

Current source count is 219 core Python files. This postdates the full default
checkpoint and prepared environment v3, whose scopes remain unchanged. Actual
daemon/image qualification, start/attach integration, watchdog/owner-loss cleanup,
resource/privacy enforcement, independent tasks, useful gains/tolerances and the
scientific matrix remain open. No image, dependency installation or independent
scientific confirmation was attempted.

Nineteen documentation checks passed in 1.04 seconds. Full Ruff, explicit
100-column checks on changed Python files and whitespace checks passed. Regression
source pins identify the 407-case run. Final snapshots also include the later
cancellation/cold-process and native POST checks. Core source was unchanged
between those successful runs. No actual daemon endpoint was contacted.
