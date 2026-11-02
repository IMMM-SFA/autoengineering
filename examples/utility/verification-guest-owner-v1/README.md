# Candidate guest owner journal

The journal binds one owner directory to the original suite inference claim. Its
create-only owner lease precedes manifest publication. The journal records the
ordered create intent, original creation, start intent, original started/stopped
observations, cleanup intent and original cleanup. Reopening cannot consume a
transition twice. Missing observations retain uncertainty. The original suite
claim stays charged; this journal does not refund scientific reservations.

Records use the existing owner-private directories, writer lock, durable immutable
writes, confined artifact reads and content hashes. Saved observations must pass
the shared fixed OCI checks. Interrupted initialization leaves its owner lease in
place and requires explicit reconciliation. Relocated copies permit replay only.
Completed evidence projects into the existing guest archive format without a new
clock sample. Unknown original elapsed time remains null.

This is an evidence journal, not a launcher or staging implementation. The future
owner must hold its writer lock from intent through the single external dispatch.
This module neither issues daemon calls nor makes a reusable dispatch token.
Actual dispatch, input transfer, watchdog/early-abort cleanup, owner lease recovery,
image assembly and OS/resource/privacy qualification remain open. No default
executor, confirmation service or existing scorer allowlist activates the path.

The first focused command ran the owner and observation modules with owned local
process supervision and passed 110 cases in 25.14 seconds. The shared fixture runs
an ordinary authored development baseline. All OCI captures are authored; no guest
or independent data executes. Failure injection covers both sides of all seven
journal commits and loss after owner-lease publication. Additional checks cover
writer contention, cross-directory owner reuse, out-of-order/repeated transitions,
corruption, foreign observations, mutable caller data and size limits.

The later related regression adds the existing guest archive reader, guest job,
local inference, composite and confirmation-cost suites. It includes a positive
journal-to-archive handoff and a fresh cold process. Cold replay denies model
imports, array interpretation, process launches, sockets, clock sampling and
unrelated or writable file access. Exact terminal results are in summary.json.

This increment postdates the last full default checkpoint. It cannot establish
real container identity, scientific utility or independent-task admission.

Terminal results: 221 related tests passed in 145.63 seconds, 19 documentation
cases passed in 0.65 seconds, and the relocated authored archive replay passed.
Full Ruff, explicit 100-column checks on changed Python files and whitespace
checks passed. Source pins identify the later 221-case run, including the two
additional handoff/cold-process cases. The initial 110-case run predates those two
tests. Core runtime source was unchanged between successful runs.
