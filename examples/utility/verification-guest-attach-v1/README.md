# Candidate Unix attach transport

`utility.guest_attach` opens one explicit Unix stream endpoint and sends only the
fixed versioned attach request for an immutable container ID. It requires an HTTP
101 upgrade and a known raw/multiplexed media type. Header size/count, frame count,
stdout, stderr and request bytes have fixed bounds. Prefetched output and fragmented
frames are preserved. Stderr is counted and discarded without exposing its bytes.
Unknown channels, malformed/truncated frames and excess output refuse.

One verified bootstrap request is matched to expected job/launch/package digests,
then written once and stdin half-closed. Partial writes, cancellation and errors
consume the connection's input attempt. No method reconnects or starts/restarts a
container. The original monotonic deadline covers handshake, input, output and
EOF waiting, with cancellation polled during idle I/O. Short connection timeouts
remain unverified connection outcomes, not invented absolute-deadline/model failures.
An I/O timeout or closed descriptor is not proof of container termination.

The framing and upgrade design follows the current primary sources:
[Moby attach client](https://github.com/moby/moby/blob/master/client/container_attach.go),
[HTTP upgrade](https://github.com/moby/moby/blob/master/client/hijack.go), and
[stdin copy semantics](https://github.com/moby/moby/blob/master/daemon/internal/stream/attach.go).
Moby applies detach escapes only to TTY input. Its non-TTY `StdinOnce` path closes
stdin while retaining output. These source observations support the fixed candidate
configuration, but do not qualify a real daemon/version or its binary transfer.

The first focused check passed 48 cases in 9.52 seconds. The broader guest/bootstrap/
package/owner/environment/local inference/composite/cost regression passed 368 cases
in 208.37 seconds. The final attach check passed 53 cases in 9.28 seconds after
adding trailing-daemon-error/media-type cases and making the temporary socket path
portable across the declared POSIX platforms. Core transport bytes were unchanged.
Separate regression/final source snapshots preserve these scopes.

Authored socket responses test headers, frames, byte caps, cancellation, progress
without deadline renewal, partial writes and error sanitization. Real owned Unix
sockets test stdin half-close, exact full input transfer, multiplexed output into
the existing capture reader, idle deadlines and backpressure after an actual write.
The temporary fixture has a short `/tmp` path for native Unix sockaddr limits.
It is an authored peer, not Docker. No real guest model runs in these tests. The
common fixture's ordinary authored development baseline remains separate work.

The native proof records the request hash, response digest, observed byte counters
and peer-observed stdin EOF. The capsule retains original committed inputs and
captured result. Cold relocated replay passes with model imports, attach, process
launches, sockets and new clocks denied. Native timers/descriptors here establish
current-host IPC behavior, not Linux/image/OS privacy or watchdog qualification.

The caller must still verify daemon/image/container identity, retain durable
ownership/intents, attach before the single start and provide the independent
watchdog/stop/cleanup chain. This module supplies no admission or stop proof. No
default executor/service or existing scorer allowlist activates it. It postdates
prepared environment v3 and the full default checkpoint; neither is relabeled as
qualification for the current 218-core-file state. Independent tasks, useful gains/
tolerances and scientific comparison remain open.

Documentation passed 19 cases in 0.87 seconds. Full Ruff, explicit line-length
and whitespace checks passed. The original native fixture captured 7,423 stdout
bytes and discarded 27 diagnostic bytes. Its peer observed stdin EOF after the
complete request. These are authored protocol bytes, not scientific measurements
or proof of a real guest's termination.
