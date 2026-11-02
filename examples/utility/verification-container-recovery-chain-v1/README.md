# Original creation and lifecycle recovery

Fixed-container recovery now requires the original durable creation intent,
pending ownership and acknowledged plan to agree. It verifies the exact resource
configuration and all four staged source/input hashes. Saved before-start state
must be created, stopped and unpaused with PID zero and no restart. Completed
state must be exited, stopped and unpaused with PID zero, integer exit code zero,
Boolean OOM=false and no restart. Live start/completion use the same state rules.

Recovery also validates watchdog readiness, original start/cleanup/result receipt
schemas and finite nonnegative lifecycle time when present. Missing legacy timing
stays unknown. Parsed response and result projections must agree without numeric
type coercion. Symlinked evidence directories refuse. Relocated evidence retains
its original logical mount path while all reads use the relocated directory.
Private label arrays and the daemon are unnecessary for completed-result recovery.

The initial 24-case regression recorded 23 failures and one pass. The repaired
focused output/creation/runtime/archive/scorer/recovery/execution suite passed
160 tests in 12.59 seconds. Ruff passed. The complete utility regression passed 680 tests with 26 skips in 570.86 seconds.
Its JUnit record has 706 cases, no errors and no failures. All 12,426 pinned
source/test/example/configuration files remained unchanged. Exact command,
environment, source pins and terminal result are retained separately. This is
not a rerun of the full default or Bayes suite.
Authored fixture checks do not independently attest OS or daemon behavior.

One approved bounded local synthetic confirmation used the cached ARM64 image.
It started one container and one scoring child, returned RMSE 1.0 W and removed
the original container. Suite publication was deliberately interrupted after
score creation. Recovery with all labels deleted and API/new starts denied
published that original score while retaining reservation and access history.
No real confirmation data, provider call, image pull or remote job was used.

A wheel built from an isolated source copy matched all 199 current core Python
files. Its isolated reader recovered relocated evidence with socket creation,
subprocesses and daemon calls denied. It rejected both ambiguous output with a
matching saved hash/projection and an already-running before-start record.
The 23 original synthetic execution files contain no label arrays. Their manifest
SHA-256 is f97ee5cb354deb45b1526c0e65d992e125be6dca10e09e71bebd56306dff66be.

This increment does not qualify the whole private runtime. Earlier interruption,
resource and isolation controls keep their original source scopes. Complete
current-source failure/privacy qualification, independent task custody,
thresholds, unmeasured costs and a frozen protocol remain open. Part 5 remains
incomplete and private scoring remains unqualified.
