# Original creation ownership and reconciliation

The fixed scorer runtime now persists ownership intent before its create request.
The sidecar binds the original name/nonce, runtime/source/configuration identities,
endpoint/API and input hashes. File and containing-directory writes are fsynced.
This preserves the lookup identity when creation acknowledgement is lost or
pipe setup fails before the independent watchdog can arm. This is not a tested
power-loss or storage-disaster guarantee.

Creation/pipe failures attempt bounded cleanup of the same original object. An
existing attempt directory still prevents another creation. Explicit
reconcile_creation(root) only observes; stop=True permits removal of that owned
container, including a running one. It cannot create, start or score. A discovered
original ID is saved before removal and used for later observations. No unrelated
container is selected by enumeration.

Without a known ID, name-based HTTP 404 remains absent_at_observation with creation
uncertainty. The original request might commit later. This is never no_launch,
never an allowance refund, and never authority for a new scientific attempt.
The method supplies no scientific score. Cleanup retries preserve the first raw
snapshot and append subsequent snapshots/observations. API errors and conflicting
ownership remain unverified and do not permit deletion or result reuse.

Two approved local synthetic creation controls ran on the cached pinned ARM64
image. Each made one create request and zero start requests:

| Control | Actual result |
| --- | --- |
| Lost create acknowledgement | The real daemon returned a created ID to the harness transport. Response delivery to the runtime was deliberately interrupted. The runtime resolved its original name/nonce, removed that exact stopped ID and confirmed HTTP 404. |
| Pipe setup failure | The created ID was acknowledged. Owner-pipe setup then raised the injected error. Cleanup removed that original stopped ID before any watchdog or scoring launch. |

Both original inspections showed status created, Running=false and Pid=0.
Start requests were blocked by the harness. Each original ID was removed once.
Repeated reconciliation and an attempted repeat run caused no new create or
start. These are injected controller faults, not a real daemon transport outage.
Late creation after an absent lookup is covered by an authored fixture, not an
actual delayed daemon commit.

A distinct synthetic success/recovery control then used the same runtime source.
It returned RMSE 1.0, removed its original container, deleted all synthetic label
copies and recovered the public receipt with further API/starts denied. Across
these controls, three container objects were created and one container/scoring
child started. No real confirmation data, provider call, image pull or remote job
was used. The original execution files, source hashes and harness text are retained.

The initial five tests failed because ownership intent was absent before create.
Their red log is preserved. The final combined runtime/scorer/execution/recovery/
cost/report/analysis/docs suite passed 139 tests in 21.84 seconds. After removing
an unused test import reported by Ruff, all seven creation tests passed again in
0.06 seconds and Ruff passed. Tests also cover foreign ownership, unknown lookup,
failed-delete retry and metadata-only reconciliation. They qualify no real data.

The wheel matched all 199 core Python files. New and legacy public receipts replayed
after relocation with private/original-root opens, scorer methods, sockets,
processes and optional scientific imports forbidden. Legacy unknown quantities
were preserved. This installed check is public replay, not daemon reconciliation.

The source remains an unqualified candidate. Full new-source lifecycle/failure
qualification, independent task custody, thresholds, unmeasured costs and a frozen
authorized protocol remain outstanding. Earlier full and utility regressions
retain their original source scopes. No scientific utility or independent
hardware claim follows from these local synthetic controls.
