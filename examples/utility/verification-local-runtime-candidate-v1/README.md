# Cached local protected-runtime candidate

Read-only inspection found a running local OrbStack Linux ARM64 engine with
cgroup v2 and a cached Python 3.12 image. The exact image ID, worker hash, observed
feature flags and proposed qualification limits are in candidate.json. The fixed
RMSE worker uses only the standard library, so this candidate needs no new package
installation or image pull for an initial synthetic check.

This is a reviewable candidate, not a qualified scoring profile. Engine flags do
not establish memory/CPU/PID enforcement. ARM64 does not satisfy the separate
Linux x86-64 gate. A container can outlive a killed Docker CLI, so owner-loss and
lost-acknowledgement proof must cover the actual container identity and daemon.
No private scoring can be admitted from this metadata inspection.

The proposed qualification is serial and synthetic only: 64 MiB memory, no swap,
one CPU, 16 PIDs, 10-second wall limit and 16 KiB output. It must use the cached
image by immutable ID with pull disabled, no network, a read-only root, no added
capabilities and no new privileges. Only an owned synthetic stage may be mounted.
The Docker socket, host home, credentials and private data must not be mounted.
The full controls and required refusal/recovery cases are listed in candidate.json.
Those controls have not run and may reveal that the candidate is unsuitable.

No container started, image pulled, private data read, provider contacted or remote
host used. An initial sandboxed metadata query was denied socket access. The same
read-only local query passed with the explicit sandbox exception. This was not an
automatic approval-review rejection or an execution qualification.

Both existing full regression results remain separate and unchanged: base 2309
passed/109 skipped, Bayes 2365 passed/57 skipped/44 warnings. This candidate adds
no scientific observations. Data custody, runtime choice, admitted task contracts
and a frozen authorized protocol are still required for the complete Part 5 goal.


The synthetic probe source and unit evidence are now available in
verification-local-runtime-probe-v1. This prepares four control modes but does not
start a container or select this runtime. Its observations never grant admission.
