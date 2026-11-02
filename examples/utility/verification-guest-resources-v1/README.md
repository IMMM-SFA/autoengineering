# Local candidate resource diagnostics

Six actual resource controls passed against the built Linux amd64 image on the
local ARM64 OrbStack host. Each case created and started one container. Its
original terminal state and subsequent absence were recorded. No model, fitting,
scientific labels, score, provider, image pull or host mount was used.

| Control | Observed result |
| --- | --- |
| Memory | Daemon `OOMKilled=true`, exit 137, after guarded readiness |
| Processes | `EAGAIN`, cgroup count 16, 15 authored children reaped |
| Workspace | `ENOSPC` after 134,217,728 bytes on the 128 MiB tmpfs |
| Root filesystem | `EROFS` in a world-writable directory |
| Network | Only loopback, one connect attempt returning `ENETUNREACH` |
| Host canary | Fresh authored host file absent inside the guest, `ENOENT` |

All workers first checked the actual CPython build, isolated interpreter,
UID/GID 1000, 1 GiB memory, zero swap, PID limit 16, CPU quota, capability removal,
no-new-privileges, seccomp, root mount and workspace. Each case reserved 60 active
seconds and one ten-second cleanup window. A separate owner-pipe process was
ready before creation and owned cleanup. These successful cases closed the pipe
normally. They do not qualify unexpected owner loss, cancellation or deadlines.

[Completion](complete.json), [observations](runtime-observations.json), individual
output logs and [summary](summary.json) retain the results. Completion digest:
`f5395216c48d94a2ada8f5090467178b2f3471d3026197c63e9412f12aa5c103`.
The request and exact executed source snapshots are preserved separately from
the later reader. Machine bindings and the host canary path stay in ignored local
proofs. Public observations include original terminal hashes, not full replay
inputs. The canary's bytes were never read inside the guest.

The preceding v1 request created one container and refused before start because
Docker inherited three unused public base-image environment variables. Cleanup
refused for the same reason. That original cleanup remains unknown in its record.
A separately recorded administrative action verified the exact original CID,
unstarted state, fixed command, owner labels and image environment, then removed
it and observed absence. No uncertain DELETE was repeated. V2 explicitly clears
the inherited variables. Their `PYTHON_VERSION` value described the base image,
not the observed inference interpreter. No scientific criterion changed.
The v1 producer snapshots were reconstructed after correction and matched all
three source hashes in the original request.

Across both versions: seven creations, six starts, zero scientific starts. Both
requests remain consumed. The original 26-case proposal is unchanged and has not
run as a whole. These separately identified diagnostics must not erase the failed
creation or silently expand that proposal's 20-create/15-start reservation.

The saved reader verifies the six original requests, source hashes, projected
policies, ready output, terminal states, start/cleanup intents and completions.
A fresh process replayed 108 relocated metadata files, 403,086 bytes, with outside
file-content reads, writes, imports, processes, sockets and clocks denied after
initialization. Dependencies were inherited. See [reader](cold-resource-reader.py.txt),
[output](cold-reader.log) and [scope](cold-reader.json). This is source-based replay,
not installed-package qualification or independent OS attestation.

From the checkout, verification of retained local proofs is:

```sh
pixi run python -m examples.utility.guest_resource_reader outputs/guest-resources-v2 \
  --expected-digest f5395216c48d94a2ada8f5090467178b2f3471d3026197c63e9412f12aa5c103
```

The 1 GiB policy remains an unqualified candidate. Six preflight controls,
fourteen inference/lifecycle handlers, full inference/scoring qualification and
independent task admission remain open. The production inference environment
projection also needs an explicit treatment of inherited image variables before
its actual controls. This diagnostic change does not alter that frozen core or
the built wheel/image.

The final related regression passed 254 tests with no failures, errors or skips.
It includes the 114 diagnostic/proof checks plus identity, build, daemon,
interpreter and documentation checks. Repository Ruff checks passed. See
[JUnit](final.xml), [output](final.log) and [command](final-command.json).
The full default checkpoint predates these example/helper additions and was not
rerun for this increment.
