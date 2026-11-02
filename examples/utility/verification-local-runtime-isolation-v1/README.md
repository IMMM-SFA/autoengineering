# Local synthetic isolation control

One approved synthetic isolation control ran on the cached pinned OrbStack Linux
ARM64 image. The original container exited 0, its nonce-bound checks passed, and
the independent watchdog removed it. The host controller confirmed HTTP 404 for
that exact original ID. No image pull, private confirmation input, provider call
or remote job was used.

The host created and read a public canary outside the container mount. The probe
read its matching mounted copy. It could not open the original host path or reach
the sibling canary through parent traversal. Root and source-stage writes failed.
A temporary canary could be written and read in the bounded tmpfs. These checks
used owned public paths. They did not probe a real home, credential or label file.

A local TCP loopback exchange succeeded. A connection to the documentation-only
address 192.0.2.1:9 failed with Linux ENETUNREACH. The probe also observed only the
loopback interface. The host inspected the exact original container's none network
mode, dropped capabilities, nonroot identity, read-only root and mounts. This is
evidence about that namespace and address. It is not an external-service reachability
survey, an attack against Docker, or a proof against kernel/daemon compromise.

The control retained 64 MiB memory, zero swap, one CPU, 16 PIDs, the ten-second
watchdog and alarm, no-new-privileges, one owned read-only stage and a 4 MiB tmpfs.
Its executed driver and probe bytes are preserved with original intents,
inspection/output/cleanup receipts, host positive control and public canary.
The driver's historical `remaining` list is not aggregate qualification status.
This increment's summary records the current remaining work.

The offline reader verified all 25 raw files after relocation. Its required
separately retained execution-manifest SHA-256 is:

```text
05f47329263976ac54d2b5e2212f138b38a4e22265505d1570835d5187e66032
```

Use the project Python interpreter with
`scripts/verify_utility_local_runtime_archive.py ARCHIVE --kind isolation --manifest-sha256 DIGEST`.
Keep the trusted companion driver beside the reader. Archived Python is only
hashed. The reader checks saved identity, resource/isolation settings, public
canary, positive and negative results, source bindings and cleanup receipts.
It does not open original host paths, start processes or query a live daemon.
It cannot establish current live absence or independently prove daemon assertions.

The final probe/driver/archive/private-access/documentation suite passed 115 tests
in 3.95 seconds. The earlier sandbox run passed 109 and failed six authored
private-scoring process checks because `ps` was forbidden. That log is preserved.
The full focused retry passed after permission for owned-process inspection.
No container was started by those tests. Rehashed changes to positive/negative
control results and missing host-positive evidence were refused. Ruff passed.

Private scoring remains unqualified. Adversarial output enforcement, production
integration, independent task custody and the frozen protocol remain outstanding.
This local ARM64 evidence does not qualify Linux x86-64 or establish scientific
utility, complete cost accounting, or independent hardware confirmation.
