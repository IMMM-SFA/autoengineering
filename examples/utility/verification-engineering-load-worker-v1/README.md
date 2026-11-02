# Coupled-load worker development check

The new [fixed worker](../engineering_load_worker.py) binds raw input bytes by
SHA-256 before model imports or execution. It accepts exactly 24 cases and the
fixed circuit policy. The packet cannot select executable code or filesystem
paths. Its source-binding digest is an identity field, not proof of a valid grant
or authorization to open a source.

The worker calls the existing coupled OpenMDAO kernel. It exports only the score
and aggregate work counts. Private receipts remain in the supplied private work
root. A POSIX child shares one regular file for stdout and stderr, with a hard
16 KiB file-size limit. Exceptions, native diagnostic text, unapproved JSON and
truncated output yield no public result. Receipt reads reject symlinks, FIFOs,
oversized files and mismatched execution identities.

Final interoperability checks passed 36 tests. Base, kernel and documentation
checks passed 68 tests with one expected optional skip before the final test added
output archival. The final authored model check completed 24 solves, 360 solver
iterations, 5,880 component calls and 1,800 component linearizations. The aggregate
source power was 0.27174569156641054 W. These are exposed development cases.
An earlier successful 24-case check is also charged in this increment's summary.
There were no new container starts. The v14 guest register retains its existing
scope and counts. The archived per-case files are public authored test evidence,
not part of the production worker's output protocol.

The manifest binds source snapshots, test output and the final model receipts.
`verify.py.txt` checks saved bytes and arithmetic without importing models.
It does not independently attest to process isolation or reconstruct the initial
test's missing wrapper receipt. Supply the manifest hash held by the caller.

The worker has no standalone registered container entrypoint yet. Trusted source
and work paths, packet pinning and outer deadlines belong to the future runtime.
Sealed-source access, versioned execution/cost registration, Linux worker checks,
owner-loss cleanup and resource qualification remain open. The frozen v6 wheel
and dependency image do not contain this worker. Private admission and task
admission remain false.
