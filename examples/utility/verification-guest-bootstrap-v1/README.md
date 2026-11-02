# Candidate stdio guest bootstrap

The fixed bootstrap receives one bounded canonical request on stdin, verifies the
frozen package before writing input files, checks the actual interpreter/wheel,
invokes the existing fixed worker once and returns only its declared bounded result
artifacts on stdout. Results leave before the process exits and its tmpfs disappears.
No transferred Python source executes. The new policy fixes the bootstrap command
and one-shot stdin, retaining all resource, network, mount, privilege and logging
limits. The original direct-worker policy keeps its fields and behavior.

The transport design follows the current Moby filesystem implementation: archive
operations create a separate tmpfs view, so they cannot stage inputs into the
worker's tmpfs. Docker also removes tmpfs contents when a container stops. Sources:
[Moby filesystem view](https://github.com/moby/moby/blob/master/daemon/containerfs_linux.go),
[Docker tmpfs lifecycle](https://docs.docker.com/engine/storage/tmpfs/).
These source observations are a design constraint, not an actual-daemon test.

Headers, archive bytes, results and artifact sizes have fixed caps. Short reads
and writes preserve framing. Foreign identities, bad/truncated/trailing frames,
noncanonical worker bytes and output paths outside the fixed artifacts refuse.
A completed capture is published last. Saved verification needs no original
stream, source/driver directories, model, runtime probe, array load or new clock.
Missing or contradictory evidence cannot authorize a new worker attempt.

The first focused run had 10 failures and 15 passes. Authored completed results
incorrectly omitted the worker duration required by the existing contract. The
negative host test also called the Linux-only identity constructor without handling
its expected refusal on macOS. The fixture was corrected without relaxing the
contract; unsupported bootstrap interpreters now get a clear refusal before
extraction. The corrected check passed 25 cases in 17.34 seconds.

The related guest/package/owner/environment/local inference/composite/cost regression
passed 316 tests in 178.83 seconds. The final bootstrap check, including a fresh cold
process, passed 30 cases in 25.92 seconds. Positive bootstrap orchestration uses an
authored worker stub and authored interpreter-validation hooks, never a real model
under a simulated qualification claim. The real host mismatch test refuses before
writing a file or invoking the worker. The common fixture's ordinary development
baseline is separate from guest execution. A synthetic stdio capture reaches the
existing archive reader with authored lifecycle observations and boundary unchanged.

The public capsule preserves the committed owner/input package and captured stub
result. Its request is deterministically reconstructed from those original bytes.
Its response digest is the one recorded by the original capture. Relocated and
extracted-wheel cold replay passed with model imports, processes, sockets and new
clocks denied. A fresh-process test additionally denies arrays and unrelated or
writable file reads. None of these checks independently attests OS enforcement.

The offline wheel build uses 348 copied inputs and contains 217 core Python files
with exact source parity. The first administrative build script failed before
building because its script search path omitted the repository namespace. Both
script versions and the failed log remain. The corrected script explicitly adds
the requested source root and uses the installed build backend, with no dependency
installation. Successor environment v3 pins 307 wheel Python sources and the same
49 archive identities/265,399,717 compressed bytes. Both prior packages still verify.
No archive acquisition, dependency installation, image build or container occurred.

Actual Unix-socket attach/start, Docker stream multiplexing, absolute deadlines,
owner-loss watchdog, early-abort/cleanup and image/OS/resource/privacy qualification
remain open. Native stdout/stderr behavior and backpressure need actual-runtime
checks. No default executor/service or existing scorer allowlist activates stdio.
Independent partitions, useful gains/tolerances and scientific comparison remain
open. The full default checkpoint predates these changes.
