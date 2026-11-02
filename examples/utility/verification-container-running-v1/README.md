# Running-container interruption controls

Five approved local synthetic controls started one original container each. The
harness observed a running PID, paused that exact container and verified its paused
state before injecting the fault. All five original containers were removed by
the independent watchdog. The observer confirmed HTTP 404 for each original ID
and issued no deletion requests. No replacement attempt or scientific result was
accepted. Scoring-child starts remain unknown because a running container PID does
not establish that its scoring child started.

| Control | Creator outcome | Automatic cleanup |
| --- | --- | --- |
| Cancellation | Actual SIGTERM exit -15 | owner_pipe_eof |
| Owner loss | Actual SIGKILL exit -9 | owner_pipe_eof |
| Lost start acknowledgement after real HTTP 204 | TimeoutError preserved | owner_pipe_eof |
| Start response delivery held with owner lease open | Refused after original object removal | Independent watchdog deadline |
| Normal start response delivery, paused workload | Refused through runtime eight-second poll timeout | owner_pipe_eof |

The last control has a separate archive under `execution-timeout/`. The first four
archives and their original manifest remain unchanged. This pause-induced hang
checks cleanup of a running original object. It does not establish which phase
of model computation was interrupted. Source, original IDs/nonces, transport
requests, running/paused inspections and cleanup receipts are retained. Authored
job/label copies were deleted before archiving. No real confirmation data, image
pull, provider call or remote job was used.

Run `scripts/verify_utility_running_archive.py ARCHIVE --manifest-sha256 DIGEST`
with the project interpreter and its trusted companion scripts available. Add
`--execution-timeout-only` for the nested timeout archive. Required separately
retained manifest hashes are:

| Archive | Files | SHA-256 |
| --- | --- | --- |
| Four interruption controls | 90 | `2dc0acfa21ca8535436ac5875dc594380943c8b8f22d50ea9703d828e8d6703a` |
| execution-timeout | 23 | `dbca0ddd48c6925c7ca1a0c186b858650c15f2c59cc776a52589e37dc591e8e0` |

The passive reader verifies hashes, original configuration and source identity,
start/pause requests, ownership, exit codes, automatic cleanup and absence of an
accepted result. It rejects job/label archive members before opening them. Tests
relocate both archives and forbid sockets, subprocesses and daemon API calls.
Rehashed false exit, ownership, pause, cleanup, retry and result claims are refused.
This checks saved trusted-producer evidence, not independent attestation or live
absence at replay time.

The focused archive/creation/runtime suite passed 49 tests in 0.56 seconds. Ruff
passed. All 199 core Python files still match the existing wheel, which was reused.
The runtime and worker sources did not change. Prior broader test checkpoints
retain their earlier source scopes.

Full candidate-runtime resource, privacy, malformed-output and result-commit
failure qualification remains open. These macOS-owner/Linux ARM64 container
controls do not qualify Linux x86-64 or independent hardware. Independent task
custody, thresholds, unmeasured costs and a frozen authorized protocol are still
missing. Part 5 remains incomplete and private scoring remains unqualified.
