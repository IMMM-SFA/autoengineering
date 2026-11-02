# Coupled-container owner-pipe controls

The candidate owner now arms an independent pipe watchdog after verifying the
acknowledged container and before START. The watchdog has no create, start or
packet operation. It checks exact image, configuration, labels and CID before
cleanup. Owner EOF or the active deadline triggers bounded cleanup. Parent and
watchdog serialize mutations with a separate cleanup lock. Normal completion
requires the watchdog's own absence observation before the owner returns.

Two actual controls killed the exact owner PID with SIGKILL after watchdog
readiness. One container was unstarted. The other was observed running before
input submission. In both cases, the watchdog reported owner EOF, removed the
original container and exited. The producer separately confirmed exact-CID
absence and absence of the recorded watchdog PID. No packet or private source
was submitted. No model result was observed, and unknown work remains separate
from the known lower bound.

The focused suite passed 74 tests. It covers the owner, source callback, typed
cost records, watchdog EOF/deadline behavior, ownership changes and documentation.
The malformed creation-acknowledgment path also preserves named cleanup before
any START. Full lint passed. The full default suite was not rerun. No image build,
installation or new scientific confirmation was needed for these controls.

The public receipts bind the original plans, ready/outcome records, owner kill
intent and watchdog process observations. A standalone stdlib reader verifies
those joins outside the checkout. This is producer evidence, not independent OS
attestation or a complete interruption matrix.

The [v17 register](../guest-qualification-accounting-v17.json) now has 54 container
creations and 42 starts. Its known model-start lower bound remains 81, including
72 coupled evaluations. Earlier unknown work remains unknown.

Pre-acknowledgment creation loss, loss during actual model computation, watchdog
loss and the complete resource matrix remain unverified for this owner. The
earlier generated-source confirmation used the preceding owner implementation.
These controls do not transfer qualification to that older implementation or
establish a new scientific result. Runtime and private boundary admission remain
false, and the independent utility study remains open.
