# Local synthetic lifecycle controls

Four approved synthetic controls ran serially using the cached pinned ARM64
image. All original containers were running when the independent watchdog
removed them. Subsequent live API queries returned HTTP 404 for each exact ID.
No image pull, private input, provider call or remote job was used.

| Fault | Observed result |
| --- | --- |
| Deadline | The independent five-second watchdog removed the running container before the probe's ten-second alarm. The owner remained alive for reconciliation. |
| Cancellation | The synthetic owning controller received SIGTERM and exited -15. Its independent watchdog observed pipe EOF and removed the running container. |
| Owner loss | The synthetic owning controller received SIGKILL and exited -9. Its finally block could not run. The independent watchdog observed pipe EOF and removed the running container. |
| Lost start acknowledgement | One real start request was made. Its response was deliberately withheld from the controller's success check. The running witness and original ID were reconciled, then lease EOF removed that original container. No start or create retry occurred. |

The lost acknowledgement is an injected response-delivery fault. It does not
establish behavior under a real transport outage or lost create acknowledgement.
These tests concern the local macOS owner and OrbStack Linux ARM64 container.
They do not qualify Linux x86-64, another daemon, or independent hardware.

The container retained the original isolation and caps: nonroot UID/GID 65534,
64 MiB memory, zero swap, one CPU, 16 PIDs, no network, read-only root, dropped
capabilities, no-new-privileges, one owned read-only stage and a 4 MiB tmpfs.
The watchdog used a five-second bound for these hold probes. The probe's own
ten-second alarm remained a backup. This is no claim about whole-host memory
or wall time spent creating containers and collecting evidence.

Each run preserves its executed controller, staged sources, create/start intents,
original running witness, fault intent, before-removal inspection, cleanup receipt,
owner exit and live reconciliation. An expected owner exit of 2 for the deadline
and lost-ack cases means that the ordinary success summary refused qualification.
Their separate fault reconciliation proves the expected synthetic lifecycle
outcome. Terminated owners have no ordinary summary. No record is relabelled as
a successful private scoring attempt.

The offline reader verified all 88 execution files after relocation. It requires
the separately retained manifest SHA-256:

```text
3c1c1255a20a261122fe1e0cb9c9076d050690e17729ed85f87881f66e519765
```

Run the project Python interpreter with
`scripts/verify_utility_local_runtime_archive.py ARCHIVE --kind lifecycle --manifest-sha256 DIGEST`.
The trusted companion driver must remain beside the reader. Archived Python is
hashed as data. Original stage paths are identity metadata and are not opened.
Offline verification checks saved evidence and makes no daemon query or process
start. It cannot establish current live absence or independently prove a daemon
assertion. A hash manifest must be anchored outside an untrusted archive.

The final driver/probe/archive/documentation suite passed 87 tests in 1.48 seconds.
Socket and process starts were denied during offline-reader tests. Rehashed
changes to owner exits, IDs, cleanup reasons, running state, retry count and fault
witnesses were refused. One initial unit fixture lacked an API-version field.
Its failure is retained and was corrected before live dispatch. Ruff passed.

Private scoring remains unqualified. Network and host-path negative controls,
adversarial output enforcement, production integration, independent task custody
and the frozen protocol remain outstanding. No scientific utility or total-cost
claim follows from these synthetic controls. Earlier broad test checkpoints keep
their original source scope.
