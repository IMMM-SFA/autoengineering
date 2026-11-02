# Actual local synthetic container controls

Four approved development controls ran serially on the cached pinned local
OrbStack Linux ARM64 image. Each used 64 MiB memory, zero swap, one CPU, 16 PIDs,
no network, a read-only root and one owned read-only source stage. The container
received no Docker socket, host home, credentials or private inputs. No image
was pulled, remote host used or provider called.

| Control | Original result |
| --- | --- |
| Preflight | Exact cgroup limits, UID/GID 65534, empty capability sets, no-new-privileges, read-only root, bounded tmpfs and loopback-only interfaces observed. |
| Small allocation | 8 MiB allocated and touched successfully. |
| Fixed scoring | The hash-pinned worker returned RMSE 1.0 for its internally generated 64-value synthetic vectors. |
| Memory overrun | Allocating/touching 128 MiB under the 64 MiB limit exited 137 with original-container OOMKilled=true. |

The driver uses only the explicit local Unix-socket API. Creation is separate
from start. The original ID, nonce, image, command, mounts and resource settings
are checked before start. A separate owner-pipe watchdog is armed first. On EOF
or deadline it removes that exact owned ID, preventing a delayed start request
from reviving it. Only authoritative HTTP 404 establishes absence. Generic API
errors do not. Normal owner-pipe closure and original-ID removal were exercised
for all four controls. Every original ID was removed; no unrelated container was
changed. Actual owner death and timeout/cancellation remain untested.

Executed controllers and source hashes are preserved inside each execution
archive. The later explicit no-restart policy/created-state/restart-count checks
have unit evidence and were checked against the saved original inspect metadata.
All four had the no-restart policy and zero restarts. They are not relabelled as
executions of the later code. Current source is stored separately. The initial
40 driver/probe unit checks passed. Final driver/probe/private-scoring/documentation
checks passed 62 tests with two production-profile skips in 1.76 seconds. Ruff
passed. Fixtures do not establish actual enforcement beyond the four live controls.

This is partial development evidence, not private-scoring admission. The existing
macOS scorer remains unchanged. Full network/host-path negative controls,
timeout/cancellation/owner-loss tests and lost acknowledgement remain required.
Docker log retrieval is bounded, but an
adversarial output-limit control has not run. No complete cost or scientific
utility claim follows. ARM64 does not establish Linux x86-64 qualification or an
independent hardware result.

The immutable image, original create/start/inspect/output/cleanup evidence and
watchdog source are retained. Raw execution file hashes are in execution-files.json.
No private confirmation data was read. Task custody/admission and a frozen
independent protocol are still needed. Earlier full-suite checkpoints retain their
original source scope and were not rerun for these standalone scripts.

The offline archive reader verified all 84 raw execution files after relocation
to a fresh directory. It requires the separately retained execution manifest
SHA-256 `598831557821112e1f3fd8890b826a48df9fc2ed072e58715ff9bddd511fda98`.
Run `scripts/verify_utility_local_runtime_archive.py ARCHIVE --manifest-sha256 DIGEST`
with the project Python interpreter. The trusted companion driver must remain
beside the reader. Archived Python files are only hashed, never imported. Saved
stage paths are identity metadata and are not opened. The reader checks original
IDs, nonce/source/image bindings, resource settings, stopped results and cleanup
receipts. It does not query live container absence or establish the truth of a
daemon assertion. The 74 focused archive/driver/probe/documentation tests passed
in 1.13 seconds. This includes socket/process denial during relocated reading and
rehashed corrupt-evidence cases. No additional container started.
