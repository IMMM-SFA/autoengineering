# Fixed scorer output enforcement

Three approved synthetic controls ran serially on the cached pinned OrbStack
Linux ARM64 image. Each original container exited 0 and was removed. The host
controller confirmed HTTP 404 for each exact original ID. No private confirmation
data, image pull, provider call or remote job was used.

| Control | Observed result |
| --- | --- |
| Small output | The fixed child wrote 4096 bytes and exited 0. |
| Aggregate overrun | After stdout filled the shared 16384-byte file, one more byte on stderr caused kernel SIGXFSZ (25). Captured output remained 16384 bytes. |
| Bounded synthetic scoring | The hash-pinned RMSE child returned 1.0 for internally generated 64-value vectors. Its 78-byte result was below the limit. |

The new standalone `private_container_worker.py` is included in the package.
It runs only the existing hash-pinned RMSE worker or fixed public output probes.
Both child output descriptors refer to the same temporary regular file. A hard
RLIMIT_FSIZE limits their aggregate storage. The child clears its environment,
uses null stdin and closes extra descriptors. A hit at the boundary discards the
response even if its prefix parses as JSON. The parent exports bounded metadata
and the successful score, never truncated child bytes or an exception. The
temporary file remains inside the trusted scorer and is closed after collection.

This is a fixed trusted scorer boundary. It is not a sandbox for arbitrary
generated code or a hard quota on Docker's stdout stream. The container retains
the previously checked 64 MiB memory, zero swap, one CPU, 16 PIDs, no network,
read-only root, owned read-only source stage and 4 MiB tmpfs. Its watchdog and
probe alarm remain bounded at ten seconds. The wrapper does not itself qualify
those outer controls, grant label access or register a production scorer.

The driver, probe, output wrapper and RMSE source hashes used for execution are
retained. Original intents, source stage, inspections, outputs and cleanup
receipts are archived. All 66 raw files passed offline verification after
relocation. The separately retained execution-manifest SHA-256 is:

```text
263e4cac0493286449c36c08168ff4c6735c739c169935186ad6d1d0c1f82405
```

Use the project Python interpreter with
`scripts/verify_utility_local_runtime_archive.py ARCHIVE --kind output --manifest-sha256 DIGEST`.
Keep the trusted companion driver beside the reader. Archived Python is only
hashed. The reader checks source/image/nonce bindings, resource settings,
bounded-output observations and cleanup receipts without executing code from the
archive or contacting Docker. It does not independently prove daemon assertions
or current live container absence.

The final output/probe/driver/archive/documentation suite passed 112 tests in
1.95 seconds. Ruff passed. A wheel built offline without dependency installation.
All 196 core Python files matched current source bytes, and the extracted-wheel
wrapper passed small-output, overrun and authored-score checks from an isolated
directory. The first `python -m build` attempt found the local build namespace
without a `__main__`. The subsequent isolated pip wheel command succeeded. Both
logs are retained. The packaging checks are local POSIX evidence. Actual Linux
enforcement is established by the separate three container controls.

Private scoring remains unqualified. Production integration/admission, independent
task custody and the frozen confirmation protocol remain outstanding. This local
ARM64 evidence does not establish Linux x86-64 support, scientific utility,
complete cost accounting or independent hardware confirmation. Earlier broad
test checkpoints retain their original source scope.
