# Shared baseline scenario and charge guards

A shared deterministic baseline now requires the same task and scenario identity.
The existing frozen model/selected-state checks remain. Confirmation analysis
refuses to fill an aliased cell that already has any confirmation reservation,
started attempt or committed result. A shared receipt cannot hide an original
charge, unresolved work or a separately executed result.

Before this fix, different scenarios were accepted as one reference, and cells
with reserved or started confirmation attempts could receive an alias score.
Separately scored cells were already rejected later as duplicate assigned cells.
The first test run recorded four failures and one pass, including an overly
specific error-message expectation for that already-rejected case. After removing
that diagnostic assumption, the behavior regression recorded three failures and
two passes. Both raw checkpoints are preserved.

The repaired baseline/analysis/report/confirmation/recovery/CLI/cost suite passed
89 tests in 16.35 seconds. It verifies valid never-attempted reuse still yields two
logical cells from one committed public receipt. Reserved, started and scored
targets reject, without changing the journal or refunding charges. Ruff passed.
No new suite schema or receipt serialization was introduced.

A wheel built from an isolated local source copy matched all 200 core Python
files. Its isolated reader reconstructed relocated authored public evidence with
original fixture roots, sockets and child processes denied. Valid reuse retained
two logical cells and one physical score receipt. A reserved target and changed
scenario identity were refused. No new callback, model, provider or private-data
access occurred during reconstruction. Fixtures and their callback results are
authored evidence, not independent scientific confirmation or process counts.

The runtime and both fixed worker payloads remain unchanged. Earlier broader
regression and lifecycle evidence keep their recorded scopes. This increment did
not rerun full default, Bayes or complete utility suites. It fixes reader safety;
execution-time shared-baseline scheduling is still unfinished. Complete private
profile admission, independent data custody, thresholds, the full frozen protocol,
platform/host qualification and independent reports remain open. Part 5 remains
incomplete.
