# Explicit confirmation recovery publication

ConfirmationService now provides `recover(grant)` for an original pending
confirmation. It requires the original charged reservation, committed access
intent, frozen selection, unchanged grant and registered scorer recovery method.
It never calls the scoring callback. The scorer's trusted `recover(grant, model)`
must verify the original completed result without restarting work or opening
labels. Missing evidence leaves the original access history and charges intact.

New recovered receipts contain utility-confirmation-recovery-v1 provenance for
the original attempt, grant, access intent, scorer and exact public score. Recovery
does not time a new callback or invent the original duration. Legacy and ordinary
receipt serialization is unchanged. A committed receipt, including one whose
acknowledgement was interrupted, replays directly without calling either scorer
method. Cancellation remains recorded while an existing result can be settled.
Scientific failures retain their original statuses and have no penalty objective.

One approved synthetic container confirmation ran with an injected interruption
after original score creation and before suite publication. The fixed worker
returned RMSE 1.0. The original container was removed and its exact ID returned
HTTP 404. All three synthetic label copies were then deleted. With daemon
requests and new runtime starts forbidden, explicit recovery published the original
result against the same reservation and access intent. Repeated recover/confirm
calls reused the committed receipt. No real confirmation data, provider call,
image pull or remote job was used. This is local ARM64 software evidence, not
private runtime admission or independent scientific confirmation.

The public cost reader records one recovery publication. Original callback time,
callback completion count and physical scoring starts remain unknown. The
reservation, access, score and recovery counters are distinct bookkeeping events,
not additive physical executions. Complete cost evidence remains false.

The source used for execution, harness text, original journal, both public receipt
artifacts, container evidence and cleanup receipt are retained. The earlier orphan
receipt is not rewritten or selected by directory scanning. The committed journal
references the recovery receipt. Raw execution files are hashed in
execution-files.json. A manifest requires a separately trusted digest and cannot
independently establish daemon assertions or current live absence.

The focused recovery/scoring/cost/container/report/analysis suite passed 91 tests
in 17.35 seconds. It covers publication crashes before and after commit, changed
grants, missing reservations/access/results/recovery methods, stale provenance,
private-exception sanitization, cancellation and original failure statuses.
Documentation checks passed 19 tests in 0.61 seconds. Ruff passed. A broader
utility regression has its own log, XML and source pins. Its result must be read
from completed evidence, not inferred from these focused checks.

The offline wheel matched all 198 core Python files. Its relocated public-journal
replay used no private or original root, socket, scorer callback or process start.
Both receipt artifacts remained present. The journal head did not change, and the
report retained unknown costs and complete-cost-evidence=false. These installed
checks do not qualify the candidate runtime's full failure matrix.

Remaining work includes complete failure-matrix qualification of the candidate
runtime, container-specific public execution/cost receipts, independent task
custody, useful-gain thresholds and a frozen authorized protocol. Part 5 remains
active and incomplete. Earlier broad base/Bayes checkpoints retain their original
source scope and are not fresh checks of this change.

The complete utility regression finished with exit 0: 567 passed and 26 skipped
in 573.25 seconds. The original handle was 16460. JUnit records 593 cases with
zero failures/errors. All 395 pinned source/test/config files stayed unchanged.
The final log, XML and hashes are recorded in regression-terminal.json. This
closes that running check. It is not a new full default/Bayes run or benchmark.
The earlier inflight checkpoint is retained as history.
