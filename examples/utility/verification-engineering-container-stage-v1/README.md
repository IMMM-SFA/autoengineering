# Coupled engineering container dependency stage

Seven exact pure-Python wheels were acquired from PyPI and checksum verified.
Versions match the existing native development environment. Metadata checks
covered their Linux Python 3.12 requirements against the frozen base. The
[OpenMDAO 3.41.0 release](https://pypi.org/project/openmdao/3.41.0/) supplies the
published wheel hash. Other source URLs, versions, requirements and hashes are
in [the pinned plan](dependencies/download-plan.json). Acquisition used seven
metadata GETs and seven archive GETs, totaling 14,243,480 archive bytes. No
resolver, install, model or private-data action ran during acquisition.

One local dependency overlay built from the exact existing v6 image. No pull
command ran. Build steps had networking disabled. Seven cached dependency wheels
were installed, and trusted model source/lock bytes were copied into the image.
The base project wheel stayed unchanged. The build requested one CPU and 2 GiB,
with a 600-second client deadline. Disk quota and daemon-side cancellation are
unqualified. BuildKit internals are excluded from runtime container counts.

Image: `sha256:39fb6f877a99e384ec2af08363a598ea23fd6ef7ec3bae076e0ab1ffe99508b0`.
Environment digest: `24be3793c90641a2de10966c8cd3af0be3e1f04f0f2d1e52d6751d45ccabf0ce`.
This is a new coupled-model environment candidate, separate from the frozen
routing image and its catalogue. No older image controls were transferred.

One isolated Linux amd64 container evaluated 24 previously exposed authored
cases at the current selected by the earlier macOS native control. All 24 source
powers and node voltages matched the reference exactly in this observation.
The frozen comparison tolerances were `atol=1e-10`, `rtol=1e-12`. Every case passed
the strict `0.66 V` requirement, convergence and `1e-10 A` residual checks.
No fitting, optimization, scoring or private-source read occurred in this control.
The container observed UID/GID 1000, read-only root, no network, no capabilities,
seccomp, 1 GiB memory, 16 PIDs, one CPU and a 128 MiB private tmpfs. This is local
ARM64-hosted Linux emulation, not independent physical x86 hardware.

The model and CLI returned success. The original controller then exited nonzero
because it incorrectly parsed an empty DELETE response as JSON. A separate GET
confirmed the exact original CID absent. Saved outputs and ownership were verified
without another DELETE, container or model start. The failed original attempt,
delete intent and read-only reconciliation remain distinct. This was not a clean
single controller pass. The consumed request cannot be retried.

An initial preparation used the base environment, which lacked optional OpenMDAO
version metadata, and refused before creating a request or contacting a daemon.
A separate scope prepared successfully in the existing optional environment.
The empty original scope remains. The first cold reader also refused a transitive
NumPy import before replay. The final reader uses only the standard library.

The compact [manifest](evidence-manifest.json) binds 87 original receipt/source
files across dependency, image and probe scopes. Wheel archives and the 74 MB
client plugin remain in ignored local caches and are not redistributed here.
Original cached wheel hashes were rechecked before handoff. The relocated reader
verifies recorded metadata/provenance consistency and recomputes public numerical
comparisons. It does not independently attest the OS or recompute model physics.

The final reader requires an explicit caller-held manifest hash. Model imports
are blocked from startup. After initialization, guards deny processes, sockets,
clocks, writes, new imports and outside file reads. It passed after relocation,
and rejected altered cleanup semantics even when the test copy's file manifest
was intentionally updated. Reader failures and corrected versions are retained.

```sh
python -I -B cold-reader-v3.py.txt PATH_TO_EVIDENCE \
  d49722c1af53c1cf8598c0dc36eab738b89ecfedb0f86c42fe936f011978f0e9
```

This stage supplies a compatible dependency image and a public coupled-model
control. It has no fixed private packet worker, sealed-source access in the
container, protected callback integration or complete resource/interruption
matrix. Private/runtime admission, actual comparative utility and independent
task admission remain open. No proposed final source was opened.

The cumulative explicit runtime register now retains 50 creations and 39 starts.
The known fixed-model forward-start lower bound is 33, including these 24 coupled
evaluations nested in one container. Total work remains unknown. Earlier 15
inference grants, two scoring grants, two native references, six starts without
model results and unknown label quantities are preserved. These units overlap
and must not be summed as independent totals.

Documentation passed 19 tests. Ruff, whitespace and original public-file hash
checks passed. Runtime code did not change, and the full default suite was not
rerun. All 316 frozen v6 code sources still align. See
[final checks](final-checks.json) and the
[source inventory](../source-inventory-engineering-container-stage-v1.json).
