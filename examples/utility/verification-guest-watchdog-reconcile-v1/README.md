# Original watchdog startup cleanup reconciliation

This increment adds an explicit original-owner cleanup path for interrupted
watchdog startup. It does not create a watchdog, reattach stdin, dispatch START,
run a model, renew scientific time or refund any charged attempt.

The original watchdog and the reconciliation path hold the same exclusive,
nonblocking advisory cleanup lease. A live child refuses parent takeover. A
parent holding the original suite/owner writers may resolve an unstarted journal
after the child is absent or delayed. Original suite, charged access, runtime,
plan and container identity remain mandatory. Cancellation does not revoke owned
cleanup authority.

The first cleanup fixes its reason, start time and deadline in a create-only
window bounded by both ten seconds and the original plan's cleanup cap. Mutation
intents are persisted before RPC. Interrupted cleanup keeps the same window,
reason and consumed operations. A legacy interrupted cleanup without a saved
window refuses a new allowance. An expired window publishes uncertainty without
contacting the runtime. Saved outcomes bind the window digest. Legacy completed
outcome bytes without that optional field remain readable.

A delayed original child must use existing cleanup evidence before publishing
readiness. Once cleanup is intended, a new start intent is refused. The facade
attempts original startup cleanup on an early failure while preserving its
original error. The explicit facade operation is `cleanup_watchdog_startup`.

All positive daemon/container observations in this increment are authored test
data. Actual runtime/privacy qualification, strict synchronous filesystem timing,
installed/platform/host qualification and the independent scientific comparison
remain open. The preceding wheel snapshot predates these source changes.
Verification results are recorded in the retained logs and final summary.


## Verification results

The initial focused check passed 30 cases (52.69 seconds). After correcting the
delayed-child readiness race, the related lifecycle check passed 105 cases (344.82
seconds). The copied-control-scope regression then reproduced a fresh-scope bug.
After that correction, all 34 final startup/composite cases passed (146.76 seconds).
The final scope includes actual owned fixture-child termination and an injected
Popen failure. New and legacy guarded cold readers pass. Prior failures and source
snapshots are retained. `summary.json` records the exact JUnit scope and limits.
