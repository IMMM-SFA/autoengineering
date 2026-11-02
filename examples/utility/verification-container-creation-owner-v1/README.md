# Creator termination around container ownership

Six approved local synthetic controls exercised the unchanged fixed-container
runtime source. No container or scoring worker started. All six original created
objects were removed, and live API checks returned HTTP 404 for each exact ID.
No image pull, real confirmation data, provider call or remote job was used.

| Boundary | Creator exits | Cleanup evidence |
| --- | --- | --- |
| Create response received by harness transport, before delivery to runtime | SIGTERM (-15), SIGKILL (-9) | No acknowledged plan or watchdog existed. A fresh runtime resolved the persisted original name/nonce and removed its ID using metadata only. |
| Acknowledged plan saved, before owner-pipe creation | SIGTERM (-15), SIGKILL (-9) | No watchdog existed. A fresh runtime used the original acknowledged ID and removed it using metadata only. |
| Watchdog armed, before start request delivery | SIGTERM (-15), SIGKILL (-9) | The independent watchdog recorded owner_pipe_eof and removed the original object. The observer issued no deletion request. |

The creator killed only itself. Its parent observed the actual negative exit code
through the owned Popen handle. SIGKILL could not execute Python exception or
finally cleanup. In the four pre-arm cases, all job/label copies were deleted
before reconciliation and the observer rejected job/label reads and every POST.
Repeated reconciliation performed no replacement creation, start or extra delete.
In the two post-arm cases, the harness recorded a start attempt and terminated its
caller before forwarding that request. Cleanup inspections retained status created
and Pid=0. This is no evidence about termination during running computation.

Original creator requests, termination intent, transport-created ID, pending/known
ownership, source stage, stop/removal observations and controller results are
retained. The original and extended harness source texts are separate artifacts.
The runtime source did not change between these controls or from the preceding
creation increment. The existing wheel was reused: all 199 core Python files
still matched its contents. No new package build or installation was performed.

The offline verifier checked all 120 archived files after relocation. Its required
separately retained execution-manifest SHA-256 is:

```text
a46ef478ed68ef724955e1230a6972c853b0f30310d28af0260c88eefcb1ede4
```

Run the project Python interpreter with
`scripts/verify_utility_creation_owner_archive.py ARCHIVE --manifest-sha256 DIGEST`.
Keep its trusted companion archive-reader scripts available. It checks manifest
hashes, original runtime/configuration identities, IDs/nonces, owner exits,
creation/start boundaries, resource policy and cleanup receipts. It hashes archived
code as data and does not execute it, query Docker, read original paths or open
job/label arrays. This is consistency checking of saved trusted-producer evidence,
not independent OS/daemon attestation or proof of current live absence.

The owner-archive/creation/runtime/archive suite passed 71 tests in 0.85 seconds.
Tests forbid sockets/process starts and daemon requests during relocated reading.
Rehashed changes to exits, creator PID, runtime/ID/nonce, stop state and cleanup
reason were refused. Ruff passed. These checks do not replace full runtime
qualification, and prior broader suites retain their original source scopes.

Remaining runtime work includes active-workload interruption, lost start/result
acknowledgements and complete resource/privacy/failure-matrix closure for the
current candidate source. Independent task custody, thresholds, unmeasured costs
and a frozen authorized protocol also remain open. This local macOS-owner/Linux
ARM64-object evidence does not qualify Linux x86-64, independent hardware,
scientific utility or real private confirmation. Part 5 remains incomplete.

The final metadata-only guard also rejects job/label archive members before
opening them. The updated focused suite passed 72 tests in 0.88 seconds, and
Ruff passed. The earlier 71-test checkpoint is retained separately.
