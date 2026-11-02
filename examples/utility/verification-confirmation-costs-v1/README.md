# Confirmation callback cost verification

Public confirmation receipts now optionally carry a versioned callback measurement
bound to their grant, scorer and exact public score. The service measures elapsed
time around the trusted callback. This includes nested private I/O/workers, but
excludes registration, grant validation and reservation overhead. It is observed
callback duration, not CPU time, a timeout guarantee or complete confirmation cost.
Do not add it to overlapping worker durations.

The offline accounting join now covers every confirmation allocation. It exports
reservations, committed access intents/scores and measured callback completions/time.
It never infers worker/model starts from a public score. Missing, interrupted and
legacy timing remains unknown. Legacy four-field receipt bytes retain their shape.
A pending confirmation allocation is reconciliation_required rather than falsely
not_attempted. Complete cost remains false while full solver/training/preparation,
resource, provider and human-effort evidence is missing.

The full utility/documentation group passed 397 tests with 26 optional/platform
skips in 503.38 seconds. Source hashes remained fixed. Ruff and whitespace checks
passed. Tests cover measured/legacy receipts, wrong grant/score/scorer, invalid
clock values, infeasible scientific scores, pending reservations, orphan uncommitted
score artifacts, no rescore on completed replay, tampering and CSV allocation.
Initial tests had one fixture writer-lock failure; the next had one CSV test using
fraction instead of the actual allocation column. The corrected tests preserve
both production contracts. Failed logs remain.

synthetic-public-example is an authored public callback fixture. One scalar score
is recorded, its measured callback cost is exported, and completed resume adds no
callback. It contains no private or independent observations, native scientific
model process or provider result. Its incomplete pair is inconclusive. It is not
the frozen four-family experiment or evidence of scientific/cost gain.

A fresh wheel matched all 192 core Python files and was extracted into a fresh
venv with cached base dependencies. A copied public fixture rebuilt all ten export
files byte for byte, including six confirmation cost rows. A startup audit hook
denied original checkout access, sockets and subprocesses, with explicit denial
controls. The scorer entry was replaced with a failure guard. Optional PyWake,
TOPFARM, OpenMDAO, Anthropic, Torch and BoTorch packages were absent. Runtime
stdlib/dependency paths under the existing Pixi environment were allowed. This is
wheel-extracted installed-reader evidence, not a fresh solve or installed execution.
The first checker mistook verify_export's file count for a file map. Its failure
is retained. The corrected checker used the manifest and a new output directory.
SDK source did not change. Build logs, wheel, guards and reader code are preserved.

No actual provider, independent/private confirmation or new scientific matrix was
accessed. Private scorer memory qualification, actual host/platform qualification,
four admitted tasks, full costs/effort and the remaining Part 5 requirements stay
open. Earlier results keep their original source identities.
