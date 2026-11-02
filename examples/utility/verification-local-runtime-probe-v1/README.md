# Synthetic container probe preparation

The standalone script scripts/utility_container_probe.py prepares four controls:
preflight, a small allocation, a deliberate memory overrun and fixed synthetic
RMSE scoring. It does not start Docker, install anything, accept a private input
path or register an admitted scoring profile. Every completed control explicitly
reports qualified=false. The runtime choice remains pending.

Before work, the real CLI requires Linux, UID/GID 65534, exactly 64 MiB memory,
zero swap, one CPU and 16 PIDs in cgroup v2. All five capability sets must be zero,
no-new-privileges must be set, the root must be read only, /tmp must be a bounded
4 MiB tmpfs with noexec/nosuid/nodev, and only loopback may appear as an interface.
These observations are not a full network or mount-isolation attestation.

Scope metadata has an exact canonical nonce binding. Worker bytes must match the
fixed private_score_worker.py hash. The probe hashes and executes the same bytes.
Scoring creates a fresh owned temporary directory with internally authored inputs
of length 64 and expected RMSE 1.0. It never opens caller-supplied labels. Input
reads refuse symlinks/nonregular files and are bounded and nonblocking. Memory
controls touch allocated pages. Surviving an overrun is an explicit failure.

The ten-second alarm bounds the control body after preflight and stage checks.
It is not a daemon or parent-loss watchdog and does not cover preflight setup.
The eventual caller must enforce a whole-container deadline and verify image,
command, mounts, user, flags, identity/nonce and original OOM/stop evidence.
Killing only the Docker CLI does not establish container termination. Those
controls remain unimplemented/unexecuted pending runtime selection.

Focused checks passed 45 tests with two expected skips in 1.18 seconds. Linux
guard tests use authored proc/cgroup files. They cover unbounded/loosened caps,
all five capability sets, unsafe privilege/mount/network observations, bad scope,
changed worker bytes, bounded reads, synthetic worker reuse and refusal before
allocation. They do not establish real Linux enforcement. An actual Mac CLI call
to memory-overrun returned refused/qualified=false with exit 2 before allocation.

The initial related path-denial test failed because the sandbox denied ps. The
same group passed with the owned process-inspection exception. Initial failure
and intermediate 40-pass logs/XML remain. Ruff passed for src/tests/examples and
the new script. Final sources and hashes are retained here.

No container started, image pulled, private input read, provider contacted or
remote job ran. Earlier full base/Bayes results retain their original scope and
do not silently cover this new script/test. ARM64 candidate metadata does not
establish Linux x86-64 qualification. Data custody, runtime choice, admitted task
contracts and the frozen independent protocol remain unresolved. Part 5 is not
complete.
