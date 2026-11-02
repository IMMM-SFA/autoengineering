# Production preflight refusal controls

All six controls produced their exact expected refusal: changed source, model,
fit seed, daily axis, partition and cancellation before access. Each used a fresh
copy of the existing frozen authored fixture and the resource-checked derivative
profile. The original fit and seed were retained except for the explicit negative
seed test. No new fitting, scoring or independent-data access occurred.

During each production `GuestRoutingExecutor.execute` call, audit guards denied
NPZ/driver opens, socket creation and process launches. The API request method
was replaced by a guard that counts and rejects every request. All four counters
remained zero for every case. No transport success response was fabricated.
Expected exceptions and messages were saved before execution. An unexpected
refusal, success or forbidden operation would fail the control.

The request digest is
`6c215b4742a993bcae69790ab9ac23699145eadb18e3fdadcc5f2b1c26d73b2b`.
The completion digest is
`cb7654ca24899ef29172f7c9268690ea8e017d01361869bc276fa808a2eee1a2`.
`runner.py.txt` preserves the producer. Each case directory contains its prepared
fixture request, control intent and observed result. `proof-manifest.json` hashes
those records. Original working suites remain in the ignored output directory.
The parent composite reservations remain charged and unfinished. They are not
physical starts or private-label accesses.

These separately prepared controls establish refusal before driver/API/process
access. They do not establish actual daemon or kernel refusal, owner-loss
cleanup, running cancellation or private admission. The original 26-case proposal
and earlier consumed attempts remain unchanged.
