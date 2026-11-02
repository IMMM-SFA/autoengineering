# Authored guest OCI observation checks

This increment supplies a fixed candidate OCI create request and validates saved
image, creation, start, stop and cleanup documents before projecting guest receipts.
It performs no daemon operations. Captures in this directory are authored fixtures,
not observations of an actual container. Hashes identify saved claims and cannot
independently attest OS enforcement or provenance.

The focused command was:

```sh
PATH="$PWD/.pixi/envs/default/bin:$PATH" .pixi/envs/default/bin/python -m pytest \
  tests/test_utility_guest_observations.py -q -p no:cacheprovider
```

The first sandboxed fixture stopped with scientific work uncertain before any new
observation test could run. Its 67 setup errors remain in focused.log. A fresh
fixture run with owned-process supervision passed 72 cases in 9.44 seconds, recorded
in focused-owned-process.log. It did not retry or reconcile the original charged
scientific attempt. Five timestamp/terminal-state cases were added before the
successful run. The shared fixture runs an ordinary authored development baseline;
no guest model executes in these checks.

The positive fixture links canonical raw-document hashes to guest start/stop/cleanup
records and verifies the resulting archive. Projection and cold archive reading
run with subprocesses, sockets and monotonic clock sampling denied. Unknown elapsed
time remains null. The refusal cases cover changed image/platform/provenance,
command, environment, owner binding, mounts, capabilities, resources, namespaces,
restarts, lifecycle states/times and cleanup. Failed lifecycle outcomes never supply
a scoring vector. Fixed policy tests check the requested command and resource and
isolation values explicitly.

The source snapshots and tested-source-pins.json identify the code checked here.
The broader regression, documentation checks and artifact pins are recorded in
summary.json when terminal. This increment postdates the full default checkpoint.
No default executor or confirmation service activates the candidate guest path.
Actual image assembly, enforced runtime/privacy controls, independent task admission,
owner-approved gains and tolerances, and the scientific matrix remain open.

The related regression passed 208 cases in 125.25 seconds. Documentation passed
19 cases in 0.67 seconds. An explicit line-length check found one long tmpfs
string; splitting adjacent string literals preserved its value. The final guest
observation/archive check then passed 124 cases in 13.87 seconds. The initial
source snapshots/pins remain alongside the final formatted source snapshot/pins.

The public tar contains 23 files. replay-public.py.txt reconstructs the raw
observations and archived projections after relocation with subprocesses, sockets
and clock sampling denied. Its first attempt refused the system temporary path's
symlink component. The corrected harness resolves the owned temporary directory
before extraction. Both scripts/logs remain. No artifact path check was weakened,
and the successful replay created no scientific attempt.
