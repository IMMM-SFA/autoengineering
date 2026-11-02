# Successor inference environment inputs with guest transport sources

Status: prepared inputs only. This successor binds the new 212-core-file wheel,
including the candidate v2 guest job and worker preflight. It preserves 302 wheel
Python-source hashes and the same 49 Linux x86-64 archive pins totaling 265,399,717
compressed bytes. No archive was acquired and no image was built or installed.
The original v1 input package and its digest remain unchanged.

The v2 job pins environment, wheel/source, image, interpreter/build and proposed
resource identities. Its scope uses grant/executor/nonce identities rather than
host directory names. The worker checks observed Linux x86-64 CPython identity,
pinned environment metadata and installed source bytes before model/driver access.
The profile remains an unqualified candidate. Authored observations in tests are
not actual Linux or image qualification.

An actual image identity, qualified owner-side launcher, one-claim/start/stop proof,
guest execution receipt/archive and full OS/resource controls remain open. The
worker cannot independently attest an OCI image ID or enforce the proposed limits.
Old local supervisor archives explicitly refuse guest jobs. No default executor,
confirmation service, CLI or private runtime registration activates the guest type.

The old wheel lacks the guest module and cannot be silently adopted as this
runtime. Any qualified image/runtime/metadata change needs a new immutable identity.
The image identity is still absent in review.json; starts_authorized and
runtime_qualified remain false. Limits remain proposals and independent data stays
unadmitted.

See [manifest](manifest.json), [review](review.json),
[lineage and wheel evidence](../verification-inference-guest-v1/prepared-inputs.json),
[the predecessor](../prepared-inference-environment-v1/README.md) and
[the implementation audit](../../../docs/reviews/part-5-completion-audit.md).
