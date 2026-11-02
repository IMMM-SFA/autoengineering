# Local image preparation request and client supervision

The new source-checkout helper prepares a pinned local job and executes it only
with separate authority. The [actual request](../prepared-guest-build-v1/README.md)
is ready for review. The actual work directory remains absent and no daemon call,
image acquisition, installation or build has occurred in this increment.

103 related tests passed in 5.43 seconds. They cover no retry after every failed
phase, source drift before dispatch, remote/wrong-endpoint refusal, base/final
image identity, fixed command/environment checks, saved completion replay and
ambient secret/context exclusion. Docker metadata and builds are authored stubs.
The actual Popen supervisor is checked with owned Python fixtures for successful
exit, timeout and output overflow. No downloaded binary is executed.

Saved completion validation checks the original request, bindings, source, command
intents, log hashes and image metadata without a current source/binary/endpoint
probe or clock. It validates required proofs, not all incidental client cache files.
The helper reports a candidate image only. It cannot qualify daemon cancellation,
storage quotas, CPU/memory enforcement or runtime/privacy isolation.

Read-only local CLI help confirmed supported flags. Filesystem metadata identified
the installed CLI and existing Unix socket without connecting to that socket.
Official Docker documentation describes the per-step resource capability limits.
Machine-specific bindings are private and ignored. Context/archive payloads remain
local. This helper is outside the preceding 315-source runtime wheel scope.

The full default suite was not rerun. Actual image preparation still needs separate
authority. Runtime/platform/host and independent scientific confirmation remain
open. Part 5 is incomplete.
