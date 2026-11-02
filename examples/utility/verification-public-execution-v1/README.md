# Public confirmation execution evidence

Public confirmation receipts can now include
utility-confirmation-container-execution-v1 metadata from a registered trusted
scorer. It binds the original grant, scorer, score, runtime, container/nonce,
pinned image, source hashes and start/stop/cleanup receipt hashes. It exports no
private paths, label hashes or arrays. The producer verifies private original
execution evidence; the public reader verifies bindings and serialized integrity.
The public receipt is not an independent daemon attestation or runtime admission.

The fixed runtime records host monotonic duration from immediately before the
start request through stopped-container inspection. This includes API/polling
overhead and excludes preflight, staging, creation, output collection and cleanup.
It overlaps callback duration and is not CPU time or complete phase cost. The
metadata hook runs after the timed scoring callback. That export work is not part
of the callback measurement. Runtime and scorer configuration drift now refuses
before further private use rather than retaining a stale identity.

One approved bounded synthetic confirmation ran on the cached pinned local
OrbStack Linux ARM64 image. The fixed worker returned RMSE 1.0 and its container
was removed, with HTTP 404 confirming absence of the original ID. Publication was
interrupted after normal receipt creation. All three synthetic label copies were
deleted. With daemon requests and new runtime starts forbidden, explicit recovery
published the original result and the same saved execution metadata. The original
reservation and access intent were unchanged. No real confirmation data, provider
call, image pull or remote job was used.

Its public report records one container start, one scoring-child process start
and lifecycle duration 0.18108187522739172 seconds. The original callback duration
and completion count remain unknown after recovery. The two start scopes are not
two scientific evaluations. Counts and nested durations must not be added to
reservation/bookkeeping quantities or overlapping callback time. Complete cost
evidence remains false.

The original execution, source used, harness text and public normal/recovery
receipts are retained. Raw files are hashed in execution-files.json. A manifest
needs a separately trusted digest. Offline hashes do not establish current live
absence or independently prove daemon assertions. The runtime still has no
complete failure-matrix qualification or CLI/registry activation for private use.

The final focused execution/runtime/scorer/recovery/cost/report/analysis/docs
suite passed 126 tests in 21.73 seconds. It covers invalid counts/durations,
foreign grants/scores/scorers, sanitized export failures, unknown timing and
changed runtime/scorer registrations. Ruff passed. Earlier 62-test and 43-test
checks exercised incremental subsets; these counts are not independent evidence.

An offline wheel matched all 199 core Python files. From relocated new and legacy
archives, its public journal and cost reader ran with private/original-root opens,
scorer methods, sockets, process/fork starts and optional scientific runtime imports
forbidden. New records retained known execution quantities. Legacy records kept
their original digest/shape and unknown starts, with no retroactive metadata.
Journal heads stayed unchanged. No archived code was executed by those readers.

The prior complete utility regression (567 passed, 26 skipped) covers its earlier
source checkpoint. This increment has the focused evidence above, not a fresh
complete utility/default/Bayes run. Remaining work includes full candidate-runtime
failure-matrix qualification, independent task custody, useful-gain thresholds,
unmeasured cost categories and a frozen authorized protocol. Part 5 remains active
and incomplete. No scientific utility, efficiency or independent hardware claim
follows from this local synthetic control.
