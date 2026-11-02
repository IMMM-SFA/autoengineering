# Candidate single-start guest dispatch

The new controller binds original watchdog readiness and completed HTTP attach
into the original start intent. START is sent once. Its returned status, bounded
body size and body digest are recorded before interpretation. Only an empty HTTP
204 permits one frozen stdin transfer. Output is fully captured before observing
stop and requesting watchdog cleanup. A surviving owner retains measured elapsed
time. Interrupted recovery preserves missing original time as unknown.

Reconciliation reads only original watchdog observations and can append only the
lifecycle events they support. Missing start intent or stop evidence stays
incomplete. It issues no CREATE, START, attach, input or model request. The cold
completion reader verifies original pins, capture, journal and cleanup after
relocation. Cancellation after stop observation prevents a complete transport
verdict without relabeling the stop event. Legacy owner event bytes omit the new
optional dispatch reference.

The first focused run had two failures and two passes. Repeated full suite replay
on every I/O chunk exhausted the authored deadline. Cancellation now polls the
external callback each time and replays the suite when its event files change.
The next run exposed a separate incorrect stderr length in the authored peer.
After correcting the frame, four focused cases passed in 35.77 seconds. The first
26-case interruption matrix passed in 200.15 seconds. The measured-duration,
late-cancellation and actual owner SIGKILL checks passed three cases in 26.70 seconds.
An edit precondition failure was caught before another run began. Its interrupted
zero-test log is retained and contributes no passing evidence.

The broader run passed 370 cases and failed one in 346.02 seconds. That failure
exposed a watchdog race: pipe EOF at the execution deadline was classified as
owner loss. The deterministic reproducer failed for that exact classification.
The fix gives an expired original deadline precedence after reading the pipe.
All 46 final dispatch/watchdog cases passed in 229.39 seconds. The log and XML
record verification of the successor sources. Documentation passed 19 cases. Initial, pre-fix and final source pins/snapshots distinguish these scopes.
The earlier 221-file core pins belong to the broad run before that final fix.

All positive daemon state and guest results are authored. Owned native Unix peers
exercise the actual HTTP upgrade, binary input/half-close, multiplexed stdout and
stderr, single START, lost response, truncation, cancellation, idle deadline and
20 interruption points. An actual owner subprocess is killed with SIGKILL after
sending input. The detached watchdog survives, observes EOF, records the peer's
stop/absence and terminates. No actual Docker, container, image or guest model runs.
The metadata fixture includes ordinary authored development execution.

The retained owner archives are original authored records from the broad run.
Run the guarded readers with:

```sh
.pixi/envs/default/bin/python \
  examples/utility/verification-guest-dispatch-v1/replay-dispatch.py.txt
.pixi/envs/default/bin/python \
  examples/utility/verification-guest-dispatch-v1/replay-dispatch.py.txt owner-loss
```

During verification, guards deny model imports, process/socket creation, array
loading, new clocks, writes and reads outside the relocated archive. The first
reader attempt verified the record but kept the read guard active during temporary
directory teardown. Its nonzero log is retained. The corrected harness ends the
guard after verification, before teardown. Prior original creation and watchdog
archives also replay unchanged.

These are unqualified candidate process/protocol records. They do not establish
container isolation, scientific utility, installed-package, platform or host
admission. No default executor, confirmation service or scorer allowlist changes.
Actual runtime/image/resource/privacy qualification, inference archive/service
integration, initialization recovery, independent task partitions and thresholds,
and the scientific matrix remain open.
