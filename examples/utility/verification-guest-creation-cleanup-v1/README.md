# Original guest creation cleanup

This increment adds cleanup for the original charged creation before watchdog
ownership. It is an explicit candidate interface, outside default activation.
All daemon observations and container identities are authored test data.

The original suite and owner writers, grant, runtime, nonce, response and optional
container ID bind a single cleanup plan. Its fixed deadline and durable kill and
forced-removal intents survive interruption without another allowance or mutation
retry. Cancellation and resource drift do not remove cleanup authority. Conflicting
image or owner labels refuse mutation. Once cleanup begins, journal advancement,
creation reconciliation and watchdog arming are refused.

A lost CREATE response can discover the original named resource only after exact
ownership checks. Named absence without an original container ID remains
`creation_unresolved`, because an in-flight creation could finish later. Saved
outcomes replay without a daemon, suite, model, array load, new clock or writes.
Elapsed time after resumed cleanup remains unknown. The executor attempts early
cleanup on failure and preserves the original exception and charges.

## Verification

- Initial focused check: 16 passed in 19.61 seconds.
- Related cleanup/daemon/executor/watchdog regression: 99 passed in 142.37 seconds.
- Final cleanup and composite check: 40 passed in 143.26 seconds. This includes
  the later original-response pointer fix and native lost-CREATE-response case.
- `replay-cleanup.py.txt` verifies the relocated saved owner archive while denying
  model imports, processes, sockets, arrays, clocks, writes and unrelated reads.
- Final source snapshots and pins preserve the tested source. Earlier snapshots
  remain intact and identify the earlier regression scope.

The retained owner archive contains private authored lifecycle observations. It
is a test artifact, not a public scientific archive. No real daemon, container,
image, provider or independent confirmation data ran in these checks.

## Remaining requirements

Unknown creation and uncertain consumed removal require explicit resolution.
An existing watchdog plan prevents a competing cleanup authority. Interrupted
watchdog startup needs its own original-owner reconciliation path. Synchronous
filesystem operations still have no strict interruption guarantee. Actual runtime
and privacy qualification, current installed/platform/host checks, independent
task admission, approved thresholds and the frozen scientific comparison remain
open. The full default suite was not rerun for this increment. Part 5 is incomplete.
