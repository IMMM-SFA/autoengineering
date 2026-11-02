# Prepared Linux inference environment inputs

Status: prepared inputs only. The manifest binds the existing default Linux x86-64
lock selection, the preserved pure Python wheel, all 300 wheel Python-source
hashes and the preparer source digest. The runtime closure contains 49 conda-forge
archives totaling 265,399,717 compressed bytes. Archive bytes were not acquired.
Uncompressed environment size remains unknown. License text is copied metadata
from the lock; third-party archive content is not included.

The preparer follows dependency names within the already resolved lock selection.
It does not solve a new environment or independently recheck version constraints.
Python remains 3.12. The lock's Linux 4.18, glibc 2.28 and x86-64 assumptions are
retained alongside individual virtual dependency constraints. Source and wheel
bytes are SHA-256 bound. The original wheel filename is preserved.

The package is written to a fresh owner-private directory, manifest last. Repeating
preparation into an existing or interrupted directory refuses. The verifier needs
an explicit expected manifest digest and reconstructs the closure from the saved
lock/wheel. It imports no wheel code, extracts nothing and performs no acquisition,
installation or execution. A metadata record cannot authorize starts or claim
runtime qualification.

Review.json proposes 1 GiB memory, one CPU, 16 pids, a 128 MiB workspace, no network,
a read-only root and a 60-second maximum model timeout. No such boundary has been
executed or qualified. The base image identity, assembly procedure, actual resource
limits and failure controls remain open. The current fixed scorer admits ARM64;
this package targets Linux x86-64 and needs separate compatibility evidence.

The existing v1 inference job also binds its identity to the host interpreter and
workspace. A versioned guest transport/execution contract is required before these
inputs can serve that worker in a container. No image or private scorer is
registered by this package. Independent data and scientific execution remain
unadmitted. Use a successor package for any changed input or policy.

See [manifest](manifest.json), [review](review.json),
[verification](../verification-inference-environment-v1/summary.json) and
[the preparer](../inference_environment.py). Verification uses the manifest digest
from the reviewed source inventory as expected_digest, not a digest read from an
untrusted replacement manifest.

The exact producer bytes are preserved in
[preparer-source.py.txt](../verification-inference-environment-v1/preparer-source.py.txt).
A later strict JSON-type reader check continues to verify this original manifest.
The current source link above therefore need not have the same digest as the
original producer. The input package and its expected digest remain unchanged.
