# Lifecycle controls on the frozen recovery source

Eleven approved local synthetic controls exercised the unchanged runtime source
c7a4b87a3dd54a5eaa880244815f14d7dcfeeb4c27543400d90a8d79c306d3cd.
This is the source with the 680-pass/26-skip utility regression and actual
success/recovery evidence in verification-container-recovery-chain-v1. No core
code, test, dependency or resource policy changed during this increment. All 199
core files still matched the existing wheel, which was reused.

| Controls | Created objects | Container starts | Original cleanup |
| --- | --- | --- | --- |
| SIGTERM/SIGKILL before create acknowledgement delivery | 2 | 0 | Fresh metadata-only observer removed original ID after all job/label copies were deleted. |
| SIGTERM/SIGKILL before owner-pipe creation | 2 | 0 | Fresh metadata-only observer removed original ID after all job/label copies were deleted. |
| SIGTERM/SIGKILL after watchdog arming, before start delivery | 2 | 0 | Automatic owner_pipe_eof cleanup. Recorded start requests were not forwarded. |
| Running paused container: SIGTERM, SIGKILL, lost start acknowledgement | 3 | 3 | Automatic owner_pipe_eof cleanup. |
| Running paused container with start response delivery held | 1 | 1 | Automatic independent watchdog deadline cleanup. |
| Running paused container with normal start response delivery | 1 | 1 | Runtime eight-second poll timeout; automatic owner_pipe_eof cleanup. |

All eleven exact original IDs were removed and observed absent through HTTP 404.
The running controls and two armed controls needed no observer deletion. No
replacement attempt or accepted scientific result occurred. Scoring-child starts
remain unknown for the five started containers. A running PID and controlled pause
do not establish which phase of scoring computation was interrupted.

The controls used the existing cached image, 64 MiB RAM, no swap, one CPU, 16 PIDs,
no network, a read-only root/stage and the fixed bounded worker. The five running
controls reused authored 100,000-element vectors under the one-MiB input-file
limit, then deleted all job/label copies. The six creation controls used two-element
vectors and started no workload. No real confirmation data, image pull, provider
call or remote job was used.

The existing passive verifiers checked all 233 files after relocation with socket
creation, subprocesses and daemon calls denied. Required separately retained
execution-manifest SHA-256 values are:

| Archive | Files | SHA-256 |
| --- | --- | --- |
| creation | 120 | fe870f9fa6899778a623429716db38d0a08f4c236bef47aa2955a69d8e048b81 |
| running | 90 | 9de933907ce1e1010a0183ae35e17a262e34515118a73cc2d8ee7d04330e0d02 |
| running/execution-timeout | 23 | 285f7809050f5645988534427c9139a0bb00c8f1244cfafb2e33ca415c62030a |

Use scripts/verify_utility_creation_owner_archive.py for creation and
scripts/verify_utility_running_archive.py for running. Supply ARCHIVE and
--manifest-sha256 DIGEST. Add --execution-timeout-only for the timeout archive.
Keep their trusted companion scripts available. Archived source is hashed as
data and never executed by these readers. Saved evidence consistency does not
independently attest the daemon or establish current live absence at replay.

The focused archive/recovery-chain/runtime suite passed 71 tests in 0.62 seconds.
Ruff passed. The earlier complete utility regression remains applicable to the
unchanged core/tests and retains its recorded source inventory. It was not rerun.
Earlier controls remain intact, with their own IDs, source hashes and scopes.

Current-source creator/running lifecycle coverage no longer depends on earlier
runtime hashes. This does not complete resource, privacy or every failure-path
qualification. Linux x86-64 and independent hardware remain unverified. Independent
task custody, thresholds, complete measured costs and the frozen scientific
protocol are still missing. Part 5 remains incomplete and private scoring remains
unqualified.
