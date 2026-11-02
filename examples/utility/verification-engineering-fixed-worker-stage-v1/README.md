# Fixed Linux engineering worker

The new image contains the fixed coupled-load worker, scoring kernel, exact model
source bytes and a fixed stdin entrypoint. One offline source overlay build used
the existing dependency image. It performed no installation, download or model
evaluation. The frozen v6 routing image and project wheel remain unchanged.

The entrypoint checks its source catalogue and effective resource settings before
reading one bounded packet. The immutable container command supplies the expected
packet hash. Packet fields cannot choose code or paths. The worker clears the
child environment and supplies only fixed single-thread numerical settings.
Its child stdout/stderr share a hard 16 KiB file limit. The main entrypoint has a
45-second alarm. That alarm has not yet been tested as a lifecycle qualification.

The actual Linux amd64 container under local ARM64 emulation completed 24 exposed
authored cases. The power score was 0.27174569156641054 W, matching the saved macOS
reference in this observation. Reported work was 360 solver iterations, 5,880
component calls and 1,800 component linearizations. The public response contained
no case identifiers or forcing arrays. Exact-container cleanup succeeded with
one DELETE and a subsequent absence check.

An initial controller invocation failed on a missing verifier binding before any
execution intent, daemon call, container creation or model start. Its script and
failure record remain. The corrected controller executed the original one-start
request. No uncertain model attempt was repeated. The earlier dependency-image
control's separate cleanup parse failure remains in its original evidence.

Base worker, entrypoint, kernel and documentation tests passed 80 cases with one
expected optional skip. Full lint passed. The full default suite was not rerun.
The proof includes 67 copied receipt/source files and a standalone stdlib reader.
The caller-held manifest SHA-256 is
`8c7fee110544cd333c4073f76bdb160be59fbb490b3fa11605d128357f4cf766`.
The reader verifies saved image/source/request/output/cleanup bytes and the score
comparison without importing models or contacting the daemon. This is replay of
producer evidence, not independent OS attestation.

The updated [runtime register](../guest-qualification-accounting-v15.json) records
51 container creations, 40 starts and a known forward-model-start lower bound of
57. The 48 coupled-model evaluations are a subset of that lower bound, nested in
two public control containers. Older unknown work remains unknown. Earlier
macOS authored unit cases remain outside this register's scope.

No sealed source was opened. Source authorization, installed runtime/cost receipt
integration, owner-loss recovery and the worker's resource-overrun matrix remain
open. Private boundary admission and the independent utility study remain false.
