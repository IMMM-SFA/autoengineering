# Current v6 owner and watchdog process loss

Four actual local controls passed against the current v6 image using its existing
exposed authored fit. Four containers were created and two started. All original
containers were confirmed absent, including separate actual GETs after cleanup.
Three exact owned owner processes were killed with SIGKILL. A fourth owner killed
its own exact ready watchdog handle, then exited normally after production
liveness checking refused START. Only owned Popen handles were signaled.

| Control | Observed outcome |
| --- | --- |
| Before watchdog readiness | Owner killed after saving the watchdog plan, before spawn. Explicit parent startup cleanup removed the unstarted guest. |
| Running owner | Owner killed after actual START, before input transfer. Detached watchdog observed owner loss and cleaned the original guest. |
| After capture | Owner killed after result capture, before the stop journal. Watchdog cleaned the original guest. Saved recovery returned that successful result without rerunning it. |
| Ready watchdog child | Owner killed its own watchdog after attach, before START. Liveness checking refused START. Startup cleanup removed the unstarted original guest. |

Both starts remain charged and lifecycle time remains unknown. One captured
model result is known. Work in the other started guest remains unknown. No new
fit, score, private observation or provider call was used. Every case refused
redispatch without contacting the daemon. Parent composite reservations remain
charged and unfinished. These cases do not establish interruption during model
computation or autonomous cleanup before watchdog ownership.

The [351-file public archive](public-proof.tar.gz) contains original process,
owner, API, input-transfer and cleanup records, plus a saved public suite for
captured-result recovery. Input-transfer tars include declared source, fit
metadata and known exposed meteorological drivers. Fitting/comparison and private
label arrays are absent. The [manifest](evidence-manifest.json) binds every regular
file's size and hash. Source and driver roots are unnecessary for saved replay.

A fresh process verified the extracted archive after relocation. Model imports
were blocked from startup. Imports and metadata initialization preceded guards
that denied processes, sockets, arrays, clocks, writes and outside content reads.
The captured result replayed through the production recovery-only facade. This
verifies saved producer evidence, not independent OS attestation. Dependencies
and example helpers were inherited before the guard.

A separate altered proof with the wrong owner PID was rejected. The original
proof hashes remained unchanged. Read-only process-table checks found all three
recorded watchdog PIDs absent. Their first diagnostic referenced the wrong JSON
field before running ps. That refusal and the corrected diagnostic are retained.
No control or guest was restarted.

Request digest:
`608f49736fd42cb82a02ce618d2e31be516f2eaf37ce3fcda1bc065a51b01911`.
Completion digest:
`994ab5b042da691d65e5a1f81e7105e97a26e67f0a4a93763068f270466bc311`.

```sh
pixi run python -m examples.utility.guest_owner_loss_reader PATH_TO_PROOF \
  --expected-digest 994ab5b042da691d65e5a1f81e7105e97a26e67f0a4a93763068f270466bc311
```

The related regression passed 73 tests in 92.86 seconds. No runtime source
changed. This host is local OrbStack Linux amd64 emulation on macOS ARM64.
Independent physical x86 qualification, private scoring, the full matrix and
scientific task admission remain open. Runtime qualification remains false.
The original 26-case proposal and all earlier evidence remain unchanged.

Cumulative explicit runtime accounting now records 47 creations and 36 starts,
including 14 charged inference starts and two native references. The known model
inference lower bound is eight; total model work remains unknown. Six started
attempts have no observed model result. Earlier unknown label quantities remain
unknown. BuildKit internals and authored unit fixtures remain outside this scope.

Documentation passed 19 tests. Ruff and whitespace checks passed. All 316
declared v6 code sources still align. The source inventory and original proof
hashes verified. Full default tests were not rerun for this evidence-only
increment. See [final checks](final-checks.json).
